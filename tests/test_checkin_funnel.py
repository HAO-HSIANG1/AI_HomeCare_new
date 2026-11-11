"""固定打卡網址（Tailscale Funnel）與防休眠：用假的 tailscale 指令測狀態判斷，不需要真的安裝 Tailscale。"""
import json

import pytest

from checkin import runner

HOST = 'office-pc.tail1234.ts.net'


def _fake(monkeypatch, *, installed=True, logged_in=True, funnel=None, approve=False):
    """假的 tailscale：status --json 回登入狀態；funnel status --json 回 funnel 設定；funnel --bg 依 approve 決定結果。"""
    calls = []
    state = {'funnel': funnel}

    def run(*args, timeout=20):
        calls.append(args)
        if args[:2] == ('status', '--json'):
            return 0, json.dumps({'BackendState': 'Running' if logged_in else 'NeedsLogin', 'Self': {'DNSName': HOST + '.'}})
        if args[:3] == ('funnel', 'status', '--json'):
            return 0, json.dumps(state['funnel'] or {})
        if args[:2] == ('funnel', '--bg'):
            if approve:
                return 1, 'Funnel is not enabled on your tailnet.\nTo enable, visit:\n\n  https://login.tailscale.com/f/funnel?node=abc\n'
            state['funnel'] = {'Web': {f'{HOST}:443': {'Handlers': {'/': {'Proxy': f'http://127.0.0.1:{runner.PORT}'}}}},
                               'AllowFunnel': {f'{HOST}:443': True}}
            return 0, 'Available on the internet'
        if args[:2] == ('funnel', '--https=443'):
            state['funnel'] = None
            return 0, ''
        return 1, ''
    monkeypatch.setattr(runner, 'tailscale_path', lambda: 'tailscale' if installed else None)
    monkeypatch.setattr(runner, '_tailscale', run)
    runner._funnel_cache.update(at=0.0, state=None)
    return calls


def test_not_installed_and_logged_out(monkeypatch):
    _fake(monkeypatch, installed=False)
    assert runner.funnel_state(refresh=True)['status'] == runner.FUNNEL_NOT_INSTALLED
    _fake(monkeypatch, logged_in=False)
    assert runner.funnel_state(refresh=True)['status'] == runner.FUNNEL_LOGGED_OUT
    assert '登入' in runner.start_funnel()['message']


def test_start_funnel_gives_fixed_url_used_by_checkin_url(monkeypatch, tmp_path):
    _fake(monkeypatch)
    monkeypatch.setenv('CAREFLOW_CHECKIN_DB', str(tmp_path / 'c.sqlite3'))
    monkeypatch.delenv('CAREFLOW_CHECKIN_PUBLIC_URL', raising=False)
    assert runner.funnel_state(refresh=True)['status'] == runner.FUNNEL_OFF
    result = runner.start_funnel()
    assert result['ok'] and result['url'] == f'https://{HOST}'
    assert runner.checkin_url() == (f'https://{HOST}', '固定網址')          # 打卡網址與 QR Code 改用固定網址
    assert runner.auto_tunnel() is False                                    # 有固定網址就不再開臨時通道
    runner.stop_funnel()
    assert runner.funnel_state()['status'] == runner.FUNNEL_OFF


def test_first_time_returns_approval_link(monkeypatch):
    _fake(monkeypatch, approve=True)
    result = runner.start_funnel()
    assert not result['ok'] and result['approve'] == 'https://login.tailscale.com/f/funnel?node=abc'


def test_funnel_to_another_port_is_not_ours():
    other = {'Web': {f'{HOST}:443': {'Handlers': {'/': {'Proxy': 'http://127.0.0.1:3000'}}}}, 'AllowFunnel': {f'{HOST}:443': True}}
    assert not runner._funnel_points_here(json.dumps(other), HOST)


def test_keep_awake_only_on_windows(monkeypatch):
    monkeypatch.setattr(runner.platform, 'system', lambda: 'Linux')
    assert runner.keep_awake() is False
    monkeypatch.setattr(runner.platform, 'system', lambda: 'Windows')
    monkeypatch.setenv('CAREFLOW_KEEP_AWAKE', '0')
    assert runner.keep_awake() is False


