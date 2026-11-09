"""試辦 KPI：分 3 組、共 8 項，每項都回傳分子、分母、期間、計算方式與明細表。

  A 服務量能　　　：A1 派案成功率、A2 未派服務時數比例（附原因分布）、A3 居服員產能利用率
  B 照顧品質　　　：B1 照顧連續性（主責居服員比例）
  C 人力負荷與成本：C1 平均交通時間、C2 轉場工時占比、C3 工時落在平均 ±20% 的人數比例、C4 加班合規率

畫面（kpi_view.py）、CSV 與 PILOT_KPI.md 都用這裡的 GROUPS／KPI_SPECS，說法只有一份。
- 只讀排班結果，不重新排班、不改班表；全部由系統資料計算，不需要人工輸入。
- 只用 ID 運算（任務ID、案家ID、居服員ID）；姓名由 app.py 的 show_table／export_frame 依遮罩設定顯示。
- 分母是 0 時數值留空（None），不自行假設。
- 基準月、試辦月的數值存在 output_results/pilot_kpi.sqlite3（CAREFLOW_KPI_DB 可改路徑）。
  只新增不覆蓋：同一個月份重存時，以最後一次為準，舊的留著備查。
純函式＋SQLite，不 import streamlit。
"""
from __future__ import annotations

import math
import os
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

CAREFLOW_BUILD = '2026.10.18-v19'

DEFAULT_DB = Path('output_results') / 'pilot_kpi.sqlite3'
TIMEZONE = ZoneInfo('Asia/Taipei')
BASELINE, PILOT = '基準月', '試辦月'
KINDS = (BASELINE, PILOT)
SYSTEM, MANUAL = '系統計算', '人工登錄'
UNASSIGNED = {'', 'nan', 'none', '未指派', '未派'}
OVERTIME_WARNING = 0.8        # 加班使用率達 80% 算「接近上限」，和主管報表（dashboard_metrics.build_dashboard）相同
NORMAL_DAILY_HOURS = 8.0      # 產能利用率的每日可上班時數上限；app.py 傳入 PipelineConfig.normal_daily_hours
WORKLOAD_BAND = 0.2           # C3：工時在平均的 80%～120% 之間算「接近平均」

# 組別：(代碼字母, 名稱, 這一組回答的問題)
GROUPS = [
    ('A', '服務量能', '服務有沒有排出去、人力夠不夠用'),
    ('B', '照顧品質', '案家是不是由同一位居服員照顧'),
    ('C', '人力負荷與成本', '交通、工時、加班是否合理'),
]
GROUP_NAME = {code: name for code, name, _ in GROUPS}


@dataclass(frozen=True)
class KpiSpec:
    """一項 KPI 的定義。scale：數值＝分子 ÷ 分母 × scale（百分比 100，平均 1）。"""
    code: str
    name: str
    unit: str
    better: str            # 'higher'（越高越好）或 'lower'（越低越好）
    numerator: str
    denominator: str
    method: str
    source: str
    num_unit: str = '次'
    den_unit: str = '次'
    scale: float = 100.0
    old_code: str = ''     # 分組前的代碼（PILOT_KPI.md 對照用）
    hint: str = ''         # 畫面上 KPI 卡下方的灰色小字：一句話說明算法

    @property
    def group(self):
        return self.code[0]


