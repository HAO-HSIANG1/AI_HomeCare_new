"""讓打卡網頁跟著 HomeCare AI 一起啟動，並決定要給居服員的打卡網址與 QR Code。

- HomeCare AI（app.py）開啟時在背景啟動打卡網頁（同一台主機、port 8600）；已經有人開著（例如另外執行
  `python -m checkin.server`）就直接沿用。設 CAREFLOW_CHECKIN_AUTOSTART=0 可以關掉（打卡網頁另外架在別台主機時）。
- 打卡網址依序取：04 頁設定的固定網址 → 環境變數 CAREFLOW_CHECKIN_PUBLIC_URL → 外部網址（Cloudflare 臨時通道）
  → 這台電腦在辦公室網路的位址。只有 https 網址手機才會給定位；辦公室位址只能在同一個 Wi-Fi 試用，也不記位置。
- 外部網址：04 頁按「🌐 產生外部網址」，用 cloudflared 開一條免費臨時通道（https://….trycloudflare.com）。
  第一次會從 Cloudflare 官方 GitHub 下載 cloudflared（約 50MB）到 output_results/bin；電腦本來有安裝就直接用。
  臨時通道每次重開都換網址，只適合試用。
- 固定網址（正式上線，擇一）：
  1. Tailscale Funnel（免費、免買網域，但要在電腦安裝 Tailscale；畫面不主動推薦，裝了會自動偵測）：這台電腦裝好 Tailscale 並登入後，04 頁按「📌 開啟固定網址」，
     會執行 `tailscale funnel --bg --https=443 http://127.0.0.1:8600`，網址固定是 https://<電腦名稱>.<tailnet>.ts.net，
     重開機後 Tailscale 會自己恢復，網址和 QR Code 不會變。
  2. Cloudflare 具名通道（建議；不用安裝任何軟體，需要一個放在 Cloudflare 的網域）：04 頁「📌 固定網址」貼上網址與
     Cloudflare 給的權杖（或設環境變數 CAREFLOW_CHECKIN_TUNNEL_TOKEN＋CAREFLOW_CHECKIN_PUBLIC_URL），
     HomeCare AI 每次啟動自動執行專案內的 `cloudflared tunnel run --token`。
- 防休眠：Windows 上 HomeCare AI 開著時，告訴系統「不要自動睡眠」（螢幕照樣會關），避免居服員打不到卡；
  CAREFLOW_KEEP_AWAKE=0 可關閉。筆電闔上螢幕仍可能睡眠，請在電源設定把「闔上螢幕」改成「不做任何動作」。
- QR Code 用 segno；主機沒有安裝時改用隨程式附上的 checkin/_vendor/segno，不必另外安裝。

不 import streamlit。
"""
from __future__ import annotations

import io
import importlib.util
import os
import platform
import re
import shutil
import socket
import subprocess
import threading
import urllib.request
from pathlib import Path

import json
import secrets
import time

from checkin import store

PORT = int(os.getenv('CAREFLOW_CHECKIN_PORT', '8600'))
URL_KEY = 'public_url'
REQUIRED = (('flask', 'flask'), ('waitress', 'waitress'))   # segno 有隨程式附上的版本，不算缺
_lock = threading.Lock()
_started = {}


def autostart_enabled():
    return os.getenv('CAREFLOW_CHECKIN_AUTOSTART', '1').strip().lower() not in ('0', 'false', 'no', 'off')


def missing_packages():
    """打卡需要、但這台主機還沒安裝的套件名稱（requirements.txt 都有列）。"""
    return [name for module, name in REQUIRED if importlib.util.find_spec(module) is None]


def is_up(url, timeout=1.5):
    """打卡網頁有沒有在回應（打 /healthz）。"""
    try:
        with urllib.request.urlopen(url.rstrip('/') + '/healthz', timeout=timeout) as resp:
            return resp.status == 200
    except Exception:          # 連不上、逾時、非 200 都當成沒在跑
        return False


