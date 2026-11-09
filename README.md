# HomeCare AI 居服排班工作台

以 AI 協助居家服務督導員（居督）排班的 Streamlit 網頁工作台。匯入機構 Excel 後，系統依居服員資格、可服務時段、交通、休息與工時限制，自動產生整月班表，並集中處理未派案家、臨時異動與 LINE 派案訊息。

## 功能

畫面依排班流程分成五個步驟，從頁面上方的步驟列切換：

| 步驟 | 內容 |
|---|---|
| 01 資料匯入與排班設定 | Excel 拖曳匯入、排班期間、交通方式、排班規則、服務碼檢查與資料表編輯 |
| 02 智慧排班作業 | 一鍵 AI 全域最佳化排班、週班表（大字）、拖曳調整、人工改派 |
| 03 衝突與異常處理 | 班次重疊、轉場不足、資格不符等分類；未派案家 AI 替代方案（挪時間、換人、拆兩段）；臨時新增／請假／改期／延遲；LINE 派案訊息解析與定位 |
| 04 排班結果與覆核 | 排班完成率、已排與未排班次、警示案件、最終班表匯出、居服員打卡（QR Code、發布今日班表、手機綁定、補登覆核、當日看板）、執行對照、人工覆寫紀錄 |
| 05 人力與效益分析 | 排班效益、需求熱圖與增聘／調派建議、工時與負荷、轉場時間、營收與薪資估算；🎯 試辦 KPI（3 組 8 項、基準月 vs 試辦月，見 `PILOT_KPI.md`） |

介面採高對比大字設計，頁首可切換「標準／大／特大」字體。

## 試辦 KPI（05 › 🎯 試辦 KPI，只有主管）

05 頁首可切換「📊 主管報表／🎯 試辦 KPI」。試辦 KPI 分 3 組、共 8 項，全部由系統資料計算：

| 組別 | 指標 |
|---|---|
| A 服務量能 | A1 派案成功率、A2 未派服務時數比例（附原因分布）、A3 居服員產能利用率 |
| B 照顧品質 | B1 照顧連續性（主責居服員比例） |
| C 人力負荷與成本 | C1 平均交通時間、C2 轉場工時占比、C3 工時落在平均 ±20% 的人數比例、C4 加班合規率 |

- 每組一排大字 KPI 卡，下方是逐項指標表（分子、分母、期間、計算方式），展開看逐筆明細；可下載總表、明細、基準月比較三份 CSV。
- **基準月 vs 試辦月**：試辦前的人工排班月份用「✏️ 人工登錄基準月」填分子與分母；系統排班的月份按「💾 存成試辦月」。之後任選兩個月份比較，標示改善／變差。
- 資料存在 `output_results/pilot_kpi.sqlite3`（`CAREFLOW_KPI_DB` 可改）；示範模式寫到示範暫存檔。定義與計算細節見 [`PILOT_KPI.md`](PILOT_KPI.md)。

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

## 居服員打卡（QR Code）

居服員不用裝 App、不用密碼：用手機掃 QR Code → 第一次輸入員工編號（這支手機就綁定給他）→ 之後打開就看到今天的服務個案，按「上班」「下班」「未遇」。

打卡網頁（`checkin/`，port 8600）跟著 HomeCare AI 一起在背景啟動，不用另外開程式；設 `CAREFLOW_CHECKIN_AUTOSTART=0` 可以關掉（例如打卡網頁另外架在別台主機，或用 docker-compose 的 `checkin` 服務）。
注意：Streamlit 要有人打開 HomeCare AI 網頁，程式才會開始執行，所以本機使用時請先開啟 HomeCare AI 一次；Docker 部署用獨立的 `checkin` 服務，不受影響。

### 居督每天怎麼做（都在「④ 確認班表」頁的「📱 居服員打卡」）

1. **① 發布班表**：排好班後按「📲 發布今日班表」；有改派、代班再按一次。也可以先發布明天的班。「試用：建立一筆示範班」也在這裡。
2. **② 今日打卡看板**：每一班的上班／下班時間。過了開始時間 15 分鐘還沒打卡標 🔴「逾時未打卡」（分鐘數是 `PipelineConfig.attendance_overdue_mins`）。
3. **③ 下方同一排的三個分頁**：
   - **打卡網址**：第一次把 QR Code 圖片傳到 LINE 群組或印出來。
   - **手機綁定**：第一支手機自動綁定。換手機時會出現「🔔 新手機等你核准」，按「核准」後舊手機自動解除。手機遺失、離職、綁錯人時按「解除綁定」。要更嚴格可以關掉「第一支手機自動綁定」，每支手機都由居督核准。
   - **補登覆核**：居服員忘記打卡或打錯時間，會在手機「補登」並寫原因；在這裡核准或退回。
