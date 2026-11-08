"""居服員 QR 打卡：手機綁定、重複打卡、補登與覆核、逾時判斷、只在 https 記位置、不存未遮罩姓名。"""
import re
import sqlite3
from datetime import date, datetime

import pandas as pd
import pytest

from checkin import runner, store

DAY = date(2026, 11, 9)


@pytest.fixture(autouse=True)
def _fresh_tunnel(monkeypatch):
    """外部網址的狀態是模組層級的，每個測試從頭開始。"""
    monkeypatch.setattr(runner, '_tunnel', {'proc': None, 'url': '', 'log': [], 'status': runner.TUNNEL_IDLE,
                                            'error': '', 'user_stopped': False})


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = str(tmp_path / 'checkin.sqlite3')
    monkeypatch.setenv('CAREFLOW_CHECKIN_DB', path)
    monkeypatch.delenv('CAREFLOW_CHECKIN_PUBLIC_URL', raising=False)
    return path


def _clock(monkeypatch, hh, mm):
    """把主機時間固定在 DAY 的 hh:mm。"""
    monkeypatch.setattr(store, 'now', lambda: datetime(2026, 11, 9, hh, mm, 0))


def _schedule():
    # 與 app.py 的 df_final 同欄名；T9 未派，T8 是別天
    return pd.DataFrame({
        '任務ID': ['T1', 'T2', 'T3', 'T8', 'T9'],
        '日期': ['2026-11-09', '2026-11-09', '2026-11-09', '2026-11-10', '2026-11-09'],
        '開始時間': ['09:00', '13:00', '15:00', '09:00', '10:00'],
        '結束時間': ['10:00', '14:00', '16:00', '10:00', '11:00'],
        '案號': ['C1', 'C2', 'C3', 'C1', 'C4'],
        '最終派單居服員': ['E001', 'E001', 'e002', 'E001', '未指派'],
        '服務項目': ['BA02(1.0)', 'BA07', 'BA01', 'BA02', 'BA02'],
        '服務地點_緯度': [25.0] * 5, '服務地點_經度': [121.5] * 5,
    })


def _publish(db, names=None):
    return store.publish_shifts(_schedule(), DAY, names if names is not None else {'C1': '王○○'}, path=db)


# ---- 班表發布與個資 ----
def test_publish_only_the_day_and_assigned_services(db):
    assert _publish(db) == (3, 0)                                    # T8 別天、T9 未派，不發布
    shifts = {s['task_id']: s for s in store.shifts_for('E001', DAY, db)}
    assert set(shifts) == {'T1', 'T2'} and shifts['T1']['service'] == 'BA02(1)'
    small = _schedule().iloc[[0]]                                  # 重新發布：當天這次沒有的班會移除
    assert store.publish_shifts(small, DAY, path=db) == (1, 2)


def test_full_names_never_stored(db):
    _publish(db, {'C1': '王小明', 'C2': '李大華'})
    raw = (pd.read_sql('SELECT * FROM shifts', sqlite3.connect(db)).astype(str).to_string())
    assert '小明' not in raw and '大華' not in raw
    assert {s['client_label'] for s in store.shifts_for('E001', DAY, db)} == {'王○○', '李○○'}


# ---- 手機綁定 ----
def test_first_phone_binds_new_phone_waits_for_approval(db):
    _publish(db)
    assert store.resolve_caregiver(' e001 ', db) == 'E001'          # 不分大小寫、回傳原本的 ID
    assert store.resolve_caregiver('E002', db) == 'e002'
    assert store.resolve_caregiver('X999', db) is None              # 不在班表的編號不建資料
    token1, status1 = store.request_device('E001', 'Mozilla (iPhone) Safari/604', db)
    assert status1 == store.DEVICE_ACTIVE
    stored = sqlite3.connect(db).execute('SELECT token_hash FROM devices').fetchone()[0]
    assert stored == store.token_hash(token1) and token1 not in stored  # 只存雜湊
    token2, status2 = store.request_device('E001', 'Android 14 Chrome/120', db)
    assert status2 == store.DEVICE_PENDING
    pending = store.devices(store.DEVICE_PENDING, db)[0]
    assert pending['label'].startswith('Android 14')
    assert store.decide_device(pending['id'], True, db) == 'E001'
    assert store.device_for_token(token2, db)['status'] == store.DEVICE_ACTIVE
    assert store.device_for_token(token1, db)['status'] == store.DEVICE_REVOKED   # 一人一支手機
    assert store.revoke_device(pending['id'], db) == 'E001'
    assert store.device_for_token(token2, db)['status'] == store.DEVICE_REVOKED


