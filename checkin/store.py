"""打卡資料庫（SQLite）：班表發布、手機綁定、打卡、補登覆核、當日看板。

純函式，不 import streamlit；HomeCare AI（app.py）與手機打卡網頁（checkin/server.py）共用。
資料存在 output_results/checkin.sqlite3（CAREFLOW_CHECKIN_DB 可改），表：
- shifts   ：居督在 04 頁發布的班。只有任務ID、案家ID、居服員ID、時段、服務項目、遮罩後的案家名稱（王○○）與案家座標。
- punches  ：打卡紀錄，**只能新增**；資料庫觸發器擋 UPDATE 與 DELETE（只有 DEMO- 示範班可以清除）。
             更正一律新增一筆「補登」（late_entry=1），狀態待覆核。
- reviews  ：居督對補登的覆核（核准／退回），一樣只能新增；同一筆補登以最後一次覆核為準。
- devices  ：手機綁定。手機只存一組隨機綁定碼（cookie），這裡只存它的 sha256。
- settings ：打卡網址、第一支手機自動綁定等設定。

打卡時間一律用主機時間（台北時區），不信任手機時間。居服員與案家都用原本的 ID，不存任何未遮罩的姓名。
"""
from __future__ import annotations

import hashlib
import math
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / 'output_results' / 'checkin.sqlite3'
TIMEZONE = ZoneInfo('Asia/Taipei')

CLOCK_IN, CLOCK_OUT, MISSED = '上班', '下班', '未遇'
KINDS = (CLOCK_IN, CLOCK_OUT, MISSED)
REVIEW_PENDING, REVIEW_APPROVED, REVIEW_REJECTED = '待覆核', '已核准', '已退回'
DEMO_PREFIX = 'DEMO-'
UNASSIGNED = ('', '未指派', '待安排', 'nan', 'None')

SCHEMA = """
CREATE TABLE IF NOT EXISTS shifts(
    task_id TEXT PRIMARY KEY, day TEXT NOT NULL, client_id TEXT, caregiver_id TEXT NOT NULL,
    start TEXT, end TEXT, minutes REAL, client_label TEXT, service TEXT, lat REAL, lon REAL, published_at TEXT);
CREATE INDEX IF NOT EXISTS shifts_cg_day ON shifts(caregiver_id, day);
CREATE TABLE IF NOT EXISTS punches(
    id INTEGER PRIMARY KEY AUTOINCREMENT, caregiver_id TEXT NOT NULL, client_id TEXT, task_id TEXT NOT NULL,
    kind TEXT NOT NULL, at TEXT NOT NULL, recorded_at TEXT NOT NULL,
    lat REAL, lon REAL, accuracy REAL, late_entry INTEGER NOT NULL DEFAULT 0, note TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS punches_task ON punches(task_id, kind);
CREATE INDEX IF NOT EXISTS punches_at ON punches(at);
CREATE TRIGGER IF NOT EXISTS punches_no_update BEFORE UPDATE ON punches
    BEGIN SELECT RAISE(ABORT, 'punches are append-only'); END;
CREATE TRIGGER IF NOT EXISTS punches_no_delete BEFORE DELETE ON punches WHEN old.task_id NOT LIKE 'DEMO-%'
    BEGIN SELECT RAISE(ABORT, 'punches are append-only'); END;
CREATE TABLE IF NOT EXISTS reviews(
    id INTEGER PRIMARY KEY AUTOINCREMENT, punch_id INTEGER NOT NULL, decision TEXT NOT NULL,
    account TEXT NOT NULL DEFAULT '', at TEXT NOT NULL, note TEXT NOT NULL DEFAULT '');
CREATE TRIGGER IF NOT EXISTS reviews_no_update BEFORE UPDATE ON reviews
    BEGIN SELECT RAISE(ABORT, 'reviews are append-only'); END;
CREATE TABLE IF NOT EXISTS devices(
    id INTEGER PRIMARY KEY AUTOINCREMENT, caregiver_id TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL DEFAULT '', status TEXT NOT NULL, created_at TEXT NOT NULL, decided_at TEXT, last_seen TEXT);
CREATE INDEX IF NOT EXISTS devices_cg ON devices(caregiver_id, status);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
"""