4. **執行對照**（打卡區下方，預設收合，按「展開執行對照明細」）：比對排班和實際打卡，列出遲到、漏打卡（整筆沒打／漏上班／漏下班）、未遇，以及早退、補登待覆核、排外打卡；可下載 CSV。只對照已發布到打卡網頁的日期。

### 規則

- **打卡時間一律用主機時間**（台北時區），不用手機時間。
- **打卡紀錄只能新增、不能修改或刪除**（資料庫觸發器擋 UPDATE／DELETE）。要更正就在手機「補登」，狀態是「待覆核」；原本的紀錄保留，居督核准後對照改用補登的時間，退回則不採用。重複按同一個按鈕會被擋下。
- **只有 https 才記錄 GPS**：手機瀏覽器在 http 下本來就不給定位，打卡網頁伺服器也會再檢查一次；補登一律不記位置。
- **GPS 距離只提醒**：打卡位置離案家超過 300 公尺（`attendance_gps_radius_m`）只在看板與對照表標「位置提醒」，不算異常、不當懲處依據。
- **個資**：打卡資料只用原本的居服員ID、案家ID、任務ID；手機上的案家名稱是遮罩後的「王○○」，資料庫不存任何未遮罩的姓名。手機只存一組隨機綁定碼，資料庫只存它的雜湊值。
- 打卡資料存在 `output_results/checkin.sqlite3`（已列入 `.gitignore`）；居督的發布、核准、解除、覆核動作寫進存取稽核紀錄（事件「打卡管理」）。

### 三種用法

| | 辦公室試用 | Cloudflare Tunnel 試用 | 正式上線（Docker＋Caddy） |
|---|---|---|---|
| 打卡網址 | `http://這台電腦IP:8600`（`CAREFLOW_CHECKIN_TUNNEL=0` 或外部網址開不成時） | `https://….trycloudflare.com`（**預設**，每次重開會變） | `https://checkin.你的網域` |
| 誰打得開 | 連同一個 Wi-Fi 的手機 | 任何有網路的手機 | 任何有網路的手機 |
| 記錄 GPS | 不會（不是 https） | 會 | 會 |
| 主機 | 這台電腦要開著 | 這台電腦要開著且連網 | 雲端或機構主機 |

#### 用 Cloudflare Tunnel 試用（不用網域、不用設防火牆）

**預設就是外部網址。** 沒有設定固定網址時，HomeCare AI 一啟動就在背景用 cloudflared 開一條臨時通道，④ 頁的 QR Code 直接是 `https://….trycloudflare.com`（產生中會顯示「⏳ 正在產生外部網址」，好了自動換成 QR Code）。
第一次會從 Cloudflare 官方 GitHub 下載 cloudflared（約 50MB）到 `output_results/bin/`（電腦已安裝 cloudflared 就直接用），需要 10～40 秒；GitHub 下載伺服器偶爾會回 504（逾時），系統會自動重試 3 次，還是失敗就顯示原因和「🌐 再試一次產生外部網址」按鈕。
用完按「停止外部網址」（之後不會自動再開）。HomeCare AI 重開後網址會變，要重新傳 QR Code。不想自動開外部網址時，設 `CAREFLOW_CHECKIN_TUNNEL=0`。

下載一直失敗時，可以自己把 cloudflared 放進來：用瀏覽器下載 `cloudflared-windows-amd64.exe`，改名成 `cloudflared.exe` 放到專案的 `output_results\bin\`；或執行 `winget install --id Cloudflare.cloudflared`。之後按「再試一次」就會直接使用，不再下載。

電腦連不到 GitHub、或想自己控制時，也可以手動開：

1. 安裝 cloudflared：Windows 在命令提示字元執行 `winget install --id Cloudflare.cloudflared`（或到 [Cloudflare Tunnel 說明頁](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)）；macOS 用 `brew install cloudflared`。
2. 先開啟 HomeCare AI（`streamlit run app.py`），打卡網頁會跟著在 8600 啟動。
3. 另開一個命令視窗執行：
   ```bash
   cloudflared tunnel --url http://localhost:8600
   ```
   畫面會出現一行 `https://隨機字.trycloudflare.com`，視窗不要關。
