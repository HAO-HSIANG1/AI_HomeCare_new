"""登入與權限：密碼驗證、帳號鎖定、防止用時間差猜帳號、角色權限、最後一位主管的保護，以及登入頁流程。"""
from pathlib import Path

import pytest

import audit_log
import auth


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / 'accounts.sqlite3')


@pytest.fixture
def fast_hash(monkeypatch):
    """測試用較少的雜湊次數（正式仍是 20 萬次）；並記錄每次雜湊，檢查帳號不存在時也有算。"""
    calls = []
    real = auth._hash

    def counted(password, salt):
        calls.append(salt)
        return real(password, salt)

    monkeypatch.setattr(auth, 'PBKDF2_ROUNDS', 1000)
    monkeypatch.setattr(auth, '_hash', counted)
    return calls


# ---------------------------------------------------------------- 密碼驗證
def test_password_rules_and_hash_storage(db, fast_hash):
    assert auth.create_user('boss', '王主管', '主管', 'short', db) == f'密碼至少 {auth.MIN_PASSWORD_LENGTH} 個字。'
    assert auth.password_error('secret123', 'secret124') == '兩次輸入的密碼不一樣。'
    assert '英文字母或數字' in auth.create_user('王', '王主管', '主管', 'secret123', db)
    assert auth.create_user('boss', '', '主管', 'secret123', db) == '請填寫姓名。'
    assert auth.create_user('boss', '王主管', '組長', 'secret123', db) == '角色只能是主管或居督。'

    assert auth.create_user('Boss', '王主管', '主管', 'secret123', db) is None
    assert auth.create_user('amy01', '林居督', '居督', 'secret123', db) is None
    assert auth.create_user('BOSS', '另一位', '居督', 'secret123', db) == '帳號 boss 已經有人使用。'

    user, message = auth.verify(' BOSS ', 'secret123', db)            # 帳號不分大小寫、去空白
    assert user == {'username': 'boss', 'name': '王主管', 'role': '主管'} and message == '登入成功。'
    assert auth.verify('boss', 'Secret123', db) == (None, auth.WRONG_LOGIN)   # 密碼分大小寫

    import sqlite3
    with sqlite3.connect(db) as conn:
        rows = conn.execute('SELECT salt, pw_hash FROM users ORDER BY username').fetchall()
    assert rows[0][0] != rows[1][0]                                    # 每個帳號各自的鹽
    assert rows[0][1] != rows[1][1]                                    # 同一個密碼，雜湊也不同
    assert b'secret123' not in Path(db).read_bytes()                   # 不存明碼


def test_default_strength_is_pbkdf2_sha256_200k():
    assert auth.PBKDF2_ROUNDS == 200_000
    salt = '11' * 16
    import hashlib
    assert auth._hash('secret123', salt) == hashlib.pbkdf2_hmac('sha256', b'secret123', bytes.fromhex(salt), 200_000).hex()


def test_unknown_or_disabled_account_still_hashes(db, fast_hash):
    auth.create_user('boss', '王主管', '主管', 'secret123', db)
    auth.create_user('amy01', '林居督', '居督', 'secret123', db)
    fast_hash.clear()
    assert auth.verify('nobody', 'secret123', db) == (None, auth.WRONG_LOGIN)
    assert len(fast_hash) == 1                                         # 帳號不存在也算一次雜湊
    auth.set_active('amy01', False, db)
    fast_hash.clear()
    assert auth.verify('amy01', 'secret123', db) == (None, auth.WRONG_LOGIN)   # 停用與不存在同一句話
    assert len(fast_hash) == 1


