# PORTING_PLAN：從 AI_HomeCare_Atrust 移植「登入 → 打卡 → KPI」

> 2026-11-08 更新：**第一階段（登入）已完成**，見「1.5 實作紀錄」。**第二階段（QR 打卡＋執行對照）已完成**，見「2.5 實作紀錄」（選配 2C 以居服員排班未做）。**第三階段（試辦 KPI）已完成**，見「3.5 實作紀錄」。
> 移植時一律遵守 `CLAUDE.md`「程式與介面風格規範」第三節的移植規則：對方程式只取邏輯，介面與命名依本專案規範重寫。
> - 對方：`lulu-tina/AI_HomeCare_Atrust`，commit `e002668`（淺層 clone，只有最新一版，看不到對方的歷史紀錄）。
> - 我方：`AI_HomeCare_new`，HEAD `d9e35ce`。
> - 行號：「我方 L123」＝**登入移植前**（`d9e35ce`）本專案檔案的行號；第一階段在 `app.py` 加了約 280 行，第二、三階段動手前請用文中的錨點文字（函式名、subhead 標題）重新定位。「對方 L123」＝Atrust 的行號。
> - 我方 `.py` 是 CRLF 換行、對方是 LF。比對前已統一換行；**直接複製整個檔案過來會讓 git 顯示整檔都改了**，移植時請保持 CRLF（或先加 `.gitattributes` 統一）。

---

## 進度總覽（2026-11-08 收尾）

| 階段 | 狀態 | commit |
|---|---|---|
| 第一階段：登入（含稽核） | ✅ 主體完成；部分稽核事件與保存期限未做（見 1.5） | `7615c84` |
| 第二階段：QR 打卡＋執行對照（選配：以居服員排班） | ✅ 打卡與執行對照完成；選配 2C 未做（見 2.5） | `dad1376` |
| 第三階段：試辦 KPI | ✅ 完成（見 3.5） | 未 commit |
| 文件 | ✅ `CLAUDE.md`「程式與介面風格規範」、README 登入與兩層登入說明 | `7615c84` |

### 已完成
- `auth.py`：
  - PBKDF2-SHA256 20 萬次加鹽
  - 連錯 5 次鎖 10 分鐘
  - 帳號不存在、已停用、鎖定中也算一次雜湊
  - 不能停用最後一位主管
  - 第一位主管只能在完全沒有帳號時建立
  - `CAREFLOW_AUTH=0` 可以關閉登入
- `audit_log.py`：只能附加的 hash chain 稽核紀錄；登入、登入失敗、登出、帳號異動都會寫入。
- `app.py`：
  - 登入閘門
  - 側邊欄帳號區（登出、變更我的密碼）
  - 主管專用的 👥 帳號管理頁（新增、重設密碼並解鎖、停用／啟用、檢查稽核紀錄）
  - 依角色把主管報表與帳號管理上鎖
- `careflow_ui.py`：共用元件 `auth_card()`、新模組 `accounts`。
- 測試：`tests/test_auth.py`、`tests/test_audit_log.py`；`tests/conftest.py` 隔離帳號與稽核資料，並設 `CAREFLOW_AUTH=0`。

### 還沒做
- **第一階段剩下的部分**：
  - 匯入、匯出、顯示遮罩姓名、請假、居督覆寫的稽核事件
  - `data_retention.py`（衝突 C1-4、C1-5）
  - 示範模式要不要記進正式稽核紀錄（C1-3）
  - 改寫 `DATA_GOVERNANCE.md` 第 44 行
- **第二階段**：選配 2C（以居服員排班）、打卡資料的到期刪除排程（見 `DATA_GOVERNANCE.md` 第四節）。
- **第三階段**：KPI 頁還沒在瀏覽器看過；`tests/test_kpi_view_ui.py`（AppTest）在沒有 streamlit 的環境略過，沒有實際跑過。
- **還沒執行過的測試**：3 個需要 Streamlit 的測試（`test_module_codes_match_ui`、`test_first_run_setup_then_roles`、`test_auth_off_skips_login`）沒有實際跑過；登入卡片、帳號管理頁也還沒在瀏覽器看過。
- **移植前就有的失敗**：`tests/test_source_workbook.py` 呼叫 `update_source_workbook(weekly_workers=...)`，但函式不接受這個參數。不在這次範圍內，沒有修。

### 遇到的問題與決定
| # | 問題／選擇 | 決定 | 原因 |
|---|---|---|---|
| D1 | 帳號管理放哪裡 | 獨立頁 `accounts`（`M_ACCOUNTS`），從側邊欄「👥 帳號管理」進入，不放在側邊欄展開區（對方的做法） | 規範規定側邊欄只放狀態；表單和表格需要整頁寬度；這一頁畫完就 `st.stop()`，不讀 Excel、不跑排班 |
| D2 | 登入頁的樣式 | 用 `careflow_ui.auth_card()` 包住既有的 `run_card_html` 和原生 `st.form`；主色沿用 `--cf-primary #1F5F7A`，**沒有新增 CSS 或配色** | 移植規則 1；對方的登入頁是 CareFlow 品牌和綠色系 |
| D3 | 居督不能看主管報表的做法 | 寫在 `_flow_locks()` 依 `auth.can_access()` 上鎖，步驟列顯示 🔒 | 換頁的唯一入口是步驟列；對方在頁面裡 `st.warning`＋`st.stop()`，不符合方案 A |
| D4 | `auth` 函式的錯誤怎麼回報 | 回傳中文錯誤字串或 None，不丟例外 | 依規範的錯誤處理第 1 層；對方是 `raise ValueError` |
| D5 | 稽核紀錄的帳號從哪裡來 | `audit_log` 是純函式，帳號由 app.py 傳入；事件只保留 4 種 | 規範：計算模組不 import streamlit；對方的 `current_account()` 會直接讀 `st.session_state` |
| D6 | 比對方多做的安全處理 | 鎖定中也算雜湊；`create_first_manager()` 用 `BEGIN IMMEDIATE`，已有帳號就拒絕；`current_user()` 每次重跑重新讀，帳號被停用立即登出；不能停用自己 | 防止猜帳號、有人搶先重建主管、被停用的人還能繼續操作 |
| D7 | Caddy basic auth | 保留，在 README 說明兩層的分工（外圍共用帳密，系統內每人一個帳號並記稽核） | 使用者指定；之後改走 VPN 可以只拿掉第一層 |
| D8 | 測試環境沒有 Streamlit | 需要 streamlit 的測試用 `pytest.importorskip`；AppTest 時把 `PBKDF2_ROUNDS` 調成 1000 | 這次的雲端和電腦端環境都不能安裝套件，不能讓整檔載入失敗；20 萬次會讓 AppTest 太慢 |
| D9 | 換行符號 | `.py` 和 `CLAUDE.md` 寫回 CRLF（和原本工作目錄一樣），git 存的是 LF（Windows autocrlf） | 在 Linux 環境裡 `git diff` 會顯示整檔修改，加 `--ignore-cr-at-eol` 才看得到實際改動；在 Windows 用 git 看是正常的 |
| D10 | 對方 repo 連不到 | 你的電腦連不到 GitHub，對方 repo 改 clone 到雲端工作區的 `/tmp/atrust` | 網路限制；分析只需要讀檔 |

