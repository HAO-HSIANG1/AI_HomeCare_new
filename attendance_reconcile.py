"""執行對照：排班（最終班表）vs 實際打卡。

逐筆服務對上手機打卡紀錄（checkin.store.punch_frame()，以任務ID 對應），列出：
漏打卡（整筆沒打、漏打上班、漏打下班）、未遇、遲到、早退、補登待覆核、換人打卡、排外打卡，以及位置提醒。

- 只用 ID 運算（任務ID、案家ID、居服員ID）；姓名由 app.py 的 show_table／export_frame 依遮罩設定顯示。
- 容許分鐘與距離都來自 PipelineConfig（attendance_*）。
- 位置提醒只是提醒：GPS 有誤差、也可能被偽造，不當懲處依據，所以不算進「異常」，嚴重度標「提醒」。
純函式，不 import streamlit。
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta

import pandas as pd

from checkin.store import (CLOCK_IN, CLOCK_OUT, MISSED, REVIEW_PENDING, REVIEW_REJECTED, UNASSIGNED, distance_m,
                           effective_punches)

CAREFLOW_BUILD = '2026.10.18-v19'

STATUS_OK = '正常'
STATUS_NOT_YET = '尚未結束'
NO_RECORD, NO_IN, NO_OUT = '漏打卡（整筆沒打）', '漏打上班', '漏打下班'
LATE, EARLY, PENDING, SWAPPED, EXTRA, FAR = '遲到', '早退', '補登待覆核', '換人打卡', '排外打卡', '位置提醒'
MISSING_FLAGS = (NO_RECORD, NO_IN, NO_OUT)

# 依序取第一個當「狀態」；嚴重度給居督排序處理
FLAG_ORDER = [NO_RECORD, MISSED, NO_IN, NO_OUT, EXTRA, SWAPPED, LATE, EARLY, PENDING, FAR]
SEVERITY = {NO_RECORD: '高', MISSED: '高', NO_IN: '中', NO_OUT: '中', EXTRA: '中', SWAPPED: '中',
            LATE: '低', EARLY: '低', PENDING: '低', FAR: '提醒'}
ADVICE = {
    NO_RECORD: '聯絡居服員確認是否到班；沒到請安排代班並通知案家，忘了打卡請用手機「補登」。',
    MISSED: '確認案家安全與去向（必要時聯絡家屬），依機構規定登錄未遇。',
    NO_IN: '請居服員用手機「補登」上班時間，再到 04 頁覆核。',
    NO_OUT: '請居服員用手機「補登」下班時間，再到 04 頁覆核。',
    EXTRA: '班表沒有這筆（或已改派）：確認是否臨時代班，必要時重新發布班表。',
    SWAPPED: '打卡的人和班表不同：確認是否為代班，並更新班表。',
    LATE: '留意是否轉場時間不足，或是常態性遲到。',
    EARLY: '確認是否案家同意提前結束。',
    PENDING: '到 04 頁「補登待覆核」核准或退回。',
    FAR: 'GPS 可能有誤差，只當提醒；有疑問再向居服員了解。',
}
OUTPUT_COLUMNS = ['狀態', '嚴重度', '異常項目', '日期', '任務ID', '案家ID', '排定居服員', '打卡居服員', '排定時段',
                  '上班', '下班', '遲到(分)', '早退(分)', '上班距案家(公尺)', '補登', '建議處理']
NUMBER_COLUMNS = ['遲到(分)', '早退(分)', '上班距案家(公尺)']
CAREGIVER_COLUMNS = ['居服員ID', '服務數', '正常', '遲到', '漏打卡', '未遇', '早退', '補登待覆核']


def _text(value):
    if value is None:
        return ''
    try:
        if pd.isna(value):
            return ''
    except (TypeError, ValueError):
        pass
    out = str(value).strip()
    return out[:-2] if re.fullmatch(r'\d+\.0', out) else out


def _number(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _day(value):
    parsed = pd.to_datetime(_text(value), errors='coerce')
    return None if pd.isna(parsed) else parsed.date()


def _moment(day, clock):
    m = re.match(r'(\d{1,2})[:：](\d{2})', _text(clock))
    if not day or not m:
        return None
    hour, minute = int(m[1]), int(m[2])
    if hour == 24 and minute == 0:
        return datetime.combine(day, datetime.min.time()) + timedelta(days=1)
    if hour > 23 or minute > 59:
        return None
    return datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)


def _cfg(config, name, default):
    return float(getattr(config, name, default)) if config is not None else float(default)


def _punch_dicts(punches):
    """punch_frame（中文欄名）→ store.effective_punches 用的 dict，依任務ID 分組；已退回的補登不算。"""
    out = {}
    if punches is None or punches.empty:
        return out
    for _, r in punches.iterrows():
        review = _text(r.get('覆核'))
        if review == REVIEW_REJECTED:
            continue
        task = _text(r.get('任務ID'))
        out.setdefault(task, []).append({
            'kind': _text(r.get('打卡類型')), 'at': _text(r.get('打卡時間')), 'late_entry': bool(r.get('補登')),
            'review': review, 'caregiver_id': _text(r.get('居服員ID')), 'client_id': _text(r.get('案家ID')),
            'lat': _number(r.get('緯度')), 'lon': _number(r.get('經度'))})
    return out


def _at(punch):
    return datetime.strptime(punch['at'], '%Y-%m-%d %H:%M:%S') if punch else None


def _finish(flags):
    flags = sorted(set(flags), key=FLAG_ORDER.index)
    problems = [f for f in flags if f != FAR]
    if not flags:
        return STATUS_OK, '', '', ''
    rank = {'高': 0, '中': 1, '低': 2, '提醒': 3}
    severity = min((SEVERITY[f] for f in flags), key=rank.get)
    return (problems[0] if problems else STATUS_OK), severity, '、'.join(flags), ' '.join(ADVICE[f] for f in flags[:2])


def reconcile(schedule, punches, config=None, now=None):
    """排班 vs 打卡，每筆已派服務一列，另加排外打卡。

    schedule：app.py 的 df_final（任務ID、日期、開始時間、結束時間、案號、最終派單居服員、服務地點_緯度／經度）；
              呼叫端先篩好要對照的日期。未派的服務不對照。
    punches：checkin.store.punch_frame() 的結果。
    now：現在時刻（預設主機時間）；還沒結束的服務不判漏打卡。
    回傳 DataFrame（OUTPUT_COLUMNS），依嚴重度排序。
    """
    from checkin.store import now as server_now
    now = now or server_now()
    late_grace = _cfg(config, 'attendance_late_grace_mins', 10)
    early_grace = _cfg(config, 'attendance_early_leave_grace_mins', 10)
    radius = _cfg(config, 'attendance_gps_radius_m', 300)
    by_task = _punch_dicts(punches)
    cg_col = next((c for c in ['最終派單居服員', '派單居服員', '居服員ID'] if c in schedule), None)
    client_col = next((c for c in ['案號', '案家ID'] if c in schedule), None)
    rows, seen = [], set()
    frame = schedule.drop_duplicates('任務ID', keep='last') if '任務ID' in schedule else schedule.iloc[0:0]
    for _, r in frame.iterrows():
        task = _text(r.get('任務ID'))
        planned = _text(r.get(cg_col)) if cg_col else ''
        if planned in UNASSIGNED:
            continue
        seen.add(task)
        day = _day(r.get('日期'))
        start_clock, end_clock = _text(r.get('開始時間', r.get('時間窗_開始')))[:5], _text(r.get('結束時間', r.get('時間窗_結束')))[:5]
        start, end = _moment(day, start_clock), _moment(day, end_clock)
        if start and end and end <= start:
            end += timedelta(days=1)
        mine = by_task.get(task, [])
        eff = effective_punches(mine)
        clock_in, clock_out = eff.get(CLOCK_IN), eff.get(CLOCK_OUT)
        ended = end is not None and end <= now
        flags, late, early, dist = [], None, None, None
        if MISSED in eff:
            flags.append(MISSED)
        elif not mine:
            if ended:
                flags.append(NO_RECORD)
        else:
            if clock_in is None and (clock_out is not None or ended):
                flags.append(NO_IN)
            if clock_in is not None and clock_out is None and ended:
                flags.append(NO_OUT)
            if clock_in is not None and start is not None:
                late = round((_at(clock_in) - start).total_seconds() / 60)
                if late > late_grace:
                    flags.append(LATE)
            if clock_out is not None and end is not None:
                early = round((end - _at(clock_out)).total_seconds() / 60)
                if early > early_grace:
                    flags.append(EARLY)
        if any(p['late_entry'] and p['review'] == REVIEW_PENDING for p in mine):
            flags.append(PENDING)
        actual = next((p['caregiver_id'] for p in mine if p['caregiver_id']), '')
        if actual and actual != planned:
            flags.append(SWAPPED)
        if clock_in is not None:
            d = distance_m(clock_in['lat'], clock_in['lon'], r.get('服務地點_緯度'), r.get('服務地點_經度'))
            if d is not None:
                dist = round(d)
                if d > radius:
                    flags.append(FAR)
        if not flags and not ended:          # 還沒結束、目前也沒有問題：先不判斷
            status, severity, items, advice = STATUS_NOT_YET, '', '', ''
        else:
            status, severity, items, advice = _finish(flags)
        rows.append({'狀態': status, '嚴重度': severity, '異常項目': items, '建議處理': advice,
                     '日期': day.isoformat() if day else '', '任務ID': task,
                     '案家ID': _text(r.get(client_col)) if client_col else '', '排定居服員': planned, '打卡居服員': actual,
                     '排定時段': f'{start_clock}～{end_clock}' if start_clock else '',
                     '上班': clock_in['at'][11:16] if clock_in else '', '下班': clock_out['at'][11:16] if clock_out else '',
                     '遲到(分)': max(late, 0) if late is not None else None,
                     '早退(分)': max(early, 0) if early is not None else None,
                     '上班距案家(公尺)': dist, '補登': '是' if any(p['late_entry'] for p in mine) else ''})
    for task, mine in by_task.items():
        if task in seen:
            continue
        eff = effective_punches(mine)
        status, severity, items, advice = _finish([EXTRA])
        first = mine[0]
        rows.append({'狀態': status, '嚴重度': severity, '異常項目': items, '建議處理': advice,
                     '日期': first['at'][:10], '任務ID': task, '案家ID': first['client_id'], '排定居服員': '',
                     '打卡居服員': first['caregiver_id'], '排定時段': '',
                     '上班': eff[CLOCK_IN]['at'][11:16] if CLOCK_IN in eff else '',
                     '下班': eff[CLOCK_OUT]['at'][11:16] if CLOCK_OUT in eff else '',
                     '補登': '是' if any(p['late_entry'] for p in mine) else ''})
    out = pd.DataFrame(rows).reindex(columns=OUTPUT_COLUMNS)
    text_cols = [c for c in OUTPUT_COLUMNS if c not in NUMBER_COLUMNS]
    out[text_cols] = out[text_cols].fillna('')
    rank = {'高': 0, '中': 1, '低': 2, '提醒': 3, '': 4}
    out['_s'] = out['嚴重度'].map(rank).fillna(4)
    out = out.sort_values(['_s', '日期', '排定時段', '任務ID'], kind='stable').drop(columns='_s')
    for col in NUMBER_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors='coerce').astype('Int64')
    return out.reset_index(drop=True)


def _has(items, flags):
    return items.fillna('').str.split('、').apply(lambda xs: any(f in xs for f in flags))


def summary(result):
    """整體數字：應對照筆數、正常、遲到、漏打卡、未遇、早退、補登待覆核、位置提醒、準時率。"""
    done = result[result['狀態'] != STATUS_NOT_YET]
    planned = done[done['排定居服員'] != '']
    items = done['異常項目']
    count = lambda flags: int(_has(items, flags).sum())
    timed = planned[(planned['上班'] != '')]
    on_time = int((~_has(timed['異常項目'], [LATE])).sum())
    return {
        '應對照': int(len(planned)),
        '正常': int((planned['狀態'] == STATUS_OK).sum()),
        '遲到': count([LATE]),
        '漏打卡': count(MISSING_FLAGS),
        '未遇': count([MISSED]),
        '早退': count([EARLY]),
        '補登待覆核': count([PENDING]),
        '排外打卡': count([EXTRA]),
        '位置提醒': count([FAR]),
        '準時率': round(on_time / len(timed) * 100, 1) if len(timed) else None,
        '尚未結束': int((result['狀態'] == STATUS_NOT_YET).sum()),
    }


def by_caregiver(result):
    """每位居服員的遲到、漏打卡、未遇次數（依排定居服員；排外打卡不算）。"""
    frame = result[(result['排定居服員'] != '') & (result['狀態'] != STATUS_NOT_YET)]
    if frame.empty:
        return pd.DataFrame(columns=CAREGIVER_COLUMNS)
    items = frame['異常項目']
    frame = frame.assign(居服員ID=frame['排定居服員'], 服務數=1, 正常=(frame['狀態'] == STATUS_OK).astype(int),
                         遲到=_has(items, [LATE]).astype(int), 漏打卡=_has(items, MISSING_FLAGS).astype(int),
                         未遇=_has(items, [MISSED]).astype(int), 早退=_has(items, [EARLY]).astype(int),
                         補登待覆核=_has(items, [PENDING]).astype(int))
    out = frame.groupby('居服員ID')[CAREGIVER_COLUMNS[1:]].sum().reset_index()
    return out.sort_values(['漏打卡', '未遇', '遲到', '居服員ID'], ascending=[False, False, False, True]).reset_index(drop=True)


def schedule_in_range(schedule, start, end):
    """班表中日期落在 start～end（含）的列。"""
    if schedule is None or schedule.empty or '日期' not in schedule:
        return schedule
    days = pd.to_datetime(schedule['日期'], errors='coerce').dt.date
    return schedule[(days >= start) & (days <= end)]
