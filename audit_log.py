"""存取稽核紀錄：只能附加，每筆帶前一筆的雜湊（hash chain），可以檢查有沒有被改過（純函式，不呼叫 Streamlit）。

- 存在 output_results/audit/audit_log.sqlite3（可用 CAREFLOW_AUDIT_DIR 指定資料夾）。
- 資料表有觸發器，UPDATE／DELETE 一律拒絕；verify() 從第一筆重算雜湊，回報第一筆不一致的序號。
- 只記帳號、事件、ID 與筆數；欄位名稱含姓名、地址、電話等字樣的內容寫入前就濾掉。
- 帳號由呼叫端傳入（app.py 傳目前登入的帳號），本模組不讀畫面狀態。
- 寫入失敗不能中斷排班或登入：record() 只回傳 True／False。
"""
CAREFLOW_BUILD = '2026.10.18-v19'
import hashlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

GENESIS = '0' * 64

# 事件代碼 → 畫面顯示名稱。新增事件時加在這裡。
EVENTS = {
    'login': '登入',
    'login_failed': '登入失敗',
    'logout': '登出',
    'account': '帳號異動',
    'checkin': '打卡管理',     # 發布班表、核准／拒絕／解除手機綁定、補登覆核、打卡網址與自動綁定設定（只記 ID）
}

# 欄位名稱含這些字就不寫進紀錄（只記 ID）。帳號代碼請用 target、account 等欄名，不要用 username。
_FORBIDDEN = ('姓名', '地址', '電話', '身分證', '診斷', 'name', 'address', 'phone')


def audit_dir(folder=None):
    return Path(folder or os.getenv('CAREFLOW_AUDIT_DIR') or Path(__file__).parent / 'output_results' / 'audit')


def db_path(folder=None):
    target = audit_dir(folder)
    target.mkdir(parents=True, exist_ok=True)
    return target / 'audit_log.sqlite3'


def _connect(folder=None):
    db = sqlite3.connect(db_path(folder), timeout=15, isolation_level=None)
    db.execute('CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, '
               'account TEXT NOT NULL, event TEXT NOT NULL, detail TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL)')
    db.execute("CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit "
               "BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END")
    db.execute("CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit "
               "BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END")
    return db


def _clean(detail):
    """過濾個資欄位；值一律轉成短字串或數字，避免把整張表寫進來。"""
    out = {}
    for key, value in (detail or {}).items():
        if any(word in str(key).lower() for word in _FORBIDDEN):
            continue
        if isinstance(value, (list, tuple, set)):
            value = [str(v)[:60] for v in value][:50]
        elif value is not None and not isinstance(value, (bool, int, float)):
            value = str(value)[:200]
        out[str(key)] = value
    return out


def _digest(prev_hash, at, account, event, detail_json):
    payload = json.dumps([prev_hash, at, account, event, detail_json], ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def record(event, account='system', folder=None, **detail):
    """附加一筆紀錄；成功回傳 True。失敗（磁碟、鎖定）回傳 False，不丟例外。"""
    try:
        account = str(account or 'system')[:64]
        detail_json = json.dumps(_clean(detail), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        at = datetime.now(ZoneInfo('Asia/Taipei')).isoformat(timespec='seconds')
        db = _connect(folder)
        try:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT hash FROM audit ORDER BY seq DESC LIMIT 1').fetchone()
            prev = row[0] if row else GENESIS
            db.execute('INSERT INTO audit(at, account, event, detail, prev_hash, hash) VALUES(?,?,?,?,?,?)',
                       (at, account, str(event), detail_json, prev, _digest(prev, at, account, str(event), detail_json)))
            db.execute('COMMIT')
        except sqlite3.Error:
            db.execute('ROLLBACK')
            raise
        finally:
            db.close()
        return True
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return False


def entries(limit=None, folder=None):
    """依序號由舊到新回傳全部紀錄（limit：只取最後幾筆）。"""
    db = _connect(folder)
    try:
        rows = db.execute('SELECT seq, at, account, event, detail, prev_hash, hash FROM audit ORDER BY seq').fetchall()
    finally:
        db.close()
    out = [dict(zip(('seq', 'at', 'account', 'event', 'detail', 'prev_hash', 'hash'), r)) for r in rows]
    return out[-limit:] if limit else out


def verify(folder=None):
    """從第一筆重算雜湊鏈。回傳 {'ok', 'count', 'first_bad_seq', 'last_hash'}。"""
    prev, count = GENESIS, 0
    for item in entries(folder=folder):
        count += 1
        expected = _digest(prev, item['at'], item['account'], item['event'], item['detail'])
        if item['prev_hash'] != prev or item['hash'] != expected:
            return {'ok': False, 'count': count, 'first_bad_seq': item['seq'], 'last_hash': prev}
        prev = item['hash']
    return {'ok': True, 'count': count, 'first_bad_seq': None, 'last_hash': prev}


def as_table(limit=50, folder=None):
    """畫面用的表格（新的在上）：序號、時間、帳號、事件、內容。"""
    import pandas as pd
    rows = [{'序號': e['seq'], '時間': e['at'][:19].replace('T', ' '), '帳號': e['account'],
             '事件': EVENTS.get(e['event'], e['event']), '內容': e['detail']}
            for e in reversed(entries(limit=limit, folder=folder))]
    return pd.DataFrame(rows, columns=['序號', '時間', '帳號', '事件', '內容'])