---

## 0. 總覽

### 0.1 功能 ↔ 對方檔案

| 功能 | 對方新增的檔案（我方沒有） | 依賴 | 測試 |
|---|---|---|---|
| 登入／權限 | `auth.py`（144 行，帳號存在 `output_results/accounts.sqlite3`，PBKDF2；角色＝主管／居督） | 只用標準函式庫 | `tests/test_auth.py`（2，AppTest） |
| 存取稽核 | `audit_log.py`（157 行，雜湊鏈、只能附加，存在 `output_results/audit/`） | 標準函式庫；會讀 `st.session_state['auth_user']` 當帳號 | `tests/test_governance.py`（6） |
| 保存期限 | `data_retention.py`（96 行） | `persistent_cache.cache_path`、`audit_log` | `tests/test_governance.py` |
| QR 打卡網頁 | `checkin/`（`server.py` Flask、`store.py` SQLite、`runner.py` 背景啟動／QR／cloudflared、`manage.py` CLI、`templates/*.html`、`README.md`）、`start_checkin.bat` | **flask、waitress、segno、cryptography**（新套件）；`store.punch_frame()` 輸出給 `attendance_reconcile` | `tests/test_checkin.py`（5）、`tests/test_checkin_simple.py`（15）、`tests/test_checkin_panel_ui.py`（6，AppTest，依賴 `test_plan_change_ui._setup`） |
| 排定 vs 實際對照 | `attendance_reconcile.py`（594 行） | pandas；讀 `PipelineConfig.attendance_*` | `tests/test_attendance_reconcile.py`（8） |
| 以居服員排班面板 | `worker_panel.py`（125 行） | `caregiver_engine` | `tests/test_worker_panel.py`（2） |
| 試辦 KPI | `kpi_metrics.py`（278 行，基準值存 `output_results/pilot_baseline.json`）、`PILOT_KPI.md` | `issue_center.assigned_overlaps / transition_issues`（我方已有） | `tests/test_kpi_metrics.py`（8） |

> ⚠️ **`worker_panel.py` 其實不是打卡功能**：它是「以居服員為主軸排班」——在「個人週班」選一位居服員，勾選未排時段一鍵排入（對方 app.py L1665–1738）。和打卡沒有程式上的關聯，可以獨立決定要不要移植（下面放在第二階段的選配 2C）。

### 0.2 這些功能動到的共用檔案

| 共用檔案 | 和這些功能有關的改動 | 對方其他改動（**不要**） |
|---|---|---|
| `app.py` | 見各階段（import、登入閘門、側邊帳號面板、稽核紀錄呼叫、打卡面板、執行對照、居服員面板、KPI） | 見 0.3，約 1,500 行 |
| `careflow_ui.py` | **無**。對方版是舊 UI（412 行），我方已大改（1308 行，步驟列、底部操作列等） | 全部（不要覆蓋） |
| `runtime_views.py` | **兩邊完全相同**，不用動 | — |
| `dispatch_workflow.py` | `add_blocks()` 結尾加 `audit_log.record('leave', …)`（對方 L120–124，5 行） | 對方**沒有**我方的 `replace_workdays`、`DEMO_STORE_DIR`／`fresh_demo_store_path`／`discard_demo_store`、`history_summary`——直接覆蓋會**刪掉示範模式與上班日修正** |
| `docker-compose.yml` | `CAREFLOW_CHECKIN_PUBLIC_URL`、`CAREFLOW_CHECKIN_SECURE`、`expose: ["8501","8600"]` | 無 |
| `deploy/Caddyfile` | 新增 `checkin.example.org { reverse_proxy careflow:8600 }` 區段 | 無 |
| `requirements.txt` | `flask>=3.0,<4`、`waitress>=3.0,<4`、`cryptography>=42`、`segno>=1.5,<2` | 無 |
| `Dockerfile`（清單外，但需要） | `EXPOSE 8501 8600` | 無 |
| `caregiver_engine.py`（清單外，但需要） | ① `PipelineConfig` 加 5 個 `attendance_*` 欄位（對方 L276–281）② `save_override_log` 結尾加 `audit_log.record('override', …)`（對方 L4446–4451）③ `identity_display` 的 `caregiver_cols` 加 `'排定居服員','實際居服員'`（對方 L4524） | 對方**沒有**我方的大眾運輸硬碟快取（`_transit_disk_key`、`_fill_transit_from_disk`、`_save_transit_to_disk`、`google_query_summary`）；對方另有「不適合居服員」硬性條件、`_FALLBACK_PAIRS` 改成每次排班獨立、`_service_code_indices` 快取、行事曆快取鍵加交通設定——都不在本次範圍 |
| `dashboard_view.py`（清單外，KPI 需要） | 新增 `render_pilot_kpis()`（對方 L147–189） | 對方是舊版儀錶板：沒有 `show_heat`／`title` 參數、`render_demand_heat` 改回私有、拿掉 `_render_staffing_advice`、`heat_legend`——直接覆蓋會**弄壞我方主管報表**（`app.py` L2933、L2965、L3032 都在用新參數） |
| `issue_center.py` | 無（對方加 `'不適合配對'` 分類，屬於「不適合居服員」功能） | 該行 |
| `calendar_view.py`、`.streamlit/config.toml`、`DATA_GOVERNANCE.md` | 無 | 對方是 CareFlow 品牌字樣與舊配色，我方已改成 HomeCare AI |
| `build_info.py` | 可選：`REQUIRED_MODULES` 加 `'auth'`、`'worker_panel'`（兩者有 `CAREFLOW_BUILD` 標記） | 對方另加的 `plan_versions`、`error_log`、`undo_stack`、`billing` |

### 0.3 對方 app.py 其他改動（我不要的，移植時跳過）