def ensure_running(port=PORT):
    """背景啟動打卡網頁；已經在跑就不重複開。回傳 (是否在跑, 說明)。"""
    if not autostart_enabled():
        return False, '自動啟動已關閉（CAREFLOW_CHECKIN_AUTOSTART=0）'
    keep_awake()
    local = f'http://127.0.0.1:{port}'
    if is_up(local):
        return True, '打卡網頁運作中'
    if 'flask' in missing_packages():
        return False, '這台主機還沒安裝 flask，請執行 pip install -r requirements.txt'
    with _lock:
        thread = _started.get(port)
        if thread is None or not thread.is_alive():
            from checkin.server import create_app
            app = create_app()

            def serve():
                try:
                    from waitress import serve as waitress_serve
                    waitress_serve(app, host='0.0.0.0', port=port, threads=8, _quiet=True)
                except ImportError:
                    app.run(host='0.0.0.0', port=port, use_reloader=False)
                except OSError:
                    pass       # port 被占用：通常是另一個打卡網頁已經開著

            thread = threading.Thread(target=serve, name='homecare-checkin', daemon=True)
            thread.start()
            _started[port] = thread
    for _ in range(20):
        if is_up(local, timeout=0.5):
            return True, '打卡網頁運作中'
        threading.Event().wait(0.15)
    return False, f'打卡網頁沒有啟動成功（port {port} 可能被其他程式占用）'


