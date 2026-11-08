# HomeCare AI 居服排班工作台

以 AI 協助居家服務督導員（居督）排班的 Streamlit 網頁工作台。匯入機構 Excel 後，系統依居服員資格、可服務時段、交通、休息與工時限制，自動產生整月班表，並集中處理未派案家、臨時異動與 LINE 派案訊息。

## 功能

畫面依排班流程分成五個步驟，從頁面上方的步驟列切換：

| 步驟 | 內容 |
|---|---|
| 01 資料匯入與排班設定 | Excel 拖曳匯入、排班期間、交通方式、排班規則、服務碼檢查與資料表編輯 |
| 02 智慧排班作業 | 一鍵 AI 全域最佳化排班、週班表（大字）、拖曳調整、人工改派 |
| 03 衝突與異常處理 | 班次重疊、轉場不足、資格不符等分類；未派案家 AI 替代方案（挪時間、換人、拆兩段）；臨時新增／請假／改期／延遲；LINE 派案訊息解析與定位 |
| 04 排班結果與覆核 | 排班完成率、已排與未排班次、警示案件、最終班表匯出、人工覆寫紀錄 |
| 05 人力與效益分析 | 排班效益、需求熱圖與增聘／調派建議、工時與負荷、轉場時間、營收與薪資估算 |

介面採高對比大字設計，頁首可切換「標準／大／特大」字體。

## 登入與權限

開啟網頁後要先登入。第一次啟動、系統還沒有任何帳號時，畫面會引導建立第一位**主管**帳號。

| 角色 | 可以使用 |
|---|---|
| 主管 | 全部步驟、主管報表（05 人力與效益分析）、👥 帳號管理 |
| 居督 | ① 匯入資料～④ 確認班表 |

- **帳號管理**（主管專用，側邊欄「👥 帳號管理」）：新增帳號、重設密碼（同時解除鎖定）、停用／啟用帳號、查看存取稽核紀錄。至少要保留一位可以登入的主管，最後一位主管不能停用。
- **密碼**：至少 8 個字。只存 PBKDF2-SHA256 雜湊（20 萬次、每個帳號各自加鹽），系統與主管都看不到原本的密碼。每個人都可以在側邊欄「🔑 變更我的密碼」自己改。
- **鎖定**：連續輸錯 5 次鎖 10 分鐘；主管重設密碼即可解鎖。帳號不存在、已停用時，回應的訊息與時間都和密碼錯誤一樣，不能用來猜帳號。
- **稽核紀錄**：登入成功、登入失敗、登出、帳號異動都會記錄（只記帳號代碼，不記姓名）。紀錄只能附加，每筆帶前一筆的雜湊，可在帳號管理頁檢查有沒有被改過。
- 帳號存在 `output_results/accounts.sqlite3`，稽核紀錄存在 `output_results/audit/`，兩者都不會被提交到 git。

| 環境變數 | 說明 |
|---|---|
| `CAREFLOW_AUTH` | 設成 `0`（或 `off`／`false`／`no`）關閉登入，以主管權限使用。**只限本機開發**，正式環境不要設 |
| `CAREFLOW_ACCOUNTS_DB` | 帳號資料庫路徑（預設 `output_results/accounts.sqlite3`） |
| `CAREFLOW_AUDIT_DIR` | 稽核紀錄資料夾（預設 `output_results/audit`） |

## 快速開始

```bash
pip install -r requirements.txt
streamlit run app.py
```

需要 Python 3.10 以上。排班最佳化使用 OR-Tools；地圖與交通時間使用：

- **機車**：自架 OSRM 機車路網（`osrm_motorcycle/`，可用 Docker 在本機或雲端架設）
- **公車／捷運**：Google Routes API（需要自己的 API 金鑰）

### 設定金鑰與交通主機

複製範例檔並填入自己的值（`secrets.toml` 已列入 `.gitignore`，不會被提交）：

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

| 設定 | 說明 |
|---|---|
| `GOOGLE_MAPS_API_KEY` | Google Routes API 金鑰（大眾運輸路線） |
| `CAREFLOW_OSRM_MOTORCYCLE_HOST` | 機車路網 OSRM 主機網址，例如 `http://127.0.0.1:5001` |