- **週計畫異動**（`plan_versions.py`，對方 L3308–3605，約 300 行）
- **復原上一步**（`undo_stack.py`，對方 L71–83、L5911–5920）
- **CSMS 申報與自付額試算**（`billing.py`，對方 L5394–5446；其中會讀打卡的「未遇」紀錄）
- **異動紀錄整合**（`change_log.py`，對方 L5837–5870，取代了我方的「人工覆寫紀錄」）
- **錯誤紀錄**（`error_log.py`，`_log_error` 在對方 app.py 用了 40 次）
- **進階模式切換**（`ui_advanced`／`_advanced`，對方 L579–583 及多處 `if _advanced:`）
- 舊版側邊欄「功能模組」radio 導覽（對方 L571–583），我方已改成頂部步驟列＋`_flow_locks()`
- 匯入區、待派案家試算、資料表編輯區的多處 UI 文字與排版差異（對方 L1092–1245、L2522–2704 等）

反過來，**我方有、對方沒有、移植時不可被覆蓋**：示範模式（`demo_mode`、`_reset_demo_store`）、主管報表（`manager_report.py`、我方 L2923–3045）、大眾運輸硬碟快取、`replace_workdays`、`history_summary`、`import_health.py`、`week_board.py`、新版 `careflow_ui.py`。

**結論：所有共用檔案都只能「挑段落手動貼入」，不能整檔覆蓋。**

---

## 第一階段：登入（含存取稽核、保存期限）

稽核要跟登入一起做：`audit_log.current_account()` 從登入資訊取帳號，登入／登入失敗／帳號管理也都寫進稽核。

### 1.1 新增檔案

| 檔案 | 說明 |
|---|---|
| `auth.py` | 原樣複製 |
| `audit_log.py` | 原樣複製 |
| `data_retention.py` | **選配**，見衝突 C1-4 |
| `tests/test_auth.py`、`tests/test_governance.py` | 原樣複製 |

### 1.2 要修改的地方

**app.py**

1. **import**：在我方 L60 附近（`from source_fields import …` 之後）加入 `import audit_log`（和選配的 `import data_retention`、`data_retention.run_daily()`）。對應對方 L59–61。
2. **登入閘門＋帳號面板**：把對方 L462–565 整段（`import auth as _auth`、`_render_login()`、`if _auth.enabled() and not st.session_state.get('auth_user'): _render_login()`、`_user`、`_is_manager`、`_account_panel()`）貼在我方 L448 `with st.sidebar:` **之前**。
3. **側邊欄**：在我方 `with st.sidebar:` 區塊（L449–456）最後加
   `if _auth.enabled(): st.divider(); _account_panel()`（對方 L600–602）。
4. **05 只限主管**：對方用 `if _module == M_ANALYTICS and not _is_manager: st.warning(...); st.stop()`（對方 L604–606）。我方改用步驟列，建議改在 `_flow_locks()`（我方 L418）裡：非主管時把 `M_ANALYTICS` 加進鎖定集合，`render_stepper` 就會自動顯示成鎖住；另外保留對方的 `st.stop()` 當最後防線。
5. **稽核紀錄呼叫**（各一行，包在原本流程裡）：
   - 匯入：我方 L898 `st.session_state['_agency_upload'] = …` 之後加 `audit_log.record('import', file_sha256=hashlib.sha256(_new_bytes).hexdigest(), size_bytes=len(_new_bytes))`（對方 L883）
   - 顯示遮罩姓名：我方 L1015–1017 的 `st.checkbox(... key="show_identity_names")` 加 `on_change=lambda: st.session_state.get('show_identity_names') and audit_log.record('reveal_names')`（對方 L993）
   - 匯出服務班表：我方 L5500 `build_schedule_excel` 按鈕產生成功後加 `audit_log.record('export', kind='服務班表 Excel', rows=…)`（對方 L5373）
   - 匯出更新機構 Excel：我方 L5562–5565 `build_source_update` 成功後加 `audit_log.record('export', kind='更新機構 Excel')`（對方 L5496）
6. **稽核檢視**：對方 L1012–1023「🧾 存取稽核紀錄」expander 放在 `if _advanced:` 底下；我方沒有進階模式，建議改成 `if _is_manager:`，放在 `_sidebar_privacy` 容器。

**dispatch_workflow.py**：只在 `add_blocks()`（我方 L102）結尾補對方 L120–124 那 5 行 `audit_log.record('leave', …)`。**其他差異一律不動。**

**caregiver_engine.py**：只在 `save_override_log`（我方 L4437 起，`entry.to_csv(...)` 之後）補對方 L4446–4451 的 `audit_log.record('override', …)`。

**tests/conftest.py**（重要）：在既有的 autouse fixture 加上
```python
monkeypatch.setenv('CAREFLOW_AUTH', 'off')                       # 既有 AppTest 測試不要卡在登入畫面
monkeypatch.setenv('CAREFLOW_ACCOUNTS_DB', str(tmp_path / 'accounts.sqlite3'))
monkeypatch.setenv('CAREFLOW_AUDIT_DIR', str(tmp_path / 'audit'))  # 測試不要寫進正式稽核紀錄
```
`test_auth.py` 自己會再把 `CAREFLOW_AUTH` 設成 `on`，不衝突。

**build_info.py**（選配）：`REQUIRED_MODULES` 加 `'auth'`。

### 1.3 可能衝突

| # | 衝突 | 建議 |
|---|---|---|
| C1-1 | 登入後 `st.stop()` 擋在側邊欄之前；我方側邊欄有 `side_brand()`、交通喚醒、示範模式開關，**登入前都不會出現**，`traffic_wake` 背景喚醒也會延到登入後才開始 | 可接受；若要提早喚醒交通主機，把 `traffic_wake.start()` 移到登入閘門之前 |
| C1-2 | 我方步驟導覽靠 `_nav_request`／`_flow_locks()`（L399–431）在檔案很前面就決定 `cf_module`；登入閘門要放在它之後、`with st.sidebar:` 之前，否則 05 的鎖定判斷拿不到 `_is_manager` | 依 1.2 第 2、4 點的位置 |
| C1-3 | `audit_log` 寫 `output_results/audit/`，示範模式的動作（請假、覆寫）也會被記進**正式**稽核紀錄 | 決定：示範模式要不要記？要隔離的話，在 `audit_log.record` 前判斷 `st.session_state.get('demo_mode')` |
| C1-4 | `data_retention.run_daily()` 會刪 30 天前的 `road_legs` 路段快取。我方 d9e35ce 才剛做「交通硬碟快取確保排班結果可重現」，刪快取後重新查路，結果可能和之前不一樣；另外它**不管我方新增的 `transit_legs` 表** | 先不移植，或把 `CAREFLOW_ROAD_CACHE_DAYS` 設大，並決定 `transit_legs` 的保存期限後再補 |
| C1-5 | `data_retention.run_daily()` 在 `import app` 時就執行，會在 `output_results/` 寫 marker 檔；測試也會碰到 | 若移植，測試環境要把 marker 指到 tmp，或加環境變數開關 |
| C1-6 | `deploy/Caddyfile` 目前是 basic auth；加上內建登入後，正式環境會**登入兩次** | 上線時拿掉 Caddy basic auth，或保留當外層防護（`DATA_GOVERNANCE.md` L44 已寫是暫時方案，要一起改） |
| C1-7 | 對方登入畫面字樣是「CareFlow 智慧居服排班」，我方已改成「HomeCare AI」 | 貼入時改字 |
| C1-8 | 自動存檔（`session_store`）只依機構／檔案分，不依帳號；兩位居督登入同一台主機仍會看到同一份進度 | 本階段不處理，記為已知限制 |