KPI_SPECS = [
    KpiSpec('A1', '派案成功率', '%', 'higher',
            '已派的服務次數', '期間內全部服務次數（週服務計畫展開後，含臨時插單）',
            '已派 ÷ 全部服務 × 100%。每一筆「案家 × 日期 × 時段」算一次服務。', '系統班表', old_code='K1'),
    KpiSpec('A2', '未派服務時數比例', '%', 'lower',
            '未派服務的時數', '期間內全部服務時數',
            '未派時數 ÷ 全部服務時數 × 100%。時數用服務歷時（分鐘），沒有時用起迄時間。'
            '原因分類和 ③ 衝突與異常處理相同，明細另列各原因的筆數與時數。',
            '系統班表＋未派原因診斷', num_unit='小時', den_unit='小時'),
    KpiSpec('A3', '居服員產能利用率', '%', 'higher',
            '居服員已排的工時（服務工時＋轉場工時）', '全部居服員期間內的可上班時數（扣掉請假）',
            '已排工時 ÷ 可上班時數 × 100%。已排工時＝服務工時＋轉場工時（和「工時與薪資」表的總工時相同）。'
            '可上班時數＝每位居服員每個可排班日的可上班時數加總：每日可服務時段扣掉當天登錄的請假時段'
            '（整天請假就是 0），最多算正常工時 8 小時。分母包含本期沒有排到班的人；'
            '看診、教育訓練等其他不可排原因不扣。',
            '系統工時估算＋員工資料（休息日、每日可服務時段）＋請假紀錄', num_unit='小時', den_unit='小時',
            hint='A3 算法：分子＝服務工時＋轉場工時；分母＝每人可排班日 ×（每日可服務時段 − 請假時段，最多 8 小時）加總，'
                 '含沒有排到班的人。'),
    KpiSpec('B1', '照顧連續性（主責居服員比例）', '%', 'higher',
            '由案家主責居服員本人服務的次數', '已派、而且案家有主責居服員的服務次數',
            '主責本人服務 ÷ 有主責的已派服務 × 100%。請假代班會讓數值下降，屬合理現象。',
            '系統班表＋主責名單（固定人選）', old_code='K4'),
    KpiSpec('C1', '平均交通時間', '分鐘／段', 'lower',
            '每段交通的車程分鐘加總（含從家裡到第一個案家）', '有車程的交通段數',
            '車程分鐘 ÷ 交通段數。每天從家裡到第一個案家、案家到下一個案家都算；同一案家接續（車程 0）、'
            '交通未算出的路段不算，也不含路段緩衝。和主管報表「排班儀錶板 › 交通」的平均相同。',
            '逐段交通（機車路網／Google 大眾運輸）', num_unit='分鐘', den_unit='段', scale=1.0, old_code='K3',
            hint='C1 算法：含從家裡到第一個案家；不含同一案家接續與路段緩衝；和主管報表「交通 › 平均」相同。'),
    KpiSpec('C2', '轉場工時占比', '%', 'lower',
            '有排班居服員的轉場工時加總', '同一群人的總工時加總',
            '轉場工時 ÷ 總工時 × 100%。轉場工時含交通與工作緩衝，首案通勤與末案返家不算（和工時與薪資表相同）。',
            '系統工時估算', num_unit='小時', den_unit='小時',
            hint='C2 算法：轉場＝前一案家到下一個不同案家的車程＋緩衝；從家裡出發、最後回家、同案接續都不算。'),
    KpiSpec('C3', '工時落在平均 ±20% 的人數比例', '%', 'higher',
            '期間總工時在平均的 80%～120% 之間的居服員人數', '本期有排班的居服員人數',
            '工時接近平均的人數 ÷ 有排班人數 × 100%。例：平均每人 75 小時，60～90 小時之間的人算接近平均。'
            '數值越高代表工作量越平均。只算本期有排班的居服員，工時含轉場；剛好落在 80% 或 120% 也算。',
            '系統工時估算', num_unit='人', den_unit='人', old_code='K7',
            hint='C3 算法：先算平均每人工時，再數有幾位落在平均的 8 折～1.2 倍之間。'),
    KpiSpec('C4', '加班合規率', '%', 'higher',
            '月加班沒有超過上限的居服員人數', '有排班的居服員人數',
            '沒有超過上限的人數 ÷ 有排班人數 × 100%，應該要是 100%。月加班含期間外已發生的加班；'
            '超過＝月加班 > 月加班上限。達上限 80% 的「接近上限」仍算合規，另在備註與明細提醒（和主管報表相同）。',
            '系統工時估算（月加班、月加班上限）', num_unit='人', den_unit='人'),
]
SPEC_BY_CODE = {spec.code: spec for spec in KPI_SPECS}

TABLE_COLUMNS = ['組別', '代碼', '指標', '數值', '單位', '分子', '分子說明', '分母', '分母說明', '期間', '計算方式',
                 '資料來源', '方向', '備註']
COMPARE_COLUMNS = ['組別', '代碼', '指標', '單位', '方向', '基準月', '基準月數值', '基準月分子', '基準月分母',
                   '試辦月', '試辦月數值', '試辦月分子', '試辦月分母', '差異', '變化']

SCHEMA = """
CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT NOT NULL, month TEXT NOT NULL,
    kind TEXT NOT NULL, code TEXT NOT NULL, numerator REAL, denominator REAL, value REAL,
    period TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '', saved_at TEXT NOT NULL, account TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS records_scope ON records(scope, month, kind);
"""


# ---------------- 共用小工具 ----------------

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


def to_number(value):
    """轉成有限的 float；空白、文字、NaN 回 None。"""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _ratio(numerator, denominator, scale):
    if numerator is None or not denominator:
        return None
    return numerator / denominator * scale


def now():
    """主機時間（台北時區、不帶時區資訊、到秒）。"""
    return datetime.now(TIMEZONE).replace(tzinfo=None, microsecond=0)


def _clock(value):
    m = re.match(r'(\d{1,2})[:：](\d{2})', _text(value))
    return int(m[1]) * 60 + int(m[2]) if m else None


