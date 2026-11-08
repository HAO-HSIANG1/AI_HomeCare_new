"""登入與權限：內建帳號密碼（純函式，不呼叫 Streamlit；畫面在 app.py 與 careflow_ui.auth_card）。

- 帳號存在本機 output_results/accounts.sqlite3（可用 CAREFLOW_ACCOUNTS_DB 指定）。
- 密碼只存 PBKDF2-SHA256 雜湊（20 萬次、每個帳號各自的 16 位元組鹽），系統與主管都看不到原本的密碼。
- 連續輸錯 5 次鎖 10 分鐘；帳號不存在、已停用、鎖定中也會算一次雜湊，回應時間一樣，不能用時間差猜帳號。
- 角色：主管（全部模組＋帳號管理＋主管報表）、居督（① 匯入資料～④ 確認班表）。
- 至少要保留一位可以登入的主管，最後一位主管不能停用。
- 本機開發可設 CAREFLOW_AUTH=0 關閉登入（也接受 off／false／no）。

錯誤一律回傳中文說明字串（成功回傳 None），不丟例外，由畫面直接顯示。
"""
CAREFLOW_BUILD = '2026.10.18-v19'
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

MANAGER = '主管'
SUPERVISOR = '居督'
ROLES = (MANAGER, SUPERVISOR)
MANAGER_ONLY_MODULES = ('analytics', 'accounts')   # careflow_ui.MODULES 的代碼；其餘模組兩種角色都能進

PBKDF2_ROUNDS = 200_000
MAX_FAILED = 5
LOCK_SECONDS = 10 * 60
MIN_PASSWORD_LENGTH = 8
_USERNAME = re.compile(r'^[a-z0-9][a-z0-9._-]{2,31}$')
_DUMMY_SALT = '00' * 16
WRONG_LOGIN = '帳號或密碼不正確。'


def enabled():
    """是否啟用登入；CAREFLOW_AUTH=0／off／false／no 時關閉（本機開發用）。"""
    return os.getenv('CAREFLOW_AUTH', '1').strip().lower() not in ('0', 'off', 'false', 'no')


def db_path(path=None):
    return Path(path or os.getenv('CAREFLOW_ACCOUNTS_DB') or Path(__file__).parent / 'output_results' / 'accounts.sqlite3')


def _connect(path=None):
    target = db_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(target, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL, '
               'salt TEXT NOT NULL, pw_hash TEXT NOT NULL, failed INTEGER NOT NULL DEFAULT 0, '
               'locked_until REAL NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, '
               'created_at TEXT NOT NULL, last_login TEXT)')
    return db


def _now_text():
    return datetime.now(ZoneInfo('Asia/Taipei')).isoformat(timespec='seconds')


def _hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', str(password or '').encode('utf-8'), bytes.fromhex(salt), PBKDF2_ROUNDS).hex()


def normalize_username(username):
    """帳號不分大小寫、去掉前後空白。"""
    return str(username or '').strip().lower()


def password_error(password, confirm=None):
    """密碼規則；不符合時回傳說明，符合時回傳 None。confirm 有給時一併檢查兩次輸入是否相同。"""
    if len(str(password or '')) < MIN_PASSWORD_LENGTH:
        return f'密碼至少 {MIN_PASSWORD_LENGTH} 個字。'
    if confirm is not None and password != confirm:
        return '兩次輸入的密碼不一樣。'
    return None


def _user_error(username, name, role, password):
    if not _USERNAME.match(username):
        return '帳號請用 3～32 個英文字母或數字（可含 . _ -），開頭要是英文或數字。'
    if role not in ROLES:
        return '角色只能是主管或居督。'
    if not str(name or '').strip():
        return '請填寫姓名。'
    return password_error(password)


def has_users(path=None):
    db = _connect(path)
    try:
        return db.execute('SELECT 1 FROM users LIMIT 1').fetchone() is not None
    finally:
        db.close()


def _insert(db, username, name, role, password):
    salt = secrets.token_hex(16)
    db.execute('INSERT INTO users(username, name, role, salt, pw_hash, created_at) VALUES(?,?,?,?,?,?)',
               (username, str(name).strip(), role, salt, _hash(password, salt), _now_text()))


def create_user(username, name, role, password, path=None):
    """新增帳號；成功回傳 None，失敗回傳說明。"""
    username = normalize_username(username)
    problem = _user_error(username, name, role, password)
    if problem:
        return problem
    db = _connect(path)
    try:
        with db:
            if db.execute('SELECT 1 FROM users WHERE username=?', (username,)).fetchone():
                return f'帳號 {username} 已經有人使用。'
            _insert(db, username, name, role, password)
    finally:
        db.close()
    return None


def create_first_manager(username, name, password, path=None):
    """第一次使用：還沒有任何帳號時建立第一位主管。已經有帳號就拒絕（避免任何人重建主管）。"""
    username = normalize_username(username)
    problem = _user_error(username, name, MANAGER, password)
    if problem:
        return problem
    db = _connect(path)
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                return '系統已經有帳號了，請直接登入。'
            _insert(db, username, name, MANAGER, password)
    finally:
        db.close()
    return None


