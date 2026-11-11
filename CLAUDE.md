# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

This is an AI dispatch/scheduling workbench for home-care caregivers (長照居家照顧派單系統), built for an AI competition. Supervisors (居督) import one agency Excel workbook; the engine expands the weekly service plan over a period (usually one month), matches caregivers under hard/soft constraints (qualifications, availability, travel, rest, working hours), solves the assignment with OR-Tools, and the Streamlit app walks the supervisor through fixing unassigned cases, reviewing and exporting the final schedule. A manager report summarises the impact; the Phase 3 DiD comparison of AI vs. human dispatch is still available in the engine.

The project is a git repository (branch `develop`) with a pytest suite under `tests/`. See `README.md` for the user-facing overview and `UI_改版進度.md` for the current UI revamp status.

## File layout

- `caregiver_engine.py` — core logic: data loading, `PipelineConfig` (all tunable dispatch-policy parameters), Phase 1/2/3, travel time (OSRM / Google transit), payroll, identity masking. Every entry point imports from here; do not duplicate logic elsewhere.
- `team_scheduler.py`, `monthly_scheduler.py` — fixed weekly patterns and extension over the whole period.
- `app.py` — Streamlit app (see "Streamlit app" below). Only UI flow and orchestration; algorithms live in the modules.
- `careflow_ui.py` — the only place for CSS and shared UI components (see 「程式與介面風格規範」).
- `auth.py`, `audit_log.py` — login/roles and the append-only audit log (pure modules, no Streamlit).
- `checkin/` — caregiver QR check-in web page (Flask, port 8600): `store.py` (SQLite `output_results/checkin.sqlite3`: published shifts, phone binding by token hash, append-only punches, late-entry reviews, day board; pure), `server.py` (phone pages; server time only; GPS kept only over https), `runner.py` (autostart with the app, check-in URL incl. the Cloudflare quick-tunnel 「外部網址」, QR PNG via installed segno or the bundled `checkin/_vendor/segno`), `templates/`. `attendance_reconcile.py` — pure schedule-vs-punch comparison (late, missing punch, missed visit…) for the ④ 執行對照 view.
- `kpi_metrics.py` — pilot KPIs in 3 groups (`GROUPS`: A 服務量能 A1～A3, B 照顧品質 B1, C 人力負荷與成本 C1～C4), all computed from system data: every result carries numerator, denominator, period, method and a detail frame (A2 also a reason `breakdown`; `KpiSpec.hint` is the gray one-line note under each group's cards; A3 deducts leave from `WorkflowStore.blocks()`); baseline-month／pilot-month records in SQLite `output_results/pilot_kpi.sqlite3` (pure, no Streamlit). `kpi_view.py` — the 05 › 🎯 試辦 KPI page. Definitions: `PILOT_KPI.md`.
- `week_board.py`, `calendar_view.py`, `dashboard_view.py` — page-level view components; `dashboard_metrics.py`, `manager_report.py` — pure calculations for the dashboard and the one-page manager report.
- `pending_clients.py`, `pending_advice.py`, `issue_center.py`, `substitute_rank.py`, `temp_case.py`, `eligibility.py` — unassigned-case diagnosis, alternatives, issue grouping, substitutes, ad-hoc cases, eligibility explanations.
- `dispatch_workflow.py` (leave / fixed caregiver / workday ledger, SQLite), `session_store.py` (autosave), `persistent_cache.py` (travel-leg disk cache), `runtime_views.py` (versioned view caches).
- `import_health.py`, `source_fields.py`, `source_workbook.py`, `workbook_edit.py`, `repair_workbook.py` — import checks and reading/writing the agency workbook.
- `dispatch_message.py`, `address_geocoder.py` — LINE dispatch-message parsing and offline address geocoding (`data/`).
- `osrm_client.py`, `traffic_wake.py` — OSRM connection and wake-up of the hosted routing server; `osrm_motorcycle/` builds the motorcycle road network.
- `build_info.py` — `CAREFLOW_BUILD` / `REQUIRED_MODULES`; `app.py` refuses to start if a listed module carries a different build marker.
- `ai_caregiver_pipeline.py` — legacy thin CLI entry point for the original single-day pipeline.
- Ported from AI_HomeCare_Atrust (2026-11-09, see `PORTING_PLAN.md` 第四階段), all pure modules: `plan_versions.py` (dated weekly-plan changes, written back to the workbook's 到期日／生效日), `undo_stack.py` (「↩️ 復原上一步」, 10 steps, `STATE_KEYS`／`RES_KEYS` must cover any new state-changing action), `billing.py` (CSMS claim export + co-payment estimate, columns in `CLAIM_COLUMNS`), `change_log.py` (merged change log in ④), `error_log.py` (error file log + per-session list).

### Streamlit app (`app.py`)

- **Login first.** Unless `CAREFLOW_AUTH=0`, nothing but the header and the login card (`careflow_ui.auth_card`) is drawn until `st.session_state['auth_user']` is set; with no accounts yet, the card creates the first 主管. Otherwise the entry page has 登入／註冊新帳號／忘記密碼 (`segmented_control` key `cf_auth_view`): sign-up and forgot-password only create requests (`auth.request_signup`／`request_reset`, table `requests`, password hashed on submit) that a 主管 approves in 👥 帳號管理 (`auth.decide_request`, role can be changed on approval; sidebar button shows the pending count). The only 主管 forgetting the password uses `python tools/reset_password.py 帳號` on the host. When the sidebar is collapsed the whole page scales ×1.12 (`--cf-s0`／`--cf-s` in `inject_css`). Fixed check-in URL, free and without installing anything: a Cloudflare Workers 「門牌」 (`checkin/runner.py › setup_gateway`／`_gateway_follow`, worker `homecare-checkin` on the user's free workers.dev subdomain, proxies to the current quick tunnel; the app re-uploads the worker with the new `TARGET` whenever the quick-tunnel URL changes and restarts a dead tunnel); own-domain alternative: Cloudflare named tunnel token (`save_named_tunnel`) in the 進階 toggle. The fixed-URL settings box is drawn only for 主管 (an expander, collapsed once configured); 居督 only see a one-line hint while no fixed URL is set. A floating 「＋ 臨時異動」 button (container `cffab`, key `cf_fab_temp`) opens a 3-step dialog (`_temp_change_dialog`, answers saved in `tcd_saved`) that prefills and opens ③ › 臨時異動 (leave is registered immediately and auto-cover starts). The assignment dialog (`calendar_view._assignment_dialog`) checks candidates automatically and lists 「⭐ 推薦」 ones first. The user is re-read from `auth.current_user()` on every rerun, so disabling an account logs it out. Roles: 主管 = everything incl. the manager report and 帳號管理; 居督 = steps ①～④.
- **Navigation.** The top stepper (`render_stepper`) is the only way to change pages: ① 匯入資料 → ② 開始排班 → ③ 處理問題 → ④ 確認班表, plus 📊 主管報表 on the right. Locks (missing data, missing schedule, role) are computed only in `_flow_locks()`. 👥 帳號管理 (`M_ACCOUNTS`) is opened from the sidebar by managers, renders and then `st.stop()`s before any data loading.
- **Check-in.** `app.py` starts the check-in server once per process (`_start_checkin_server`, `st.cache_resource`) before the login gate; `CAREFLOW_CHECKIN_AUTOSTART=0` disables it (docker-compose runs it as the separate `checkin` service). ④ has 「📱 居服員打卡」 in order: ① 發布班表 with the demo-shift expander, ② `big_tabs` key `cf_checkin_view`: 打卡網址／手機綁定／補登覆核, ③ 打卡看板 `big_tabs` key `cf_attend_view`: 今天 (`_checkin_board` fragment) ／整段期間對照 (`_attendance_view`, default range ends yesterday). The 05 manager report's three headline cards (`manager_report.headline_cards(summary, …)`) are all computed from the schedule (排班完成率、固定人選服務比例、轉場佔總工時) — no assumed numbers; appendix numbers use `careflow_ui.stat_cards`. Supervisor actions write audit event `checkin`.
- **Pilot KPI.** 05 starts with `big_tabs(['主管報表', '試辦 KPI'], 'cf_analytics_view')`; the KPI view calls `kpi_view.render_pilot_kpis` with app.py's `show_table`／`export_frame`／`download_button_quiet` and the schedule frames plus `_pending_diagnostics`, `res['df_cg']` and the period. Layout: one `kpi_cards` row per group, then the item table, then per-item expanders. Demo mode writes to `kpi_metrics.demo_db_path()` next to the demo store. Saves write audit event `kpi`.
- **Sidebar** holds status only: account (logout, change own password), data/routing status, ⚙️ 排班規則設定, 🎬 示範模式, 🔒 個資顯示設定.
- Scheduling runs only when the run button is clicked (`_request_run` → `_run_requested`); results are kept in `st.session_state['last_result']` and autosaved by `session_store`. Editing data or rules clears the old schedule and marks `_result_stale`.

## Running

```bash
pip install -r requirements.txt
streamlit run app.py                  # web app; run from the repo root
pip install -r requirements-dev.txt
python -m pytest tests                # tests; conftest.py isolates caches, accounts and the audit log
```

Requires Python 3.10+, `streamlit`, `ortools`, `pandas`, `numpy`, `openpyxl`, `requests`, `matplotlib`, `seaborn`. Keys and hosts come from environment variables first, then `.streamlit/secrets.toml` (`GOOGLE_MAPS_API_KEY`, `CAREFLOW_OSRM_MOTORCYCLE_HOST`). Set `CAREFLOW_AUTH=0` to skip login for local development only.

After changing any module other than `app.py`, restart Streamlit — it only reloads `app.py`. Never run AppTest from the project folder (it writes to the real `output_results/`); use `tmp_path` + `monkeypatch.chdir` as in `tests/test_manager_report.py`.

## Data source

The current input is one agency workbook with six sheets (`員工資料`, `個案資料`, `週服務計畫`, `Service_code`, `案家姓名對照`, `居服員姓名對照`; see `README.md`). `caregiver_engine.load_agency_workbook()` converts it into the internal DataFrames below. The original four-sheet format described next is still readable through `load_data()`.

The legacy input lives in `00_DB/AI_Caregiver_Allocation_Ultimate_Database.xlsx`, with four sheets that map directly onto DataFrames in the script:

- **Caregiver_Profiles** (`df_cg`) — one row per 居服員 (caregiver): home lat/lon, certifications, daily hour caps, current fatigue (monthly cumulative hours), average satisfaction score, exclusion conditions (e.g. refuses walk-ups/pets/smoking environments), and up to two pre-existing time-blocked appointments for today.
- **Client_Profiles** (`df_cl`) — one row per 案家 (client household): service location, required caregiver gender, care level (CMS), special care needs, environment tags, heavy-lift-assistance flag, and historical preferred caregiver ID.
- **Today_Pending_Tasks** (`df_tasks`) — today's unassigned tasks: time window, duration, priority, and requested service type. Merged with `Client_Profiles` on 案家ID at load time to form `tasks`.
- **Historical_Service_Logs** (`df_hist`) — 300 historical service records with a `歷史媒合機制(Treatment)` flag (1 = AI-matched, 0 = human-matched) used purely for the Phase 3 outcome comparison, not for scheduling.

Column names are Traditional Chinese; keep them as-is when reading/writing this workbook (spot checks with the Bash tool over this data mangle the encoding — read Excel contents via Python/pandas or the Read tool instead of piping through the terminal).

Other files in `00_DB/` (PDFs, other `.xlsx` files) are reference/source materials for the long-term-care service statistics this project is built around — not consumed by the script.

## Pipeline architecture (`caregiver_engine.py`)

Three sequential phases, each a standalone function that both `ai_caregiver_pipeline.py` and `app.py` call in order:

1. **Phase 1 — `run_phase1_matching`** (candidate generation): for every (task × caregiver) pair, apply hard filters, then score survivors starting from `config.base_score` (default 60):
   - Hard filters (reject pair entirely): gender requirement, heavy-lift capability requirement, `EXCLUSION_MAP` environment conflicts (caregiver aversion vs. client environment tag), and daily-hour-cap overflow. These are not exposed as adjustable — they are eligibility rules, not dispatch policy.
   - Soft scoring (`score`, floored at 0): +certification match (`cert_bonus_dementia` / `cert_bonus_other`), +`preferred_caregiver_bonus` for historical preferred caregiver, +satisfaction deviation from `satisfaction_baseline` weighted by `satisfaction_weight`, −travel-time penalty (weighted by `travel_penalty_weight`, capped at `travel_penalty_cap`) computed from `calc_travel_minutes` (real OSRM road-network minutes, falling back to the `calc_distance_km` flat-degree approximation on API failure — see "Travel time model" below), −fatigue penalty (`fatigue_weight`) based on **service-intensity-weighted** monthly cumulative hours vs. `fatigue_reference_hours` (see "Fatigue model" below).
   - Output: `df_matches`, one row per surviving (task, caregiver) candidate pair.

2. **Phase 2 — `run_phase2_optimization`** (time-conflict filtering + OR-Tools MIP):
   - Drops candidate pairs that conflict with a caregiver's pre-existing appointments today, accounting for travel time plus `config.buffer_mins` transition buffer (parking/stairs/access/handoff).
   - Builds a binary assignment MIP with OR-Tools' `SCIP` backend: decision var `X[task_id, cg_id]`; constraint 1 — each task assigned to at most one caregiver; constraint 2 — no caregiver double-booked into two new tasks whose windows (plus travel+buffer) overlap.
   - Objective: maximize `match_score − objective_travel_weight×travel_minutes + priority_bonus` (priority_bonus is `urgent_priority_bonus` if the task priority string contains "緊急" (urgent), else `normal_priority_bonus`) — this weighting is where dispatch policy actually lives, not in the hard filters.
   - Output: dict with `df_valid`, `df_result` (final task→caregiver assignment, includes lat/lon for map plotting), `status`, `assigned_count`.

3. **Phase 3 — `run_phase3_did`**: splits `Historical_Service_Logs` into AI-treated vs. human-control groups on `歷史媒合機制(Treatment)` and reports the uplift in mean satisfaction and reduction in early-termination rate attributable to AI matching. This is a retrospective analysis over historical data, independent of Phases 1–2's live scheduling run, and is **not** affected by `PipelineConfig` — it does not take config as an argument.

All dispatch-policy coefficients named above live in the `PipelineConfig` dataclass; `app.py`'s sidebar exposes one slider per field. When adding a new tunable coefficient, add it to `PipelineConfig` first, thread it through the relevant Phase function, then add a sidebar slider — never hardcode a new policy constant directly in `app.py` or `ai_caregiver_pipeline.py`.

### Travel time model (OSRM)

- `calc_travel_minutes(lat1, lon1, lat2, lon2, config)` is the single entry point for transition travel time, used identically in four places: Phase 1 scoring, Phase 2's existing-schedule conflict check, Phase 2's new-task-pair conflict check, and `_diagnose_caregiver_change`'s pair check — keep them consistent if changing the transit-time model.
- Internally it calls `get_osrm_travel_time`, which queries the free OSRM public API (`router.project-osrm.org`, `biking` profile) for real road-network minutes between two points, backed by a module-level dict cache (`_OSRM_TRAVEL_TIME_CACHE`, keyed on coordinates rounded to 6 decimals). On request timeout (`OSRM_TIMEOUT_SECONDS`), network failure, or a non-`Ok` response, it prints an `[OSRM Warning]` log and falls back to the `calc_distance_km` flat-degree estimate (1° lat ≈ 111 km, 1° lon ≈ 101 km) × `travel_min_per_km`.
- Before their pairwise loops, `run_phase1_matching` and `run_phase2_optimization` each call `prefetch_osrm_travel_times(origins, destinations, travel_min_per_km)`, which batches the whole origin×destination coordinate set into one (or a few, chunked at `OSRM_TABLE_MAX_COORDS`) OSRM `/table` matrix requests and pre-populates the shared cache — this is what keeps a 20-caregiver × 25-task run to a handful of HTTP calls instead of hundreds; without it the per-pair fallback path still works, just far slower. A failed batch prints a warning and leaves those pairs to be resolved (and independently degrade) on the next per-pair `get_osrm_travel_time` call.
- `OSRM_HOST` / `OSRM_PROFILE` / timeouts are module-level constants, not `PipelineConfig` fields (same pattern as `calc_distance_km`'s constants) — they're plumbing, not dispatch policy.

### Fatigue model (service-intensity-weighted)

- `get_service_intensity_weight(task)` maps a task to a strain coefficient via `SERVICE_INTENSITY_WEIGHT`: 1.5 for heavy transfer/joint mobility (`需重度移位協助(0/1)==1`), 1.2 for meal care/tube feeding/hygiene (`特殊照護需求` in `{餐食照顧/管灌, 管路安全與特殊日常照護}`), else 0.8 (general housework/companionship, including dementia care).
- Phase 1 no longer uses the flat `cg["當月累計服務時數(疲勞度)"] / fatigue_reference_hours` ratio; it now multiplies the caregiver's cumulative hours by the *current candidate task's* intensity weight first: `fatigue_penalty = (cg累計時數 × intensity_weight) / fatigue_reference_hours × fatigue_weight`. This is evaluated per (task, caregiver) pair (Phase 1 has no per-service-type history to sum over), so assigning a physically demanding task to an already-fatigued caregiver is penalized more than assigning a light one.

### Other invariants when modifying this pipeline


- `EXCLUSION_MAP` keys are caregiver `特殊排斥條件` values; values are the matching `案家環境特徵` string they conflict with. Both sides are exact-string-matched against the Excel data, so any new exclusion category must be added to both the map and used consistently in the source spreadsheet.
- Time strings in the workbook use `"HH:MM-HH:MM"` (or the literal `"無既定行程"` sentinel for "no existing appointment"); `parse_time` and the task-time parsing in Phase 2 assume this exact format.
- `app.py` only runs scheduling when the ② run button (key `run_full_period`) is clicked (not on every slider/data-editor change); the last result is kept in `st.session_state["last_result"]` and re-displayed on subsequent reruns until scheduling runs again or data/rules change. Raw sheet reads are `st.cache_data`-cached (keyed on upload identity or file path + mtime), but the edited copies of the caregiver/client/task sheets live separately in `st.session_state` (`edit_cg`/`edit_cl`/`edit_tasks`) so user edits survive reruns and aren't clobbered by the cache.
- `setup_chinese_font()` in `app.py` (sets `plt.rcParams["font.sans-serif"]`) must be called *after* `sns.set_style(...)`, not before — seaborn's `set_style` overwrites `font.sans-serif` back to its own default (Arial-first) list, which silently drops all CJK glyphs from the matplotlib dashboard.

## 程式與介面風格規範

本節整理自本專案現有程式（2026-11-08，HEAD `d9e35ce`＋第 5 步未 commit 的改動；同日加入登入系統後更新），**只描述本專案既有寫法**。新增或移植功能時以本節為準；範例一律標「檔名 › 函式／變數」。

### 一、UI 風格

#### 1. 字級與對比（方案 C「暖心大字」）

- **全站樣式只從一個入口注入**：`careflow_ui.py › inject_css(scale)`，依序疊五層 `CSS + DESIGN_CSS + WARM_CSS + FIX_CSS + TIDY_CSS`，最後再補一行 `:root{--cf-s:<倍率>}`。每次重跑都要注入（由 `render_header()` 呼叫）。
  - `TIDY_CSS`（2026-11-09）是版面精簡層：主內容最寬 1720px、頁首白卡 `st-key-cf_topbar`、登入頁雙欄 `cf-auth-side`、週班表可點按鈕與「當天班表」視窗（`cfwk*`、`cf-dd-*`）。新加的樣式放這層。
  - `WARM_CSS` 是目前生效的配色與字級層；`DESIGN_CSS`（v2026.11 翡翠綠）與最前面的 `CSS`（舊版）已被覆寫，只是保留。
  - `FIX_CSS` 必須最後注入：統一按鈕所有狀態（hover／active／focus／disabled）的底色與字色、取消重跑時的淡化、讓出 Streamlit 頂部固定列。
- **字級一律寫成 `calc(基準px * var(--cf-s))`**，不寫死 px。例：`WARM_CSS` 內文 `calc(19px * var(--cf-s))`、說明文字 17px、元件標籤 18px（粗體）、h1～h3 為 34／28／24px。
- **字級切換機制**：
  - 倍率表：`careflow_ui.py › FONT_SCALES = {'標準': 0.86, '大': 0.96, '特大': 1.08}`（2026-11-09 整體下修一號）。
  - session_state key：`cf_font_scale`，預設 `'標準'`（`app.py › _SETTING_DEFAULTS`），列在 `_PERSISTED_KEYS`，換頁會保留。
  - 頁首右側：`app.py` 在 `st.container(key='cf_topbar')` 裡用兩欄，左邊 `render_header(..., scale=_font_scale, font_label=True)`，右邊 `st.segmented_control('字體大小', ..., key='cf_font_scale', label_visibility='collapsed')`，CSS 把兩欄合成同一張白卡。
- **對比規範**（寫在 `careflow_ui.py` 的 `WARM_CSS` 註解）：主要文字 `--cf-ink #2B2622`、次要 `--cf-muted #6B5E52`，白底對比都 ≥ 4.5:1；鍵盤焦點 `:focus-visible` 為 3px 主色外框。

#### 2. 顏色、卡片、標題、警示

- **顏色只用 CSS 變數**（定義在 `careflow_ui.py › WARM_CSS :root`）：
  - 主色 `--cf-primary #1F5F7A`／`--cf-primary-soft`／`--cf-primary-ink`
  - 成功 `--cf-ok #2F855A`（`-soft`、`-line`）
  - 提醒 `--cf-amber #B45309`（`-soft`、`-ink`、`-line`）
  - 錯誤 `--cf-red #B42318`（`-soft`、`-ink`）
  - AI 功能 `--cf-ai-1 #4338CA`（單色，不用漸層）
  - 底色 `--cf-bg #FBF7F0`、卡片 `--cf-card #FFFFFF`、框線 `--cf-line`／`--cf-line-2`
  - `careflow_ui.py › MODULE_COLORS`：五個模組全部用同一組深藍綠，`module_header()` 會注入 `--cf-acc*`。
  - 唯一的例外是 matplotlib 圖（讀不到 CSS 變數）：在模組常數用同一組色碼，例如 `manager_report.py › STATUS_COLORS = {'正常': '#1F5F7A', '接近上限': '#B45309', '超過上限': '#B91C1C'}`。
- **頁首與標題**
  - 全域頁首：`careflow_ui.py › render_header(ai_ready, privacy_on, version, scale)`（圓形 Logo＋「AI 系統已就緒／個資已遮蔽」狀態膠囊）；舊名 `render_brand()` 只是轉呼叫。
  - 側邊欄 Logo：`side_brand()`。
  - 模組頁首：`module_header(key)`（編號＋名稱＋本頁任務＋使用者角色徽章；角色來自 `MODULES` 第 5 欄「居督／主管」）。
  - 頁內小節：`subhead(text)`（`app.py` 用了 24 次）；`st.subheader` 只剩 2 處舊程式；細項小標用 `st.markdown('##### …')`。
- **卡片類 helper**（全部在 `careflow_ui.py`，HTML 一律經 `_e()`（`html.escape`）跳脫）：
  - 數字：`kpi_cards(items)`（tone：good／warn／bad／ai）、`impact_cards(items, cols)`（淡底色＋圖示圓章，item 可帶 tone／icon／ring）、`stat_strip(items)`（同一組數字放進一張大卡分格，④ 的打卡看板、執行對照、CSMS 試算用）、`result_hero(...)`；三者的 item 都可帶 `ring`（0～100，`ring_html()` 畫小圓環，只用在比例類數字）
  - 狀態：`ready_cards(items)`、`conn_card(title, detail, latency, tone)`、`import_card(number, title)` → `(容器, set_head)`
  - 流程：`run_card_html()`、`run_steps_markdown()`、`signoff_head_html()`、`family_heading(n)`
  - 登入：`auth_card(mode)`（login／setup；回傳送出的欄位與訊息容器，驗證由 app.py 呼叫 `auth`）
  - 建議：`advice_cards(items)`（自動加「✨ AI 建議」徽章）
  - 空白狀態：`empty_module(key, message, target, button)`
- **徽章與標籤**：`badges([(文字, tone)])`／`badge_html(text, tone)`（tone：red／amber／green／slate／ai）、`chips(items, tone)`；衝突原因轉短徽章用 `reason_badge(text)`（對照表 `_REASON_BADGES`，前面加 🔴🟡🟠⚪）。
- **警示**：沒有包裝 helper，直接用 Streamlit 原生元件，樣式由 CSS 的 `[data-testid="stAlert"]` 統一：
  - `st.success`（完成）、`st.info`（說明／下一步）、`st.warning`（需要注意，但流程可繼續）、`st.error`（失敗或會讓結果錯誤）。`app.py` 裡分別約 17／27／36／34 處。
  - 完成大動作後的短通知用 `st.toast(..., icon='✅')`（`app.py`：載入 Demo、排班完成）。
  - 需要使用者確認的阻擋用 `@st.dialog(..., on_dismiss=...)`（`app.py › _dismiss_leave_issues`、「確認寫入代班」）。

#### 3. 版面

- **導覽（方案 A）**：頂部步驟列是**唯一**的換頁方式。
  - `careflow_ui.py › render_stepper(current, done, locked, warn)`：① 匯入資料 → ② 開始排班 → ③ 處理問題 → ④ 確認班表，主管報表（📊）獨立放最右邊。順序來自 `FLOW_KEYS`，名稱來自 `STEP_LABELS`。
  - 按鈕 key 固定為 `cfnav_<模組>`；外層容器 key `cfstep_<now|done|todo|lock|warn>_<模組>`，給 CSS 上色。
  - 上鎖規則只寫在 `app.py › _flow_locks()`；步驟列由 `app.py › _draw_stepper()` 在資料讀完後畫，每次執行只畫一次。
  - 目前模組存在 `st.session_state['cf_module']`，模組代碼在 `careflow_ui.py › MODULES`／`MODULE_KEYS`（`app.py` 解成 `M_IMPORT, M_SCHEDULE, M_ISSUES, M_REVIEW, M_ANALYTICS, M_ACCOUNTS`）。換頁用回呼 `go_to_module(key)`。
  - 不在步驟列上的頁面（目前只有 👥 帳號管理）由側邊欄按鈕進入，頁尾用 `step_action_bar(..., target=原本的頁面)` 返回。這類頁面如果不需要排班資料，畫完就 `st.stop()`（`app.py › _render_accounts_page`）。
- **每頁底部**：`careflow_ui.py › step_action_bar(current, label, target, hint, disabled, on_click, tone)`。左邊「← 上一步」、中間一句「還差什麼」、右邊唯一的主按鈕；`tone='warn'` 時改用琥珀色。舊的 `module_nav_buttons()` 已不用。
- **側邊欄只放狀態**：`app.py › with st.sidebar:` 依序是 `_sidebar_account`（👤 登入者、登出、主管的「👥 帳號管理」、🔑 變更我的密碼）、`_sidebar_status`、`_sidebar_wake`（交通主機燈號）、`_sidebar_rules`（⚙️ 排班規則設定，`render_dispatch_settings()`）、`_sidebar_privacy`（🔒 個資顯示設定）。
- **分區**：
  - 同頁的多個視角用 `careflow_ui.py › big_tabs(options, key, icons, size, suffixes)`（大型分頁按鈕，可附「· 6 案」小計），例如 `app.py` 的 `big_tabs(['週班表（大字）', '拖曳調整（進階）'], 'cf_sched_view')`、05 的 `big_tabs(['主管報表', '試辦 KPI'], 'cf_analytics_view')`。
  - 附錄類內容用 `st.tabs`（例：主管報表附錄 `_ap1…_ap4`）。
  - 細節收合用 `st.expander`；分頁裡面不要再放 expander。
  - 收件匣類版面用 `st.columns` 左清單、右詳情（③ 處理問題）。
- **按鈕**：
  - 每一區只有一顆 `type='primary'`，其餘是預設 secondary。
  - 寬度一律寫 `width='stretch'`（不用已淘汰的 `use_container_width`）。
  - 動作一律用 `on_click=` 回呼（例：`app.py › _request_run`、`_finalize_schedule`），不在按鈕回傳值後面直接改導覽狀態。
  - AI 專屬按鈕放在 key 以 `cfai` 開頭的容器裡（CSS 會套靛藍色）。
  - 下載一律用 `app.py › download_button_quiet()`（`on_click='ignore'`，不重跑整頁）。
- **表單（`st.form`）**：只用在「一次送出多個欄位、而且含密碼」的情境，也就是登入（`careflow_ui.py › auth_card`）和帳號表單（`app.py › _render_accounts_page`、側邊欄「🔑 變更我的密碼」）。
  - 其他設定類元件照舊即時生效，不包表單。
  - 有密碼欄的表單用 `clear_on_submit=True`，送出後不把密碼留在畫面上（登入卡片例外：送出失敗時保留帳號方便重打）。
  - 送出鍵用 `st.form_submit_button(..., width='stretch')`，一張表單只有一顆。
  - 成功訊息如果要在 `st.rerun()` 之後才顯示，先存 `st.session_state['_account_notice']`，下次畫面再取出顯示（`app.py › _account_notice`）。
- **表格**：
  - 唯讀表格一律用 `app.py › show_table(data, hide_index=True, width='stretch', column_config=...)`，不直接呼叫 `st.dataframe`（它會依個資設定套用 `identity_display`）；`app.py` 有 57 處 `show_table`，直接用 `st.dataframe` 只有 1 處。
  - 可編輯表格用 `st.data_editor`（`app.py › render_editable_sheet()`）。
  - 長文字欄位用 `st.column_config.TextColumn(width='large')`。
  - 對齊：`careflow_ui.py › uniform_table_alignment()`（由 `inject_css` 呼叫）包住 `st.dataframe`／`st.data_editor`，沒指定 `alignment` 的欄一律 `TABLE_ALIGN = 'left'`，數字欄不再靠右。需要 Streamlit 1.56 以上。
- **HTML 元件的 CSS 一律放在 `careflow_ui.py`**。例：`week_board.py` 只輸出 `cf-wk-*` class，樣式在 `careflow_ui.py`。`calendar_view.py › _GRID_CSS` 是舊有例外，不要再增加新的例外。居服員手機打卡頁（`checkin/templates/base.html`）是另一個 Flask 網頁、讀不到 `careflow_ui.py`，CSS 寫在模板裡，但變數名稱與色碼照抄 `WARM_CSS` 的 `--cf-*`，字級同樣用 `calc(px * var(--cf-s))`。

#### 4. 用語

- **語氣**：白話、短句、告訴使用者下一步。
  - 例：`step_action_bar` 的 hint「還差：…」、`family_heading()`「還有 N 個家庭需要您看一下」、`signoff_head_html()`「尚未定稿：逐項確認後，按下方…」。
  - 錯誤訊息的寫法是「發生什麼＋影響範圍＋原因」，例如 `app.py`：「交通暫未計算，班表仍可檢視與下載；估計交通留空。原因：…」。
  - 盡量不出現工程名詞；必要的放在「進階」展開區或 `help=`。
- **專有名詞**（以畫面出現次數為準）：
  - 人：**居督**（使用者；「督導」只剩 1 處，不要再用）、**居服員**（不用「照服員」）、**案家**（排班情境）／**個案**（資料表、資格情境）、**主管**。
  - 排班狀態：**已派／未派**（服務層級，最常用）、**已排／未排**（班次、日曆）。「未排入」只出現 1 次，不要新增。
  - 其他：**主責**、**備援**、**代班**、**改派**、**固定人選**、**歷史首選**、**請假**、**定稿**、**班表**。
  - 介面稱呼使用者時沿用既有寫法（多為「請…」祈使句），不刻意加「您／你」。
- **數字**：
  - 千分位 `f'{n:,}'`，小數 `:.1f`，去尾 0 用 `:g`，金額 `f'{x:,.0f} 元'`。
  - 數字和單位之間空一格：「12 筆」「3 位」「6 案」「4.0 小時」「15 分鐘」。
  - 百分比寫 `f'{rate:.1f}%'`。
- **日期時間**：
  - 畫面顯示 `%Y/%m/%d`；期間用全形波浪號：`app.py › _period_title()` →「11 月」或「2026/11/05～12/04」。
  - 短日期 `%m/%d`，時刻 `%H:%M`，時段「09:00～10:00」。
  - 資料與存檔用 ISO `%Y-%m-%d`（例：`dispatch_workflow.py › stamp()` 用 `Asia/Taipei` 時區、`isoformat(timespec='seconds')`）。
  - 星期寫「星期一」或「週一」，對照表見 `week_board.py › _WEEKDAYS`。
- **標點**：中文介面用全形「：」「（）」「／」「～」「、」。分隔用「 · 」或「　·　」。

#### 5. 一般模式與進階模式

- **本專案沒有全域的「進階模式」開關**（沒有 `ui_advanced` 之類的 key），進階內容就地收在三種地方：
  - 標題含「進階」的 `st.expander`：`app.py` 的「進階：Google 查詢上限與連線檢查」、「演算法指派明細（進階）」、「進階：單筆配對說明與適配分數」。
  - `big_tabs` 的「（進階）」分頁：「拖曳調整（進階）」。
  - ③ 右欄預設收合的「③ 自己處理」。
- **示範模式**是唯一的全域模式開關：`app.py` 側邊欄的 `st.toggle('🎬 示範模式（只用 Excel）', key='demo_mode', on_change=_reset_demo_store)`。開啟時改用 `dispatch_workflow.py › fresh_demo_store_path()` 的暫存資料庫。
- **角色權限**（登入）：`auth.py › can_access(role, module)`，主管全部可用，居督不能進 `MANAGER_ONLY_MODULES = ('analytics', 'accounts')`。
  - 畫面只在 `app.py › _flow_locks()` 依角色上鎖，步驟列顯示 🔒「只有主管帳號可以使用」。不要在各頁另外寫 `if 不是主管: st.stop()`。
  - `careflow_ui.py › MODULES` 第 5 欄的「居督／主管」要和 `MANAGER_ONLY_MODULES` 一致（`tests/test_auth.py › test_module_codes_match_ui` 會檢查）。
  - `CAREFLOW_AUTH=0` 時不登入，以主管權限使用（`app.py › _LOCAL_USER`），帳號管理頁上鎖。

### 二、程式風格

#### 1. 命名、型別、docstring

- **檔名**：小寫 snake_case、名詞片語：`dispatch_workflow.py`、`schedule_checks.py`、`manager_report.py`、`import_health.py`、`week_board.py`。純畫面 helper 集中在 `careflow_ui.py`，某一頁的畫面元件獨立成 `*_view.py`／`*_board.py`（`dashboard_view.py`、`week_board.py`）。
- **函式**：snake_case、動詞開頭，例如 `build_health_items`、`render_week_board`、`load_identity_mapping`、`workload_error`。
  - 模組內部用 `_` 開頭，例如 `week_board.py › _chip`、`session_store.py › _connect`。
  - Streamlit 畫面函式叫 `render_*`；只回傳 HTML 字串的叫 `*_html`（`badge_html`、`run_card_html`）。
- **純邏輯和畫面分開**：
  - 計算模組不 import streamlit，並在模組 docstring 寫明，例如 `manager_report.py`「純函式，不呼叫 Streamlit」、`careflow_ui.py`「Presentation-only helpers. No scheduling or external requests.」。
  - 計算結果以 dict／DataFrame 回傳，例如 `manager_report.py › headline_cards()` 回傳 `dict(title, number, before, after, note, ai)`，交給 `impact_cards()` 顯示。
- **常數**：大寫 snake_case 放在模組頂端，例如 `session_store.py › DB_PATH`、`KEEP_PER_SCOPE`、`STATE_KEYS`；`careflow_ui.py › RUN_STEPS`、`CHANGE_REASONS`。
- **換行符號**：Windows 工作目錄裡的檔案是 CRLF，git 存成 LF（autocrlf）。
  - 新檔案和修改後的檔案都維持 CRLF。
  - 在 Linux 環境（例如 Claude 的工作區）用 git 看差異時，要加 `--ignore-cr-at-eol`，否則會顯示整個檔案都改了。
- **版本標記**：要列入一致性檢查的模組頂端都有 `CAREFLOW_BUILD = '2026.10.18-v19'`，名單在 `build_info.py › REQUIRED_MODULES`，由 `app.py › _check_install()` 在啟動時比對。新增核心模組時兩邊要一起加。
- **type hints**：只用在 `caregiver_engine.py`（`PipelineConfig` 的 dataclass 欄位、部分公開函式，例如 `load_override_log(log_path: str = OVERRIDE_LOG_PATH) -> pd.DataFrame`）。畫面與其他模組（`careflow_ui.py`、`dispatch_workflow.py`、`manager_report.py`…）都不寫，新程式依所在檔案的慣例。
- **docstring**：
  - 新程式一律用**繁體中文**，一句話講用途，再補參數說明，例如 `careflow_ui.py › render_stepper`「done：已完成的模組；locked：{模組: 尚未解鎖原因}…」、`import_card`「state：done（✓ 已完成）／now…」。
  - 模組 docstring 說明「做什麼、不做什麼、資料存哪」（`session_store.py`、`week_board.py`）。
  - 少數舊檔是英文一行（`schedule_checks.py`、`persistent_cache.py`、`runtime_views.py`），不用改寫。
- **註解**：寫「為什麼」，例如 `careflow_ui.py › FIX_CSS` 上方逐條說明每個修正的原因、`dispatch_workflow.py › replace_workdays` 說明帳本只增不減造成的問題。

#### 2. 設定放在哪裡

- **派單政策參數**：一律放在 `caregiver_engine.py › PipelineConfig`（dataclass，有型別和中文分類註解）。畫面要調整的參數只透過 session_state 轉進去：`app.py` 的 `cfg_buffer_mins`、`cfg_travel_penalty_weight` → `buffer_mins`、`travel_penalty_weight`。
- **機密**：`.streamlit/secrets.toml`（不進 git，範本是 `.streamlit/secrets.toml.example`）。讀取順序是**環境變數優先，再讀 `st.secrets`**，例如 `caregiver_engine.py` 讀 `GOOGLE_MAPS_API_KEY`、`app.py` 讀 `CAREFLOW_OSRM_MOTORCYCLE_HOST`，都包在 `try/except`。
- **環境變數命名**：專案自己的設定一律 `CAREFLOW_` 前綴＋大寫底線，例如 `CAREFLOW_CACHE_DIR`、`CAREFLOW_AGENCY_DIR`、`CAREFLOW_ROAD_CACHE_DAYS`、`CAREFLOW_TRANSIT_CACHE_DAYS`、`CAREFLOW_OSRM_MAP_VERSION`、`CAREFLOW_TRAVEL_PROVIDER`；第三方金鑰沿用官方名稱（`GOOGLE_MAPS_API_KEY`）。
  - 登入相關：`CAREFLOW_AUTH`（`0`／`off`／`false`／`no` 關閉）、`CAREFLOW_ACCOUNTS_DB`、`CAREFLOW_AUDIT_DIR`（`auth.py › enabled()`／`db_path()`、`audit_log.py › audit_dir()`）。
  - 打卡相關：`CAREFLOW_CHECKIN_AUTOSTART`、`CAREFLOW_CHECKIN_PUBLIC_URL`、`CAREFLOW_CHECKIN_TUNNEL`（沒有固定網址時預設自動開外部網址，`0` 關閉）、`CAREFLOW_CHECKIN_TUNNEL_TOKEN`（Cloudflare 具名通道權杖，搭配 `CAREFLOW_CHECKIN_PUBLIC_URL`）、`CAREFLOW_KEEP_AWAKE`（Windows 防休眠，`0` 關閉）；免網域的固定網址用 Tailscale Funnel（`checkin/runner.py › start_funnel`／`funnel_state`，④ 打卡網址分頁的「📌 固定網址」）、`CAREFLOW_CHECKIN_PORT`、`CAREFLOW_CHECKIN_DB`、`CAREFLOW_CHECKIN_SECURE`、`CAREFLOW_CHECKIN_SECRET`（`checkin/runner.py`、`checkin/store.py`、`checkin/server.py`）。打卡容許值（遲到、早退、逾時、GPS 半徑）是派單政策參數，放在 `PipelineConfig.attendance_*`。
  - 試辦 KPI：`CAREFLOW_KPI_DB`（`kpi_metrics.py › db_path()`）。
  - 每個讀取點都要有預設值：`os.getenv('CAREFLOW_ROAD_CACHE_DAYS','30')`。
  - 路徑類變數讓測試可以導到暫存資料夾（`tests/conftest.py` 設定 `CAREFLOW_CACHE_DIR`）。
- **管線常數**（主機、逾時）是模組常數，不放進 `PipelineConfig`，例如 `OSRM_TIMEOUT_SECONDS`、`OSRM_TABLE_MAX_COORDS`、`GOOGLE_ROUTES_TIMEOUT_SECONDS`。
- **session_state key 命名**：
  - `cf_` 開頭：畫面導覽與顯示（`cf_module`、`cf_font_scale`、`cf_period_range`、`cf_sched_view`）
  - `cfg_` 開頭：排班規則（`cfg_buffer_mins`）
  - `_` 開頭：內部旗標（`_result_stale`、`_finalized`、`_stepper_drawn`、`_health_ack`、`_accounts_return`）
  - 例外：登入者存在 `auth_user`（dict：username、name、role），不進 `_PERSISTED_KEYS`，也不進自動存檔
  - 要跨換頁保留的，加進 `app.py › _SETTING_DEFAULTS`／`_PERSISTED_KEYS`；要進自動存檔的，加進 `session_store.py › STATE_KEYS`／`SETTING_KEYS`。
- **給 CSS 用的容器 key 前綴**：`cfstep_`、`cfnav_`、`cftabs_`、`cfactionbar_`、`cfimport_card_`、`cfinbox_`、`cfai`。

#### 3. 資料存取、錯誤處理、log

- **本機資料庫**一律 SQLite，放在 `output_results/`，每次連線時 `CREATE TABLE IF NOT EXISTS`：
  - `session_store.py › _connect()`：自動存檔 `work_snapshots`，與請假、固定人選共用 `output_results/dispatch_workflow.sqlite3`。用「機構＋Excel 指紋 `file_key()`＋期間」辨識。
  - `dispatch_workflow.py › WorkflowStore(scope, path)`：scope 先 sha256；表有 `records`／`blocks`／`pending`／`history`／`client_primary`／`workdays`；時間戳用 `stamp()`。
  - `persistent_cache.py › cache_path()`／`read_legs()`／`write_legs()`／`read_transit()`／`write_transit()`：交通路段快取，key 用 `json.dumps(..., ensure_ascii=True)`，依天數過期。
- **Excel**：
  - 讀：`pandas.read_excel(..., dtype=str)`＋`openpyxl`，例如 `caregiver_engine.py › load_identity_mapping()`；`app.py` 的 `_read_raw_sheets()`、`_load_agency_cached()` 用 `st.cache_data` 快取。
  - 寫回機構 Excel 用 `source_workbook.py › update_source_workbook()`，保留公式與表格。
  - 欄位名稱維持繁體中文原樣。
- **畫面結果快取**：`runtime_views.py › snapshot(cache, name, key, factory)`，key 由 `frame_version()`／`finance_key()`／`payroll_key()` 組成，篩選畫面不重算財務與匯出。
- **錯誤處理**分三層：
  1. 計算／資料層回傳中文錯誤字串或 `None`，不丟例外。例：`schedule_checks.py › workload_error()` 回傳「每日工時超標：…」、`dispatch_workflow.py › blocked_reason()` 格式錯誤時回傳「臨時不可排時段資料格式錯誤」。
  2. 快取或輔助功能失敗不能影響排班，只接住明確的例外。例：`persistent_cache.py › read_legs()` 用 `except (OSError, sqlite3.Error, ValueError): return {}`，並註明「不會提供猜測值」；`dispatch_workflow.py › overlap()` 用 `except (ValueError, TypeError, KeyError)`。
  3. 畫面層用 `except Exception as exc:`，接著顯示 `st.error`／`st.warning` 白話說明，並附 `'原因：' + str(exc)`，例如 `app.py` 的「交通暫未計算…」「寫入失敗：」「整案套用失敗：」。
- **存取稽核紀錄**：`audit_log.py › record(event, account=..., **detail)`，只能附加，有雜湊鏈與觸發器，`verify()` 可以檢查竄改。
  - 帳號一律由呼叫端傳入（`account=_user['username']`），模組本身不讀畫面狀態。
  - 事件代碼先加進 `audit_log.EVENTS`。detail 只放 ID 與筆數，欄名含 name、姓名、地址的會被濾掉，所以帳號代碼請用 `target`，不要用 `username`。
  - 寫入失敗只回傳 False，不影響登入與排班。
  - 目前記錄的事件：login、login_failed、logout、account（create_first_manager／create／reset_password／disable／enable／change_own_password）、checkin（publish／device_approve／device_reject／device_revoke／review／set_url／auto_bind／tunnel）、kpi（save_month）、undo（復原上一步）、plan_change（週計畫異動）、export（更新機構 Excel）。
- **錯誤紀錄**：畫面層的 `except Exception as exc:` 在顯示白話訊息前先呼叫 `app.py › _log_error('功能名稱', exc)`（轉呼叫 `error_log.log_error(where, exc, st.session_state)`），完整追蹤寫進 `output_results/logs/careflow_errors.log`（`CAREFLOW_LOG_DIR` 可改），側邊欄「⚠️ 進階：本次有 N 個系統錯誤」可看代碼、下載紀錄檔。
- **log**：除了上面的錯誤紀錄，沒有其他 logging。只有引擎在外部服務退回估算時 `print('[OSRM Warning] …')`（`caregiver_engine.py`）。需要留存的操作紀錄寫成資料：居督覆寫寫進 `output_results/supervisor_override_log.csv`（`caregiver_engine.py › save_override_log`／`load_override_log`）、請假歷程寫進 `WorkflowStore` 的 `history` 表。

#### 4. 個資遮罩（姓名 → 王○○）

- 遮罩函式：`caregiver_engine.py › _privacy_mask_name(name)`（只留第一個字，例「王小明」→「王○○」）。
- 讀姓名對照：`load_identity_mapping(source, kind)`／`load_identity_mappings_from_workbook(source)`，只回傳 `{ID: 遮罩姓名}`，原始姓名不進排班 DataFrame、不送外部 API。
- 顯示副本：`identity_display(frame, caregivers, clients)`，只改 `caregiver_cols` 等欄位的顯示值，計算用的 ID 不變。
- 畫面一律透過 `app.py` 的包裝函式，不自己拼姓名：
  - 表格：`show_table()`（依 `_show_names`）
  - 匯出：`export_frame()`（依 `_export_names`）
  - 單一 ID：`caregiver_label(id)`、`client_label(id)` → 「ID｜王○○」
  - 文字裡的 ID：`_label_ids_plain(text)`
- 設定 key：`show_identity_names`（畫面顯示）、`export_identity_mode`（「代碼版」或「遮罩姓名版（ID＋王○○）」），兩者都在 `_PERSISTED_KEYS`。
- 新增會顯示居服員或案家的表格欄位時，要把欄名加進 `identity_display` 的 `caregiver_cols`。

#### 5. 測試

- **新測試放 `tests/test_<模組或功能>.py`**，寫 pytest 函式 `def test_<行為>():`、用裸 `assert`，例如 `tests/test_import_health.py › test_issue_light`、`tests/test_manager_report.py › test_headline_cards_numbers`。
  - 測試檔開頭寫中文 docstring 說明範圍。
  - 測資用 `_frames()`／`_dashboard()` 這類小 helper 現場建 DataFrame，不讀正式 Excel。
  - 數字斷言旁邊註解算式，例如 `# 4 − 3/60 = 3.95 → 4.0`。
- 根目錄的 `test_v14.py`～`test_v18.py`、`test_agency_import.py` 是舊的 `unittest.TestCase` 寫法，保留不改，新測試不要放根目錄。
- **整頁測試用 AppTest，一定要隔離**：
  - `monkeypatch.chdir(tmp_path)`、`monkeypatch.setenv('CAREFLOW_AGENCY_DIR', str(tmp_path))`，在 tmp_path 用 `pd.ExcelWriter` 產生最小機構 Excel。
  - 把交通查詢 monkeypatch 掉（`engine.calc_travel_minutes`、`prefetch_osrm_travel_times`、`prefetch_google_transit_pairs`）。
  - 用 `AppTest.from_file(..., default_timeout=90)`，靠固定的元件 key 操作（`cfnav_schedule`、`run_full_period`、`cf_period_range`），最後 `assert not app.exception`。
  - 範例：`tests/test_manager_report.py › test_analytics_page_renders`。
  - 不可以在專案資料夾直接跑 AppTest，會寫進正式的 `output_results/`（見 `UI_改版進度.md` 注意事項）。
- 資料庫測試傳入 tmp_path 路徑，或 monkeypatch 模組常數，例如 `tests/test_demo_mode.py` 的 `WorkflowStore('中化', tmp_path / 'real.sqlite3')`、`monkeypatch.setattr(wf, 'DEMO_STORE_DIR', ...)`。
- `tests/conftest.py` 的 autouse fixture 負責把全域的路徑類環境變數導到暫存資料夾（`CAREFLOW_CACHE_DIR`、`CAREFLOW_ACCOUNTS_DB`、`CAREFLOW_AUDIT_DIR`、`CAREFLOW_CHECKIN_DB`、`CAREFLOW_KPI_DB`），設 `CAREFLOW_CHECKIN_AUTOSTART=0` 讓測試不在 8600 埠開打卡網頁，並設 `CAREFLOW_AUTH=0` 讓既有流程測試不必登入；新增會寫檔的模組時，在這裡加上對應的環境變數。
  - 要測登入頁的 AppTest 自己 `monkeypatch.setenv('CAREFLOW_AUTH', '1')`，並把 `auth.PBKDF2_ROUNDS` 調低加快（`tests/test_auth.py › _app`）。
  - 需要 streamlit 的測試用 `pytest.importorskip('streamlit.testing.v1')`，沒裝時略過，不會整檔載入失敗。

### 三、移植時要遵守的規則

從其他 repo（例如 `AI_HomeCare_Atrust`）移植功能時：

1. **UI 一律用既有的共用元件和 helper，不可以另寫新的 CSS 或配色。**
   - 顏色只能用 `WARM_CSS` 的 `var(--cf-*)`，字級只能用 `calc(px * var(--cf-s))`。
   - 標題用 `module_header`／`subhead`，卡片用 `kpi_cards`／`impact_cards`／`advice_cards`，徽章用 `badges`／`badge_html`。
   - 警示用 `st.success`／`st.info`／`st.warning`／`st.error`，表格用 `show_table`，下載用 `download_button_quiet`。
   - 換頁只能用 `render_stepper` 和 `step_action_bar`，不能帶入對方的側邊欄選單或 `module_nav_buttons`。
2. **對方的程式碼只取「邏輯」，介面和命名要依照本規範重寫。**
   - 計算放純函式模組（不 import streamlit）。
   - 畫面文字改成本專案的用語（居督、居服員、案家、已派／未派、`%Y/%m/%d`、全形標點），品牌一律「HomeCare AI」。
   - 設定進 `PipelineConfig` 或 `CAREFLOW_*` 環境變數；session_state key 依 `cf_`／`cfg_`／`_` 前綴規則命名。
   - 錯誤處理依三層寫法；顯示 ID 一律經 `caregiver_label`／`client_label`／`show_table`／`export_frame`。
   - 測試放 `tests/test_*.py`，並在 `tests/conftest.py` 隔離新的路徑。
3. **如果本專案缺少某種元件（例如登入表單），要用現有風格做一個新的共用元件放進 `careflow_ui.py`，不要寫死在功能檔裡。**
   - 新元件要沿用 `_e()` 跳脫、`var(--cf-*)` 顏色、`calc(... * var(--cf-s))` 字級。
   - CSS 加在 `WARM_CSS` 的對應段落；按鈕狀態若要另外上色，在 `FIX_CSS` 末段用容器 key 前綴指定。
   - 加上中文 docstring 說明參數與回傳值。
   - 功能檔（例如 `app.py`）只呼叫這個元件。