def _assigned_map(assignments):
    """任務ID → 派單居服員（只算真的有派人）。"""
    out = {}
    if assignments is None or assignments.empty or not {'任務ID', '派單居服員'} <= set(assignments.columns):
        return out
    for tid, worker in zip(assignments['任務ID'].map(_text), assignments['派單居服員'].map(_text)):
        if tid and worker.lower() not in UNASSIGNED:
            out[tid] = worker
    return out


def _task_frame(tasks):
    if tasks is None or tasks.empty or '任務ID' not in tasks:
        return pd.DataFrame(columns=['任務ID'])
    frame = tasks.copy()
    frame['任務ID'] = frame['任務ID'].map(_text)
    return frame.loc[frame['任務ID'].ne('')].drop_duplicates('任務ID', keep='last')


def _slot(row):
    start, end = _text(row.get('時間窗_開始'))[:5], _text(row.get('時間窗_結束'))[:5]
    return f'{start}～{end}' if start or end else ''


def _task_minutes(row):
    """一筆服務的分鐘：先用「服務歷時(分鐘)」，沒有就用起迄時間。"""
    minutes = to_number(row.get('服務歷時(分鐘)'))
    if minutes is not None and minutes > 0:
        return minutes
    start, end = _clock(row.get('時間窗_開始')), _clock(row.get('時間窗_結束'))
    if start is None or end is None:
        return 0.0
    return float(end - start if end > start else end + 24 * 60 - start)


def _payroll(monthly_payroll, columns):
    """月薪資表依居服員加總（同一人跨月有多列）；缺欄位回 None。"""
    if monthly_payroll is None or monthly_payroll.empty or not {'居服員ID', *columns} <= set(monthly_payroll.columns):
        return None
    frame = monthly_payroll.copy()
    frame['居服員ID'] = frame['居服員ID'].map(_text)
    for col in columns:
        frame[col] = pd.to_numeric(frame[col], errors='coerce')
    return frame


def period_label(tasks):
    """服務日期範圍：「2026/10/01～2026/10/31」。"""
    if tasks is None or tasks.empty or '日期' not in tasks:
        return '本次排班期間'
    days = pd.to_datetime(tasks['日期'], errors='coerce').dropna()
    if days.empty:
        return '本次排班期間'
    return f'{days.min():%Y/%m/%d}～{days.max():%Y/%m/%d}'


def period_month(tasks):
    """服務期間第一天所在月份（YYYY-MM），當作儲存時的預設月份。"""
    if tasks is None or tasks.empty or '日期' not in tasks:
        return now().strftime('%Y-%m')
    days = pd.to_datetime(tasks['日期'], errors='coerce').dropna()
    return f'{days.min():%Y-%m}' if not days.empty else now().strftime('%Y-%m')


def _result(code, numerator, denominator, period, detail=None, note='', breakdown=None):
    """組成一項 KPI 的結果。數值在分母為 0 或分子未知時是 None。breakdown：另外顯示的分類小計（例如未派原因）。"""
    spec = SPEC_BY_CODE[code]
    value = _ratio(numerator, denominator, spec.scale)
    if value is None and not note:
        note = '尚無資料'
    return {'組別': GROUP_NAME[spec.group], '代碼': code, '指標': spec.name,
            '數值': None if value is None else round(value, 1), '單位': spec.unit,
            '分子': None if numerator is None else round(float(numerator), 2),
            '分母': None if denominator is None else round(float(denominator), 2),
            '分子說明': spec.numerator, '分母說明': spec.denominator, '期間': period,
            '計算方式': spec.method, '資料來源': spec.source,
            '方向': '越高越好' if spec.better == 'higher' else '越低越好', '備註': note,
            'detail': detail if detail is not None else pd.DataFrame(),
            'breakdown': breakdown if breakdown is not None else pd.DataFrame()}


# ================ A 服務量能 ================

def dispatch_rate(tasks, assignments, period=None):
    """A1：已派 ÷ 全部服務。明細：每筆服務的已派／未派（未派排前面）。"""
    frame = _task_frame(tasks)
    assigned = _assigned_map(assignments)
    rows = [{'結果': '已派' if r['任務ID'] in assigned else '未派', '任務ID': r['任務ID'],
             '日期': _text(r.get('日期'))[:10], '時段': _slot(r), '案家ID': _text(r.get('案家ID')),
             '派單居服員': assigned.get(r['任務ID'], '')} for _, r in frame.iterrows()]
    detail = pd.DataFrame(rows, columns=['結果', '任務ID', '日期', '時段', '案家ID', '派單居服員'])
    detail = detail.sort_values(['結果', '日期', '時段', '任務ID'], ascending=[False, True, True, True], kind='stable')
    numerator = int((detail['結果'] == '已派').sum())
    return _result('A1', numerator, len(detail), period or period_label(tasks), detail.reset_index(drop=True))