def test_auto_bind_off_requires_approval(db):
    _publish(db)
    store.set_setting(store.AUTO_BIND_KEY, '0', db)
    _, status = store.request_device('E001', '', db)
    assert status == store.DEVICE_PENDING
    _, again = store.request_device('E001', '', db)                 # 重按只留一筆待核准
    assert again == store.DEVICE_PENDING and len(store.devices(store.DEVICE_PENDING, db)) == 1


# ---- 打卡 ----
def test_duplicate_and_out_of_order_punches_rejected(db, monkeypatch):
    _publish(db)
    _clock(monkeypatch, 9, 3)
    assert not store.add_punch('E001', 'T1', '下班', path=db)[0]   # 還沒上班
    ok, msg = store.add_punch('E001', 'T1', '上班', lat=25.0, lon=121.5, path=db)
    assert ok and msg.startswith('上班打卡完成 09:03')
    ok, msg = store.add_punch('E001', 'T1', '上班', path=db)
    assert not ok and '不用重複打卡' in msg
    assert not store.add_punch('E001', 'T1', '未遇', path=db)[0]   # 已上班不能改未遇
    assert not store.add_punch('E002', 'T1', '上班', path=db)[0]   # 不是自己的班
    assert not store.add_punch('E001', 'T8', '上班', path=db)[0]   # 不是今天的班
    _clock(monkeypatch, 9, 58)
    assert store.add_punch('E001', 'T1', '下班', path=db)[0]
    assert not store.add_punch('E001', 'T1', '下班', path=db)[0]
    assert store.add_punch('E001', 'T2', '未遇', path=db)[0]
    assert not store.add_punch('E001', 'T2', '上班', path=db)[0]
    assert len(store.punch_frame(path=db)) == 3


def test_punches_are_append_only(db, monkeypatch):
    _publish(db)
    _clock(monkeypatch, 9, 0)
    store.add_punch('E001', 'T1', '上班', path=db)
    con = sqlite3.connect(db)
    with pytest.raises(sqlite3.DatabaseError, match='append-only'):
        con.execute("UPDATE punches SET at='2026-11-09 08:00:00'")
    with pytest.raises(sqlite3.DatabaseError, match='append-only'):
        con.execute('DELETE FROM punches')


def test_late_entry_needs_reason_and_waits_for_review(db, monkeypatch):
    _publish(db)
    _clock(monkeypatch, 9, 30)
    assert '原因' in store.add_punch('E001', 'T1', '上班', at='09:00', path=db)[1]
    assert '晚於現在' in store.add_punch('E001', 'T1', '上班', at='10:00', note='忘了', path=db)[1]
    ok, msg = store.add_punch('E001', 'T1', '上班', at='09:00', note='手機沒電', lat=25.0, lon=121.5, path=db)
    assert ok and '等居督覆核' in msg
    assert '等居督覆核' in store.add_punch('E001', 'T1', '上班', at='09:01', note='再一次', path=db)[1]  # 不能重複送
    pending = store.pending_reviews(db)
    assert len(pending) == 1 and pending[0]['補登時間'] == '09:00' and pending[0]['原因'] == '手機沒電'
    frame = store.punch_frame(path=db)
    assert frame.loc[0, '覆核'] == store.REVIEW_PENDING and pd.isna(frame.loc[0, '緯度'])   # 補登不記位置
    assert store.add_punch('E001', 'T1', '下班', path=db)[0]       # 待覆核的補登可以先當上班用
    assert store.review_punch(pending[0]['紀錄ID'], True, account='amy', path=db) is None
    assert store.pending_reviews(db) == []


def test_late_entry_corrects_existing_punch_only_after_approval(db, monkeypatch):
    _publish(db)
    _clock(monkeypatch, 8, 40)
    store.add_punch('E001', 'T1', '上班', path=db)                 # 太早按了
    _clock(monkeypatch, 9, 10)
    ok, _ = store.add_punch('E001', 'T1', '上班', at='09:00', note='提早按錯', path=db)
    assert ok

    def used():
        punches = store.punches_for_tasks(['T1'], db)['T1']
        return store.effective_punches(punches)['上班']['at'][11:16]
    assert used() == '08:40'                                        # 覆核前仍用現場打卡
    pid = store.pending_reviews(db)[0]['紀錄ID']
    store.review_punch(pid, True, path=db)
    assert used() == '09:00'                                        # 核准後改用補登時間
    store.review_punch(pid, False, path=db)                         # 改成退回：以最後一次覆核為準
    assert used() == '08:40'
    assert store.review_punch(999, True, path=db) == '找不到這筆補登。'