# ---------------------------------------------------------------- 帳號鎖定
def test_lockout_after_five_failures_and_unlock(db, fast_hash):
    auth.create_user('boss', '王主管', '主管', 'secret123', db)
    auth.create_user('amy01', '林居督', '居督', 'secret123', db)
    now = 1_000_000.0
    for i in range(auth.MAX_FAILED - 1):
        assert auth.verify('amy01', 'wrong-pass', db, now=now + i) == (None, auth.WRONG_LOGIN)
    user, message = auth.verify('amy01', 'wrong-pass', db, now=now + 4)
    assert user is None and '帳號鎖定 10 分鐘' in message                 # 第 5 次鎖定

    user, message = auth.verify('amy01', 'secret123', db, now=now + 60)
    assert user is None and '請 10 分鐘後再試' in message                # 鎖定中密碼正確也不能進
    assert next(u for u in auth.users(db, now=now + 60) if u['username'] == 'amy01')['locked']

    assert auth.verify('amy01', 'secret123', db, now=now + 4 + auth.LOCK_SECONDS + 1)[0] is not None   # 10 分鐘後恢復

    for i in range(auth.MAX_FAILED):
        auth.verify('amy01', 'wrong-pass', db, now=now + 2000 + i)
    assert auth.set_password('amy01', 'newpass99', db) is None         # 主管重設密碼同時解鎖
    assert auth.verify('amy01', 'newpass99', db, now=now + 2010)[0]['username'] == 'amy01'


def test_success_resets_failure_count(db, fast_hash):
    auth.create_user('amy01', '林居督', '居督', 'secret123', db)
    for _ in range(auth.MAX_FAILED - 1):
        auth.verify('amy01', 'wrong-pass', db)
    assert auth.verify('amy01', 'secret123', db)[0] is not None
    for _ in range(auth.MAX_FAILED - 1):                                # 成功一次後重新計算
        assert auth.verify('amy01', 'wrong-pass', db) == (None, auth.WRONG_LOGIN)


def test_change_own_password_needs_current_password(db, fast_hash):
    auth.create_user('amy01', '林居督', '居督', 'secret123', db)
    assert auth.change_own_password('amy01', 'wrong-pass', 'newpass99', 'newpass99', db) == '目前的密碼不正確。'
    assert auth.change_own_password('amy01', 'secret123', 'newpass99', 'other999', db) == '兩次輸入的密碼不一樣。'
    assert auth.change_own_password('amy01', 'secret123', 'newpass99', 'newpass99', db) is None
    assert auth.verify('amy01', 'newpass99', db)[0] is not None
    assert auth.set_password('ghost', 'newpass99', db) == '找不到這個帳號。'


# ---------------------------------------------------------------- 角色權限
def test_role_permissions():
    for module in ('import', 'schedule', 'issues', 'review', 'analytics', 'accounts'):
        assert auth.can_access('主管', module)
    for module in ('import', 'schedule', 'issues', 'review'):
        assert auth.can_access('居督', module)
    assert not auth.can_access('居督', 'analytics')
    assert not auth.can_access('居督', 'accounts')
    assert not auth.can_access(None, 'import')                          # 沒登入什麼都不能進
    assert not auth.can_access('訪客', 'import')


def test_module_codes_match_ui():
    pytest.importorskip('streamlit')
    from careflow_ui import MODULE_KEYS, _MODULE_INFO
    assert set(auth.MANAGER_ONLY_MODULES) <= set(MODULE_KEYS)
    assert all(_MODULE_INFO[m][4] == '主管' for m in auth.MANAGER_ONLY_MODULES)   # 頁首角色徽章與權限一致


def test_current_user_follows_disable_and_enabled_switch(db, fast_hash, monkeypatch):
    auth.create_user('boss', '王主管', '主管', 'secret123', db)
    auth.create_user('amy01', '林居督', '居督', 'secret123', db)
    assert auth.current_user('AMY01', db) == {'username': 'amy01', 'name': '林居督', 'role': '居督'}
    auth.set_active('amy01', False, db)
    assert auth.current_user('amy01', db) is None                       # 停用後已登入的人會被登出
    assert auth.current_user(None, db) is None
    for value, expected in (('0', False), ('off', False), ('FALSE', False), ('no', False), ('1', True), ('', True)):
        monkeypatch.setenv('CAREFLOW_AUTH', value)
        assert auth.enabled() is expected
    monkeypatch.delenv('CAREFLOW_AUTH')
    assert auth.enabled()                                               # 沒設定時預設開啟