def unassigned_hours(tasks, assignments, diagnostics=None, period=None):
    """A2：未派時數 ÷ 全部服務時數。breakdown：各原因（③ 的問題類型）的筆數、時數與占未派時數的比例。

    diagnostics：app.py 的 _pending_diagnostics（排班診斷＋居督標記待處理），沒有就全部歸「其他未成功派班」。
    """
    from issue_center import GROUP_NAMES, unassigned_issues
    frame = _task_frame(tasks)
    assigned = _assigned_map(assignments)
    frame['_min'] = [_task_minutes(r) for _, r in frame.iterrows()] if not frame.empty else []
    total = float(frame['_min'].sum()) / 60 if not frame.empty else 0.0
    pending = frame.loc[~frame['任務ID'].isin(assigned)] if not frame.empty else frame
    issues = unassigned_issues(pending.drop(columns='_min'), diagnostics) if not pending.empty else pd.DataFrame()
    minutes = dict(zip(pending['任務ID'], pending['_min'])) if not pending.empty else {}
    columns = ['問題類型', '原因分類', '日期', '時段', '案家ID', '任務ID', '時數', '原因', '建議處理']
    if issues.empty:
        detail = pd.DataFrame(columns=columns)
    else:
        detail = issues.assign(時數=issues['任務ID'].map(lambda t: round(minutes.get(t, 0.0) / 60, 2)))[columns]
    hours = float(detail['時數'].sum()) if not detail.empty else 0.0
    breakdown = pd.DataFrame(columns=['問題類型', '筆數', '時數', '占未派時數(%)'])
    if not detail.empty:
        grouped = detail.groupby('問題類型').agg(筆數=('任務ID', 'size'), 時數=('時數', 'sum')).reset_index()
        grouped['時數'] = grouped['時數'].round(1)
        grouped['占未派時數(%)'] = (grouped['時數'] / hours * 100).round(1) if hours else 0.0
        order = {name: i for i, name in enumerate(GROUP_NAMES)}
        grouped['_o'] = grouped['問題類型'].map(order).fillna(len(order))
        breakdown = grouped.sort_values(['時數', '_o'], ascending=[False, True], kind='stable').drop(columns='_o').reset_index(drop=True)
    note = f'未派 {len(detail):,} 筆' if not detail.empty else ('全部已派' if total else '')
    return _result('A2', hours, total, period or period_label(tasks), detail, note, breakdown)


def _workdays(row):
    """員工資料的「可排班星期」（1＝星期一…7＝星期日）；空白代表每天都可以。"""
    text = _text(row.get('可排班星期')).replace('，', ',')
    return {int(x) for x in text.split(',') if x.strip().isdigit()}


def _leave_spans(leaves, row):
    """這位居服員的請假時段 [(開始, 結束)]：請假紀錄（原因以「請假」開頭）＋員工資料的「請假日期」（整天）。"""
    cid = _text(row.get('居服員ID'))
    spans = []
    for item in leaves or []:
        if _text(item.get('cg')) != cid or not _text(item.get('reason')).startswith('請假'):
            continue
        a, b = pd.to_datetime(item.get('start'), errors='coerce'), pd.to_datetime(item.get('end'), errors='coerce')
        if pd.notna(a) and pd.notna(b) and b > a:
            spans.append((a, b))
    for day in _text(row.get('請假日期')).replace('、', ',').split(','):
        d = pd.to_datetime(day.strip(), errors='coerce')
        if day.strip() and pd.notna(d):
            spans.append((d.normalize(), d.normalize() + pd.Timedelta(days=1)))
    return spans


def _overlap_hours(start, end, spans):
    """[start, end) 被請假時段蓋到的小時數（重疊的請假只算一次）。"""
    cut = sorted((max(a, start), min(b, end)) for a, b in spans if a < end and b > start)
    total, cursor = 0.0, start
    for a, b in cut:
        a = max(a, cursor)
        if b > a:
            total += (b - a).total_seconds() / 3600
            cursor = b
    return total


