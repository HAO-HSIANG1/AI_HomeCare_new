"""錯誤紀錄：畫面上照舊給居督看白話訊息，完整的錯誤追蹤另外寫進紀錄檔，給資訊人員追查。

- 紀錄檔：output_results/logs/careflow_errors.log（每檔 1MB、保留 5 份，自動輪替）；
  路徑可用環境變數 CAREFLOW_LOG_DIR 改（測試導到暫存資料夾）。
- 本次作業的錯誤清單：呼叫端傳入 state（app.py 傳 st.session_state），存在 state['_error_log']（最多 30 筆），
  側邊欄「目前狀態」可展開看代碼、下載紀錄檔。
- 不 import streamlit；不記錄個資，只記程式位置、錯誤類型與訊息。
"""
CAREFLOW_BUILD = '2026.10.18-v19'
import logging
import os
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = None          # 測試可直接指定；None 時依 CAREFLOW_LOG_DIR，預設 output_results/logs
MAX_ITEMS = 30
_logger = logging.getLogger('careflow')


def log_dir():
    if LOG_DIR is not None:
        return Path(LOG_DIR)
    return Path(os.getenv('CAREFLOW_LOG_DIR', str(Path(__file__).parent / 'output_results' / 'logs')))


def _ensure_handler():
    folder = log_dir()
    for handler in list(_logger.handlers):
        if getattr(handler, '_careflow', None) == str(folder):
            return
        if getattr(handler, '_careflow', None) is not None:      # 路徑換了（例如測試）：換一個新的檔案
            _logger.removeHandler(handler)
            handler.close()
    try:
        folder.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(folder / 'careflow_errors.log', maxBytes=1_000_000, backupCount=5, encoding='utf-8')
    except OSError:
        handler = logging.StreamHandler()
    handler._careflow = str(folder)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


def log_error(where, exc=None, state=None):
    """記一筆錯誤；回傳錯誤代碼（例 E1108-1415-3），畫面可以附在白話訊息後面，方便回報。

    where：發生在哪個功能（中文）；exc：例外物件；state：放本次錯誤清單的 dict（通常是 st.session_state）。"""
    stamp = datetime.now()
    detail = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__)) if exc is not None else ''
    message = f'{type(exc).__name__}: {exc}' if exc is not None else ''
    entry = {'時間': stamp.strftime('%m/%d %H:%M:%S'), '位置': str(where), '錯誤': message[:300]}
    if state is not None:
        items = state.get('_error_log')
        if not isinstance(items, list):
            items = []
        entry['代碼'] = f"E{stamp:%m%d-%H%M}-{len(items) + 1}"
        items.append(entry)
        state['_error_log'] = items[-MAX_ITEMS:]
    else:
        entry['代碼'] = f"E{stamp:%m%d-%H%M%S}"
    try:
        _ensure_handler()
        _logger.error('[%s] %s %s\n%s', entry['代碼'], where, message, detail)
    except (OSError, ValueError):       # 紀錄檔寫不進去也不能影響畫面
        pass
    return entry['代碼']


def session_errors(state):
    return list((state or {}).get('_error_log') or [])


def log_file():
    return log_dir() / 'careflow_errors.log'