### 1.4 驗收
`tests/test_auth.py`、`tests/test_governance.py` 通過；既有測試結果不比基準差（見第 5 節）。

### 1.5 實作紀錄（2026-11-08 完成）

依使用者這次的範圍：**登入、角色權限、帳號管理、登入／帳號異動的稽核紀錄**。依風格規範，和 1.1～1.3 的原計畫有以下差異：

| 項目 | 原計畫（照搬對方） | 實際做法（依本專案規範） |
|---|---|---|
| 登入畫面 | 貼對方 `_render_login()`，表單寫在 app.py | 新增共用元件 `careflow_ui.auth_card(mode)`（login／setup），沿用既有的 `run_card_html` 與表單樣式，沒有新增 CSS；app.py 的 `_render_login()` 只負責驗證與寫稽核 |
| 帳號管理 | 側邊欄 expander（對方 `_account_panel`） | 新模組 `accounts`（`careflow_ui.MODULES` 第 6 項、`M_ACCOUNTS`），主管從側邊欄「👥 帳號管理」進入；頁面用 `module_header`、`subhead`、`show_table`、`step_action_bar`；畫完就 `st.stop()`，不讀 Excel、不跑排班 |
| 05 只限主管 | `st.warning` ＋ `st.stop()` | 寫進 `_flow_locks()`：依 `auth.can_access(role, module)` 上鎖，步驟列顯示 🔒 與「只有主管帳號可以使用」；停在上鎖頁會自動退回 |
| `auth.py` | 錯誤用 `raise ValueError` | 依規範「資料層回傳中文錯誤字串或 None」；另加 `create_first_manager()`（已有帳號就拒絕）、`current_user()`（每次重跑重新讀帳號，被停用立即登出）、`change_own_password()`、`can_access()`；鎖定中也會算一次雜湊；`CAREFLOW_AUTH=0` 關閉 |
| `audit_log.py` | `current_account()` 會 import streamlit 讀登入資訊 | 純函式，帳號由呼叫端傳入；`EVENTS` 只留目前用到的 login／login_failed／logout／account |
| 測試隔離 | conftest 設 3 個環境變數 | 同左（`CAREFLOW_AUTH=0`、`CAREFLOW_ACCOUNTS_DB`、`CAREFLOW_AUDIT_DIR`） |

新增：`auth.py`、`audit_log.py`、`tests/test_auth.py`、`tests/test_audit_log.py`。
修改：`app.py`、`careflow_ui.py`、`build_info.py`（`REQUIRED_MODULES` 加 `auth`、`audit_log`）、`tests/conftest.py`、`README.md`（含 Caddy 與系統登入兩層的說明）、`CLAUDE.md`。
**沒有動**：`deploy/Caddyfile`（basic auth 保留）、`dispatch_workflow.py`、`caregiver_engine.py`。

**第一階段尚未做（留待之後決定）**：
- 1.2 第 5 點的其他稽核事件：匯入、顯示遮罩姓名、匯出、請假（`dispatch_workflow.add_blocks`）、居督覆寫（`caregiver_engine.save_override_log`）。要做時在 `audit_log.EVENTS` 加事件代碼，呼叫時傳 `account=_user['username']`。
- `data_retention.py`（衝突 C1-4、C1-5 未解決）。
- C1-3（示範模式的動作要不要記進正式稽核紀錄）：目前登入相關事件與示範模式無關，暫不影響。
- `DATA_GOVERNANCE.md` 第 44 行「只有一組 supervisor 帳號」的現況描述已過時，需要改寫。

---

## 第二階段：QR 打卡（含執行對照；選配：以居服員排班）

### 2.1 新增檔案

| 檔案 | 說明 |
|---|---|
| `checkin/`（整個資料夾，含 `templates/`、`README.md`） | 原樣複製；畫面字樣 CareFlow → HomeCare AI |
| `start_checkin.bat` | 原樣複製 |
| `attendance_reconcile.py` | 原樣複製 |
| `tests/test_checkin.py`、`tests/test_checkin_simple.py`、`tests/test_attendance_reconcile.py` | 原樣複製 |
| `tests/test_checkin_panel_ui.py` | **要改寫**：它 `from test_plan_change_ui import _setup`，而 `test_plan_change_ui.py` 屬於週計畫異動（不移植）。需把 `_setup` 搬進這支測試或 conftest |
| （選配 2C）`worker_panel.py`、`tests/test_worker_panel.py` | 原樣複製 |

### 2.2 要修改的地方

**requirements.txt**：加 `flask>=3.0,<4`、`waitress>=3.0,<4`、`cryptography>=42`、`segno>=1.5,<2`。

**docker-compose.yml**：`environment` 加 `CAREFLOW_CHECKIN_PUBLIC_URL`、`CAREFLOW_CHECKIN_SECURE: "1"`；`expose` 改 `["8501", "8600"]`。

**deploy/Caddyfile**：加 `checkin.<網域> { reverse_proxy careflow:8600 }`（不加 basic auth，居服員用員編＋PIN）。

**Dockerfile**：`EXPOSE 8501 8600`。

**caregiver_engine.py**：
- `PipelineConfig`（我方 L179 起）加 5 個欄位：`attendance_late_grace_mins`、`attendance_early_leave_grace_mins`、`attendance_short_ratio`、`attendance_match_window_mins`、`attendance_gps_radius_m`（對方 L276–281）。app.py 用到 `config.attendance_gps_radius_m`，所以一定要加。
- `identity_display`（我方 L4530）的 `caregiver_cols` 加 `'排定居服員','實際居服員'`。