def capacity_utilization(caregivers, monthly_payroll, start, end, normal_daily_hours=NORMAL_DAILY_HOURS, period=None,
                         leaves=None):
    """A3：已排工時（服務＋轉場）÷ 可上班時數（扣掉請假）。

    caregivers：員工資料（居服員ID、可排班星期、每日可服務時段_起／迄、請假日期）；start／end：排班期間（含）。
    leaves：請假與不可排紀錄 [{'cg', 'start', 'end', 'reason'}]（WorkflowStore.blocks()），只扣原因是「請假」的。
    每人每天可上班時數＝每日可服務時段（沒有時段就整天）扣掉當天請假，最多 normal_daily_hours。
    """
    columns = ['居服員ID', '可排班日數', '請假扣除時數', '可上班時數', '服務工時', '轉場工時', '已排工時', '利用率(%)']
    if caregivers is None or caregivers.empty or '居服員ID' not in caregivers or start is None or end is None:
        return _result('A3', None, None, period or '本次排班期間', pd.DataFrame(columns=columns))
    days = pd.date_range(pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize(), freq='D')
    served, moved = {}, {}
    pay = _payroll(monthly_payroll, ['服務工時', '轉場工時'])
    if pay is not None:
        served = pay.groupby('居服員ID')['服務工時'].sum().to_dict()
        moved = pay.groupby('居服員ID')['轉場工時'].sum().to_dict()
    rows = []
    for _, r in caregivers.drop_duplicates('居服員ID').iterrows():
        cid = _text(r.get('居服員ID'))
        if not cid:
            continue
        allowed, spans = _workdays(r), _leave_spans(leaves, r)
        a, b = _clock(r.get('每日可服務時段_起')), _clock(r.get('每日可服務時段_迄'))
        if a is None or b is None or b <= a:
            a, b = 0, 24 * 60
        count, available, deducted = 0, 0.0, 0.0
        for d in days:
            if allowed and d.weekday() + 1 not in allowed:
                continue
            count += 1
            w0, w1 = d + pd.Timedelta(minutes=a), d + pd.Timedelta(minutes=b)
            full = min((b - a) / 60, normal_daily_hours)
            left = min(max((b - a) / 60 - _overlap_hours(w0, w1, spans), 0.0), normal_daily_hours)
            available += left
            deducted += full - left
        service, travel = float(served.get(cid) or 0.0), float(moved.get(cid) or 0.0)
        worked = service + travel
        rows.append({'居服員ID': cid, '可排班日數': count, '請假扣除時數': round(deducted, 1),
                     '可上班時數': round(available, 1), '服務工時': round(service, 1), '轉場工時': round(travel, 1),
                     '已排工時': round(worked, 1), '利用率(%)': round(worked / available * 100, 1) if available else None})
    detail = pd.DataFrame(rows, columns=columns).sort_values('利用率(%)', ascending=False, kind='stable', na_position='last')
    idle = int((detail['已排工時'] <= 0).sum())
    leave_total = float(detail['請假扣除時數'].sum())
    note = (f'{len(detail)} 位居服員，其中 {idle} 位本期沒有排班；已扣請假 {leave_total:,.1f} 小時' if len(detail) else '')
    return _result('A3', float(detail['已排工時'].sum()), float(detail['可上班時數'].sum()), period or '本次排班期間',
                   detail.reset_index(drop=True), note)


# ================ B 照顧品質 ================

def continuity(tasks, assignments, primary_map, period=None):
    """B1：主責本人服務 ÷ 有主責的已派服務。明細：每筆有主責的已派服務。"""
    owners = {_text(k): _text(v) for k, v in (primary_map or {}).items() if _text(v)}
    assigned = _assigned_map(assignments)
    rows = []
    for _, r in _task_frame(tasks).iterrows():
        worker, owner = assigned.get(r['任務ID']), owners.get(_text(r.get('案家ID')))
        if worker and owner:
            rows.append({'結果': '主責本人' if worker == owner else '其他居服員', '任務ID': r['任務ID'],
                         '日期': _text(r.get('日期'))[:10], '時段': _slot(r), '案家ID': _text(r.get('案家ID')),
                         '主責居服員': owner, '派單居服員': worker})
    detail = pd.DataFrame(rows, columns=['結果', '任務ID', '日期', '時段', '案家ID', '主責居服員', '派單居服員'])
    detail = detail.sort_values(['結果', '日期', '時段'], kind='stable').reset_index(drop=True)
    return _result('B1', int((detail['結果'] == '主責本人').sum()), len(detail), period or period_label(tasks), detail)


# ================ C 人力負荷與成本 ================

def transition_time(routes, period=None):
    """C1：平均交通時間＝有車程的交通分鐘 ÷ 段數（含從家裡到第一個案家；和主管報表「交通 › 平均」相同）。

    明細：每一段交通是否計入；車程 0（同一案家接續或同地點）與交通未算出的路段不計入，也不含路段緩衝。
    """
    columns = ['是否計入', '不計入原因', '交通日期', '派單居服員', '任務ID', '交通路段', '預估車程(分)']
    if routes is None or routes.empty or '預估車程(分)' not in routes:
        return _result('C1', None, 0, period or '本次排班期間', pd.DataFrame(columns=columns))
    frame = routes.copy()
    minutes = pd.to_numeric(frame['預估車程(分)'], errors='coerce')
    reason = pd.Series('', index=frame.index)
    reason[minutes.isna()] = '交通未算出'
    reason[minutes.notna() & minutes.le(0)] = '車程 0（同一案家接續或同地點）'
    counted = reason.eq('')
    blank = pd.Series('', index=frame.index)
    detail = pd.DataFrame({'是否計入': counted.map({True: '計入', False: '不計入'}), '不計入原因': reason,
                           '交通日期': frame.get('交通日期', blank).map(_text),
                           '派單居服員': frame.get('派單居服員', blank).map(_text),
                           '任務ID': frame.get('任務ID', blank).map(_text),
                           '交通路段': frame.get('交通路段', blank).map(_text),
                           '預估車程(分)': minutes.round(1)}, columns=columns)
    picked = minutes[counted]
    return _result('C1', float(picked.sum()) if len(picked) else None, int(len(picked)), period or '本次排班期間',
                   detail.reset_index(drop=True))


