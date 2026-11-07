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
| `tests/` | 單元與流程測試 |

## 測試

```bash
pip install -r requirements-dev.txt
python -m pytest tests
```

## 部署

- `Dockerfile`、`docker-compose.yml`：機構內部主機部署（含 Caddy HTTPS 與帳密，見 `deploy/Caddyfile`）。
- `osrm_motorcycle/`：建立機車路網 OSRM 主機的腳本。