**app.py**
1. **import**（我方 L60 附近）：`import attendance_reconcile as _att`、`from checkin import store as _checkin_store`、`from checkin import runner as _checkin_runner`，以及 `_fresh_module()`、`_start_checkin_once()`（對方 L68、L84–116）。
2. **打卡面板**：對方 L5510–5726（`subhead('📱 居服員打卡')`、`_checkin_publish/_decide/_revoke/_demo`、`_checkin_panel()`），貼在我方 L5575 `_source_update_download()` 之後、L5577 `subhead('人工覆寫紀錄')` 之前（都在 `if _module == M_REVIEW:` 內）。
3. **執行對照**：對方 L5728–5835（`subhead('執行對照（排定 vs 實際）')`、`_attendance_view()`），接在打卡面板之後。
4. **（選配 2C）以居服員排班**：對方 L1665–1738 的 `_render_worker_panel()` 貼在我方 L1700（`_quick_reassign` 那組函式之後）；呼叫點（對方 L2783–2784）貼在我方 L2864 `render_calendar_overview(...)` 之後：
   `if st.session_state.get('cf_calendar_mode') == '個人週班' and st.session_state.get('cf_person'): _render_worker_panel(...)`。
   用到的 `_workflow_frames`、`_quick_reassign`、`_label_ids_plain`、`_workflow_store.record_workdays` 我方都有。

**tests/conftest.py**：加 `monkeypatch.setenv('CAREFLOW_CHECKIN_AUTOSTART', '0')`、`monkeypatch.setenv('CAREFLOW_CHECKIN_DB', str(tmp_path / 'checkin.sqlite3'))`，避免每支 AppTest 都真的在 8600 埠開伺服器、寫正式打卡資料庫。

### 2.3 可能衝突

| # | 衝突 | 建議 |
|---|---|---|
| C2-1 | 打卡面板與執行對照裡用了 `_log_error(...)` 4 處（第三階段 KPI 段另有 2 處），來自 `error_log.py`（我方沒有，屬於不要的改動） | 二選一：(a) 在 app.py 頂端放一個 3 行的替代函式 `def _log_error(where, exc): print(f'[{where}] {exc}')`；(b) 連 `error_log.py`（61 行、只用標準函式庫）一起搬。建議 (a)，範圍最小 |
| C2-2 | 對方 L5712–5714 等處 `st.session_state['checkin_board_day']` 用 `date_input` 預設今天；我方示範模式用固定日期的示範 Excel，**今天通常不在班表期間內**，看板會是空的 | 示範模式時預設改成班表第一天，或用對方內建「➕ 建立示範班」 |
| C2-3 | 打卡資料庫 `output_results/checkin.sqlite3` 和示範模式無關：示範模式下按「📲 發布目前班表」會覆蓋正式打卡班表 | 示範模式時停用發布按鈕，或把 `CAREFLOW_CHECKIN_DB` 指到示範暫存檔 |
| C2-4 | `_start_checkin_once()` 在 `import app` 時就在背景開 8600 埠；我方 Windows 本機若同時開 `start_checkin.bat` 會撞埠（對方已處理 `OSError`，只是要知道） | 依對方設計，CareFlow 開著就自動起；正式環境若另架主機，設 `CAREFLOW_CHECKIN_AUTOSTART=0` |
| C2-5 | `runner.py` 的「產生外部網址」會從 GitHub 下載 cloudflared（約 50MB）並開 trycloudflare 通道，任何人拿到網址都能連到打卡頁 | 正式環境改用 Caddy 固定網域；外部網址只在試辦／示範用 |
| C2-6 | 打卡、對照畫面字樣為 CareFlow；`checkin/README.md` 指向對方部署方式 | 改字、改 README 的部署段落 |
| C2-7 | 打卡位置（GPS）是新的個資類別；我方 `DATA_GOVERNANCE.md` 還沒寫 | 移植時同步補上收集目的、保存期限 |
| C2-8 | 打卡面板放在 04 的「匯出」區之後，我方 04 最下面有 `step_action_bar`；對方是 `module_nav_buttons(M_REVIEW)` | 只貼面板本體，不要帶對方的 `module_nav_buttons` |

### 2.4 驗收
`test_checkin*.py`、`test_attendance_reconcile.py`（＋選配 `test_worker_panel.py`）通過。手動：發布班表 → 手機掃 QR → 到勤／離開 → 04 執行對照讀「打卡網頁」來源。

### 2.5 實作紀錄（2026-11-08 完成）

對方 commit 已更新為 `25abbef`（「打卡看板分開顯示到勤與離開的位置、距離」）。依使用者這次的範圍與風格規範，和 2.1～2.3 的原計畫差異如下：

| 項目 | 原計畫（照搬對方） | 實際做法 |
|---|---|---|
| 打卡種類 | 簽到／簽退／未遇（畫面「到勤」「離開」） | 依使用者指定：**上班／下班／未遇**，資料庫與畫面一致 |
| 登入方式 | 對方已從 PIN 改成手機綁定，但仍留 PIN 表與 `manage.py` | 只做手機綁定；不搬 PIN、`accounts` 表、`manage.py`、`start_checkin.bat` |
| 員工編號 | 一律轉大寫存 | 存**原本的居服員ID**；手機輸入不分大小寫，用 `store.resolve_caregiver()` 對回原 ID |
| 主機時間 | `datetime.now()`（Docker 容器是 UTC） | `store.now()` 固定用 `Asia/Taipei` |
| 補登 | 只能補沒打到的卡，標「補卡待審」，沒有覆核動作 | 也可以**更正已打過的卡**；新增只能附加的 `reviews` 表，04 頁「補登覆核」核准／退回。採用順序：已核准補登 → 現場打卡 → 待覆核補登；退回不採用 |
| 只能新增 | 觸發器只擋 UPDATE | 也擋 DELETE（只有 `DEMO-` 示範班可刪）；`reviews` 也只能新增 |
| GPS | 手機有給就記；http 時手機畫面顯示紅色錯誤 | **伺服器端也判斷 https**（`request.is_secure`／`Cf-Visitor`），不是 https 就不存；手機畫面改成提醒「只記時間」 |
| 位置異常 | 「地點異常」嚴重度高 | 改名「位置提醒」，嚴重度「提醒」，**不算異常**、不影響狀態；看板不產生 Google 地圖連結（避免座標送第三方） |
| 姓名 | `mask_name` 王○明 | 同 `caregiver_engine._privacy_mask_name`（王○○），發布時再遮一次，資料庫不存原名 |
| 發布範圍 | 整個期間 | 依使用者指定「發布今日班表」；另可選一天先發布 |
| 執行對照 | `attendance_reconcile.py` 594 行，可上傳機構 Excel／CSV、欄名別名、時間窗配對 | 重寫成約 260 行：直接讀打卡資料庫、以任務ID 對應；只對照**已發布的日期**；列出遲到、漏打卡（整筆沒打／漏上班／漏下班）、未遇、早退、補登待覆核、換人打卡、排外打卡 |
| 外部網址 | `runner.py` 自動下載 cloudflared（約 50MB）並開 trycloudflare | 同對方：④ 頁「🌐 產生外部網址／停止外部網址」（使用者要求和對方畫面一致，2026-11-08 補上）。之後依使用者要求改成**沒有固定網址時預設自動在背景開外部網址**（`CAREFLOW_CHECKIN_TUNNEL=0` 關閉），下載 cloudflared 遇到 504 會重試 3 次；④ 打卡區改成由上而下：① 發布班表（含示範班）→ ② 今日打卡看板 → ③ 分頁「打卡網址／手機綁定／補登覆核」，執行對照明細預設收合 |
| 辦公室網址 | 解析 Windows `ipconfig` 挑網卡 | 只用 `lan_ip()`；不搬 ipconfig 解析 |
| 缺套件 | 04 頁一鍵 `pip install` | 不做一鍵安裝。segno 改成隨程式附上（`checkin/_vendor/segno`，BSD-3），主機沒裝也能產生 QR Code；缺 flask 時只顯示警告與指令 |
| `_log_error`（C2-1） | 需要替代函式 | 不需要：畫面層依三層錯誤處理寫 `st.error('…原因：' + str(exc))` |
| 示範模式（C2-2、C2-3） | — | 示範模式時停用「發布今日班表」；保留「建立示範班」給第一次試用 |
| Docker（C2-4） | 跟著 Streamlit 自動啟動 | Streamlit 要有人開網頁才會執行 app.py，所以 docker-compose 另開 `checkin` 服務常駐，`careflow` 設 `CAREFLOW_CHECKIN_AUTOSTART=0` |
| 容許值 | 5 個 `attendance_*` | `attendance_late_grace_mins`、`attendance_early_leave_grace_mins`、`attendance_overdue_mins`（新增，15 分鐘）、`attendance_gps_radius_m`；不需要 `short_ratio`、`match_window_mins` |
| 稽核 | — | `audit_log.EVENTS` 加 `checkin`（發布、手機核准／拒絕／解除、補登覆核、網址、自動綁定設定） |