def transition_share(monthly_payroll, period=None):
    """C2：轉場工時 ÷ 總工時（有排班的人）。明細：每位居服員的轉場工時、總工時與占比。"""
    columns = ['居服員ID', '轉場工時', '總工時', '轉場占比(%)']
    pay = _payroll(monthly_payroll, ['轉場工時', '總工時'])
    if pay is None:
        return _result('C2', None, None, period or '本次排班期間', pd.DataFrame(columns=columns))
    per = pay.groupby('居服員ID')[['轉場工時', '總工時']].sum()
    per = per[per['總工時'] > 0]
    detail = pd.DataFrame({'居服員ID': per.index, '轉場工時': per['轉場工時'].round(1).values,
                           '總工時': per['總工時'].round(1).values,
                           '轉場占比(%)': (per['轉場工時'] / per['總工時'] * 100).round(1).values}, columns=columns)
    detail = detail.sort_values('轉場占比(%)', ascending=False, kind='stable').reset_index(drop=True)
    if per.empty:
        return _result('C2', None, None, period or '本次排班期間', detail)
    return _result('C2', float(per['轉場工時'].sum()), float(per['總工時'].sum()), period or '本次排班期間', detail)


def workload_spread(monthly_payroll, period=None, band=WORKLOAD_BAND):
    """C3：期間總工時落在平均 ±20%（含邊界）的人數 ÷ 有排班人數。明細：每人總工時、和平均差幾 %、偏高／偏低。"""
    columns = ['結果', '居服員ID', '期間總工時', '和平均差距(%)']
    pay = _payroll(monthly_payroll, ['總工時'])
    per = pay.groupby('居服員ID')['總工時'].sum() if pay is not None else pd.Series(dtype=float)
    per = per[per > 0].dropna()
    if per.empty:
        return _result('C3', None, None, period or '本次排班期間', pd.DataFrame(columns=columns))
    mean = float(per.mean())
    low, high = mean * (1 - band), mean * (1 + band)
    gap = (per / mean - 1) * 100
    result = pd.Series('接近平均', index=per.index)
    result[per < low - 1e-9] = '偏低'
    result[per > high + 1e-9] = '偏高'
    detail = pd.DataFrame({'結果': result.values, '居服員ID': per.index, '期間總工時': per.round(1).values,
                           '和平均差距(%)': gap.round(1).values}, columns=columns)
    rank = {'偏高': 0, '偏低': 1, '接近平均': 2}
    detail = detail.assign(_r=detail['結果'].map(rank)).sort_values(['_r', '期間總工時'], ascending=[True, False],
                                                                   kind='stable').drop(columns='_r').reset_index(drop=True)
    near = int((result == '接近平均').sum())
    note = (f'平均每人 {mean:,.1f} 小時，±{band * 100:.0f}% 為 {low:,.1f}～{high:,.1f} 小時；'
            f'偏高 {int((result == "偏高").sum())} 人、偏低 {int((result == "偏低").sum())} 人')
    return _result('C3', near, len(per), period or '本次排班期間', detail, note)