也可以用同名環境變數設定。

### 匯入資料

一份 Excel（`.xlsx`）包含六個工作表：`員工資料`、`個案資料`、`週服務計畫`、`Service_code`、`案家姓名對照`、`居服員姓名對照`。

本 repo **不附任何 Excel 資料檔**。若要產生虛構示範資料，可參考 `tools/make_demo_workbook.py`；把示範檔命名為 `居服機構資料_三工作表_示範版_v1.xlsx` 放在 `app.py` 旁，01 頁的「下載標準範例檔」與「一鍵載入 Demo 資料」就會啟用。

## 個資保護

- 排班、最佳化與交通查詢全程使用 ID（案家ID、居服員ID、任務ID）；姓名匯入後立即遮罩（例如 王O明 → 王○○），只用於畫面顯示。
- 送往 Google／OSRM 的只有座標、時間與交通模式。
- LINE 派案訊息解析後原文立即清除；地址定位使用本機的政府公開門牌資料（`data/`），不送外部服務。
- 詳細設計見 [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)。

## 專案結構

| 檔案 | 用途 |
|---|---|
| `app.py` | Streamlit 主程式（各步驟畫面） |
| `careflow_ui.py` | 介面樣式與共用元件（Design System） |
| `week_board.py` | 週班表（大字）與 AI 排班提醒 |
| `caregiver_engine.py` | 排班引擎：資料載入、資格檢查、OR-Tools 最佳化、交通與薪資計算 |
| `team_scheduler.py`、`monthly_scheduler.py` | 固定週型與整月／整年延展 |
| `pending_clients.py`、`pending_advice.py` | 未派案家診斷與替代方案 |
| `dispatch_message.py`、`address_geocoder.py` | LINE 派案訊息解析與離線門牌定位 |
| `dashboard_metrics.py`、`dashboard_view.py` | 人力與效益儀錶板 |
| `osrm_client.py`、`traffic_wake.py` | 交通路網連線與喚醒 |
| `auth.py`、`audit_log.py` | 登入與角色權限、存取稽核紀錄（hash chain） |
| `tests/` | 單元與流程測試 |

## 測試

```bash
pip install -r requirements-dev.txt
python -m pytest tests
```

測試會自動關閉登入（`tests/conftest.py` 設 `CAREFLOW_AUTH=0`），帳號與稽核紀錄寫到暫存資料夾；登入流程另由 `tests/test_auth.py` 開啟登入後測試。

## 部署

- `Dockerfile`、`docker-compose.yml`：機構內部主機部署（含 Caddy HTTPS 與帳密，見 `deploy/Caddyfile`）。
- `osrm_motorcycle/`：建立機車路網 OSRM 主機的腳本。

### 兩層登入：Caddy 帳密＋系統帳號

正式部署時，使用者會先後遇到兩道關卡，兩者用途不同，目前**都保留**：

| | 第一層：Caddy basic auth（`deploy/Caddyfile`） | 第二層：系統登入（`auth.py`） |
|---|---|---|
| 擋什麼 | 網路上的任何人連到網站；沒過這關連登入頁都看不到 | 已經進到網站的人，確認是誰、能用哪些功能 |
| 帳號 | 全機構共用一組（`supervisor`） | 每人一個帳號，分主管／居督 |
| 記錄 | 只有 Caddy 的連線紀錄 | 登入、失敗、帳號異動寫進稽核紀錄 |
| 鎖定 | 無 | 連錯 5 次鎖 10 分鐘 |

- 第一層是外圍防護：減少系統登入頁直接暴露在網路上被猜密碼，也擋掉還沒登入就能看到的畫面（例如頁首）。共用密碼請只給機構內部人員。
- 第二層才決定「誰做了什麼」：稽核紀錄、角色權限都以系統帳號為準，Caddy 的共用帳號不會出現在稽核紀錄裡。
- 之後若改用 VPN／Tailscale 只在內部網路開放，可以拿掉第一層（刪掉 Caddyfile 的 `basicauth` 區段），第二層不受影響。