# ---------------------------------------------------------------- 最後一位主管
def test_last_manager_cannot_be_disabled(db, fast_hash):
    assert not auth.has_users(db)
    assert auth.create_first_manager('boss', '王主管', 'secret123', db) is None
    assert auth.create_first_manager('boss2', '別人', 'secret123', db) == '系統已經有帳號了，請直接登入。'
    auth.create_user('amy01', '林居督', '居督', 'secret123', db)

    assert '最後一位主管' in auth.set_active('boss', False, db)
    assert auth.verify('boss', 'secret123', db)[0] is not None          # 仍然可以登入
    assert auth.set_active('amy01', False, db) is None                  # 停用居督沒問題

    auth.create_user('boss2', '李主管', '主管', 'secret123', db)
    assert auth.set_active('boss', False, db) is None                   # 有兩位主管時可以停用其中一位
    assert '最後一位主管' in auth.set_active('boss2', False, db)          # 剩一位又要擋
    assert auth.set_active('boss', True, db) is None
    assert auth.set_active('ghost', False, db) == '找不到這個帳號。'
    assert [u['username'] for u in auth.users(db) if u['role'] == '主管' and u['active']] == ['boss', 'boss2']


# ---------------------------------------------------------------- 登入頁流程（需要 streamlit）
def _app(tmp_path, monkeypatch):
    testing = pytest.importorskip('streamlit.testing.v1')
    import caregiver_engine as engine
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('CAREFLOW_AGENCY_DIR', str(tmp_path))            # 沒有機構 Excel，只看登入與權限
    monkeypatch.setenv('CAREFLOW_AUTH', '1')
    monkeypatch.setattr(auth, 'PBKDF2_ROUNDS', 1000)
    return testing.AppTest.from_file(str(Path(engine.__file__).with_name('app.py')), default_timeout=90)


def _submit(app, label):
    next(b for b in app.button if b.label == label).click().run()
    assert not app.exception, [e.message for e in app.exception]


def test_first_run_setup_then_roles(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch).run()
    assert not app.exception, [e.message for e in app.exception]
    page = ' '.join(m.value for m in app.markdown)
    assert '建立主管帳號' in page
    assert not [b for b in app.button if b.key and b.key.startswith('cfnav_')]   # 沒登入看不到步驟列

    app.text_input(key='setup_user').input('boss')
    app.text_input(key='setup_name').input('王主管')
    app.text_input(key='setup_pw1').input('secret123')
    app.text_input(key='setup_pw2').input('secret123')
    _submit(app, '建立主管帳號並登入')
    assert app.session_state['auth_user']['role'] == '主管'
    assert any('王主管（主管）' in c.value for c in app.sidebar.caption)
    assert app.button(key='cfnav_analytics').help != '只有主管帳號可以使用'      # 主管只等班表產生
    app.button(key='auth_open_accounts').click().run()
    assert not app.exception, [e.message for e in app.exception]
    assert '目前帳號 · 1 個' in ' '.join(m.value for m in app.markdown)

    assert auth.create_user('amy01', '林居督', '居督', 'secret123') is None
    app.button(key='auth_logout').click().run()
    assert 'auth_user' not in app.session_state
    app.text_input(key='login_user').input('amy01')
    app.text_input(key='login_pw').input('wrong-pass')
    _submit(app, '登入')
    assert any(auth.WRONG_LOGIN in e.value for e in app.error)
    app.text_input(key='login_pw').input('secret123')
    _submit(app, '登入')
    assert app.session_state['auth_user']['role'] == '居督'
    assert app.button(key='cfnav_analytics').disabled
    assert app.button(key='cfnav_analytics').help == '只有主管帳號可以使用'   # 居督不能進主管報表
    assert not [b for b in app.button if b.key == 'auth_open_accounts']  # 居督沒有帳號管理

    events = audit_log.entries()
    assert [e['event'] for e in events] == ['account', 'login', 'logout', 'login_failed', 'login']
    assert [e['account'] for e in events] == ['boss', 'boss', 'boss', 'amy01', 'amy01']
    assert audit_log.verify()['ok']


def test_auth_off_skips_login(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    monkeypatch.setenv('CAREFLOW_AUTH', '0')
    app.run()
    assert not app.exception, [e.message for e in app.exception]
    assert app.button(key='cfnav_import')                              # 直接看到步驟列
    assert any('CAREFLOW_AUTH=0' in c.value for c in app.sidebar.caption)
