@echo off
rem 第一階段（登入）本機驗證：先跑 pytest，再用獨立的測試帳號庫啟動 Streamlit。
rem 測試帳號與稽核紀錄寫在 output_results\_verify\，不會動到正式的 accounts.sqlite3。
chcp 65001 >nul
cd /d %~dp0..
if not exist output_results\_verify mkdir output_results\_verify
set PYTHONIOENCODING=utf-8
echo [1/2] 執行 pytest，結果寫到 output_results\_verify\pytest.txt ...
python -c "import sys,streamlit,pytest;print(sys.executable, 'streamlit', streamlit.__version__, 'pytest', pytest.__version__)" > output_results\_verify\pytest.txt 2>&1
python -c "import importlib.util as u;print('phase2 packages:',{m:bool(u.find_spec(m)) for m in ('flask','waitress','segno','cryptography')})" >> output_results\_verify\pytest.txt 2>&1
python -m pytest tests -q -rs -p no:cacheprovider >> output_results\_verify\pytest.txt 2>&1
echo pytest 結束，代碼 %ERRORLEVEL%
echo [2/2] 啟動 Streamlit（登入開啟），網址 http://localhost:8501 ，關閉這個視窗即停止。
set CAREFLOW_AUTH=1
set CAREFLOW_ACCOUNTS_DB=%CD%\output_results\_verify\accounts.sqlite3
set CAREFLOW_AUDIT_DIR=%CD%\output_results\_verify\audit
python -m streamlit run app.py --server.headless true --server.port 8501
pause