# ---- 看板與逾時 ----
def test_board_marks_overdue_after_fifteen_minutes(db, monkeypatch):
    _publish(db)
    _clock(monkeypatch, 13, 0)
    store.add_punch('E001', 'T2', '上班', lat=25.01, lon=121.5, path=db)     # 約 1.1 公里外
    at = lambda hh, mm: datetime(2026, 11, 9, hh, mm)
    board = store.day_board(DAY, path=db, moment=at(15, 14)).set_index('任務ID')
    assert board.loc['T3', '狀態'] == '未開始'                        # 15:00 開始，14 分鐘還不算
    board = store.day_board(DAY, path=db, moment=at(15, 15)).set_index('任務ID')
    assert board.loc['T3', '狀態'] == '逾時未打卡'
    assert board.loc['T1', '狀態'] == '逾時未打卡'
    assert board.loc['T2', '狀態'] == '服務中' and board.loc['T2', '上班'] == '13:00'
    assert 1000 < board.loc['T2', '上班距案家(公尺)'] < 1200 and '僅提醒' in board.loc['T2', '提醒']
    other_day = store.day_board(DAY, path=db, moment=datetime(2026, 11, 10, 18, 0)).set_index('任務ID')
    assert other_day.loc['T3', '狀態'] == '未開始'                    # 只判斷今天的班
    assert store.is_overdue(DAY, '09:00', at(9, 20), overdue_mins=30) is False


def test_demo_shift_can_be_cleared_without_touching_real_punches(db, monkeypatch):
    _publish(db)
    _clock(monkeypatch, 9, 0)
    store.add_punch('E001', 'T1', '上班', path=db)
    task = store.add_demo_shift('E001', path=db)
    assert store.add_punch('E001', task, '上班', path=db)[0]
    assert store.clear_demo(db) == 1
    assert list(store.punch_frame(path=db)['任務ID']) == ['T1']


# ---- 打卡網頁 ----
flask = pytest.importorskip('flask')


def _phone(db, monkeypatch, https):
    from checkin.server import create_app
    _publish(db)
    _clock(monkeypatch, 9, 2)
    client = create_app(db_path=db).test_client()
    headers = {'X-Forwarded-Proto': 'https', 'Host': 'checkin.example.org'} if https else {'Host': '192.168.1.5:8600'}
    page = client.get('/login', headers=headers).get_data(as_text=True)
    token = re.search(r'name="csrf" value="([^"]+)"', page)[1]
    reply = client.post('/login', data={'csrf': token, 'cg': 'e001'}, headers=headers)
    assert reply.status_code == 302 and reply.headers['Location'].endswith('/')
    return client, headers


def test_phone_flow_binds_and_shows_buttons(db, monkeypatch):
    client, headers = _phone(db, monkeypatch, https=True)
    page = client.get('/', headers=headers).get_data(as_text=True)
    assert '今天的班' in page and '>上班<' in page and '>下班<' in page and '>未遇<' in page
    assert '王○○' in page and 'HomeCare AI' in page
    csrf = re.search(r'var CSRF = "([^"]+)"', page)[1]
    reply = client.post('/punch', json={'task_id': 'T1', 'kind': '上班', 'lat': 25.0, 'lon': 121.5},
                        headers=dict(headers, **{'X-CSRF-Token': csrf}))
    assert reply.json['ok'] and reply.json['message'].startswith('上班打卡完成 09:02')
    again = client.post('/punch', json={'task_id': 'T1', 'kind': '上班'}, headers=dict(headers, **{'X-CSRF-Token': csrf}))
    assert again.status_code == 409 and not again.json['ok']
    assert store.punch_frame(path=db).loc[0, '緯度'] == 25.0            # https：記位置
    assert client.post('/punch', json={'task_id': 'T1', 'kind': '下班'}, headers=headers).status_code == 400  # 缺 CSRF
    # 居督解除綁定 → 這支手機立刻不能打卡
    store.revoke_device(store.devices(store.DEVICE_ACTIVE, db)[0]['id'], db)
    assert client.post('/punch', json={'task_id': 'T2', 'kind': '未遇'},
                       headers=dict(headers, **{'X-CSRF-Token': csrf})).status_code == 401