def db_path(path=None):
    return Path(path or os.getenv('CAREFLOW_CHECKIN_DB') or DEFAULT_DB)


def connect(path=None):
    p = db_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(p, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript(SCHEMA)
    return db


def now():
    """主機時間（台北時區，不帶時區資訊、到秒）。打卡、補登、看板都用這個，不用手機時間。"""
    return datetime.now(TIMEZONE).replace(tzinfo=None, microsecond=0)


def _stamp(moment):
    return moment.strftime('%Y-%m-%d %H:%M:%S')


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


def _num(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def mask_name(name):
    """和 caregiver_engine._privacy_mask_name 一樣只留第一個字：王小明 → 王○○。

    04 頁傳進來的已經是遮罩後的名稱；這裡再遮一次，確保資料庫不會存到完整姓名。
    """
    compact = ''.join(_text(name).split())
    if not compact:
        return ''
    if len(compact) <= 1:
        return '○'
    return compact[0] + '○' * (len(compact) - 1)


def _clock(value):
    text = _text(value)
    m = re.match(r'(\d{1,2})[:：](\d{2})', text)
    return f'{int(m[1]):02d}:{m[2]}' if m else ''


# ---------------------------------------------------------------------------
# 班表發布
# ---------------------------------------------------------------------------
def publish_shifts(schedule, day, client_names=None, path=None):
    """把 04 頁的最終班表中「某一天、已派」的服務發布到手機打卡頁。

    schedule：app.py 的 df_final（任務ID、日期、開始時間、結束時間、案號、最終派單居服員…）。
    day：要發布的日期（date）。這一天原本有、這次沒有的班會移除；已經打過的卡不受影響。
    client_names：{案家ID: 遮罩姓名}，只用來在手機上顯示「王○○」。
    回傳 (發布筆數, 移除筆數)。
    """
    client_names = client_names or {}
    cg_col = next((c for c in ['最終派單居服員', '派單居服員', '居服員ID'] if c in schedule), None)
    client_col = next((c for c in ['案號', '案家ID'] if c in schedule), None)
    if cg_col is None or '任務ID' not in schedule or '日期' not in schedule:
        return 0, 0
    iso = day.isoformat()
    stamp = _stamp(now())
    rows = []
    for _, r in schedule.drop_duplicates('任務ID', keep='last').iterrows():
        cg = _text(r.get(cg_col))
        parsed = pd.to_datetime(_text(r.get('日期')), errors='coerce')
        if cg in UNASSIGNED or pd.isna(parsed) or parsed.date().isoformat() != iso:
            continue
        client = _text(r.get(client_col)) if client_col else ''
        service = re.sub(r'\((\d+)\.0\)', r'(\1)', _text(r.get('服務項目')))
        rows.append((_text(r['任務ID']), iso, client, cg,
                     _clock(r.get('開始時間', r.get('時間窗_開始'))), _clock(r.get('結束時間', r.get('時間窗_結束'))),
                     _num(r.get('服務分鐘')), mask_name(client_names.get(client, '')), service[:120],
                     _num(r.get('服務地點_緯度')), _num(r.get('服務地點_經度')), stamp))
    ids = {r[0] for r in rows}
    db = connect(path)
    try:
        with db:
            old = [x[0] for x in db.execute('SELECT task_id FROM shifts WHERE day=? AND task_id NOT LIKE ?',
                                            (iso, DEMO_PREFIX + '%'))]
            removed = [t for t in old if t not in ids]
            db.executemany('DELETE FROM shifts WHERE task_id=?', [(t,) for t in removed])
            db.executemany('INSERT OR REPLACE INTO shifts VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', rows)
    finally:
        db.close()
    return len(rows), len(removed)


def published_days(path=None):
    """已發布的日期與筆數：[(日期, 筆數, 最後發布時間)]，新的在前。"""
    db = connect(path)
    try:
        return [tuple(r) for r in db.execute(
            'SELECT day, COUNT(*), MAX(published_at) FROM shifts WHERE task_id NOT LIKE ? GROUP BY day ORDER BY day DESC',
            (DEMO_PREFIX + '%',))]
    finally:
        db.close()


def shifts_for(caregiver_id, day, path=None):
    db = connect(path)
    try:
        return [dict(r) for r in db.execute('SELECT * FROM shifts WHERE caregiver_id=? AND day=? ORDER BY start, task_id',
                                            (caregiver_id, day.isoformat()))]
    finally:
        db.close()


def resolve_caregiver(text, path=None):
    """手機輸入的員工編號 → 資料庫裡原本的居服員ID（不分大小寫、去空白）；查不到回傳 None。

    只有出現在已發布班表或已綁過手機的編號才算數，亂打的編號不會建資料。
    """
    key = _text(text).replace(' ', '').upper()
    if not key:
        return None
    db = connect(path)
    try:
        row = (db.execute('SELECT caregiver_id FROM shifts WHERE upper(caregiver_id)=? LIMIT 1', (key,)).fetchone()
               or db.execute('SELECT caregiver_id FROM devices WHERE upper(caregiver_id)=? LIMIT 1', (key,)).fetchone())
        return row[0] if row else None
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 打卡與補登
# ---------------------------------------------------------------------------
def _reviews(db, ids):
    if not ids:
        return {}
    marks = ','.join('?' * len(ids))
    out = {}
    for r in db.execute(f'SELECT punch_id, decision FROM reviews WHERE punch_id IN ({marks}) ORDER BY id', list(ids)):
        out[r['punch_id']] = r['decision']              # 以最後一次覆核為準
    return out


def _with_review(db, rows):
    rows = [dict(r) for r in rows]
    decided = _reviews(db, [r['id'] for r in rows if r['late_entry']])
    for r in rows:
        r['review'] = decided.get(r['id'], REVIEW_PENDING) if r['late_entry'] else ''
    return rows


def effective_punches(punches):
    """一筆班每種打卡實際採用哪一筆：{種類: 打卡 dict}。

    順序：已核准的補登（取最後一筆）→ 現場打卡 → 待覆核的補登（暫時採用，畫面標「補登待覆核」）。已退回的補登不採用。
    punches：同一個任務ID 的打卡 dict（含 review 欄）。
    """
    out = {}
    for kind in KINDS:
        mine = [p for p in punches if p['kind'] == kind]
        approved = [p for p in mine if p['late_entry'] and p.get('review') == REVIEW_APPROVED]
        live = [p for p in mine if not p['late_entry']]
        pending = [p for p in mine if p['late_entry'] and p.get('review') == REVIEW_PENDING]
        if approved:
            out[kind] = approved[-1]
        elif live:
            out[kind] = live[0]
        elif pending:
            out[kind] = pending[-1]
    return out


def shift_state(effective):
    """一筆班的狀態：未開始／服務中／已完成／未遇。effective：effective_punches() 的結果。"""
    if MISSED in effective:
        return '未遇'
    if CLOCK_OUT in effective:
        return '已完成'
    if CLOCK_IN in effective:
        return '服務中'
    return '未開始'


def punches_for_tasks(task_ids, path=None):
    """{任務ID: [打卡 dict（含 review）]}。"""
    task_ids = [t for t in dict.fromkeys(task_ids) if t]
    if not task_ids:
        return {}
    db = connect(path)
    try:
        marks = ','.join('?' * len(task_ids))
        rows = _with_review(db, db.execute(f'SELECT * FROM punches WHERE task_id IN ({marks}) ORDER BY at, id', task_ids))
    finally:
        db.close()
    out = {}
    for r in rows:
        out.setdefault(r['task_id'], []).append(r)
    return out


def add_punch(caregiver_id, task_id, kind, lat=None, lon=None, accuracy=None, at=None, note='',
              gps_allowed=True, path=None):
    """新增一筆打卡。回傳 (成功, 給手機看的訊息)。

    at：None＝現場打卡（時間用主機現在時間）；'HH:MM'＝補登，必須寫原因，狀態待覆核。
        補登可以補沒打到的卡，也可以更正已經打過的卡（原紀錄保留，覆核通過後改用補登的時間）。
    gps_allowed：只有 https 連線才記位置（server.py 依連線決定）；補登一律不記位置。
    """
    if kind not in KINDS:
        return False, '打卡類型不正確。'
    stamp = now()
    today = stamp.date()
    note = _text(note)[:200]
    late = at is not None
    if late:
        if kind == MISSED:
            return False, '未遇請直接按「未遇」，不需要補登。'
        if not note:
            return False, '補登請寫原因（例如：手機沒電）。'
        m = re.fullmatch(r'(\d{1,2}):(\d{2})', _text(at))
        if not m or int(m[1]) > 23 or int(m[2]) > 59:
            return False, '補登時間的格式是 HH:MM，例如 08:30。'
        moment = datetime.combine(today, datetime.min.time()).replace(hour=int(m[1]), minute=int(m[2]))
        if moment > stamp:
            return False, '補登時間不能晚於現在。'
    else:
        moment = stamp
    lat, lon, accuracy = _num(lat), _num(lon), _num(accuracy)
    if late or not gps_allowed or lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        lat = lon = accuracy = None
    db = connect(path)
    try:
        shift = db.execute('SELECT * FROM shifts WHERE task_id=? AND caregiver_id=?', (task_id, caregiver_id)).fetchone()
        if shift is None or shift['day'] != today.isoformat():
            return False, '這筆不是你今天的班；臨時代班請聯絡居督重新發布班表。'
        mine = _with_review(db, db.execute('SELECT * FROM punches WHERE task_id=? ORDER BY at, id', (task_id,)))
        mine = [p for p in mine if p.get('review') != REVIEW_REJECTED]
        live = {p['kind'] for p in mine if not p['late_entry']}
        done = effective_punches(mine)
        if MISSED in done:
            return False, '這筆班已登錄未遇。'
        if not late and kind in live:
            return False, f'這筆班已經打過「{kind}」了，不用重複打卡。打錯時間請用「補登」更正。'
        if late and any(p['late_entry'] and p['kind'] == kind and p['review'] == REVIEW_PENDING for p in mine):
            return False, f'「{kind}」已經有一筆補登在等居督覆核。'
        if kind == CLOCK_OUT and CLOCK_IN not in done:
            return False, '還沒有上班打卡。忘記打卡請先用「補登」補上班時間。'
        if kind == MISSED and (CLOCK_IN in done or CLOCK_OUT in done):
            return False, '已經上班打卡的班不能改成未遇，請聯絡居督。'
        if kind == CLOCK_OUT and _stamp(moment) < done[CLOCK_IN]['at']:
            return False, '下班時間不能早於上班時間。'
        if kind == CLOCK_IN and late and CLOCK_OUT in done and _stamp(moment) > done[CLOCK_OUT]['at']:
            return False, '上班時間不能晚於下班時間。'
        with db:
            db.execute('INSERT INTO punches(caregiver_id, client_id, task_id, kind, at, recorded_at, lat, lon, accuracy,'
                       ' late_entry, note) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (caregiver_id, shift['client_id'], task_id, kind, _stamp(moment), _stamp(stamp),
                        lat, lon, accuracy, int(late), note))
    finally:
        db.close()
    if kind == MISSED:
        head = f'已登錄未遇 {moment:%H:%M}，請記得通知居督'
    else:
        head = f'{kind}打卡完成 {moment:%H:%M}'
    if late:
        return True, head + '（補登，等居督覆核）'
    return True, head + ('' if lat is not None else '（這次沒有記錄位置）')


def review_punch(punch_id, approve, account='', note='', path=None):
    """居督覆核一筆補登；只新增覆核紀錄，不改打卡本身。回傳錯誤訊息或 None。"""
    db = connect(path)
    try:
        row = db.execute('SELECT late_entry FROM punches WHERE id=?', (int(punch_id),)).fetchone()
        if row is None or not row['late_entry']:
            return '找不到這筆補登。'
        with db:
            db.execute('INSERT INTO reviews(punch_id, decision, account, at, note) VALUES(?,?,?,?,?)',
                       (int(punch_id), REVIEW_APPROVED if approve else REVIEW_REJECTED, _text(account)[:60],
                        _stamp(now()), _text(note)[:200]))
    finally:
        db.close()
    return None


def pending_reviews(path=None):
    """待覆核的補登（新的在前），表格欄位已是中文。"""
    db = connect(path)
    try:
        rows = _with_review(db, db.execute('SELECT * FROM punches WHERE late_entry=1 AND task_id NOT LIKE ? ORDER BY id DESC',
                                           (DEMO_PREFIX + '%',)))
    finally:
        db.close()
    return [{'紀錄ID': r['id'], '日期': r['at'][:10], '居服員ID': r['caregiver_id'], '案家ID': r['client_id'],
             '任務ID': r['task_id'], '打卡類型': r['kind'], '補登時間': r['at'][11:16], '登錄時間': r['recorded_at'][5:16],
             '原因': r['note']} for r in rows if r['review'] == REVIEW_PENDING]


PUNCH_COLUMNS = ['紀錄ID', '日期', '居服員ID', '案家ID', '任務ID', '打卡類型', '打卡時間', '登錄時間', '補登', '覆核',
                 '緯度', '經度', '定位精度(公尺)', '備註']


def punch_frame(start=None, end=None, path=None):
    """期間內所有打卡（一列一次打卡，含補登與覆核狀態），給 attendance_reconcile 用。start／end 為 date（含）。

    示範班（DEMO-）不算。
    """
    db = connect(path)
    try:
        sql, args = 'SELECT * FROM punches WHERE task_id NOT LIKE ?', [DEMO_PREFIX + '%']
        if start:
            sql += ' AND at >= ?'
            args.append(start.isoformat())
        if end:
            sql += ' AND at < ?'
            args.append((end + timedelta(days=1)).isoformat())
        rows = _with_review(db, db.execute(sql + ' ORDER BY at, id', args))
    finally:
        db.close()
    out = [{'紀錄ID': r['id'], '日期': r['at'][:10], '居服員ID': r['caregiver_id'], '案家ID': r['client_id'],
            '任務ID': r['task_id'], '打卡類型': r['kind'], '打卡時間': r['at'], '登錄時間': r['recorded_at'],
            '補登': bool(r['late_entry']), '覆核': r['review'], '緯度': r['lat'], '經度': r['lon'],
            '定位精度(公尺)': r['accuracy'], '備註': r['note']} for r in rows]
    return pd.DataFrame(out, columns=PUNCH_COLUMNS)


# ---------------------------------------------------------------------------
# 當日打卡看板（04 頁）
# ---------------------------------------------------------------------------
def distance_m(lat1, lon1, lat2, lon2):
    """兩點直線距離（公尺）；任一點缺座標回傳 None。"""
    vals = [_num(v) for v in (lat1, lon1, lat2, lon2)]
    if any(v is None for v in vals):
        return None
    lat1, lon1, lat2, lon2 = map(math.radians, vals)
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371000.0 * 2 * math.asin(min(1.0, math.sqrt(a)))


def is_overdue(day, start, moment, overdue_mins=15):
    """今天的班已經過了開始時間 overdue_mins 分鐘還沒上班打卡 → True。"""
    clock = _clock(start)
    if not clock or day != moment.date():
        return False
    hh, mm = map(int, clock.split(':'))
    begin = datetime.combine(day, datetime.min.time()).replace(hour=hh, minute=mm)
    return moment >= begin + timedelta(minutes=float(overdue_mins))


BOARD_COLUMNS = ['任務ID', '時段', '案家ID', '居服員ID', '狀態', '上班', '下班', '上班距案家(公尺)', '下班距案家(公尺)', '提醒']


def day_board(day, path=None, moment=None, overdue_mins=15, gps_radius_m=300):
    """某一天已發布的班 × 打卡，一班一列。

    過了開始時間 overdue_mins 分鐘還沒上班打卡標「逾時未打卡」；打卡位置離案家超過 gps_radius_m 公尺只在「提醒」欄提示
    （GPS 可能有誤差或被偽造，只當提醒，不當懲處依據）。
    """
    moment = moment or now()
    db = connect(path)
    try:
        shifts = [dict(r) for r in db.execute('SELECT * FROM shifts WHERE day=? ORDER BY start, caregiver_id, task_id',
                                             (day.isoformat(),))]
    finally:
        db.close()
    punches = punches_for_tasks([s['task_id'] for s in shifts], path)
    rows = []
    for s in shifts:
        mine = [p for p in punches.get(s['task_id'], []) if p.get('review') != REVIEW_REJECTED]
        eff = effective_punches(mine)
        state = shift_state(eff)
        if state == '未開始' and is_overdue(day, s['start'], moment, overdue_mins):
            state = '逾時未打卡'
        notes = []
        if any(p['late_entry'] and p['review'] == REVIEW_PENDING for p in mine):
            notes.append('補登待覆核')
        dist = {}
        for kind in (CLOCK_IN, CLOCK_OUT):
            p = eff.get(kind)
            d = distance_m(p['lat'], p['lon'], s['lat'], s['lon']) if p else None
            dist[kind] = round(d) if d is not None else None
            if d is not None and d > gps_radius_m:
                notes.append(f'{kind}位置離案家約 {round(d):,} 公尺（僅提醒）')
            if p and not p['late_entry'] and p['lat'] is None:
                notes.append(f'{kind}沒有位置')
        for p in mine:
            if p['note'] and p['kind'] != MISSED:
                notes.append(p['note'])
        if MISSED in eff:
            notes.append('未遇，請確認案家狀況')
        rows.append({'任務ID': s['task_id'], '時段': f"{s['start']}～{s['end']}", '案家ID': s['client_id'],
                     '居服員ID': s['caregiver_id'], '狀態': state,
                     '上班': eff[CLOCK_IN]['at'][11:16] if CLOCK_IN in eff else '',
                     '下班': eff[CLOCK_OUT]['at'][11:16] if CLOCK_OUT in eff else '',
                     '上班距案家(公尺)': dist[CLOCK_IN], '下班距案家(公尺)': dist[CLOCK_OUT],
                     '提醒': '、'.join(dict.fromkeys(notes))})
    return pd.DataFrame(rows, columns=BOARD_COLUMNS)


# ---------------------------------------------------------------------------
# 手機綁定：居服員只輸入員工編號。
# - 這個編號還沒綁手機 → 第一支手機自動綁定，直接可以打卡（04 頁可關掉自動綁定，改成每支都要核准）。
# - 已經綁了別支手機 → 新手機變成「待核准」，居督核准後才能用，舊手機同時解除（一人一支手機）。
# 手機上只存一組隨機綁定碼（cookie），資料庫只存它的 sha256；居督隨時可以解除。
# ---------------------------------------------------------------------------
AUTO_BIND_KEY = 'auto_bind_first_device'
DEVICE_ACTIVE, DEVICE_PENDING, DEVICE_REVOKED, DEVICE_REJECTED = 'active', 'pending', 'revoked', 'rejected'
DEVICE_STATUS_TEXT = {DEVICE_ACTIVE: '使用中', DEVICE_PENDING: '待核准', DEVICE_REVOKED: '已解除', DEVICE_REJECTED: '未核准'}


def token_hash(token):
    return hashlib.sha256(str(token).encode()).hexdigest()


def device_label(user_agent):
    """從瀏覽器資訊猜手機種類，讓居督認得是哪一支（例：iPhone・Safari、Android 14・Chrome）。"""
    ua = _text(user_agent)
    if 'iPhone' in ua:
        phone = 'iPhone'
    elif 'iPad' in ua:
        phone = 'iPad'
    elif 'Android' in ua:
        m = re.search(r'Android (\d+)', ua)
        phone = 'Android' + (f' {m.group(1)}' if m else '')
    elif 'Windows' in ua:
        phone = 'Windows 電腦'
    elif 'Macintosh' in ua:
        phone = 'Mac 電腦'
    else:
        phone = '其他裝置'
    browser = ('LINE' if ' Line/' in ua else 'Edge' if 'Edg/' in ua else 'Chrome' if ('Chrome/' in ua or 'CriOS' in ua)
               else 'Safari' if 'Safari/' in ua else '瀏覽器')
    return f'{phone}・{browser}'


def get_setting(key, default='', path=None):
    db = connect(path)
    try:
        row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return row['value'] if row else default
    finally:
        db.close()


def set_setting(key, value, path=None):
    db = connect(path)
    try:
        with db:
            if _text(value):
                db.execute('INSERT OR REPLACE INTO settings VALUES(?, ?)', (key, _text(value)))
            else:
                db.execute('DELETE FROM settings WHERE key=?', (key,))
    finally:
        db.close()


def auto_bind_enabled(path=None):
    return get_setting(AUTO_BIND_KEY, '1', path=path) != '0'


def secret_key(path=None):
    """打卡網頁的 session 金鑰：第一次啟動時產生並存進資料庫，重開主機不會把大家登出。"""
    env = os.getenv('CAREFLOW_CHECKIN_SECRET')
    if env:
        return env
    key = get_setting('secret_key', path=path)
    if not key:
        key = secrets.token_hex(32)
        set_setting('secret_key', key, path=path)
    return key


def request_device(caregiver_id, user_agent='', path=None):
    """這支手機第一次用這個編號登入。回傳 (綁定碼明碼, 狀態)；明碼只給手機存一次，資料庫只存雜湊。

    狀態 active＝可以直接打卡；pending＝等居督核准。
    """
    token = secrets.token_urlsafe(32)
    stamp = _stamp(now())
    db = connect(path)
    try:
        with db:
            has_active = db.execute('SELECT 1 FROM devices WHERE caregiver_id=? AND status=?',
                                    (caregiver_id, DEVICE_ACTIVE)).fetchone()
            status = DEVICE_PENDING if has_active or not auto_bind_enabled(path) else DEVICE_ACTIVE
            # 同一人同時只留一筆待核准，避免重複按出很多筆
            db.execute('UPDATE devices SET status=?, decided_at=? WHERE caregiver_id=? AND status=?',
                       (DEVICE_REJECTED, stamp, caregiver_id, DEVICE_PENDING))
            db.execute('INSERT INTO devices(caregiver_id, token_hash, label, status, created_at, decided_at, last_seen)'
                       ' VALUES(?,?,?,?,?,?,?)', (caregiver_id, token_hash(token), device_label(user_agent)[:60], status,
                                                  stamp, stamp if status == DEVICE_ACTIVE else None, stamp))
    finally:
        db.close()
    return token, status


def device_for_token(token, path=None, touch=True):
    """手機 cookie 裡的綁定碼 → 綁定紀錄（dict）；查不到回傳 None。"""
    if not token:
        return None
    db = connect(path)
    try:
        row = db.execute('SELECT * FROM devices WHERE token_hash=?', (token_hash(token),)).fetchone()
        if row and touch and row['status'] == DEVICE_ACTIVE:
            with db:
                db.execute('UPDATE devices SET last_seen=? WHERE id=?', (_stamp(now()), row['id']))
        return dict(row) if row else None
    finally:
        db.close()


def decide_device(device_id, approve, path=None):
    """居督核准或拒絕一支待核准的手機。核准時同一人的舊手機自動解除。回傳居服員ID，失敗回傳 None。"""
    stamp = _stamp(now())
    db = connect(path)
    try:
        row = db.execute('SELECT * FROM devices WHERE id=?', (int(device_id),)).fetchone()
        if row is None or row['status'] != DEVICE_PENDING:
            return None
        with db:
            if approve:
                db.execute('UPDATE devices SET status=?, decided_at=? WHERE caregiver_id=? AND status=?',
                           (DEVICE_REVOKED, stamp, row['caregiver_id'], DEVICE_ACTIVE))
            db.execute('UPDATE devices SET status=?, decided_at=? WHERE id=?',
                       (DEVICE_ACTIVE if approve else DEVICE_REJECTED, stamp, row['id']))
        return row['caregiver_id']
    finally:
        db.close()


def revoke_device(device_id, path=None):
    """解除綁定（手機遺失、離職、綁錯人）。這支手機下次開頁面就要重新輸入編號。回傳居服員ID 或 None。"""
    db = connect(path)
    try:
        row = db.execute('SELECT caregiver_id FROM devices WHERE id=? AND status IN (?, ?)',
                         (int(device_id), DEVICE_ACTIVE, DEVICE_PENDING)).fetchone()
        if row is None:
            return None
        with db:
            db.execute('UPDATE devices SET status=?, decided_at=? WHERE id=?', (DEVICE_REVOKED, _stamp(now()), int(device_id)))
        return row['caregiver_id']
    finally:
        db.close()


def devices(status=None, path=None):
    db = connect(path)
    try:
        sql, args = 'SELECT id, caregiver_id, label, status, created_at, decided_at, last_seen FROM devices', ()
        if status:
            sql, args = sql + ' WHERE status=?', (status,)
        return [dict(r) for r in db.execute(sql + ' ORDER BY created_at DESC, id DESC', args)]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 示範班：給居督第一次試用。今天、現在開始的一筆班，不設案家位置，不進執行對照，可一鍵清除。
# ---------------------------------------------------------------------------
def add_demo_shift(caregiver_id, minutes=60, path=None):
    caregiver_id = _text(caregiver_id)
    start = now().replace(second=0)
    end = min(start + timedelta(minutes=minutes), start.replace(hour=23, minute=59))
    task_id = f'{DEMO_PREFIX}{start:%Y%m%d%H%M}-{caregiver_id}'
    clear_demo(path, caregiver_id)
    db = connect(path)
    try:
        with db:
            db.execute('INSERT OR REPLACE INTO shifts VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       (task_id, start.date().isoformat(), 'DEMO', caregiver_id, f'{start:%H:%M}', f'{end:%H:%M}',
                        float(minutes), '示範案家', '示範服務', None, None, _stamp(now())))
    finally:
        db.close()
    return task_id


def clear_demo(path=None, caregiver_id=None):
    """刪除示範班與示範打卡（只動 DEMO- 開頭的資料，正式打卡不受影響）。回傳刪除的班數。"""
    like = DEMO_PREFIX + '%'
    db = connect(path)
    try:
        with db:
            if caregiver_id:
                tasks = [r[0] for r in db.execute('SELECT task_id FROM shifts WHERE task_id LIKE ? AND caregiver_id=?',
                                                  (like, caregiver_id))]
            else:
                tasks = [r[0] for r in db.execute('SELECT task_id FROM shifts WHERE task_id LIKE ?', (like,))]
            db.executemany('DELETE FROM punches WHERE task_id=?', [(t,) for t in tasks])
            db.executemany('DELETE FROM shifts WHERE task_id=?', [(t,) for t in tasks])
        return len(tasks)
    finally:
        db.close()