def overtime_compliance(monthly_payroll, warning=OVERTIME_WARNING, period=None):
    """C4：月加班沒有超過上限的人數 ÷ 有排班人數（應為 100%）。明細：每人月加班、上限、使用率與狀態（超過的排最前面）。"""
    columns = ['狀態', '居服員ID', '期間總工時', '月加班(含期外)', '月加班上限', '加班使用率(%)']
    pay = _payroll(monthly_payroll, ['總工時', '合計加班時數', '月加班上限'])
    if pay is None:
        return _result('C4', None, None, period or '本次排班期間', pd.DataFrame(columns=columns))
    per = pay.groupby('居服員ID').agg(總工時=('總工時', 'sum'), 月加班=('合計加班時數', 'max'), 上限=('月加班上限', 'max'))
    per = per[per['總工時'] > 0]
    if per.empty:
        return _result('C4', None, None, period or '本次排班期間', pd.DataFrame(columns=columns))
    usage = (per['月加班'].fillna(0) / per['上限'].where(per['上限'] > 0)).fillna(0).clip(lower=0)
    status = usage.map(lambda v: '超過上限' if v > 1 + 1e-9 else '接近上限' if v >= warning else '正常')
    detail = pd.DataFrame({'狀態': status.values, '居服員ID': per.index, '期間總工時': per['總工時'].round(1).values,
                           '月加班(含期外)': per['月加班'].fillna(0).round(1).values, '月加班上限': per['上限'].values,
                           '加班使用率(%)': (usage * 100).round(1).values}, columns=columns)
    rank = {'超過上限': 0, '接近上限': 1, '正常': 2}
    detail = detail.assign(_r=detail['狀態'].map(rank)).sort_values(['_r', '加班使用率(%)'], ascending=[True, False],
                                                                   kind='stable').drop(columns='_r').reset_index(drop=True)
    over, near = int((status == '超過上限').sum()), int((status == '接近上限').sum())
    note = (f'超過上限 {over} 人（不合規）、接近上限 {near} 人（合規但要留意）；'
            f'加班合計 {per["月加班"].fillna(0).sum():,.1f} 小時（含期外）')
    return _result('C4', len(per) - over, len(per), period or '本次排班期間', detail, note)


# ---------------- 組合、表格、比較 ----------------

def compute_all(tasks, assignments, routes=None, monthly_payroll=None, primary_map=None, diagnostics=None,
                caregivers=None, start=None, end=None, normal_daily_hours=NORMAL_DAILY_HOURS, leaves=None):
    """一次算出 8 項 KPI，回傳結果清單（順序同 KPI_SPECS）。

    diagnostics：未派原因診斷（A2）；caregivers：員工資料（A3）；start／end：排班期間（A3，預設用服務日期範圍）；
    leaves：請假紀錄（A3 扣除，WorkflowStore.blocks()）。
    """
    period = period_label(tasks)
    if (start is None or end is None) and tasks is not None and not tasks.empty and '日期' in tasks:
        days = pd.to_datetime(tasks['日期'], errors='coerce').dropna()
        if not days.empty:
            start, end = start or days.min(), end or days.max()
    return [dispatch_rate(tasks, assignments, period),
            unassigned_hours(tasks, assignments, diagnostics, period),
            capacity_utilization(caregivers, monthly_payroll, start, end, normal_daily_hours,
                                 f'{pd.Timestamp(start):%Y/%m/%d}～{pd.Timestamp(end):%Y/%m/%d}' if start is not None and end is not None else period,
                                 leaves),
            continuity(tasks, assignments, primary_map, period),
            transition_time(routes, period),
            transition_share(monthly_payroll, period),
            workload_spread(monthly_payroll, period),
            overtime_compliance(monthly_payroll, period=period)]


def by_group(results):
    """[(組代碼, 組名, 說明, [該組結果])]，給畫面分組顯示。"""
    return [(code, name, question, [r for r in results if r['代碼'].startswith(code)]) for code, name, question in GROUPS]


def kpi_table(results):
    """畫面與 CSV 用的總表（TABLE_COLUMNS），一項 KPI 一列。"""
    return pd.DataFrame([{k: r.get(k) for k in TABLE_COLUMNS} for r in results], columns=TABLE_COLUMNS)


def detail_table(results):
    """所有明細接成一張長表（前面加組別、代碼、指標），給「下載明細 CSV」用。"""
    parts = [r['detail'].assign(組別=r['組別'], 代碼=r['代碼'], 指標=r['指標']) for r in results
             if isinstance(r.get('detail'), pd.DataFrame) and not r['detail'].empty]
    if not parts:
        return pd.DataFrame(columns=['組別', '代碼', '指標'])
    out = pd.concat(parts, ignore_index=True, sort=False)
    return out[['組別', '代碼', '指標'] + [c for c in out.columns if c not in ('組別', '代碼', '指標')]]


def manual_result(code, numerator, denominator, period=''):
    """人工登錄（例如試辦前人工排班的基準月）：由分子、分母算出數值，格式和系統計算相同。"""
    return _result(code, to_number(numerator), to_number(denominator), period, note='人工登錄')


def as_records(results):
    """結果清單 → {代碼: {numerator, denominator, value, period}}，給 compare_table 與 save_month 用。"""
    return {r['代碼']: {'numerator': r['分子'], 'denominator': r['分母'], 'value': r['數值'], 'period': r['期間']}
            for r in results}


def _change(spec, base, pilot):
    if base is None or pilot is None:
        return None, '無法比較'
    diff = round(pilot - base, 1)
    if abs(diff) < 0.05:
        return diff, '持平'
    better = diff > 0 if spec.better == 'higher' else diff < 0
    return diff, '改善' if better else '變差'