4. 到 ④ 頁「📱 居服員打卡 › 網址與發布 › 進階：設定固定打卡網址」貼上這個網址並儲存，QR Code 會換成新網址。
5. 試用結束：關掉 cloudflared 視窗，回到 04 頁把固定網址清空。

注意：免帳號的臨時通道只適合試辦——網址每次重開都會變（要重新發 QR Code）、沒有服務保證，而且任何拿到網址的人都能打開登入頁（仍要輸入已發布班表裡的員工編號）。試用期間建議關掉「第一支手機自動綁定」，每支手機由居督核准。

### 打卡相關環境變數

| 變數 | 說明 |
|---|---|
| `CAREFLOW_CHECKIN_AUTOSTART` | `0` 不跟著 HomeCare AI 啟動打卡網頁 |
| `CAREFLOW_CHECKIN_PUBLIC_URL` | 固定打卡網址（04 頁「進階」設定的優先） |
| `CAREFLOW_CHECKIN_TUNNEL` | `0`：沒有固定網址時不要自動開外部網址（Cloudflare 臨時通道），改用辦公室網路位址 |
| `CAREFLOW_CHECKIN_PORT` | 打卡網頁埠號，預設 `8600` |
| `CAREFLOW_CHECKIN_DB` | 打卡資料庫路徑，預設 `output_results/checkin.sqlite3` |
| `CAREFLOW_CHECKIN_SECURE` | `1`：綁定 cookie 只走 https（正式上線請開） |
| `CAREFLOW_CHECKIN_SECRET` | 打卡網頁的 session 金鑰；不設時第一次啟動自動產生並存在打卡資料庫 |

QR Code 用 segno 產生；主機沒有安裝 segno 時，自動改用隨程式附上的 `checkin/_vendor/segno`（BSD-3 授權），不必另外安裝。

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
| `checkin/` | 居服員手機打卡網頁：`store.py` 資料庫（班表發布、手機綁定、打卡、補登覆核、看板）、`server.py` Flask 網頁、`runner.py` 自動啟動與網址／QR Code、`templates/` 手機畫面 |
| `attendance_reconcile.py` | 執行對照：排班 vs 打卡（遲到、漏打卡、未遇…） |
| `tests/` | 單元與流程測試 |

## 測試

```bash
pip install -r requirements-dev.txt
python -m pytest tests
```

測試會自動關閉登入（`tests/conftest.py` 設 `CAREFLOW_AUTH=0`），帳號、稽核紀錄與打卡資料庫寫到暫存資料夾，也不會在 8600 埠開打卡網頁；登入流程另由 `tests/test_auth.py` 開啟登入後測試。打卡相關測試在 `tests/test_checkin.py`、`tests/test_attendance_reconcile.py`、`tests/test_checkin_panel_ui.py`。

## 部署

- `Dockerfile`、`docker-compose.yml`：機構內部或雲端主機部署，三個服務：`careflow`（HomeCare AI，8501）、`checkin`（居服員打卡網頁，8600）、`caddy`（對外 443，自動 HTTPS）。
- `osrm_motorcycle/`：建立機車路網 OSRM 主機的腳本。

### Docker 部署步驟（含打卡網域）

1. 準備一台一直開著、可以對外連線的主機（雲端或機構內），安裝 Docker 與 Docker Compose。
2. 在 DNS 加兩筆 A 紀錄指到這台主機：`careflow.你的網域`（居督用）、`checkin.你的網域`（居服員打卡用）。防火牆開 80、443。
3. 修改 `deploy/Caddyfile`：把兩個 `example.org` 網域換成你的；產生居督共用密碼的雜湊 `docker run --rm caddy:2 caddy hash-password`，貼到 `PASTE_HASH_HERE`。
4. 修改 `docker-compose.yml`：`CAREFLOW_CHECKIN_PUBLIC_URL` 改成 `https://checkin.你的網域`；`CAREFLOW_OSRM_MOTORCYCLE_HOST` 改成你的 OSRM 主機。Google 金鑰放 `.env`。
5. 啟動：`docker compose up -d --build`。Caddy 會自動申請 https 憑證（第一次約 1 分鐘）。
6. 檢查：瀏覽器開 `https://checkin.你的網域/healthz` 應顯示 `ok`；開 `https://careflow.你的網域` 登入後到 ④ 頁，QR Code 應該是 `https://checkin.你的網域`。
7. 備份：資料都在 `careflow_data` volume（排班存檔、帳號、稽核、`checkin.sqlite3`），請定期備份。

打卡網頁不加 Caddy basic auth：居服員用員工編號＋手機綁定，只能看到自己今天的班。

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