新增：`checkin/`（`__init__.py`、`store.py`、`server.py`、`runner.py`、`templates/base.html`、`login.html`、`pending.html`、`today.html`）、`attendance_reconcile.py`、`tests/test_checkin.py`（15）、`tests/test_attendance_reconcile.py`（6）、`tests/test_checkin_panel_ui.py`（1，AppTest，需要 streamlit）。
修改：`app.py`（import、`_start_checkin_server()`、④ 打卡面板與執行對照）、`caregiver_engine.py`（`PipelineConfig.attendance_*`、`identity_display` 加「排定居服員」「打卡居服員」）、`careflow_ui.py`（MODULES 04 說明）、`audit_log.py`、`build_info.py`（`attendance_reconcile`）、`tests/conftest.py`、`requirements.txt`（flask、waitress、segno）、`Dockerfile`、`docker-compose.yml`、`deploy/Caddyfile`、`README.md`、`DATA_GOVERNANCE.md`、`CLAUDE.md`。

---

## 第三階段：試辦 KPI

### 3.1 新增檔案

| 檔案 | 說明 |
|---|---|
| `kpi_metrics.py` | 原樣複製 |
| `PILOT_KPI.md` | 複製；文中「05 人力與效益分析 › 試辦 KPI」位置要改成我方實際位置 |
| `tests/test_kpi_metrics.py` | 原樣複製 |

### 3.2 要修改的地方

**dashboard_view.py**：只把對方 L147–189 的 `render_pilot_kpis()` **新增**到檔尾。不要動 `render_dashboard`／`render_demand_heat`／`_render_staffing_advice`（我方主管報表在用）。

**app.py**：我方 05 已改成主管報表＋「附錄：詳細數據」四個分頁（L3006 `_ap1, _ap2, _ap3, _ap4 = st.tabs([...])`）。建議：
- 分頁加一個「試辦 KPI」（變成五個），裡面呼叫
  `render_pilot_kpis(df_tasks, _effective_for_kpi, df_route_result, monthly_payroll, config.client_primary_map, load_override_log())`（對方 L2875–2881）。
- `load_override_log` 我方已 import（L145），`_effective_for_kpi`、`df_route_result`、`monthly_payroll` 我方都有。
- 外層的 `try/except` 依對方寫法保留，`_log_error` 用 C2-1 的替代函式。

### 3.3 可能衝突

| # | 衝突 | 建議 |
|---|---|---|
| C3-1 | K1／K3／K6 和我方主管報表「三大數字」、儀錶板的派單成功率、平均轉場時間算法可能不同（`kpi_metrics` 自己算；主管報表用 `manager_report`） | 移植後用同一份示範 Excel 對數字；定義以 `PILOT_KPI.md` 為準，必要時讓主管報表改用 `kpi_metrics` 的函式，只留一套算法 |
| C3-2 | K5 居督覆寫率讀 `supervisor_override_log.csv`，**示範模式的覆寫也會被算進去** | 示範模式時 KPI 改讀空的覆寫紀錄，或標示「示範資料」 |
| C3-3 | 基準值存 `output_results/pilot_baseline.json`，不分機構；測試也會寫這個檔 | 測試時 monkeypatch `kpi_metrics.BASELINE_PATH` 到 tmp |
| C3-4 | KPI 只有主管能看（05 已在第一階段鎖住） | 依賴第一階段完成 |
| C3-5 | 我方主管報表可下載一頁 A4 PNG；KPI 表不會進那張圖 | 若要放進報表，另外處理 |

### 3.4 驗收
`tests/test_kpi_metrics.py` 通過；05 附錄出現「試辦 KPI」表，可登錄基準值並下載 CSV。

---

### 3.5 實作紀錄（2026-11-08 完成）

對方 commit `25abbef`。依使用者這次的範圍與風格規範，和 3.1～3.3 的原計畫差異如下：