def test_phone_over_http_records_no_gps(db, monkeypatch):
    client, headers = _phone(db, monkeypatch, https=False)
    page = client.get('/', headers=headers).get_data(as_text=True)
    assert '不記錄位置' in page
    csrf = re.search(r'var CSRF = "([^"]+)"', page)[1]
    reply = client.post('/punch', json={'task_id': 'T1', 'kind': '上班', 'lat': 25.0, 'lon': 121.5},
                        headers=dict(headers, **{'X-CSRF-Token': csrf}))
    assert reply.json['ok']
    assert pd.isna(store.punch_frame(path=db).loc[0, '緯度'])          # http：手機送了也不存


def test_second_phone_waits_on_pending_page(db, monkeypatch):
    from checkin.server import create_app
    _publish(db)
    store.request_device('E001', 'iPhone', db)                         # 第一支已綁
    client = create_app(db_path=db).test_client()
    page = client.get('/login').get_data(as_text=True)
    token = re.search(r'name="csrf" value="([^"]+)"', page)[1]
    reply = client.post('/login', data={'csrf': token, 'cg': 'E001'})
    assert reply.headers['Location'].endswith('/pending')
    assert '等居督核准' in client.get('/pending').get_data(as_text=True)
    assert client.get('/').status_code == 302                           # 還不能打卡
    store.decide_device(store.devices(store.DEVICE_PENDING, db)[0]['id'], True, db)
    assert client.get('/pending').headers['Location'].endswith('/')


# ---- 網址 ----
def test_checkin_url_prefers_saved_fixed_url(db, monkeypatch):
    url, kind = runner.checkin_url(db)
    assert kind == '辦公室網路' and url.startswith('http://') and url.endswith(':8600')
    monkeypatch.setenv('CAREFLOW_CHECKIN_PUBLIC_URL', 'https://env.example.org/')
    assert runner.checkin_url(db) == ('https://env.example.org', '固定網址')
    assert runner.save_public_url('https://checkin.example.org/', path=db) is None
    assert runner.checkin_url(db) == ('https://checkin.example.org', '固定網址')
    assert 'https' in runner.save_public_url('http://not-secure.example.org', path=db)
    runner.save_public_url('', path=db)
    assert runner.checkin_url(db)[0] == 'https://env.example.org'


def test_autostart_can_be_turned_off(monkeypatch):
    monkeypatch.setenv('CAREFLOW_CHECKIN_AUTOSTART', '0')
    assert runner.ensure_running(port=65530) == (False, '自動啟動已關閉（CAREFLOW_CHECKIN_AUTOSTART=0）')


def test_qr_code_works_without_segno_installed(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, 'segno', None)                 # 模擬主機沒有安裝 segno → 用 checkin/_vendor/segno
    png = runner.qr_png('https://checkin.example.org')
    assert png[:8] == b'\x89PNG\r\n\x1a\n'
    assert 'segno' not in runner.missing_packages()


class _FakeTunnel:
    """假的 cloudflared：照實際輸出格式印出 trycloudflare 網址。"""
    def __init__(self, lines):
        self.stdout = iter(lines)
        self.alive = True

    def poll(self):
        return None if self.alive else 0

    def terminate(self):
        self.alive = False

    def wait(self, timeout=None):
        return 0


def test_external_url_used_until_stopped(db, monkeypatch, tmp_path):
    fake = _FakeTunnel(['INF Requesting new quick Tunnel on trycloudflare.com...\n',
                        'INF |  https://effect-toxic-degree-ruled.trycloudflare.com  |\n'])
    monkeypatch.setattr(runner, 'cloudflared_path', lambda: tmp_path / 'cloudflared')
    monkeypatch.setattr(runner.subprocess, 'Popen', lambda *a, **k: fake)
    assert runner.start_tunnel(wait=2) == (True, 'https://effect-toxic-degree-ruled.trycloudflare.com')
    assert runner.checkin_url(db) == ('https://effect-toxic-degree-ruled.trycloudflare.com', '外部網址')
    runner.save_public_url('https://checkin.example.org', path=db)    # 固定網址優先
    assert runner.checkin_url(db)[1] == '固定網址'
    runner.save_public_url('', path=db)
    runner.stop_tunnel()
    assert runner.checkin_url(db)[1] == '辦公室網路' and not fake.alive