TOKEN = 'eyJhIjoiYWJjZGVmIiwidCI6IjEyMzQ1Njc4OTAiLCJzIjoieHl6MTIzIn0='


def test_named_tunnel_token_from_pasted_command(monkeypatch, tmp_path):
    """Cloudflare 固定網址：貼整行安裝指令也認得出權杖；儲存後啟動 cloudflared，打卡網址改用固定網址。"""
    monkeypatch.setenv('CAREFLOW_CHECKIN_DB', str(tmp_path / 'c.sqlite3'))
    monkeypatch.delenv('CAREFLOW_CHECKIN_PUBLIC_URL', raising=False)
    monkeypatch.delenv('CAREFLOW_CHECKIN_TUNNEL_TOKEN', raising=False)
    assert runner.parse_token(f'cloudflared.exe service install {TOKEN}') == TOKEN
    assert '看不出權杖' in runner.save_named_tunnel('https://checkin.example.org', '亂打的字')
    started = []

    class Proc:
        def poll(self):
            return None

        def terminate(self):
            pass

        def wait(self, t):
            pass
    monkeypatch.setattr(runner, 'cloudflared_path', lambda: 'cloudflared')
    monkeypatch.setattr(runner.subprocess, 'Popen', lambda args, **k: started.append(args) or Proc())
    assert runner.save_named_tunnel('https://checkin.example.org', f'cloudflared.exe service install {TOKEN}') is None
    assert started[-1][-2:] == ['--token', TOKEN]
    assert runner.named_tunnel_state()['running']
    assert runner.checkin_url() == ('https://checkin.example.org', '固定網址')
    assert runner.save_named_tunnel('', '') is None                         # 清除＝停止並改回臨時網址
    assert not runner.named_tunnel_state()['configured']


def test_free_gateway_setup_and_follow(monkeypatch, tmp_path):
    """免費固定網址（Workers 門牌）：權杖→自動建好 workers.dev 網址；臨時網址換了會自動改指新網址。不連真的 Cloudflare。"""
    monkeypatch.setenv('CAREFLOW_CHECKIN_DB', str(tmp_path / 'c.sqlite3'))
    monkeypatch.delenv('CAREFLOW_CHECKIN_PUBLIC_URL', raising=False)
    calls = []

    def fake_cf(method, path, token, **kw):
        calls.append((method, path, kw))
        if path == '/accounts':
            return [{'id': 'acc123'}]
        if path.endswith('/workers/subdomain'):
            return {'subdomain': 'amy'}
        return {}
    monkeypatch.setattr(runner, '_cf', fake_cf)
    monkeypatch.setattr(runner, 'tunnel_url', lambda: 'https://a-b-c.trycloudflare.com')
    monkeypatch.setattr(runner.threading.Thread, 'start', lambda self: self.run())   # 背景更新改成當場執行，方便檢查
    assert '不完整' in runner.setup_gateway('abc')[1]
    url, err = runner.setup_gateway('x' * 40)
    assert err is None and url == 'https://homecare-checkin.amy.workers.dev'
    upload = next(kw for m, p, kw in calls if m == 'PUT' and p.endswith('/scripts/homecare-checkin'))
    meta = json.loads(upload['files']['metadata'][1])
    assert meta['bindings'][0] == {'type': 'plain_text', 'name': 'TARGET', 'text': 'https://a-b-c.trycloudflare.com'}
    assert ('POST', '/accounts/acc123/workers/scripts/homecare-checkin/subdomain', {'json': {'enabled': True}}) in calls
    assert runner.checkin_url()[0] == url                                         # QR Code 用門牌網址
    calls.clear()
    assert runner._gateway_follow('https://new-one.trycloudflare.com') is True    # 重開後新的臨時網址
    assert runner.gateway_state()['target'] == 'https://new-one.trycloudflare.com'
    assert runner._gateway_follow('https://new-one.trycloudflare.com') is False   # 同一個網址不重複上傳
    runner.clear_gateway()
    assert not runner.gateway_state()['configured']