| 項目 | 原計畫（照搬對方） | 實際做法 |
|---|---|---|
| 指標 | 對方 K1～K8 | 依使用者指定：K1 派案成功率、K2 排班作業時間、K3 平均轉場時間、K4 照顧連續性（主責居服員比例）、K5 居督改派率、K6 排班錯誤率、K7 居服員工時差距（變異係數）、K8 居服員滿意度；有打卡資料時另加 **A1 實際準時率、A2 未遇率**（和 ④ 執行對照的 `summary()` 同一套算法） |
| 每項顯示 | 一張大表 | 每項都回傳分子、分母、期間、計算方式＋**明細 DataFrame**；畫面是 KPI 卡＋總表＋每項一個展開區（分子、分母、期間、計算方式、逐筆明細） |
| K2 | 居督手動輸入分鐘 | **自動計時**：`_data_source_key` 改變時記「匯入」（還原上次進度不算）；④ 三顆匯出按鈕改用 `download_button_export()`，on_click 記「匯出」並帶排班期間。`timing_rounds()`：匯出後再匯入開新回合，回合期間＝最後一次匯出時的期間；K2＝本期完成回合的分鐘加總 ÷ 回合數 |
| K5 | 覆寫紀錄中本期任務ID 去重 | 覆寫紀錄只會累加，改成**只算和目前班表一致的紀錄**：最後一筆的居督指定＝目前派單居服員，且≠第一筆的 AI 推薦（改回 AI 建議不算、舊紀錄不算）。名稱用使用者的「改派」 |
| K6 | 同對方 | 同對方，明細合併同一任務的多個問題；重疊的兩筆都算 |
| K7 | 同對方 | 同對方（母體標準差），明細列每人總工時與和平均的差距 |
| K8 | 輸入分數總和與人數 | 逐列輸入每位居服員的分數（1～5 分，`st.data_editor`），依月份存；超出範圍回中文錯誤 |
| 基準值 | `pilot_baseline.json` 一組基準＋目標值 | `output_results/pilot_kpi.sqlite3`（`CAREFLOW_KPI_DB`）：依**月份 × 基準月／試辦月**存分子、分母、數值，只新增不覆蓋（同月重存以最後一次為準）。基準月可「人工登錄」分子分母，或把本期存成基準月；比較表任選基準月與試辦月（或「本期（尚未儲存）」），差異＝試辦 − 基準，依方向標改善／變差／持平。待量測的項目不存。沒有做「目標值／是否達標」（使用者沒有要求） |
| 畫面位置 | 05 附錄 `st.tabs` 加第五個分頁 | 05 頁首 `big_tabs(['主管報表', '試辦 KPI'], 'cf_analytics_view')`：附錄分頁裡不能再放展開區（規範），而「點開看明細」需要展開區。主管限定沿用 `_flow_locks()`（C3-4） |
| 畫面程式 | `dashboard_view.render_pilot_kpis()` | 新檔 `kpi_view.py`（`dashboard_view.py` 不動）；ID 一律經 app.py 傳入的 `show_table`／`export_frame`；下載用 `download_button_quiet` |
| CSV | 一份 | 三份：KPI 總表、KPI 明細（所有明細接成長表）、基準月比較 |
| 示範模式（C3-2） | — | KPI 資料檔改用 `kpi_metrics.demo_db_path()`（示範工作紀錄旁，24 小時後一起清掉），不寫稽核紀錄；畫面顯示提示 |
| 測試資料檔（C3-3） | monkeypatch `BASELINE_PATH` | `tests/conftest.py` 設 `CAREFLOW_KPI_DB` |
| `_log_error`（C2-1） | 替代函式 | 不需要：畫面層 `st.error('…原因：' + str(exc))` |
| 稽核 | — | `audit_log.EVENTS` 加 `kpi`（save_month／save_survey，只記月份、種類、筆數） |
| 個資 | — | `identity_display` 的 `caregiver_cols` 加 `主責居服員`、`AI推薦居服員ID`、`居督指定居服員ID`（K4、K5 明細） |

C3-1（和主管報表的數字不同）：K1 和主管報表「服務完成率」定義相同（已派 ÷ 全部服務），還沒用同一份 Excel 在畫面上對過數字；K3 只算不同案家之間的轉場、不含緩衝，主管報表的「轉場工時」含緩衝，兩者本來就不同，已在 PILOT_KPI.md 寫明。主管報表這次沒有改成用 `kpi_metrics`。

新增：`kpi_metrics.py`、`kpi_view.py`、`PILOT_KPI.md`、`tests/test_kpi_metrics.py`（25 個，每個 KPI 用小資料手算核對）、`tests/test_kpi_view_ui.py`（1 個 AppTest，需要 streamlit）。
修改：`app.py`（import、`_kpi_db`／`_kpi_period_key`／`_mark_export`／`download_button_export`、匯入計時、④ 三顆匯出按鈕、05 分頁與試辦 KPI 區）、`audit_log.py`、`caregiver_engine.py`（`identity_display`）、`careflow_ui.py`（MODULES 05 說明）、`build_info.py`（`kpi_metrics`、`kpi_view`）、`tests/conftest.py`、`README.md`、`DATA_GOVERNANCE.md`、`CLAUDE.md`。

**測試（雲端工作區，Python 3.13、pandas、pytest，沒有 streamlit／ortools）**：移植前 `11 failed, 105 passed, 4 skipped, 18 errors`；移植後 `11 failed, 130 passed, 5 skipped, 18 errors`。多出的 25 個通過是 `test_kpi_metrics.py`，多 1 個略過是 `test_kpi_view_ui.py`；失敗與收集錯誤逐項相同（比第 5 節多的 3 個失敗是這次只複製了 .py 檔、沒有 `data/` 與 xlsx 造成的，移植前後一樣）。另用假的 streamlit 模組實際跑過一次 `render_pilot_kpis()` 與三個儲存回呼，沒有錯誤。

### 3.6 改版：3 組 9 項（2026-11-08，取代 3.5 的指標清單）

使用者以居督角度重新挑選，只保留可由系統量化的指標，分 3 組，代碼依組別重編：

| 組別 | 指標（分組前代碼） |
|---|---|
| A 服務量能 | A1 派案成功率（K1）、**A2 未派服務時數比例＋原因分布（新）**、**A3 居服員產能利用率（新）** |
| B 照顧品質 | B1 照顧連續性（K4）、B2 排班錯誤率（K6） |
| C 人力負荷與成本 | C1 平均轉場時間（K3）、**C2 轉場工時占比（新）**、C3 居服員工時差距（K7）、**C4 加班合規（新）** |

- **拿掉**：K2 排班作業時間（連同自動計時：`record_timing`、`timing_rounds`、`download_button_export`、匯入計時、`_kpi_period`；④ 三顆匯出按鈕改回 `download_button_quiet`）、K5 居督改派率、K8 居服員滿意度（問卷表）、打卡 A1 實際準時率／A2 未遇率（打卡對照仍在 ④）。`identity_display` 拿掉 `AI推薦居服員ID`、`居督指定居服員ID`，保留 `主責居服員`。資料庫只剩 `records` 表；舊代碼的紀錄讀取時略過。
- **新增指標的資料來源**：A2 用 `issue_center.unassigned_issues`（和 ③ 同一套原因分類）＋服務歷時；A3 用 `res['df_cg']` 的可排班星期、每日可服務時段與 `PipelineConfig.normal_daily_hours`（8 小時）；C2 用工時表的轉場工時／總工時；C4 用月加班（含期外）÷ 月加班上限，80% 門檻和主管報表 `build_dashboard(load_warning=0.8)` 相同。
- **畫面**：每組一個 `subhead`＋一排 `kpi_cards`（大字數值＋「分子 ／ 分母」）→ 逐項指標表（多「組別」欄）→ 依組別列出各項展開區（A2 先列原因分布再列逐筆明細）→ 基準月 vs 試辦月 → 三份 CSV。
- **測試**：`tests/test_kpi_metrics.py` 改寫成 21 個（9 項各自手算核對、分組、儲存與比較、舊代碼略過）；整套 `11 failed, 126 passed, 5 skipped, 18 errors`（移植前 105 passed，失敗與收集錯誤項目不變）。另用假的 streamlit 模組實際跑過 `render_pilot_kpis()`，沒有錯誤。