def compare_table(baseline, pilot, baseline_label='', pilot_label=''):
    """基準月 vs 試辦月。baseline／pilot：{代碼: {numerator, denominator, value}}；差異＝試辦月 − 基準月。"""
    rows = []
    for spec in KPI_SPECS:
        b, p = (baseline or {}).get(spec.code), (pilot or {}).get(spec.code)
        if b is None and p is None:
            continue
        bv, pv = to_number((b or {}).get('value')), to_number((p or {}).get('value'))
        diff, change = _change(spec, bv, pv)
        rows.append({'組別': GROUP_NAME[spec.group], '代碼': spec.code, '指標': spec.name, '單位': spec.unit,
                     '方向': '越高越好' if spec.better == 'higher' else '越低越好',
                     '基準月': baseline_label, '基準月數值': bv,
                     '基準月分子': to_number((b or {}).get('numerator')), '基準月分母': to_number((b or {}).get('denominator')),
                     '試辦月': pilot_label, '試辦月數值': pv,
                     '試辦月分子': to_number((p or {}).get('numerator')), '試辦月分母': to_number((p or {}).get('denominator')),
                     '差異': diff, '變化': change})
    return pd.DataFrame(rows, columns=COMPARE_COLUMNS)


# ---------------- 儲存（SQLite） ----------------

def db_path(path=None):
    return Path(path or os.getenv('CAREFLOW_KPI_DB') or DEFAULT_DB)


def _connect(path=None):
    p = db_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(p, timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def demo_db_path(demo_store_path):
    """示範模式的 KPI 暫存檔：放在示範工作紀錄旁邊（同一資料夾、24 小時後一起清掉），不碰正式的 pilot_kpi.sqlite3。"""
    if not demo_store_path:
        return None
    store = Path(demo_store_path)
    return str(store.with_name(store.stem + '_kpi.sqlite3'))


def valid_month(month):
    return bool(re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', _text(month)))


def save_month(scope, month, kind, records, source=SYSTEM, account='', path=None):
    """把一個月份的 KPI 數值存成基準月或試辦月。records：as_records() 的格式。成功回 None，否則回中文錯誤。"""
    if not valid_month(month):
        return '月份格式要像 2026-09（西元年-月）。'
    if kind not in KINDS:
        return '種類只能是「基準月」或「試辦月」。'
    stamp = now().strftime('%Y-%m-%d %H:%M:%S')
    # 沒有數值的項目（尚無資料）不存，避免蓋掉同月份之前存好的數字
    rows = [(str(scope), month, kind, code, to_number(r.get('numerator')), to_number(r.get('denominator')),
             to_number(r.get('value')), _text(r.get('period')), source, stamp, str(account or ''))
            for code, r in (records or {}).items() if code in SPEC_BY_CODE and to_number(r.get('value')) is not None]
    if not rows:
        return '沒有可以儲存的 KPI 數值。'
    try:
        with closing(_connect(path)) as db, db:
            db.executemany('INSERT INTO records(scope, month, kind, code, numerator, denominator, value, period, source,'
                           ' saved_at, account) VALUES (?,?,?,?,?,?,?,?,?,?,?)', rows)
    except (OSError, sqlite3.Error) as exc:
        return '儲存失敗：' + str(exc)
    return None


def saved_months(scope, path=None):
    """已存的月份數值（每個月份 × 種類 × 代碼只留最後一次；只留目前定義裡的代碼）。"""
    columns = ['month', 'kind', 'code', 'numerator', 'denominator', 'value', 'period', 'source', 'saved_at', 'account']
    try:
        with closing(_connect(path)) as db:
            rows = db.execute('SELECT * FROM records WHERE scope=? ORDER BY id', (str(scope),)).fetchall()
    except (OSError, sqlite3.Error):
        rows = []
    frame = pd.DataFrame([dict(r) for r in rows], columns=['id', 'scope'] + columns)
    frame = frame.loc[frame['code'].isin(SPEC_BY_CODE)]
    return frame.drop_duplicates(['month', 'kind', 'code'], keep='last')[columns].reset_index(drop=True)


def month_options(saved, kind):
    """某種類已存的月份，新到舊。"""
    if saved is None or saved.empty:
        return []
    return sorted(saved.loc[saved['kind'] == kind, 'month'].unique(), reverse=True)


def month_values(saved, month, kind):
    """saved_months() → {代碼: {numerator, denominator, value, period, source}}。"""
    if saved is None or saved.empty:
        return {}
    part = saved.loc[(saved['month'] == month) & (saved['kind'] == kind)]
    return {r['code']: {'numerator': r['numerator'], 'denominator': r['denominator'], 'value': r['value'],
                        'period': r['period'], 'source': r['source']} for _, r in part.iterrows()}