def verify(username, password, path=None, now=None):
    """登入檢查。回傳 (使用者 dict 或 None, 訊息)。

    帳號不存在、已停用、鎖定中都會算一次雜湊再回應；不存在與停用回一樣的訊息。
    連續輸錯 MAX_FAILED 次鎖定 LOCK_SECONDS 秒，期間密碼正確也不能登入；主管重設密碼即解鎖。
    """
    username = normalize_username(username)
    now = time.time() if now is None else now
    db = _connect(path)
    try:
        row = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        if row is None or not row['active']:
            _hash(password, _DUMMY_SALT)
            return None, WRONG_LOGIN
        if row['locked_until'] > now:
            _hash(password, _DUMMY_SALT)
            minutes = int((row['locked_until'] - now) // 60) + 1
            return None, f'密碼輸錯太多次，請 {minutes} 分鐘後再試，或請主管重設密碼。'
        if hmac.compare_digest(_hash(password, row['salt']), row['pw_hash']):
            with db:
                db.execute('UPDATE users SET failed=0, locked_until=0, last_login=? WHERE username=?', (_now_text(), username))
            return {'username': username, 'name': row['name'], 'role': row['role']}, '登入成功。'
        failed = row['failed'] + 1
        locked_until = now + LOCK_SECONDS if failed >= MAX_FAILED else 0
        with db:
            db.execute('UPDATE users SET failed=?, locked_until=? WHERE username=?',
                       (0 if locked_until else failed, locked_until, username))
        if locked_until:
            return None, WRONG_LOGIN + f'已連續輸錯 {MAX_FAILED} 次，帳號鎖定 {LOCK_SECONDS // 60} 分鐘。'
        return None, WRONG_LOGIN
    finally:
        db.close()


def current_user(username, path=None):
    """每次畫面重跑時重新讀取：帳號被停用或刪除就回傳 None（已登入的人會被登出），角色異動立即生效。"""
    if not username:
        return None
    db = _connect(path)
    try:
        row = db.execute('SELECT username, name, role, active FROM users WHERE username=?',
                         (normalize_username(username),)).fetchone()
    finally:
        db.close()
    if row is None or not row['active']:
        return None
    return {'username': row['username'], 'name': row['name'], 'role': row['role']}


def set_password(username, password, path=None):
    """重設密碼（同時解除鎖定）；成功回傳 None，失敗回傳說明。"""
    problem = password_error(password)
    if problem:
        return problem
    salt = secrets.token_hex(16)
    db = _connect(path)
    try:
        with db:
            count = db.execute('UPDATE users SET salt=?, pw_hash=?, failed=0, locked_until=0 WHERE username=?',
                               (salt, _hash(password, salt), normalize_username(username))).rowcount
    finally:
        db.close()
    return None if count else '找不到這個帳號。'


def change_own_password(username, old_password, new_password, confirm, path=None):
    """使用者自己改密碼：要先輸入目前的密碼（輸錯也會累計鎖定次數）。"""
    problem = password_error(new_password, confirm)
    if problem:
        return problem
    user, message = verify(username, old_password, path)
    if user is None:
        return '目前的密碼不正確。' if message == WRONG_LOGIN else message
    return set_password(username, new_password, path)


def set_active(username, active, path=None):
    """啟用／停用帳號；停用會擋下最後一位可以登入的主管。成功回傳 None，失敗回傳說明。"""
    username = normalize_username(username)
    db = _connect(path)
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT role, active FROM users WHERE username=?', (username,)).fetchone()
            if row is None:
                return '找不到這個帳號。'
            if not active and row['role'] == MANAGER and row['active']:
                managers = db.execute('SELECT COUNT(*) FROM users WHERE role=? AND active=1', (MANAGER,)).fetchone()[0]
                if managers <= 1:
                    return '至少要保留一位可以登入的主管，不能停用最後一位主管。'
            db.execute('UPDATE users SET active=?, failed=0, locked_until=0 WHERE username=?', (int(bool(active)), username))
    finally:
        db.close()
    return None


def users(path=None, now=None):
    """帳號清單（不含密碼雜湊與鹽）；locked 表示目前是否鎖定中。"""
    now = time.time() if now is None else now
    db = _connect(path)
    try:
        rows = db.execute('SELECT username, name, role, active, locked_until, created_at, last_login FROM users '
                          'ORDER BY role DESC, username').fetchall()
    finally:
        db.close()
    return [{'username': r['username'], 'name': r['name'], 'role': r['role'], 'active': bool(r['active']),
             'locked': r['locked_until'] > now, 'created_at': r['created_at'], 'last_login': r['last_login']} for r in rows]


def can_access(role, module):
    """角色能不能進入這個模組：主管全部可以；居督不能進主管報表與帳號管理。"""
    if role == MANAGER:
        return True
    return role == SUPERVISOR and module not in MANAGER_ONLY_MODULES
