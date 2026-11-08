"""讓打卡網頁跟著 HomeCare AI 一起啟動，並決定要給居服員的打卡網址與 QR Code。

- HomeCare AI（app.py）開啟時在背景啟動打卡網頁（同一台主機、port 8600）；已經有人開著（例如另外執行
  `python -m checkin.server`）就直接沿用。設 CAREFLOW_CHECKIN_AUTOSTART=0 可以關掉（打卡網頁另外架在別台主機時）。
- 打卡網址依序取：04 頁設定的固定網址 → 環境變數 CAREFLOW_CHECKIN_PUBLIC_URL → 外部網址（Cloudflare 臨時通道）
  → 這台電腦在辦公室網路的位址。只有 https 網址手機才會給定位；辦公室位址只能在同一個 Wi-Fi 試用，也不記位置。
- 外部網址：04 頁按「🌐 產生外部網址」，用 cloudflared 開一條免費臨時通道（https://….trycloudflare.com）。
  第一次會從 Cloudflare 官方 GitHub 下載 cloudflared（約 50MB）到 output_results/bin；電腦本來有安裝就直接用。
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
    if fixed or not tunnel_enabled() or _tunnel['user_stopped'] or _tunnel['status'] != TUNNEL_IDLE:
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