def test_external_url_reports_download_failure(monkeypatch):
    monkeypatch.setattr(runner, 'cloudflared_path', lambda: None)
    def fail(*a, **k):
        raise OSError('連不到 GitHub')
    monkeypatch.setattr(runner, 'download_cloudflared', fail)
    ok, msg = runner.start_tunnel(wait=1)
    assert not ok and '連不到 GitHub' in msg


def test_download_retries_when_github_times_out(monkeypatch, tmp_path):
    """GitHub 下載伺服器回 504 時會重試，第三次成功就用下載好的檔案。"""
    import io
    import urllib.error
    monkeypatch.setattr(runner, 'cloudflared_target', lambda: tmp_path / 'bin' / 'cloudflared.exe')
    monkeypatch.setattr(runner.threading.Event, 'wait', lambda self, t=None: True)   # 不真的等
    calls = []

    def fake_open(request, timeout=None):
        calls.append(request.full_url)
        if len(calls) < 3:
            raise urllib.error.HTTPError(request.full_url, 504, 'Gateway Time-out', {}, None)
        return io.BytesIO(b'x' * 2_000_000)
    monkeypatch.setattr(runner.urllib.request, 'urlopen', fake_open)
    monkeypatch.setattr(runner.platform, 'system', lambda: 'Windows')
    monkeypatch.setattr(runner, '_arch', lambda: 'amd64')
    path = runner.download_cloudflared()
    assert len(calls) == 3 and path.stat().st_size == 2_000_000

    calls.clear()
    monkeypatch.setattr(runner.urllib.request, 'urlopen',
                        lambda request, timeout=None: (_ for _ in ()).throw(urllib.error.HTTPError(request.full_url, 504, 'Gateway Time-out', {}, None)))
    with pytest.raises(RuntimeError, match='試了 3 次'):
        runner.download_cloudflared()


def test_failed_download_explains_manual_install(monkeypatch):
    monkeypatch.setattr(runner, 'cloudflared_path', lambda: None)
    monkeypatch.setattr(runner, 'download_cloudflared', lambda: (_ for _ in ()).throw(RuntimeError('HTTP Error 504')))
    ok, msg = runner.start_tunnel(wait=1)
    assert not ok and '504' in msg and 'winget install --id Cloudflare.cloudflared' in msg
    state = runner.tunnel_state()
    assert state['status'] == runner.TUNNEL_FAILED and state['error'] == msg


def test_external_url_is_the_default(db, monkeypatch):
    """沒有固定網址時，自動在背景開外部網址；產生中先不給辦公室網址。"""
    started = []
    monkeypatch.setattr(runner, 'start_tunnel_async', lambda port=runner.PORT: started.append(port) or True)
    assert not runner.auto_tunnel(db)                                  # conftest 關掉了（CAREFLOW_CHECKIN_TUNNEL=0）
    monkeypatch.setenv('CAREFLOW_CHECKIN_TUNNEL', '1')
    assert runner.auto_tunnel(db) and started == [runner.PORT]
    runner._tunnel['status'] = runner.TUNNEL_STARTING
    assert runner.checkin_url(db)[1] == '外部網址產生中'
    assert not runner.auto_tunnel(db)                                  # 已經在開，不重複
    runner._tunnel.update(status=runner.TUNNEL_FAILED)
    assert not runner.auto_tunnel(db)                                  # 失敗後不自動重試，等居督按「再試一次」
    runner._tunnel.update(status=runner.TUNNEL_IDLE)
    runner.stop_tunnel()                                               # 居督手動停止後也不自動再開
    assert not runner.auto_tunnel(db)
    runner._tunnel.update(user_stopped=False)
    runner.save_public_url('https://checkin.example.org', path=db)     # 有固定網址就不開外部網址
    assert not runner.auto_tunnel(db) and len(started) == 1


def test_start_tunnel_async_runs_once(monkeypatch):
    calls = []
    monkeypatch.setattr(runner, 'start_tunnel', lambda port=runner.PORT: calls.append(port))
    assert runner.start_tunnel_async()
    assert runner.tunnel_state()['status'] == runner.TUNNEL_STARTING
    assert not runner.start_tunnel_async()                             # 產生中再按不會重複開
