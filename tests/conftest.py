import pytest


@pytest.fixture(autouse=True)
def _isolated_travel_cache(tmp_path, monkeypatch):
    """交通硬碟快取（機車路網、公車／捷運）一律寫到每個測試自己的暫存資料夾，
    不讀也不污染正式的 output_results/cache，測試之間也不互相影響。"""
    monkeypatch.setenv('CAREFLOW_CACHE_DIR', str(tmp_path / 'travel_cache'))
    # 登入：既有的 AppTest 流程測試不要卡在登入頁（tests/test_auth.py 需要時會自己改成 1）；
    # 帳號與稽核紀錄寫到暫存資料夾，不碰正式的 output_results。
    monkeypatch.setenv('CAREFLOW_AUTH', '0')
    monkeypatch.setenv('CAREFLOW_ACCOUNTS_DB', str(tmp_path / 'accounts.sqlite3'))
    monkeypatch.setenv('CAREFLOW_AUDIT_DIR', str(tmp_path / 'audit'))
    # 打卡網頁：測試不在 8600 埠開伺服器，打卡資料寫到暫存資料夾，不碰正式的 output_results/checkin.sqlite3。
    monkeypatch.setenv('CAREFLOW_CHECKIN_AUTOSTART', '0')
    monkeypatch.setenv('CAREFLOW_CHECKIN_TUNNEL', '0')          # 測試不下載 cloudflared、不開外部網址
    monkeypatch.setenv('CAREFLOW_CHECKIN_DB', str(tmp_path / 'checkin.sqlite3'))
    monkeypatch.delenv('CAREFLOW_CHECKIN_PUBLIC_URL', raising=False)