def lan_ip():
    """這台電腦在辦公室網路的 IP（不會真的送出封包）。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('10.255.255.255', 1))
            return s.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return '127.0.0.1'


def checkin_url(path=None):
    """回傳 (網址, 種類)。種類：'固定網址'、'外部網址'（都是 https，外面也能打、會記位置）、
    '外部網址產生中'（暫時回傳辦公室位址，畫面不要發這個 QR Code）或 '辦公室網路'（只能同 Wi-Fi、不記位置）。"""
    fixed = (store.get_setting(URL_KEY, path=path) or os.getenv('CAREFLOW_CHECKIN_PUBLIC_URL', '')).strip().rstrip('/')
    if fixed:
        return fixed, '固定網址'
    gw = store.get_setting('gw_url', path=path)
    if gw and store.get_setting('gw_token', path=path):
        return gw, '固定網址'
    funnel = funnel_state()
    if funnel['status'] == FUNNEL_ON and funnel['url']:
        return funnel['url'], '固定網址'
    if tunnel_url():
        return tunnel_url(), '外部網址'
    if _tunnel['status'] == TUNNEL_STARTING:
        return f'http://{lan_ip()}:{PORT}', '外部網址產生中'
    return f'http://{lan_ip()}:{PORT}', '辦公室網路'


def save_public_url(url, path=None):
    """儲存固定打卡網址；空字串＝清除。網址不是 https 開頭時回傳錯誤訊息，成功回傳 None。"""
    url = (url or '').strip().rstrip('/')
    if url and not url.startswith('https://'):
        return '固定網址要用 https:// 開頭，手機才會給定位。'
    store.set_setting(URL_KEY, url, path=path)
    return None


def qr_png(url, scale=10):
    """網址的 QR Code（PNG bytes）。顏色用主色 #1F5F7A（同 careflow_ui 的 --cf-primary）。

    優先用主機已安裝的 segno；沒有安裝時用 checkin/_vendor/segno，所以不需要另外 pip install。
    """
    try:
        import segno
    except ImportError:
        from checkin._vendor import segno
    buf = io.BytesIO()
    segno.make(url, error='m').save(buf, kind='png', scale=scale, border=2, dark='#1F5F7A')
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 外部網址（Cloudflare 免費臨時通道）：居服員在外面用行動網路也能打卡，而且是 https、手機會給定位。
# 不用網域、不用設防火牆。限制：這台電腦要開著且連網；HomeCare AI 重開後網址會變，只適合試辦。
# 沒有設定固定網址時，HomeCare AI 一啟動就在背景開外部網址（CAREFLOW_CHECKIN_TUNNEL=0 可關閉），
# 所以 04 頁預設給居服員的就是外部網址，不是辦公室網路的 http 位址。
# ---------------------------------------------------------------------------
CLOUDFLARED_DOWNLOADS = {
    ('Windows', 'amd64'): 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe',
    ('Windows', 'x86'): 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-386.exe',
    ('Linux', 'amd64'): 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64',
    ('Linux', 'arm64'): 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64',
}
DOWNLOAD_TRIES = 3
# winget／官方安裝程式的預設位置：剛裝好時 PATH 還沒更新，shutil.which 找不到，所以另外檢查
_WINDOWS_INSTALL_PATHS = (r'C:\Program Files (x86)\cloudflared\cloudflared.exe', r'C:\Program Files\cloudflared\cloudflared.exe')
_TUNNEL_RE = re.compile(r'https://(?!api\.)[a-z0-9-]+\.trycloudflare\.com')   # 排除錯誤訊息裡的 api.trycloudflare.com
TUNNEL_IDLE, TUNNEL_STARTING, TUNNEL_ON, TUNNEL_FAILED = 'idle', 'starting', 'on', 'failed'
_tunnel = {'proc': None, 'url': '', 'log': [], 'status': TUNNEL_IDLE, 'error': '', 'user_stopped': False}
_tunnel_lock = threading.Lock()


def tunnel_enabled():
    """沒有固定網址時，是否自動開外部網址（預設開）。"""
    return os.getenv('CAREFLOW_CHECKIN_TUNNEL', '1').strip().lower() not in ('0', 'false', 'no', 'off')


def _arch():
    machine = platform.machine().lower()
    if machine in ('amd64', 'x86_64'):
        return 'amd64'
    if machine in ('arm64', 'aarch64'):
        return 'arm64'
    return 'x86'


def cloudflared_target():
    name = 'cloudflared.exe' if platform.system() == 'Windows' else 'cloudflared'
    return store.ROOT / 'output_results' / 'bin' / name


def cloudflared_path():
    """已經有的 cloudflared：專案內下載（或手動放進 output_results/bin）的、PATH 上的、winget 預設安裝位置；都沒有回傳 None。"""
    target = cloudflared_target()
    if target.exists() and target.stat().st_size > 1_000_000:
        return target
    found = shutil.which('cloudflared')
    if found:
        return Path(found)
    if platform.system() == 'Windows':
        for candidate in _WINDOWS_INSTALL_PATHS:
            if Path(candidate).exists():
                return Path(candidate)
    return None


def download_cloudflared(timeout=180, tries=DOWNLOAD_TRIES):
    """從 Cloudflare 官方 GitHub 下載 cloudflared（約 50MB）到 output_results/bin。

    GitHub 的下載伺服器偶爾回 504（逾時），所以失敗會等幾秒重試，共 tries 次；都失敗才丟 RuntimeError／OSError。
    """
    url = CLOUDFLARED_DOWNLOADS.get((platform.system(), _arch()))
    if not url:
        raise RuntimeError(f'這台電腦（{platform.system()} {_arch()}）沒有可自動下載的版本，請資訊人員手動安裝 cloudflared。')
    target = cloudflared_target()
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + '.part')
    last = None
    for attempt in range(tries):
        if attempt:
            threading.Event().wait(3 * attempt)
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'HomeCareAI-checkin'})
            with urllib.request.urlopen(request, timeout=timeout) as resp, open(partial, 'wb') as out:
                shutil.copyfileobj(resp, out)
            if partial.stat().st_size < 1_000_000:
                raise RuntimeError('下載的檔案不完整')
            os.replace(partial, target)
            if platform.system() != 'Windows':
                target.chmod(0o755)
            return target
        except (OSError, RuntimeError) as exc:      # urllib 的 HTTPError／URLError 都是 OSError
            last = exc
    raise RuntimeError(f'試了 {tries} 次都沒有成功（{last}）')


def tunnel_url():
    """外部網址還開著就回傳網址，否則空字串。"""
    proc = _tunnel['proc']
    return _tunnel['url'] if proc is not None and proc.poll() is None and _tunnel['url'] else ''


def tunnel_state():
    """外部網址目前的狀態：dict(status, url, error)。status：idle／starting／on／failed。"""
    if _tunnel['status'] == TUNNEL_ON and not tunnel_url():
        _tunnel.update(status=TUNNEL_FAILED, error='外部網址意外中斷了（cloudflared 已結束）。')
    return {'status': _tunnel['status'], 'url': tunnel_url(), 'error': _tunnel['error']}


MANUAL_HINT = ('也可以手動安裝：在命令提示字元執行 winget install --id Cloudflare.cloudflared，'
               '或把 cloudflared-windows-amd64.exe 改名為 cloudflared.exe 放到專案的 output_results\\bin 資料夾，再按一次。')


def start_tunnel(port=PORT, wait=45):
    """開啟外部網址（會等到取得網址為止）；回傳 (成功, 網址或錯誤說明)。已經開著就直接回傳原網址。"""
    if tunnel_url():
        return True, _tunnel['url']
    _tunnel.update(status=TUNNEL_STARTING, error='', user_stopped=False)
    try:
        exe = cloudflared_path() or download_cloudflared()
    except (OSError, RuntimeError) as exc:
        msg = f'下載 cloudflared 失敗，可能是 GitHub 下載伺服器暫時沒回應或這台電腦連不到 GitHub：{exc}。請稍後再按一次。' + MANUAL_HINT
        _tunnel.update(status=TUNNEL_FAILED, error=msg)
        return False, msg
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    try:
        proc = subprocess.Popen([str(exe), 'tunnel', '--no-autoupdate', '--url', f'http://localhost:{port}'],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                encoding='utf-8', errors='replace', creationflags=flags)
    except OSError as exc:
        msg = 'cloudflared 無法執行：' + str(exc)
        _tunnel.update(status=TUNNEL_FAILED, error=msg)
        return False, msg
    _tunnel.update(proc=proc, url='', log=[])
    found = threading.Event()

    def read():
        for line in proc.stdout:
            _tunnel['log'] = (_tunnel['log'] + [line.rstrip()])[-40:]
            hit = _TUNNEL_RE.search(line)
            if hit and not _tunnel['url']:
                _tunnel['url'] = hit.group(0)
                found.set()
                _gateway_follow(_tunnel['url'])        # 有固定門牌網址：把門牌指到這個新的臨時網址
        # cloudflared 結束了：有設定固定門牌網址又不是居督手動停止，就自動重開一條（門牌會跟著更新）
        if gateway_configured() and not _tunnel['user_stopped'] and _tunnel['proc'] is proc:
            _tunnel.update(proc=None, url='', status=TUNNEL_IDLE)
            threading.Timer(GATEWAY_RESTART_SECONDS, start_tunnel_async, kwargs={'port': port}).start()
    threading.Thread(target=read, name='homecare-tunnel', daemon=True).start()
    found.wait(wait)
    if _tunnel['url']:
        _tunnel.update(status=TUNNEL_ON, error='')
        return True, _tunnel['url']
    errors = [line for line in _tunnel['log'] if 'failed' in line.lower() or ' ERR ' in line]
    tail = (errors or _tunnel['log'])[-1][-200:] if _tunnel['log'] else ''
    _stop_process()
    msg = '沒有取得外部網址（可能是這台電腦的網路擋住 Cloudflare）。' + (f'訊息：{tail}' if tail else '')
    _tunnel.update(status=TUNNEL_FAILED, error=msg)
    return False, msg


def start_tunnel_async(port=PORT):
    """在背景開外部網址，不讓畫面等待；已經在開或已開好就不重複。回傳是否有開始新的嘗試。"""
    with _tunnel_lock:
        if _tunnel['status'] == TUNNEL_STARTING or tunnel_url():
            return False
        _tunnel.update(status=TUNNEL_STARTING, error='', user_stopped=False)
    threading.Thread(target=start_tunnel, kwargs={'port': port}, name='homecare-tunnel-start', daemon=True).start()
    return True


def auto_tunnel(path=None, port=PORT):
    """沒有固定網址、沒被居督手動停止、也還沒試過時，自動在背景開外部網址。失敗後不自動重試（等居督按「再試一次」）。"""
    fixed = (store.get_setting(URL_KEY, path=path) or os.getenv('CAREFLOW_CHECKIN_PUBLIC_URL', '')).strip()
    if named_token(path):
        return start_named_tunnel(path)    # 有 Cloudflare 權杖：開固定網址那條，不開臨時通道
    if fixed or funnel_state()['status'] == FUNNEL_ON:
        return False
    if not tunnel_enabled() or _tunnel['user_stopped'] or _tunnel['status'] != TUNNEL_IDLE:
        return False
    return start_tunnel_async(port)


def _stop_process():
    proc = _tunnel['proc']
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()
    _tunnel.update(proc=None, url='')


def stop_tunnel():
    """居督手動關閉外部網址；用過的網址會失效，之後不會自動再開。"""
    _stop_process()
    _tunnel.update(status=TUNNEL_IDLE, error='', user_stopped=True)



# ---------------------------------------------------------------- 固定網址：Tailscale Funnel
FUNNEL_NOT_INSTALLED, FUNNEL_LOGGED_OUT, FUNNEL_OFF, FUNNEL_ON, FUNNEL_ERROR = (
    'not_installed', 'logged_out', 'off', 'on', 'error')
_WINDOWS_TAILSCALE = (r'C:\Program Files\Tailscale\tailscale.exe', r'C:\Program Files (x86)\Tailscale\tailscale.exe')
_APPROVE_RE = re.compile(r'https://login\.tailscale\.com/\S+')
_funnel_cache = {'at': 0.0, 'state': None}
FUNNEL_CACHE_SECONDS = 20          # 畫面每次重跑都會問網址；20 秒內沿用上次結果，不要一直呼叫 tailscale


def tailscale_path():
    """這台電腦的 tailscale 指令；沒安裝回傳 None。"""
    found = shutil.which('tailscale')
    if found:
        return found
    if platform.system() == 'Windows':
        for candidate in _WINDOWS_TAILSCALE:
            if Path(candidate).exists():
                return candidate
    return None


def _tailscale(*args, timeout=20):
    """執行 tailscale 指令，回傳 (結束碼, 輸出文字)。"""
    exe = tailscale_path()
    if not exe:
        return 127, ''
    try:
        out = subprocess.run([exe, *args], capture_output=True, text=True, encoding='utf-8', errors='replace',
                             timeout=timeout, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return out.returncode, (out.stdout or '') + (out.stderr or '')


def _funnel_host():
    """這台電腦在 Tailscale 的完整名稱（例如 office-pc.tail1234.ts.net）；沒登入回傳 ''。"""
    code, text = _tailscale('status', '--json')
    if code != 0:
        return ''
    try:
        data = json.loads(text[text.index('{'):])
    except ValueError:
        return ''
    if data.get('BackendState') != 'Running':
        return ''
    return str((data.get('Self') or {}).get('DNSName') or '').rstrip('.')


def _funnel_points_here(text, host, port=PORT):
    """`tailscale funnel status --json` 的設定是否「對外開放 host:443，且轉到本機打卡網頁的 port」。"""
    try:
        cfg = json.loads(text[text.index('{'):])
    except ValueError:
        return False
    if not (cfg.get('AllowFunnel') or {}).get(f'{host}:443'):
        return False
    handlers = ((cfg.get('Web') or {}).get(f'{host}:443') or {}).get('Handlers') or {}
    return any(str(h.get('Proxy', '')).rstrip('/').endswith(f':{port}') for h in handlers.values())


def funnel_state(refresh=False):
    """Tailscale Funnel 狀態：dict(status, url, error)。status 是 FUNNEL_* 其中之一。結果快取 20 秒。"""
    now = time.monotonic()
    if not refresh and _funnel_cache['state'] is not None and now - _funnel_cache['at'] < FUNNEL_CACHE_SECONDS:
        return _funnel_cache['state']
    if not tailscale_path():
        state = dict(status=FUNNEL_NOT_INSTALLED, url='', error='')
    else:
        host = _funnel_host()
        if not host:
            state = dict(status=FUNNEL_LOGGED_OUT, url='', error='')
        else:
            code, text = _tailscale('funnel', 'status', '--json')
            on = code == 0 and _funnel_points_here(text, host)
            state = dict(status=FUNNEL_ON if on else FUNNEL_OFF, url=f'https://{host}' if on else '', error='')
    _funnel_cache.update(at=now, state=state)
    return state


def start_funnel(port=PORT):
    """開啟固定網址（Tailscale Funnel，背景執行、重開機自動恢復）。

    回傳 dict(ok, url, message, approve)：approve 是 Tailscale 要求在網頁按「同意開啟 Funnel」的連結（第一次才會有）。"""
    if not tailscale_path():
        return dict(ok=False, url='', approve='', message='這台電腦還沒安裝 Tailscale。')
    if not _funnel_host():
        return dict(ok=False, url='', approve='', message='Tailscale 還沒登入：請在工作列的 Tailscale 圖示按「Log in」。')
    code, text = _tailscale('funnel', '--bg', '--yes', '--https=443', f'http://127.0.0.1:{port}', timeout=40)
    found = _APPROVE_RE.search(text)
    approve = found.group(0) if found else ''
    state = funnel_state(refresh=True)
    if state['status'] == FUNNEL_ON:
        _stop_process()                    # 有固定網址了，臨時通道關掉
        return dict(ok=True, url=state['url'], approve='', message='')
    if approve:
        return dict(ok=False, url='', approve=approve,
                    message='第一次使用要先在 Tailscale 網頁按同意開啟 Funnel，按完回來再按一次「📌 開啟固定網址」。')
    return dict(ok=False, url='', approve='', message='Tailscale 沒有開成功：' + (text.strip()[-300:] or f'結束碼 {code}'))


def stop_funnel():
    """關閉固定網址（Tailscale Funnel）。"""
    _tailscale('funnel', '--https=443', 'off')
    funnel_state(refresh=True)


# ---------------------------------------------------------------- 固定網址：Cloudflare 具名通道（不用安裝任何軟體）
# 需要一個放在 Cloudflare 的網域。Cloudflare 後台建立通道後會給一串「權杖」；貼到 04 頁（或設環境變數
# CAREFLOW_CHECKIN_TUNNEL_TOKEN），HomeCare AI 每次啟動就自動用專案內下載的 cloudflared 連線，網址永遠不變。
TOKEN_KEY = 'tunnel_token'
_TOKEN_RE = re.compile(r'eyJ[A-Za-z0-9_\-=+/]{40,}')
_named = {'proc': None, 'error': ''}


def parse_token(text):
    """從貼上的文字取出權杖：可以只貼權杖，也可以整行貼 Cloudflare 給的安裝指令。找不到回傳 ''。"""
    found = _TOKEN_RE.search(str(text or ''))
    return found.group(0) if found else ''


def named_token(path=None):
    return (store.get_setting(TOKEN_KEY, path=path) or os.getenv('CAREFLOW_CHECKIN_TUNNEL_TOKEN', '')).strip()


def save_named_tunnel(url, token_text, path=None):
    """儲存固定網址＋權杖並立刻連線。成功回傳 None，失敗回傳說明。url、token_text 都空白＝清除設定並停止。"""
    if not (url or '').strip() and not (token_text or '').strip():
        stop_named_tunnel()
        store.set_setting(TOKEN_KEY, '', path=path)
        return save_public_url('', path=path)
    token = parse_token(token_text)
    if not token:
        return '看不出權杖：請把 Cloudflare 頁面上「安裝並執行」那一整行指令複製貼上（裡面那串 eyJ 開頭的就是權杖）。'
    problem = save_public_url(url, path=path)
    if problem:
        return problem
    store.set_setting(TOKEN_KEY, token, path=path)
    stop_named_tunnel()
    return None if start_named_tunnel(path=path, wait=8) else (_named['error'] or 'Cloudflare 通道沒有連上。')


def start_named_tunnel(path=None, wait=0):
    """用權杖開 Cloudflare 具名通道；已經在跑就不重開。wait＞0 時等幾秒確認沒有立刻失敗。回傳是否在跑。"""
    token = named_token(path)
    proc = _named['proc']
    if not token:
        return False
    if proc is not None and proc.poll() is None:
        return True
    try:
        exe = cloudflared_path() or download_cloudflared()
        _named['proc'] = subprocess.Popen([str(exe), 'tunnel', '--no-autoupdate', 'run', '--token', token],
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, RuntimeError) as exc:
        _named['error'] = f'cloudflared 無法啟動：{exc}。' + MANUAL_HINT
        return False
    _stop_process()                     # 有固定網址了，臨時通道關掉
    _tunnel.update(status=TUNNEL_IDLE, error='', user_stopped=True)
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if _named['proc'].poll() is not None:
            _named['error'] = '權杖不正確或已在 Cloudflare 刪除，cloudflared 一啟動就結束了。請重新複製權杖。'
            return False
        time.sleep(0.5)
    _named['error'] = ''
    return True


def named_tunnel_state(path=None):
    """dict(configured, running, error)：有沒有設定權杖、cloudflared 有沒有在跑。"""
    proc = _named['proc']
    return dict(configured=bool(named_token(path)), running=proc is not None and proc.poll() is None, error=_named['error'])


def stop_named_tunnel():
    proc = _named['proc']
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()
    _named['proc'] = None


# ---------------------------------------------------------------- 防休眠（Windows）
_awake = {'thread': None}


def keep_awake():
    """HomeCare AI 開著時，請 Windows 不要自動進入睡眠（螢幕仍會照設定關掉）。其他系統不做事。"""
    if platform.system() != 'Windows' or os.getenv('CAREFLOW_KEEP_AWAKE', '1').strip().lower() in ('0', 'false', 'no', 'off'):
        return False
    if _awake['thread'] is not None and _awake['thread'].is_alive():
        return True

    def hold():
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        while True:     # 設定綁在這個執行緒上；執行緒活著，系統就不會自動睡眠
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
            time.sleep(600)

    _awake['thread'] = threading.Thread(target=hold, name='homecare-keep-awake', daemon=True)
    _awake['thread'].start()
    return True



# ---------------------------------------------------------------- 免費固定網址：Cloudflare Workers「門牌」
# 免費、不用買網域、電腦不用安裝任何軟體：在居督自己的 Cloudflare 免費帳號放一個小程式（Worker），
# 網址固定是 https://homecare-checkin.<帳號代號>.workers.dev，永遠不變；它把居服員的手機轉到這台電腦目前的臨時網址。
# 臨時網址每次重開都會換，HomeCare AI 會自動通知門牌改指新的網址，所以 QR Code 永遠不用換。
# 手機的登入與綁定都記在門牌網址上，臨時網址換了也不用重新綁定。
# 設定只要一次：在 Cloudflare 建一把「Edit Cloudflare Workers」權杖貼到 04 頁，其餘由 HomeCare AI 透過 Cloudflare API 自動完成。
GATEWAY_SCRIPT = 'homecare-checkin'
GATEWAY_KEYS = ('gw_token', 'gw_account', 'gw_url', 'gw_target', 'gw_error')
GATEWAY_RESTART_SECONDS = 10
CF_API = 'https://api.cloudflare.com/client/v4'
_gw_lock = threading.Lock()

GATEWAY_WORKER_JS = r"""
// HomeCare AI 打卡門牌：把手機轉到辦公室電腦目前的打卡網址（由 HomeCare AI 自動更新 TARGET）。
const OFFLINE = `<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>打卡暫時無法使用</title><body style="font-family:sans-serif;background:#FBF7F0;color:#2B2622;padding:32px;line-height:1.7">
<h2 style="color:#1F5F7A">打卡主機暫時沒有連線</h2><p>辦公室的電腦可能關機、斷網或 HomeCare AI 沒有開著。</p>
<p>請過 1～2 分鐘再重新整理；一直打不開請聯絡居督，事後可以在打卡頁「補登」。</p></body></html>`;
export default {
  async fetch(request, env) {
    if (!env.TARGET) return new Response(OFFLINE, {status: 503, headers: {"content-type": "text/html; charset=utf-8"}});
    const url = new URL(request.url);
    const target = new URL(url.pathname + url.search, env.TARGET);
    const headers = new Headers(request.headers);
    headers.set("X-Forwarded-Host", url.host);
    headers.set("X-Forwarded-Proto", "https");
    const init = {method: request.method, headers, redirect: "manual"};
    if (!["GET", "HEAD"].includes(request.method)) init.body = await request.arrayBuffer();
    let resp;
    try { resp = await fetch(target.toString(), init); }
    catch (e) { resp = null; }
    if (!resp || resp.status === 530 || resp.status === 502 || resp.status === 1033) {
      return new Response(OFFLINE, {status: 503, headers: {"content-type": "text/html; charset=utf-8", "cache-control": "no-store"}});
    }
    const out = new Response(resp.body, resp);
    const loc = out.headers.get("Location");
    if (loc && loc.startsWith(env.TARGET)) out.headers.set("Location", url.origin + loc.slice(env.TARGET.length));
    out.headers.set("cache-control", "no-store");
    return out;
  }
};
"""


def _gw(key, path=None):
    return store.get_setting(key, path=path) or ''


def gateway_configured(path=None):
    return bool(_gw('gw_token', path) and _gw('gw_url', path))


def gateway_state(path=None):
    """dict(configured, url, target, error)：門牌網址、它目前指到的臨時網址、最近一次更新失敗的原因。"""
    return dict(configured=gateway_configured(path), url=_gw('gw_url', path), target=_gw('gw_target', path), error=_gw('gw_error', path))


def _cf(method, path, token, **kw):
    """呼叫 Cloudflare API；回傳 result。失敗時丟 RuntimeError（白話訊息）。"""
    import requests
    try:
        resp = requests.request(method, CF_API + path, headers={'Authorization': f'Bearer {token}'}, timeout=30, **kw)
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(f'連不到 Cloudflare：{exc}') from exc
    if not data.get('success'):
        errs = '；'.join(str(e.get('message', e)) for e in data.get('errors') or []) or f'HTTP {resp.status_code}'
        raise RuntimeError(errs)
    return data.get('result')


def _upload_gateway(token, account, target):
    meta = {'main_module': 'worker.js', 'compatibility_date': '2025-01-01',
            'bindings': [{'type': 'plain_text', 'name': 'TARGET', 'text': target or ''}]}
    files = {'metadata': (None, json.dumps(meta), 'application/json'),
             'worker.js': ('worker.js', GATEWAY_WORKER_JS.encode('utf-8'), 'application/javascript+module')}
    _cf('PUT', f'/accounts/{account}/workers/scripts/{GATEWAY_SCRIPT}', token, files=files)


def setup_gateway(token_text, path=None):
    """第一次設定門牌：驗證權杖 → 找帳號 → 確認 workers.dev 代號 → 上傳門牌 → 開放 workers.dev 網址。

    回傳 (門牌網址, None) 或 (None, 錯誤說明)。權杖只存在這台電腦的打卡資料庫。"""
    token = str(token_text or '').strip().split()[-1] if str(token_text or '').strip() else ''
    if len(token) < 30:
        return None, '權杖看起來不完整，請把 Cloudflare 產生的那一長串整個複製貼上。'
    try:
        accounts = _cf('GET', '/accounts', token) or []
        if not accounts:
            return None, '這把權杖看不到任何 Cloudflare 帳號，請建立權杖時選「Edit Cloudflare Workers」範本。'
        account = accounts[0]['id']
        try:
            sub = (_cf('GET', f'/accounts/{account}/workers/subdomain', token) or {}).get('subdomain')
        except RuntimeError:
            sub = None
        if not sub:          # 新帳號還沒有 workers.dev 代號：自動取一個
            sub = 'homecare-' + secrets.token_hex(3)
            sub = (_cf('PUT', f'/accounts/{account}/workers/subdomain', token, json={'subdomain': sub}) or {}).get('subdomain', sub)
        target = tunnel_url()
        _upload_gateway(token, account, target)
        _cf('POST', f'/accounts/{account}/workers/scripts/{GATEWAY_SCRIPT}/subdomain', token, json={'enabled': True})
    except RuntimeError as exc:
        return None, f'Cloudflare 設定沒有完成：{exc}'
    url = f'https://{GATEWAY_SCRIPT}.{sub}.workers.dev'
    for key, value in (('gw_token', token), ('gw_account', account), ('gw_url', url), ('gw_target', target), ('gw_error', '')):
        store.set_setting(key, value, path=path)
    if not target:
        start_tunnel_async()                  # 還沒有臨時網址：開一條，開好會自動更新門牌
    return url, None


def _gateway_follow(target, path=None):
    """臨時網址換了：在背景把門牌改指到新網址（同一個網址就不動）。"""
    if not gateway_configured(path) or _gw('gw_target', path) == target:
        return False

    def run():
        with _gw_lock:
            try:
                _upload_gateway(_gw('gw_token', path), _gw('gw_account', path), target)
                store.set_setting('gw_target', target, path=path)
                store.set_setting('gw_error', '', path=path)
            except RuntimeError as exc:
                store.set_setting('gw_error', f'門牌網址沒有更新成功：{exc}', path=path)
    threading.Thread(target=run, name='homecare-gateway', daemon=True).start()
    return True


def clear_gateway(path=None):
    """取消門牌網址（Cloudflare 上的 Worker 留著，之後重新設定會覆蓋）。"""
    for key in GATEWAY_KEYS:
        store.set_setting(key, '', path=path)