### 3.7 調整（2026-11-08 晚）

- 拿掉 **B2 排班錯誤率**（班次重疊與轉場不足仍在 ③ 處理）；B 組只剩 B1 照顧連續性，共 8 項。
- **C4 改成「加班合規率」**：沒有超過月加班上限的人數 ÷ 有排班人數，越高越好、應為 100%；接近上限（≥ 80%）仍算合規，只在備註與明細提醒。
- **C3 白話說明**：公式不變，備註改寫成「平均每人 X 小時，一般差距 ±Y 小時；最多、最少 Z 小時」，計算方式加上例子。
- 文件補充：C1 和主管報表「交通 › 平均」的差別（後者含家 → 第一個案家）；C2 的轉場工時不含從家裡出發與返家。
- 測試：`tests/test_kpi_metrics.py` 20 個全部通過。

### 3.8 調整（2026-11-09）

- **A3**：分子改成服務工時＋轉場工時；分母扣掉請假（② 登錄、原因以「請假」開頭的時段，與員工資料「請假日期」整天），每天最多 8 小時；app.py 傳入 `_workflow_store.blocks()`（示範模式是示範暫存檔）。明細加「請假扣除時數」「服務工時」「轉場工時」。
- **C1**：改成「平均交通時間」，和主管報表「交通 › 平均」同一個算法（含首案出門，不含車程 0 與未算出的路段），只留一種數字。
- **C3**：改成「工時落在平均 ±20% 的人數比例」（越高越好，邊界算在內），明細標偏高／偏低／接近平均。
- 畫面：每組 KPI 卡下方加灰色小字（`KpiSpec.hint`）說明 A3、C1、C2、C3 的算法。
- 測試：`tests/test_kpi_metrics.py` 22 個全部通過（新增 C1 和主管報表一致、C3 邊界）。

## 4. 建議順序與工作量

1. **第一階段**：新增 2–3 個檔案；app.py 約 120 行貼入＋5 處單行；dispatch_workflow、caregiver_engine 各 5 行；conftest 3 行。
2. **第二階段**：新增 `checkin/`＋1 個檔案（＋選配 1 個）；app.py 約 340 行貼入（＋選配約 75 行）；caregiver_engine 7 行；部署檔 4 個；需處理 `test_checkin_panel_ui` 的 `_setup` 依賴。
3. **第三階段**：新增 2 個檔案；dashboard_view 新增 1 個函式；app.py 約 10 行。

每階段完成後跑一次 pytest，結果和第 5 節基準比對。

---

## 5. 測試基準（移植前，2026-11-08）

**環境限制**：這次執行的電腦端和雲端工作區都**無法安裝套件**（網路被擋），只能在已有 `pytest 9.1.1 / Python 3.13 / pandas / openpyxl / flask` 但**沒有 `streamlit`、`ortools`** 的雲端複本跑。所以下列結果大多數是「環境缺套件」，**請在你自己的 venv（`pip install -r requirements-dev.txt`）再跑一次，取代這份基準。**

指令：`python -m pytest -q --continue-on-collection-errors`（不加這個參數時，收集錯誤會讓 pytest 直接中止：`18 errors during collection`）

| 結果 | 數量 |
|---|---|
| 通過 | 67 |
| 失敗 | 8 |
| 收集錯誤（整支測試檔載入失敗） | 18 支檔案 |
| 靜態掃描的測試函式總數 | 307 |

**收集錯誤（18 支）——全部是 `ModuleNotFoundError: No module named 'streamlit'`**（`caregiver_engine` → `osrm_client` 第 9 行 `import streamlit`）：
`test_agency_import.py`、`test_near_walk_and_edit.py`、`test_qualification_recheck.py`、`tests/test_agency_rules.py`、`tests/test_app_workflow.py`、`tests/test_caregiver_engine.py`、`tests/test_case_preview_consecutive.py`、`tests/test_manager_report.py`、`tests/test_osrm_batch.py`、`tests/test_persistent_cache.py`、`tests/test_qualification_recheck.py`、`tests/test_recurring_schedule.py`、`tests/test_session_store.py`、`tests/test_source_fields.py`、`tests/test_team_scheduler.py`、`tests/test_transit_disk_cache.py`、`tests/test_transport_output.py`、`tests/test_travel_objective.py`

**失敗（8 個）**
- 7 個是環境問題（同樣缺 `streamlit`）：`test_v15.py` 的 `TransitFallbackTests` 4 個、`StatusTableTests::test_same_format_for_tried_and_untried`、`IdentityTests::test_worker_column_named_居服員_is_masked_for_display`；`test_v18.py::RouteSignatureTests::test_client_maps_do_not_invalidate_routes`
- **1 個是真的失敗，和環境無關**：`tests/test_source_workbook.py::test_weekly_team_column_preserves_formula_cache_and_table`
  → `TypeError: update_source_workbook() got an unexpected keyword argument 'weekly_workers'`（測試呼叫的參數，`source_workbook.update_source_workbook` 目前不接受）。這是移植前就存在的問題。

**第一階段移植後（2026-11-08，commit `7615c84` 的檔案，同一個環境）**：`8 failed, 80 passed, 3 skipped, 18 errors`。
- 通過數從 67 變成 80：新增的 `test_auth.py` 有 9 個、`test_audit_log.py` 有 4 個。
- 3 個略過：需要 streamlit。
- 失敗與收集錯誤共 26 項，**和移植前完全相同**（逐項比對）：沒有新的失敗，原本的也沒有變好或變壞。

**通過的 67 個**來自不需要 streamlit 的檔案：`test_v14`、`test_v16`、`test_v17`、`test_v15`／`test_v18` 的其餘部分、`test_dashboard_and_cache`、`tests/test_demo_mode`、`tests/test_import_health`、`tests/test_issue_center`、`tests/test_source_workbook`（其餘 2 個）、`tests/test_substitute_rank`。
