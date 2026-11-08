"""Presentation-only helpers. No scheduling or external requests."""
CAREFLOW_BUILD = '2026.10.18-v19'
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;600;700&display=swap');
:root {
  --cf-ink:#173a38; --cf-teal:#147d73; --cf-teal-dark:#0e665d; --cf-mint:#e4f2ec; --cf-sand:#f1b873;
  --cf-muted:#667c78; --cf-line:#e2eae6; --cf-card:#ffffff; --cf-bg:#f6f8f5;
  --cf-shadow:0 1px 2px rgba(23,58,56,.05),0 6px 18px rgba(23,58,56,.05);
}
html, body, .stApp, [data-testid="stAppViewContainer"], button, input, textarea, select {
  font-family:'Noto Sans TC','PingFang TC','Microsoft JhengHei','Segoe UI',sans-serif;
}
.stApp { background:var(--cf-bg); }
[data-testid="stMainBlockContainer"], [data-testid="stAppViewContainer"] .main .block-container { max-width:1440px; padding-top:1.6rem; padding-bottom:4rem; }
[data-testid="stSidebar"] { background:#eef4f0; border-right:1px solid var(--cf-line); }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { font-size:15px; letter-spacing:.02em; margin-top:.6rem; }
h1,h2,h3 { color:var(--cf-ink); letter-spacing:-.02em; font-weight:700; }
h3 { font-size:1.25rem; }
[data-testid="stCaptionContainer"] { color:var(--cf-muted); }

/* hero */
.cf-hero { background:radial-gradient(120% 140% at 0% 0%,#1b6f64 0%,#123f3c 60%); border-radius:22px; padding:30px 36px; color:#fff; margin-bottom:16px; box-shadow:var(--cf-shadow); position:relative; overflow:hidden; }
.cf-hero:after { content:""; position:absolute; right:-60px; top:-60px; width:240px; height:240px; border-radius:50%; background:#ffffff0d; }
.cf-eyebrow { font-size:12px; font-weight:700; letter-spacing:.18em; color:#b5dcd0; }
.cf-hero h1 { color:white; font-size:32px; font-weight:700; margin:8px 0; padding:0; }
.cf-hero p { color:#d7ebe4; margin:0; font-size:15px; line-height:1.8; }
.cf-steps { display:flex; gap:10px; flex-wrap:wrap; margin-top:22px; }
.cf-steps span { background:#ffffff14; border:1px solid #ffffff2b; border-radius:999px; padding:8px 16px; font-size:13.5px; }
.cf-bar { display:flex; align-items:center; justify-content:space-between; gap:12px; background:var(--cf-card); border:1px solid var(--cf-line); border-radius:16px; padding:12px 20px; margin-bottom:12px; box-shadow:var(--cf-shadow); }
.cf-bar b { color:var(--cf-ink); font-size:16px; letter-spacing:.02em; }
.cf-bar span { color:var(--cf-muted); font-size:13px; }
.cf-bar i { font-style:normal; background:var(--cf-mint); color:var(--cf-teal-dark); border-radius:999px; padding:3px 10px; font-size:12px; font-weight:600; }

/* section */
.cf-section { display:flex; align-items:center; gap:14px; margin:34px 0 14px; scroll-margin-top:80px; padding-top:6px; border-top:1px solid var(--cf-line); }
.cf-number { background:linear-gradient(135deg,#1a8a7d,#147d73); color:#fff; border-radius:12px; min-width:42px; text-align:center; padding:9px 0; font-size:15px; font-weight:700; box-shadow:0 4px 10px #147d7328; }
.cf-section h2 { font-size:22px; padding:0; margin:0 0 3px; }
.cf-section p { font-size:14px; color:var(--cf-muted); margin:0; }
.cf-nav { display:grid; gap:4px; }
.cf-nav a { padding:10px 14px; border-radius:10px; color:#28574e !important; text-decoration:none; font-size:14px; font-weight:600; border-left:3px solid transparent; }
.cf-nav a:hover { background:#dcece4; border-left-color:var(--cf-teal); }
.cf-empty { border:1px dashed #b9d4c8; background:white; border-radius:18px; text-align:center; padding:35px 20px; margin:12px 0; }
.cf-empty span { font-size:30px; }.cf-empty h3 { font-size:21px; padding:12px 0 8px; }.cf-empty p { color:var(--cf-muted); font-size:14px; }

/* cards */
[data-testid="stMetric"] { background:var(--cf-card); border:1px solid var(--cf-line); border-radius:16px; padding:16px 20px 14px; box-shadow:var(--cf-shadow); background-image:linear-gradient(var(--cf-teal),var(--cf-teal)); background-size:100% 3px; background-repeat:no-repeat; background-position:top; }
[data-testid="stMetricLabel"] { color:var(--cf-muted); font-size:13px; font-weight:600; letter-spacing:.02em; }
[data-testid="stMetricValue"] { color:var(--cf-teal); font-weight:700; font-size:2rem; font-variant-numeric:tabular-nums; }
[data-testid="stMetricDelta"] { font-size:12.5px; }
[data-testid="stExpander"] { background:var(--cf-card); border:1px solid var(--cf-line); border-radius:14px; box-shadow:var(--cf-shadow); }
[data-testid="stExpander"] summary { padding:13px 16px; font-weight:600; }
[data-testid="stFileUploader"] { background:white; padding:18px; border:1px solid var(--cf-line); border-radius:16px; }
[data-testid="stFileUploaderDropzone"] { background:#f4f9f6; border-radius:12px; }
[data-testid="stDataFrame"], [data-testid="stDataEditor"] { border:1px solid var(--cf-line); border-radius:12px; overflow:hidden; box-shadow:var(--cf-shadow); }
[data-testid="stForm"] { background:var(--cf-card); border:1px solid var(--cf-line); border-radius:16px; padding:18px 20px; }
[data-testid="stAlert"] { border-radius:12px; border:1px solid var(--cf-line); }

/* inputs */
[data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-baseweb="textarea"] { border-radius:10px; }
[data-baseweb="select"] > div:focus-within, [data-baseweb="input"] > div:focus-within { box-shadow:0 0 0 3px #147d7326; border-color:var(--cf-teal); }
.stButton button,.stDownloadButton button { border-radius:10px; min-height:42px; font-weight:600; transition:transform .06s ease, box-shadow .15s ease; }
.stButton button:active { transform:translateY(1px); }
.stButton button[kind="primary"] { background:var(--cf-teal); border-color:var(--cf-teal); box-shadow:0 4px 12px #147d7326; }
.stButton button[kind="primary"]:hover { background:var(--cf-teal-dark); border-color:var(--cf-teal-dark); }

/* tabs / segmented */
[data-testid="stTabs"] [role="tablist"] { gap:8px; border-bottom:1px solid var(--cf-line); }
[data-testid="stTabs"] [role="tab"] { border-radius:10px 10px 0 0; padding:10px 18px; font-weight:600; }
[data-testid="stTabs"] [aria-selected="true"] { color:var(--cf-teal); background:var(--cf-mint); }
button[kind="segmented_control"], button[kind="segmented_controlActive"] { border-radius:10px; font-weight:600; min-height:42px; padding:0 18px; }
button[kind="segmented_controlActive"] { background:var(--cf-teal) !important; color:#fff !important; border-color:var(--cf-teal) !important; }
[data-testid="stRadio"] label { font-weight:500; }

.cf-chips { display:flex; flex-wrap:wrap; gap:6px; margin:4px 0 2px; }
.cf-chip { border-radius:999px; padding:3px 11px; font-size:12.5px; font-weight:600; border:1px solid transparent; }
.cf-mint { background:var(--cf-mint); color:var(--cf-teal-dark); border-color:#c9e4d9; }
.cf-amber { background:#fdf0dc; color:#8a5a12; border-color:#f3dbb2; }
.cf-rose { background:#fbe7e4; color:#9a3a30; border-color:#f2c9c3; }
.cf-slate { background:#eef1f0; color:#46605b; border-color:#dde4e1; }

@media(max-width:640px) { .cf-hero { padding:22px 18px; }.cf-hero h1 {font-size:26px;}.cf-steps span {font-size:12px; padding:7px 11px;}.cf-section h2 {font-size:19px;} [data-testid="stMetricValue"] {font-size:1.6rem;} }

/* ---- v14 visual refresh ---- */
.cf-hero { background:linear-gradient(135deg,#0f4c47 0%,#147d73 55%,#2aa190 100%); padding:34px 40px; }
.cf-hero h1 { font-size:34px; }
.cf-steps span b { display:inline-block; background:#ffffff26; border-radius:999px; min-width:26px; text-align:center; margin-right:8px; padding:1px 0; }

/* 匯入區：大型上傳卡 */
.cf-upload-card { background:#fff; border:1px solid var(--cf-line); border-radius:20px; padding:22px 26px 6px; margin:6px 0 14px; box-shadow:var(--cf-shadow); }
.cf-upload-card h3 { margin:0 0 4px; font-size:19px; }
.cf-upload-card p { margin:0 0 10px; color:var(--cf-muted); font-size:14px; }
.cf-flow { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:8px 0 16px; }
.cf-flow div { background:#fff; border:1px solid var(--cf-line); border-radius:16px; padding:16px 18px; box-shadow:var(--cf-shadow); }
.cf-flow div.on { border-color:var(--cf-teal); background:linear-gradient(180deg,#f2faf7,#fff); }
.cf-flow b { display:flex; align-items:center; gap:10px; color:var(--cf-ink); font-size:15px; }
.cf-flow b i { font-style:normal; background:var(--cf-teal); color:#fff; border-radius:9px; width:28px; height:28px; display:inline-flex; align-items:center; justify-content:center; font-size:13px; }
.cf-flow div:not(.on) b i { background:#cfe0d9; color:#47635c; }
.cf-flow span { display:block; margin-top:6px; color:var(--cf-muted); font-size:13px; line-height:1.6; }
[data-testid="stFileUploader"] { border:1.5px dashed #7fbfae; background:linear-gradient(180deg,#f7fcfa,#fff); border-radius:20px; padding:20px 22px; box-shadow:var(--cf-shadow); }
[data-testid="stFileUploader"] section { padding:30px 20px; border-radius:14px; background:#eef8f4; border:0; }
[data-testid="stFileUploader"] section:hover { background:#e2f3ec; }
[data-testid="stFileUploader"] button { background:var(--cf-teal); color:#fff; border:0; min-height:46px; padding:0 26px; font-size:15px; font-weight:700; border-radius:12px; box-shadow:0 6px 16px #147d7338; }
[data-testid="stFileUploader"] button:hover { background:var(--cf-teal-dark); color:#fff; }
[data-testid="stFileUploader"] small { color:var(--cf-muted); }

/* 主要按鈕放大 */
.stButton button[kind="primary"] { min-height:54px; font-size:17px; letter-spacing:.04em; border-radius:14px; background:linear-gradient(135deg,#18968a,#0e665d); box-shadow:0 8px 20px #147d7333; }
.stButton button[kind="primary"]:hover { filter:brightness(1.06); transform:translateY(-1px); }
.stButton button[kind="secondary"] { border-color:#cfe0d9; background:#fff; }
.stButton button[kind="secondary"]:hover { border-color:var(--cf-teal); color:var(--cf-teal-dark); background:#f2faf7; }

/* 狀態列、資料卡 */
.cf-file { display:flex; align-items:center; gap:14px; background:#fff; border:1px solid #bfe0d4; border-left:5px solid var(--cf-teal); border-radius:14px; padding:12px 18px; margin:6px 0 12px; box-shadow:var(--cf-shadow); }
.cf-file b { color:var(--cf-ink); }
.cf-file span { color:var(--cf-muted); font-size:13px; }
.cf-card { background:#fff; border:1px solid var(--cf-line); border-radius:16px; padding:16px 20px; margin:8px 0; box-shadow:var(--cf-shadow); }
.cf-card h4 { margin:0 0 8px; font-size:15px; color:var(--cf-ink); }
.cf-checks { width:100%; border-collapse:collapse; font-size:13.5px; }
.cf-checks th { text-align:left; color:var(--cf-muted); font-weight:600; padding:6px 10px; border-bottom:1px solid var(--cf-line); }
.cf-checks td { padding:7px 10px; border-bottom:1px solid #f0f4f2; vertical-align:top; }
.cf-ok { color:#0e665d; font-weight:700; }.cf-no { color:#9a3a30; font-weight:700; }.cf-warn { color:#8a5a12; font-weight:700; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#e9f3ee,#f4f8f5); }
.cf-section { border-top:0; margin-top:40px; }
.cf-section h2 { font-size:23px; }
@media(max-width:900px) { .cf-flow { grid-template-columns:1fr; } }

/* ---- v19 功能模組 ---- */
[data-testid="stSidebar"] [role="radiogroup"] { gap:4px; }
[data-testid="stSidebar"] [role="radiogroup"] label { width:100%; padding:9px 12px; border-radius:10px; border-left:3px solid transparent; margin:0; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background:#dcece4; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background:#fff; border-left-color:var(--cf-teal); box-shadow:var(--cf-shadow); }
[data-testid="stSidebar"] [role="radiogroup"] label p { font-size:16.5px; font-weight:600; color:#28574e; line-height:1.45; }
[data-testid="stSidebar"] [role="radiogroup"] label { padding:11px 12px; }
.cf-group { font-size:13.5px; font-weight:700; letter-spacing:.12em; color:#4f6f68; margin:14px 0 6px 2px; }
/* 側邊欄字體放大（v19.1） */
section[data-testid="stSidebar"] { min-width:320px; }
[data-testid="stSidebar"] h3 { font-size:19px !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"], [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { font-size:14.5px; line-height:1.65; }
[data-testid="stSidebar"] [data-testid="stExpander"] summary p { font-size:15.5px; }
[data-testid="stSidebar"] [data-testid="stExpander"] p, [data-testid="stSidebar"] [data-testid="stExpander"] label p { font-size:14.5px; }
.cf-module { display:flex; align-items:flex-start; gap:16px; background:#fff; border:1px solid var(--cf-line); border-radius:18px; padding:18px 22px; margin:4px 0 18px; box-shadow:var(--cf-shadow); }
.cf-module .cf-number { font-size:18px; min-width:48px; padding:11px 0; }
.cf-module h2 { font-size:24px; margin:0 0 4px; padding:0; }
.cf-module p { margin:0; color:var(--cf-muted); font-size:14px; line-height:1.7; }
.cf-module .cf-role { display:inline-block; margin-left:10px; vertical-align:middle; font-size:12px; font-weight:700; padding:2px 10px; border-radius:999px; background:var(--cf-mint); color:var(--cf-teal-dark); }
.cf-module .cf-role.mgr { background:#fdf0dc; color:#8a5a12; }
.cf-status { background:#fff; border:1px solid var(--cf-line); border-radius:12px; padding:12px 14px; font-size:14.5px; color:#4f6661; line-height:1.85; }
.cf-status b { color:var(--cf-ink); }
.cf-subhead { font-size:17px; font-weight:700; color:var(--cf-ink); margin:22px 0 6px; padding-left:10px; border-left:4px solid var(--cf-teal); }
/* 分頁切換按鈕（03 的處理項目、臨時異動的事件類型）放大（v19.2） */
button[kind="segmented_control"], button[kind="segmented_controlActive"],
[data-testid="stBaseButton-segmented_control"], [data-testid="stBaseButton-segmented_controlActive"] {
  min-height:52px !important; padding:0 28px !important; border-radius:12px; }
button[kind="segmented_control"] p, button[kind="segmented_controlActive"] p,
[data-testid="stBaseButton-segmented_control"] p, [data-testid="stBaseButton-segmented_controlActive"] p {
  font-size:17.5px !important; font-weight:700 !important; letter-spacing:.02em; }
button[kind="segmented_controlActive"], [data-testid="stBaseButton-segmented_controlActive"] {
  background:var(--cf-teal) !important; color:#fff !important; border-color:var(--cf-teal) !important; }
button[kind="segmented_controlActive"] p, [data-testid="stBaseButton-segmented_controlActive"] p { color:#fff !important; }
[data-testid="stButtonGroup"] { margin:10px 0 6px; }
/* 大型分頁按鈕（v19.3） */
[class*="st-key-cftabs_"] { margin:14px 0 10px; }
[class*="st-key-cftabs_"] .stButton button { min-height:62px !important; border-radius:14px !important; border-width:2px !important; }
[class*="st-key-cftabs_"] .stButton button p { font-size:20px !important; font-weight:700 !important; letter-spacing:.03em; }
[class*="st-key-cftabs_medium"] .stButton button { min-height:52px !important; }
[class*="st-key-cftabs_medium"] .stButton button p { font-size:17.5px !important; }
[class*="st-key-cftabs_"] .stButton button[kind="secondary"] { background:#fff !important; border-color:#bcd9cf !important; color:#28574e !important; box-shadow:var(--cf-shadow); }
[class*="st-key-cftabs_"] .stButton button[kind="secondary"]:hover { border-color:var(--cf-teal) !important; background:#f2faf7 !important; }
[class*="st-key-cftabs_"] .stButton button[kind="primary"] { background:var(--cf-teal) !important; border-color:var(--cf-teal) !important; color:#fff !important; }

/* ---- v19.4 色彩與層次：每個模組一個主色，狀態用顏色區分 ---- */
:root { --cf-acc:#147d73; --cf-acc-soft:#e4f2ec; --cf-acc-ink:#0e4f48;
  --cf-blue:#2f6fb3; --cf-coral:#d0603a; --cf-violet:#6b58b8; --cf-amber:#b7791f;
  --cf-ok:#1f8a5b; --cf-ok-soft:#e5f5ec; --cf-warn:#c2410c; --cf-warn-soft:#fff1e6; --cf-bad:#c03a3a; --cf-bad-soft:#fdecec; }
.stApp { background:radial-gradient(1200px 500px at 100% -10%, var(--cf-acc-soft) 0%, transparent 60%), var(--cf-bg); }
.cf-hero { background:linear-gradient(125deg,#0f5e57 0%,#147d73 45%,#2f6fb3 100%); }
.cf-hero .cf-steps span:nth-child(1) b { background:var(--cf-blue); } .cf-hero .cf-steps span:nth-child(2) b { background:#18a08f; }
.cf-hero .cf-steps span:nth-child(3) b { background:var(--cf-coral); } .cf-hero .cf-steps span:nth-child(4) b { background:var(--cf-violet); }
.cf-hero .cf-steps span:nth-child(5) b { background:var(--cf-amber); }
.cf-bar { border-top:4px solid var(--cf-acc); }
/* 模組頁首：主色色塊＋淡色底 */
.cf-module { border:1px solid color-mix(in srgb, var(--cf-acc) 22%, white); background:linear-gradient(100deg, var(--cf-acc-soft) 0%, #fff 55%); border-left:6px solid var(--cf-acc); }
.cf-module .cf-number { background:var(--cf-acc) !important; color:#fff !important; border-radius:14px; box-shadow:0 6px 14px color-mix(in srgb, var(--cf-acc) 30%, transparent); }
.cf-module h2 { color:var(--cf-acc-ink) !important; }
.cf-module .cf-role { background:#fff; color:var(--cf-acc-ink); border:1px solid color-mix(in srgb, var(--cf-acc) 35%, white); }
.cf-subhead { border-left-color:var(--cf-acc); background:linear-gradient(90deg, var(--cf-acc-soft), transparent 70%); padding:6px 12px; border-radius:0 10px 10px 0; }
/* 側邊欄選單：每個模組的編號顏色 */
[data-testid="stSidebar"] [role="radiogroup"] label:nth-child(1) { --m:var(--cf-blue); }
[data-testid="stSidebar"] [role="radiogroup"] label:nth-child(2) { --m:#147d73; }
[data-testid="stSidebar"] [role="radiogroup"] label:nth-child(3) { --m:var(--cf-coral); }
[data-testid="stSidebar"] [role="radiogroup"] label:nth-child(4) { --m:var(--cf-violet); }
[data-testid="stSidebar"] [role="radiogroup"] label:nth-child(5) { --m:var(--cf-amber); }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { border-left:5px solid var(--m, var(--cf-teal)); background:#fff; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p { color:var(--m, var(--cf-teal)) !important; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background:color-mix(in srgb, var(--m, #147d73) 10%, white); }
/* 指標卡：上緣色條輪替，數字用同色 */
[data-testid="stColumn"]:nth-child(5n+1) [data-testid="stMetric"] { --k:#147d73; }
[data-testid="stColumn"]:nth-child(5n+2) [data-testid="stMetric"] { --k:var(--cf-blue); }
[data-testid="stColumn"]:nth-child(5n+3) [data-testid="stMetric"] { --k:var(--cf-coral); }
[data-testid="stColumn"]:nth-child(5n+4) [data-testid="stMetric"] { --k:var(--cf-violet); }
[data-testid="stColumn"]:nth-child(5n+5) [data-testid="stMetric"] { --k:var(--cf-amber); }
[data-testid="stMetric"] { background-image:linear-gradient(var(--k,#147d73),var(--k,#147d73)); background-size:100% 4px; }
[data-testid="stMetricValue"] { color:var(--k,#147d73); }
/* 提示框：左側色條＋淡底，一眼分出成功／注意／錯誤／說明 */
[data-testid="stAlert"] { border:0; border-left:5px solid #9bb5ae; }
[data-testid="stAlertContentSuccess"], [data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) { border-left-color:var(--cf-ok); }
[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) { border-left-color:#e08a1e; }
[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) { border-left-color:var(--cf-bad); }
[data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]) { border-left-color:var(--cf-blue); }
/* 表格外框用模組主色淡線 */
[data-testid="stDataFrame"] { border-color:color-mix(in srgb, var(--cf-acc) 25%, white); }
/* 大型分頁按鈕：選中用模組主色 */
[class*="st-key-cftabs_"] .stButton button[kind="primary"] { background:var(--cf-acc) !important; border-color:var(--cf-acc) !important;
  box-shadow:0 6px 16px color-mix(in srgb, var(--cf-acc) 30%, transparent) !important; }
[class*="st-key-cftabs_"] .stButton button[kind="secondary"]:hover { border-color:var(--cf-acc) !important; background:var(--cf-acc-soft) !important; }
[data-testid="stTabs"] [aria-selected="true"] { color:var(--cf-acc-ink); background:var(--cf-acc-soft); }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background:var(--cf-acc); }
/* 引導卡（02 → 03 等下一步提示） */
.cf-guide-card { border-radius:14px; padding:14px 18px; margin:6px 0 10px; background:#fff; border:1px solid var(--cf-line); border-left:6px solid var(--cf-teal); box-shadow:var(--cf-shadow); }
.cf-guide-card.cf-guide-warn { background:linear-gradient(100deg,#fff1e6,#fff 70%); border-left-color:var(--cf-coral); }
.cf-guide-card.cf-guide-ok { background:linear-gradient(100deg,var(--cf-ok-soft),#fff 70%); border-left-color:var(--cf-ok); }
.cf-guide-title { font-size:17px; font-weight:700; color:var(--cf-ink); margin-bottom:4px; }
.cf-guide-body { font-size:14.5px; color:#4f6661; line-height:1.75; }
/* LINE 派案訊息原文（示範） */
.cf-line { background:#8cabd9; background:linear-gradient(180deg,#9bb6dd,#8aa9d6); border-radius:16px; padding:14px 16px 18px; margin:6px 0 10px; }
.cf-line-head { color:#fff; font-size:13px; font-weight:700; letter-spacing:.04em; margin-bottom:10px; opacity:.95; }
.cf-line-bubble { position:relative; display:inline-block; max-width:min(560px,100%); background:#fff; color:#1f2b2a; border-radius:18px; padding:12px 16px;
  font-size:15px; line-height:1.75; white-space:pre-wrap; box-shadow:0 2px 6px rgba(0,0,0,.12); margin-left:10px; }
.cf-line-bubble:before { content:""; position:absolute; left:-7px; top:12px; border-width:7px 10px 7px 0; border-style:solid; border-color:transparent #fff transparent transparent; }
/* 主畫面單選選項與欄位標題放大（v19.6）：只針對單選與輸入欄標題，不動指標數字、按鈕與一般文字 */
[data-testid="stMain"] [role="radiogroup"] label [data-testid="stMarkdownContainer"] p { font-size:17px !important; line-height:1.6; }
[data-testid="stMain"] [role="radiogroup"] { gap:6px; }
[data-testid="stMain"] [data-testid="stNumberInput"] [data-testid="stWidgetLabel"] p,
[data-testid="stMain"] [data-testid="stDateInput"] [data-testid="stWidgetLabel"] p,
[data-testid="stMain"] [data-testid="stSelectbox"] [data-testid="stWidgetLabel"] p { font-size:16px !important; font-weight:600; }
</style>
"""

FONT_SCALES = {'標準': 1.0, '大': 1.12, '特大': 1.25}

# 最後一層修正（必須放在所有樣式之後）：
# 1. 按鈕所有狀態（hover／按下／focus／停用）都明確指定底色與字色——Streamlit 預設「按下」會把字變白、
#    「focus」會換字色，和我們的白底覆寫衝突，造成按下後看不到字。
# 2. 按鈕內文字 <p> 明確指定顏色：[data-testid="stMain"] p 的全域字色會蓋過按鈕繼承的白字，造成深底深字。
# 3. 重跑時 Streamlit 會把舊畫面淡化成 33% 透明（stale），看起來像「反白」；改成維持原樣。
# 4. Streamlit 頂部固定列（約 3.75rem）會蓋住頁首，主內容往下讓出空間。
FIX_CSS = """
<style>
/* ---- 頂部固定列不再擋住頁首 ---- */
[data-testid="stHeader"]{ background:var(--cf-bg) !important; border-bottom:1px solid var(--cf-line); height:3.5rem; }
[data-testid="stMainBlockContainer"]{ padding-top:calc(3.5rem + 14px) !important; }
[data-testid="stSidebarHeader"]{ height:3.5rem; }

/* ---- 重跑期間不要把畫面淡化 ---- */
[data-stale="true"], .stale-element, [data-testid="stElementContainer"][data-stale="true"]{ opacity:1 !important; filter:none !important; }

/* ---- 主要按鈕：深藍底＋白字，所有狀態一致 ---- */
.stButton button[kind^="primary"], .stDownloadButton button[kind^="primary"], .stFormSubmitButton button[kind^="primary"],
button[data-testid^="stBaseButton-primary"]{
  background:var(--cf-primary) !important; border:2px solid var(--cf-primary) !important; color:#FFFFFF !important; }
.stButton button[kind^="primary"]:hover, .stDownloadButton button[kind^="primary"]:hover, .stFormSubmitButton button[kind^="primary"]:hover,
button[data-testid^="stBaseButton-primary"]:hover,
.stButton button[kind^="primary"]:active, .stDownloadButton button[kind^="primary"]:active, .stFormSubmitButton button[kind^="primary"]:active,
button[data-testid^="stBaseButton-primary"]:active{
  background:var(--cf-primary-ink) !important; border-color:var(--cf-primary-ink) !important; color:#FFFFFF !important; }
.stButton button[kind^="primary"]:focus, .stDownloadButton button[kind^="primary"]:focus, .stFormSubmitButton button[kind^="primary"]:focus,
button[data-testid^="stBaseButton-primary"]:focus{ color:#FFFFFF !important; }
.stButton button[kind^="primary"] p, .stDownloadButton button[kind^="primary"] p, .stFormSubmitButton button[kind^="primary"] p,
button[data-testid^="stBaseButton-primary"] p{ color:#FFFFFF !important; }

/* ---- 次要按鈕：白底＋深字；按下時淡藍底＋深藍字（不再變白字） ---- */
.stButton button[kind^="secondary"], .stDownloadButton button[kind^="secondary"], .stFormSubmitButton button[kind^="secondary"],
button[data-testid^="stBaseButton-secondary"]{
  background:#FFFFFF !important; border:2px solid var(--cf-line-2) !important; color:var(--cf-ink) !important; }
.stButton button[kind^="secondary"] p, .stDownloadButton button[kind^="secondary"] p, .stFormSubmitButton button[kind^="secondary"] p,
button[data-testid^="stBaseButton-secondary"] p{ color:var(--cf-ink) !important; }
.stButton button[kind^="secondary"]:hover, .stDownloadButton button[kind^="secondary"]:hover, .stFormSubmitButton button[kind^="secondary"]:hover,
button[data-testid^="stBaseButton-secondary"]:hover{
  background:#F3F8FA !important; border-color:var(--cf-primary) !important; color:var(--cf-primary-ink) !important; }
.stButton button[kind^="secondary"]:active, .stDownloadButton button[kind^="secondary"]:active, .stFormSubmitButton button[kind^="secondary"]:active,
button[data-testid^="stBaseButton-secondary"]:active,
.stButton button[kind^="secondary"]:focus:not(:active), .stDownloadButton button[kind^="secondary"]:focus:not(:active),
button[data-testid^="stBaseButton-secondary"]:focus:not(:active){
  background:var(--cf-primary-soft) !important; border-color:var(--cf-primary) !important; color:var(--cf-primary-ink) !important; }
.stButton button[kind^="secondary"]:hover p, .stButton button[kind^="secondary"]:active p, .stButton button[kind^="secondary"]:focus p,
.stDownloadButton button[kind^="secondary"]:hover p, .stDownloadButton button[kind^="secondary"]:active p, .stDownloadButton button[kind^="secondary"]:focus p,
button[data-testid^="stBaseButton-secondary"]:hover p, button[data-testid^="stBaseButton-secondary"]:active p,
button[data-testid^="stBaseButton-secondary"]:focus p{ color:var(--cf-primary-ink) !important; }

/* ---- 停用按鈕：灰底灰字，但仍看得清楚 ---- */
.stButton button:disabled, .stDownloadButton button:disabled, .stFormSubmitButton button:disabled{
  background:#EFE8DD !important; border-color:#E0D5C4 !important; color:#7A6C5F !important; opacity:1 !important; }
.stButton button:disabled p, .stDownloadButton button:disabled p, .stFormSubmitButton button:disabled p{ color:#7A6C5F !important; }

/* ---- 檔案上傳按鈕 ---- */
[data-testid="stFileUploader"] button, [data-testid="stFileUploader"] button:hover,
[data-testid="stFileUploader"] button:active, [data-testid="stFileUploader"] button:focus{
  background:var(--cf-primary) !important; border-color:var(--cf-primary) !important; color:#FFFFFF !important; }
[data-testid="stFileUploader"] button:hover, [data-testid="stFileUploader"] button:active{ background:var(--cf-primary-ink) !important; }
[data-testid="stFileUploader"] button p, [data-testid="stFileUploader"] button span{ color:#FFFFFF !important; }

/* ---- 分段選擇（字體大小、分頁切換） ---- */
button[kind="segmented_control"], [data-testid="stBaseButton-segmented_control"]{ background:#FFFFFF !important; color:var(--cf-ink) !important; }
button[kind="segmented_control"] p, [data-testid="stBaseButton-segmented_control"] p{ color:var(--cf-ink) !important; }
button[kind="segmented_control"]:hover, [data-testid="stBaseButton-segmented_control"]:hover,
button[kind="segmented_control"]:active, [data-testid="stBaseButton-segmented_control"]:active{ background:var(--cf-primary-soft) !important; }
button[kind="segmented_controlActive"], [data-testid="stBaseButton-segmented_controlActive"],
button[kind="segmented_controlActive"]:hover, button[kind="segmented_controlActive"]:active, button[kind="segmented_controlActive"]:focus{
  background:var(--cf-primary) !important; border-color:var(--cf-primary) !important; color:#FFFFFF !important; }

/* ---- 以下為特定按鈕群組，必須放在通用規則之後 ---- */
/* 1→5 步驟導引：未完成＝白底灰字；已完成＝實心綠底白字；目前＝深藍底白字＋外框 */
[class*="st-key-cfstep_"] .stButton button, [class*="st-key-cfstep_"] .stButton button:hover,
[class*="st-key-cfstep_"] .stButton button:active, [class*="st-key-cfstep_"] .stButton button:focus{
  background:#FFFFFF !important; border:2px solid var(--cf-line-2) !important; }
[class*="st-key-cfstep_"] .stButton button p{ color:#5A4D42 !important; }
[class*="st-key-cfstep_"] .stButton button:hover{ border-color:var(--cf-primary) !important; background:#F3F8FA !important; }
[class*="st-key-cfstep_done"] .stButton button, [class*="st-key-cfstep_done"] .stButton button:hover,
[class*="st-key-cfstep_done"] .stButton button:active, [class*="st-key-cfstep_done"] .stButton button:focus{
  background:#2F7A4F !important; border-color:#2F7A4F !important; }
[class*="st-key-cfstep_done"] .stButton button:hover{ background:#246140 !important; border-color:#246140 !important; }
[class*="st-key-cfstep_done"] .stButton button p{ color:#FFFFFF !important; }
[class*="st-key-cfstep_now"] .stButton button, [class*="st-key-cfstep_now"] .stButton button:hover,
[class*="st-key-cfstep_now"] .stButton button:active, [class*="st-key-cfstep_now"] .stButton button:focus{
  background:var(--cf-primary) !important; border-color:var(--cf-primary) !important; box-shadow:0 0 0 5px #BFD7E2 !important; }
[class*="st-key-cfstep_now"] .stButton button p{ color:#FFFFFF !important; font-weight:900 !important; }
/* 大型分頁按鈕 */
[class*="st-key-cftabs_"] .stButton button[kind="primary"], [class*="st-key-cftabs_"] .stButton button[kind="primary"]:hover,
[class*="st-key-cftabs_"] .stButton button[kind="primary"]:active{ background:var(--cf-acc) !important; border-color:var(--cf-acc) !important; }
/* AI 專屬按鈕（靛藍） */
[class*="st-key-cfai"] .stButton button, [class*="st-key-cfai"] .stButton button:hover,
[class*="st-key-cfai"] .stButton button:active, [class*="st-key-cfai"] .stButton button:focus{
  background:var(--cf-ai-1) !important; border-color:var(--cf-ai-1) !important; color:#FFFFFF !important; }
[class*="st-key-cfai"] .stButton button:hover, [class*="st-key-cfai"] .stButton button:active{ background:#3730A3 !important; border-color:#3730A3 !important; }
[class*="st-key-cfai"] .stButton button p{ color:#FFFFFF !important; }
</style>
"""


def inject_css(scale=1.12):
    """全站樣式：舊版樣式表＋ v2026.11 Design System＋方案 C「暖心大字」覆寫層＋最後修正層（每次重跑都要注入一次）。
    scale：字體倍率（標準 1.0／大 1.12／特大 1.25），所有字級都以 calc(px × --cf-s) 計算。"""
    st.markdown(CSS + DESIGN_CSS + WARM_CSS + FIX_CSS + f'<style>:root{{--cf-s:{float(scale):.3f};}}</style>', unsafe_allow_html=True)


def render_header(ai_ready=True, ai_text=None, privacy_on=True, version='v2026.10', scale=1.12):
    """全域頂部輕量 Header（方案 C：圓形 Logo、白話狀態）。"""
    from html import escape
    inject_css(scale)
    ai_cls = 'ok' if ai_ready else 'warn'
    ai_label = ai_text or ('AI 系統已就緒' if ai_ready else 'AI 系統準備中')
    privacy = '個資已遮蔽' if privacy_on else '個資未遮蔽'
    st.markdown(
        '<header class="cf-header" role="banner">'
        f'<div class="cf-brand">{LOGO_ROUND_SVG}<div><b>HomeCare AI 居服排班</b>'
        '<span>AI 居家照護智慧排班</span></div></div>'
        '<div class="cf-header-status" aria-label="系統狀態">'
        f'<span class="cf-pill {ai_cls}"><i></i>{escape(ai_label)}</span>'
        f'<span class="cf-pill {"ok" if privacy_on else "warn"}">{escape(privacy)}</span>'
        f'<span class="cf-pill ver">{escape(version)}</span>'
        '</div></header>', unsafe_allow_html=True)


def render_brand(build=None, compact=False):
    """相容舊呼叫：改畫輕量 Header。"""
    render_header()


def chips(items, tone='mint'):
    """小標籤列（只顯示文字，不含任何個資）。tone：mint／amber／rose／slate。"""
    from html import escape
    items = [str(x) for x in (items or []) if str(x).strip()]
    if items:
        st.markdown('<div class="cf-chips">' + ''.join(f'<span class="cf-chip cf-{escape(tone)}">{escape(x)}</span>' for x in items) + '</div>', unsafe_allow_html=True)

def section_title(anchor, number, title, description):
    from html import escape
    st.markdown(f'<div id="{escape(anchor)}" class="cf-section"><span class="cf-number">{escape(number)}</span><div><h2>{escape(title)}</h2><p>{escape(description)}</p></div></div>', unsafe_allow_html=True)

def render_summary(caregivers, clients, tasks):
    cols = st.columns(3)
    for col, label, value in zip(cols, ['居服員', '服務個案', '待排服務'], [caregivers, clients, tasks]):
        col.metric(label, f'{value:,}')


def flow_cards(active=1):
    """匯入前的三步驟說明卡。active：目前所在步驟 1～3。"""
    items = [('1', '上傳 Excel', '機構資料（員工、個案、週服務計畫、Service_code）一份檔案即可。'),
             ('2', '選擇排班期間', '預設整個月；可改一年或自訂日期。'),
             ('3', '按「開始排班」', '系統先排固定週型，再延展到整個期間。')]
    html = ''.join(f'<div class="{"on" if int(n) <= active else ""}"><b><i>{n}</i>{t}</b><span>{d}</span></div>' for n, t, d in items)
    st.markdown(f'<div class="cf-flow">{html}</div>', unsafe_allow_html=True)

def file_status(name, caregivers, clients, tasks):
    from html import escape
    st.markdown(f'<div class="cf-file"><div style="font-size:24px">✅</div><div><b>{escape(str(name))}</b><br><span>已讀取 {caregivers:,} 位居服員 · {clients:,} 位個案 · {tasks:,} 筆服務</span></div></div>', unsafe_allow_html=True)


# ---------- 功能模組 ----------
# (代碼, 編號, 名稱, 本頁任務, 主要使用者)
MODULES = [
    ('import', '01', '資料匯入與排班設定', 'Excel 匯入、排班期間、交通方式、排班規則及限制條件；確認資料無誤後再進入排班。', '居督'),
    ('schedule', '02', '智慧排班作業', 'AI 自動排班、個案與居服員媒合、候選人推薦、人工調整及日曆班表。', '居督'),
    ('issues', '03', '衝突與異常處理（含 LINE 解析）', '集中處理班次重疊、轉場不足、未成功派班、條件不符、臨時異動與替代方案。', '居督'),
    ('review', '04', '排班結果與覆核', '排班完成率、已排與未排班次、警示案件、人工覆寫紀錄、最終班表及匯出。', '居督'),
    ('analytics', '05', '人力與效益分析', '排班效益、需求熱圖與 AI 增聘／調派建議；居服員工時、負荷分布、轉場時間、人力配置、服務產出與營運效益。', '主管'),
    ('accounts', '👥', '帳號管理', '新增帳號、重設密碼、停用帳號，並查看登入與帳號異動的存取稽核紀錄；只有主管可以進入。', '主管'),
]
MODULE_KEYS = [m[0] for m in MODULES]
_MODULE_INFO = {m[0]: m for m in MODULES}


def module_label(key, badge=None):
    """側邊欄選單文字，例如「03　衝突與異常處理 · 2」。"""
    _, number, title, _, role = _MODULE_INFO[key]
    text = f'{number}　{title}'
    return text + (f'　· {badge}' if badge else '')


# 每個模組的主色（主色, 淡底, 深字）：頁首、小節標題、分頁按鈕、表格外框都跟著換色。
MODULE_COLORS = {   # 方案 C「暖心大字」：全站統一深藍綠主色
    'import': ('#1F5F7A', '#E3EEF3', '#143F52'),
    'schedule': ('#1F5F7A', '#E3EEF3', '#143F52'),
    'issues': ('#1F5F7A', '#E3EEF3', '#143F52'),
    'review': ('#1F5F7A', '#E3EEF3', '#143F52'),
    'analytics': ('#1F5F7A', '#E3EEF3', '#143F52'),
    'accounts': ('#1F5F7A', '#E3EEF3', '#143F52'),
}


def module_header(key):
    """模組頁首：編號、名稱、本頁任務與主要使用者。"""
    from html import escape
    _, number, title, purpose, role = _MODULE_INFO[key]
    acc, soft, ink = MODULE_COLORS.get(key, MODULE_COLORS['schedule'])
    st.markdown(f'<style>:root{{--cf-acc:{acc};--cf-acc-soft:{soft};--cf-acc-ink:{ink};}}</style>', unsafe_allow_html=True)
    role_html = f'<span class="cf-role{" mgr" if role == "主管" else ""}">{escape(role)}</span>'
    st.markdown(f'<div id="module-{escape(key)}" class="cf-module"><span class="cf-number">{escape(number)}</span>'
                f'<div><h2>{escape(title)}{role_html}</h2><p>{escape(purpose)}</p></div></div>', unsafe_allow_html=True)


def subhead(text):
    """模組內的小節標題。"""
    from html import escape
    st.markdown(f'<div class="cf-subhead">{escape(text)}</div>', unsafe_allow_html=True)


def go_to_module(key):
    """按鈕回呼：切換功能模組（回呼在畫面重跑前執行，可直接改選單狀態）。"""
    st.session_state['cf_module'] = key


def module_nav_buttons(current, prefix='nav'):
    """頁尾的上一步／下一步，依排班流程前往相鄰模組。"""
    index = MODULE_KEYS.index(current)
    left, _, right = st.columns([1, 2, 1])
    if index > 0:
        prev = MODULE_KEYS[index - 1]
        left.button('← ' + module_label(prev), key=f'{prefix}_prev_{current}', on_click=go_to_module, args=(prev,), width='stretch')
    if index < len(MODULE_KEYS) - 1:
        nxt = MODULE_KEYS[index + 1]
        right.button(module_label(nxt) + ' →', key=f'{prefix}_next_{current}', on_click=go_to_module, args=(nxt,), width='stretch')


def empty_module(key, message, target='schedule', button='前往「02 智慧排班作業」'):
    """尚無資料或尚未排班時的空白狀態。"""
    from html import escape
    st.markdown(f'<div class="cf-empty"><span>🗂️</span><h3>{escape(_MODULE_INFO[key][2])}</h3><p>{escape(message)}</p></div>',
                unsafe_allow_html=True)
    if target:
        st.button(button, key=f'empty_go_{key}', on_click=go_to_module, args=(target,), type='primary', width='stretch')


def _pick_tab(key, value):
    st.session_state[key] = value


def big_tabs(options, key, icons=None, size='large', suffixes=None):
    """大型分頁按鈕：比 segmented control 明顯，選中的一顆為深綠底白字。回傳目前選項。
    suffixes：每顆按鈕標籤後面的小計（例如「6 案」），只影響顯示，不影響回傳的選項值。"""
    options = list(options)
    if st.session_state.get(key) not in options:
        st.session_state[key] = options[0]
    current = st.session_state[key]
    with st.container(key=f'cftabs_{size}_{key}'):
        cols = st.columns(len(options))
        for i, (col, option) in enumerate(zip(cols, options)):
            label = (f'{icons[i]}  ' if icons and i < len(icons) else '') + option
            if suffixes and i < len(suffixes) and suffixes[i]:
                label += f'　· {suffixes[i]}'
            col.button(label, key=f'{key}__tab{i}', type='primary' if option == current else 'secondary',
                       on_click=_pick_tab, args=(key, option), width='stretch')
    return current


# ---------- 修改班表原因（處長指定：選單＋其他需補充說明，方便統計） ----------
CHANGE_REASONS = ['交通／時間銜接不足', '案家要求改時間', '案家要求換人', '居服員請假或臨時不可',
                  '資格證照不符', '工時或加班超限', '其他（需補充說明）']
OTHER_REASON = CHANGE_REASONS[-1]


def compose_reason(category, note=''):
    """選單類別＋補充說明 → 寫入紀錄的原因文字；選「其他」卻沒寫說明時回傳 None。"""
    note = str(note or '').strip()
    if not category:
        return None
    if category == OTHER_REASON:
        return f'其他：{note}' if note else None
    return f'{category}｜{note}' if note else category


def reason_category(text):
    """從原因文字取回統計用類別；舊紀錄（自由輸入）歸為「其他」。"""
    text = str(text or '').strip()
    for category in CHANGE_REASONS[:-1]:
        if text.startswith(category):
            return category
    if text.startswith('車程／交通因素'):
        return '交通／時間銜接不足'
    return '其他'


def reason_picker(key, label='修改原因（必選）', default=None, container=None):
    """原因選單＋補充說明。回傳組好的原因文字，未完成時回傳 None。"""
    box = container or st
    index = CHANGE_REASONS.index(default) if default in CHANGE_REASONS else None
    category = box.selectbox(label, CHANGE_REASONS, index=index, placeholder='請選擇原因', key=key + '_cat')
    other = category == OTHER_REASON
    note = box.text_input('補充說明（必填）' if other else '補充說明（選填）', key=key + '_note',
                          placeholder='請寫明原因' if other else '可補充細節，例如：案家要求改到下午')
    return compose_reason(category, note)


REASON_HINT = '請選擇修改原因；選「其他」時要填寫補充說明。'


# =====================================================================
# v2026.11 Design System
#   主色：深翡翠綠 #006A4E／湖水綠 #0F766E
#   AI 專屬：紫藍漸層 #6366F1 → #8B5CF6（只用在 AI 功能按鈕與 Badge）
#   警示：琥珀橘 #F59E0B／胭脂紅 #EF4444
#   背景 #F8FAFC、卡片 #FFFFFF、圓角 12～16px、微陰影
#   無障礙：關鍵數據 ≥ 38px（約 28pt）、標題 ≥ 24px（18pt）、內文 18px；文字對比皆 ≥ 4.5:1
# 以下樣式疊在舊樣式之後，同名規則以這裡為準。
# =====================================================================
LOGO_SVG = ('<svg class="cf-logo" viewBox="0 0 40 40" width="40" height="40" aria-hidden="true">'
            '<rect width="40" height="40" rx="11" fill="#006A4E"/>'
            '<path d="M12 25c0-8 6-13 16-13-1 9-6 15-13 15-1 0-2 0-3-.4" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/>'
            '<path d="M13 27c3-4 6-7 10-9" fill="none" stroke="#A7F3D0" stroke-width="2.4" stroke-linecap="round"/></svg>')

DESIGN_CSS = """
<style>
:root{
  --cf-primary:#006A4E; --cf-primary-2:#0F766E; --cf-primary-soft:#ECFDF5; --cf-primary-ink:#064E3B;
  --cf-ai-1:#6366F1; --cf-ai-2:#8B5CF6; --cf-ai-soft:#EEF2FF; --cf-gold:#F5B700;
  --cf-amber:#F59E0B; --cf-amber-soft:#FFFBEB; --cf-amber-ink:#92400E;
  --cf-red:#EF4444; --cf-red-soft:#FEF2F2; --cf-red-ink:#B91C1C;
  --cf-bg:#F8FAFC; --cf-card:#FFFFFF; --cf-ink:#0F172A; --cf-text:#1E293B; --cf-muted:#475569; --cf-line:#E2E8F0;
  --cf-radius:14px; --cf-shadow:0 1px 2px rgba(15,23,42,.06),0 6px 20px rgba(15,23,42,.06);
  --cf-fs-body:18px; --cf-fs-small:16px; --cf-fs-title:24px; --cf-fs-kpi:38px;
  /* 舊變數改指向新色票，舊元件自動換色 */
  --cf-teal:#006A4E; --cf-teal-dark:#064E3B; --cf-mint:#ECFDF5; --cf-acc:#006A4E; --cf-acc-soft:#ECFDF5; --cf-acc-ink:#064E3B;
}
.stApp{ background:var(--cf-bg) !important; color:var(--cf-text); }
[data-testid="stMainBlockContainer"]{ padding-top:1rem; }
[data-testid="stMain"] p, [data-testid="stMain"] li, [data-testid="stMain"] [data-testid="stMarkdownContainer"]{ font-size:var(--cf-fs-body); line-height:1.7; }
[data-testid="stMain"] [data-testid="stCaptionContainer"], [data-testid="stMain"] [data-testid="stCaptionContainer"] p{ font-size:var(--cf-fs-small); color:var(--cf-muted); }
[data-testid="stMain"] [data-testid="stWidgetLabel"] p{ font-size:17px !important; font-weight:600; color:var(--cf-text); }
h1,h2,h3,h4{ color:var(--cf-ink); }
:focus-visible{ outline:3px solid var(--cf-ai-1) !important; outline-offset:2px; }

/* ---------- 全域 Header ---------- */
.cf-hero{ display:none !important; }
.cf-header{ display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;
  background:var(--cf-card); border:1px solid var(--cf-line); border-radius:16px; padding:12px 20px; margin:0 0 18px; box-shadow:var(--cf-shadow); }
.cf-brand{ display:flex; align-items:center; gap:12px; }
.cf-brand b{ display:block; font-size:22px; color:var(--cf-ink); letter-spacing:.01em; line-height:1.25; }
.cf-brand span{ display:block; font-size:14px; color:var(--cf-muted); }
.cf-header-status{ display:flex; gap:8px; flex-wrap:wrap; }
.cf-pill{ display:inline-flex; align-items:center; gap:8px; border-radius:999px; padding:7px 14px; font-size:15px; font-weight:600;
  background:#F1F5F9; color:var(--cf-text); border:1px solid var(--cf-line); }
.cf-pill i{ width:10px; height:10px; border-radius:50%; background:#94A3B8; display:inline-block; }
.cf-pill.ok{ background:var(--cf-primary-soft); color:var(--cf-primary-ink); border-color:#A7F3D0; }
.cf-pill.ok i{ background:#10B981; box-shadow:0 0 0 4px #10B98126; }
.cf-pill.warn{ background:var(--cf-amber-soft); color:var(--cf-amber-ink); border-color:#FDE68A; }
.cf-pill.warn i{ background:var(--cf-amber); animation:cfpulse 1.4s ease-in-out infinite; }
.cf-pill.ver{ font-family:ui-monospace,Consolas,monospace; }
@keyframes cfpulse{ 50%{ opacity:.35; } }

/* ---------- 側邊選單 ---------- */
[data-testid="stSidebar"]{ background:#FFFFFF !important; border-right:1px solid var(--cf-line); }
[data-testid="stSidebar"] [role="radiogroup"] label{ --m:var(--cf-primary) !important; border-radius:12px; padding:12px 12px; }
[data-testid="stSidebar"] [role="radiogroup"] label p{ font-size:17px !important; color:var(--cf-text) !important; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover{ background:var(--cf-primary-soft) !important; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){ background:var(--cf-primary-soft) !important; border-left:5px solid var(--cf-primary) !important; box-shadow:none; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p{ color:var(--cf-primary-ink) !important; font-weight:700 !important; }
.cf-side-brand{ display:flex; align-items:center; gap:10px; margin:4px 0 6px; }
.cf-side-brand b{ font-size:19px; color:var(--cf-ink); }
.cf-side-brand .cf-logo{ width:34px; height:34px; }

/* ---------- 卡片、模組頁首 ---------- */
.cf-module{ background:var(--cf-card) !important; border:1px solid var(--cf-line) !important; border-left:6px solid var(--cf-primary) !important; border-radius:16px; }
.cf-module h2{ font-size:var(--cf-fs-title) !important; color:var(--cf-ink) !important; }
.cf-module p{ font-size:16px !important; color:var(--cf-muted) !important; }
.cf-module .cf-number{ background:var(--cf-primary) !important; }
.cf-subhead{ font-size:21px !important; color:var(--cf-ink) !important; border-left:5px solid var(--cf-primary) !important; background:none !important; padding:2px 12px !important; margin:28px 0 10px !important; }
[data-testid="stVerticalBlockBorderWrapper"]{ border-radius:var(--cf-radius) !important; }
[data-testid="stExpander"]{ border-radius:var(--cf-radius) !important; border-color:var(--cf-line) !important; }
[data-testid="stExpander"] summary p{ font-size:17px !important; font-weight:600; }
[data-testid="stAlert"]{ border-radius:12px !important; }
[data-testid="stAlert"] p{ font-size:17px !important; }

/* st.metric：數字與標籤分行、不截斷 */
[data-testid="stMetric"]{ background:var(--cf-card) !important; background-image:none !important; border:1px solid var(--cf-line); border-radius:16px; box-shadow:var(--cf-shadow); }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] > div{ color:var(--cf-ink) !important; font-size:32px !important; white-space:normal !important; overflow:visible !important; text-overflow:clip !important; line-height:1.2; }
[data-testid="stMetricLabel"] p{ font-size:16px !important; color:var(--cf-muted) !important; white-space:normal !important; }

/* ---------- 按鈕 ---------- */
.stButton button, .stDownloadButton button{ min-height:48px; border-radius:12px; font-size:17px; }
.stButton button p, .stDownloadButton button p{ font-size:17px; font-weight:700; }
.stButton button[kind="primary"]{ background:var(--cf-primary) !important; border-color:var(--cf-primary) !important; box-shadow:0 6px 16px #006A4E33 !important; }
.stButton button[kind="primary"]:hover{ background:var(--cf-primary-ink) !important; }
/* AI 專屬按鈕：容器 key 以 cfai 開頭 */
[class*="st-key-cfai"] .stButton button, [class*="st-key-cfai"] button[kind]{
  background:linear-gradient(135deg,var(--cf-ai-1),var(--cf-ai-2)) !important; color:#fff !important; border:0 !important;
  box-shadow:0 10px 24px rgba(99,102,241,.35) !important; min-height:56px; position:relative; overflow:hidden; }
[class*="st-key-cfai"] button p{ color:#fff !important; font-size:18px !important; font-weight:800 !important; letter-spacing:.02em; }
[class*="st-key-cfai"] button:hover{ filter:brightness(1.07); transform:translateY(-1px); }
[class*="st-key-cfai"] button:after{ content:""; position:absolute; top:0; left:-60%; width:40%; height:100%;
  background:linear-gradient(100deg,transparent,rgba(255,255,255,.35),transparent); animation:cfshine 3.2s ease-in-out infinite; }
@keyframes cfshine{ 0%{ left:-60%; } 60%,100%{ left:130%; } }
[class*="st-key-cfai_xl"] button{ min-height:88px !important; border-radius:18px !important; }
[class*="st-key-cfai_xl"] button p{ font-size:24px !important; }
@media (prefers-reduced-motion:reduce){ [class*="st-key-cfai"] button:after, .cf-pill.warn i{ animation:none; } }

/* ---------- 01 特大拖曳區 ---------- */
[class*="st-key-cf_dropzone"] [data-testid="stFileUploader"]{ background:transparent !important; border:0 !important; box-shadow:none !important; padding:0 !important; }
[class*="st-key-cf_dropzone"] [data-testid="stFileUploaderDropzone"]{
  min-height:240px; border:3px dashed #5EADA2 !important; border-radius:20px !important; background:#F0FDFA !important;
  display:flex; flex-direction:column; justify-content:center; align-items:center; gap:14px; text-align:center; padding:28px !important; }
[class*="st-key-cf_dropzone"] [data-testid="stFileUploaderDropzone"]:hover{ background:#E6FFFA !important; border-color:var(--cf-primary-2) !important; }
[class*="st-key-cf_dropzone"] [data-testid="stFileUploaderDropzone"]::before{
  content:"📥  將照護需求 Excel 檔案拖曳至此"; display:block; font-size:26px; font-weight:800; color:var(--cf-primary-ink); }
[class*="st-key-cf_dropzone"] [data-testid="stFileUploaderDropzoneInstructions"] span,
[class*="st-key-cf_dropzone"] [data-testid="stFileUploaderDropzoneInstructions"] small{ font-size:16px !important; color:var(--cf-muted) !important; }
[class*="st-key-cf_dropzone"] [data-testid="stFileUploaderDropzone"] button{ background:var(--cf-primary) !important; color:#fff !important; min-height:50px; padding:0 30px; border-radius:12px; font-size:17px; }

/* ---------- 3 連狀態卡、KPI 卡 ---------- */
.cf-ready{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; margin:14px 0 18px; }
.cf-ready > div{ display:flex; align-items:center; gap:14px; background:var(--cf-card); border:1px solid var(--cf-line); border-radius:16px; padding:18px 20px; box-shadow:var(--cf-shadow);
  animation:cfpop .45s cubic-bezier(.2,.9,.3,1.2) both; }
.cf-ready > div:nth-child(2){ animation-delay:.12s; } .cf-ready > div:nth-child(3){ animation-delay:.24s; }
.cf-ready .ic{ flex:none; width:46px; height:46px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:24px; font-weight:800;
  background:var(--cf-primary-soft); color:var(--cf-primary); }
.cf-ready .warn .ic, .cf-ready > div.warn .ic{ background:var(--cf-amber-soft); color:var(--cf-amber-ink); }
.cf-ready b{ display:block; font-size:21px; color:var(--cf-ink); line-height:1.3; }
.cf-ready span{ display:block; font-size:15px; color:var(--cf-muted); margin-top:2px; }
@keyframes cfpop{ from{ opacity:0; transform:translateY(8px) scale(.97); } to{ opacity:1; transform:none; } }

.cf-kpis{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; margin:8px 0 12px; }
.cf-kpi{ background:var(--cf-card); border:1px solid var(--cf-line); border-radius:16px; padding:18px 20px 16px; box-shadow:var(--cf-shadow); border-top:5px solid var(--k,var(--cf-primary)); min-width:0; }
.cf-kpi .lb{ display:block; font-size:16px; font-weight:700; color:var(--cf-muted); line-height:1.4; }
.cf-kpi .v{ display:block; font-size:var(--cf-fs-kpi); font-weight:800; color:var(--cf-ink); line-height:1.15; margin-top:6px; font-variant-numeric:tabular-nums; overflow-wrap:anywhere; }
.cf-kpi .v small{ font-size:20px; font-weight:700; color:var(--cf-muted); margin-left:4px; }
.cf-kpi .sub{ display:block; font-size:15px; color:var(--cf-muted); margin-top:6px; line-height:1.5; }
.cf-kpi.good{ --k:var(--cf-primary); } .cf-kpi.warn{ --k:var(--cf-amber); } .cf-kpi.bad{ --k:var(--cf-red); } .cf-kpi.ai{ --k:var(--cf-ai-1); }
.cf-kpi.warn .v{ color:var(--cf-amber-ink); } .cf-kpi.bad .v{ color:var(--cf-red-ink); }

/* ---------- 連線狀態卡 ---------- */
.cf-conn{ display:flex; align-items:center; gap:16px; background:var(--cf-card); border:1px solid var(--cf-line); border-radius:16px; padding:16px 20px; box-shadow:var(--cf-shadow); margin:6px 0 14px; }
.cf-conn .dot{ width:14px; height:14px; border-radius:50%; background:#10B981; box-shadow:0 0 0 6px #10B98122; flex:none; }
.cf-conn.warn .dot{ background:var(--cf-amber); box-shadow:0 0 0 6px #F59E0B22; animation:cfpulse 1.4s infinite; }
.cf-conn.bad .dot{ background:var(--cf-red); box-shadow:0 0 0 6px #EF444422; }
.cf-conn b{ font-size:19px; color:var(--cf-ink); }
.cf-conn span{ display:block; font-size:15px; color:var(--cf-muted); }
.cf-conn .ms{ margin-left:auto; font-family:ui-monospace,Consolas,monospace; font-size:16px; font-weight:700; color:var(--cf-primary-ink); background:var(--cf-primary-soft); border-radius:10px; padding:6px 12px; white-space:nowrap; }

/* ---------- Badge／標籤 ---------- */
.cf-badges{ display:flex; flex-wrap:wrap; gap:6px; margin:2px 0 4px; }
.cf-badge{ display:inline-flex; align-items:center; gap:6px; border-radius:999px; padding:4px 12px; font-size:15px; font-weight:700; border:1px solid transparent; line-height:1.4; white-space:nowrap; }
.cf-badge.red{ background:var(--cf-red-soft); color:var(--cf-red-ink); border-color:#FECACA; }
.cf-badge.amber{ background:var(--cf-amber-soft); color:var(--cf-amber-ink); border-color:#FDE68A; }
.cf-badge.green{ background:var(--cf-primary-soft); color:var(--cf-primary-ink); border-color:#A7F3D0; }
.cf-badge.slate{ background:#F1F5F9; color:#334155; border-color:var(--cf-line); }
.cf-badge.ai{ background:linear-gradient(135deg,var(--cf-ai-1),var(--cf-ai-2)); color:#fff; }
.cf-shift{ display:inline-flex; align-items:center; gap:8px; font-family:ui-monospace,Consolas,monospace; font-size:18px; font-weight:700; color:var(--cf-ink);
  background:var(--cf-ai-soft); border:1px solid #C7D2FE; border-radius:10px; padding:5px 12px; margin:4px 0; }
.cf-shift .ar{ color:var(--cf-ai-1); } .cf-shift .d{ color:#4338CA; background:#fff; border-radius:8px; padding:0 8px; }
[class*="st-key-cfplan"]{ border-left:5px solid var(--cf-ai-2) !important; border-radius:14px; }

/* ---------- LINE 解析 Preview ---------- */
.cf-parse{ background:var(--cf-card); border:1px solid #C7D2FE; border-radius:16px; box-shadow:0 10px 30px rgba(99,102,241,.12); overflow:hidden; animation:cfpop .4s ease both; }
.cf-parse-head{ display:flex; align-items:center; justify-content:space-between; gap:8px; padding:12px 18px; background:linear-gradient(135deg,#EEF2FF,#F5F3FF); border-bottom:1px solid #E0E7FF; }
.cf-parse-head b{ font-size:18px; color:#312E81; }
.cf-parse-body{ padding:16px 18px 18px; display:grid; gap:14px; }
.cf-parse-row{ display:grid; grid-template-columns:96px 1fr; gap:10px; align-items:start; }
.cf-parse-row > span{ font-size:15px; font-weight:700; color:var(--cf-muted); padding-top:3px; }
.cf-parse-row > div{ font-size:18px; color:var(--cf-ink); }
.cf-parse-name{ font-size:24px !important; font-weight:800; }
.cf-level{ display:inline-flex; align-items:baseline; gap:4px; background:var(--cf-primary); color:#fff; border-radius:10px; padding:2px 12px; font-size:15px; font-weight:700; }
.cf-level b{ font-size:22px; }
.cf-pin{ display:flex; gap:12px; align-items:flex-start; background:#F8FAFC; border:1px solid var(--cf-line); border-radius:12px; padding:12px 14px; }
.cf-pin .pin{ font-size:26px; line-height:1; }
.cf-pin b{ display:block; font-size:17px; color:var(--cf-ink); }
.cf-pin span{ display:block; font-size:14.5px; color:var(--cf-muted); margin-top:2px; }
.cf-pin.ok{ border-color:#A7F3D0; background:#F0FDF4; } .cf-pin.warn{ border-color:#FDE68A; background:var(--cf-amber-soft); } .cf-pin.bad{ border-color:#FECACA; background:var(--cf-red-soft); }
.cf-tag{ display:inline-flex; gap:6px; align-items:center; background:#F0FDFA; color:var(--cf-primary-ink); border:1px solid #99F6E4; border-radius:10px; padding:4px 10px; font-size:15.5px; font-weight:600; margin:0 6px 6px 0; }
.cf-tag code{ background:#fff; color:var(--cf-primary); font-weight:800; border-radius:6px; padding:0 6px; font-size:14px; }
.cf-parse-empty{ border:2px dashed #C7D2FE; border-radius:16px; background:#FAFAFF; padding:40px 24px; text-align:center; color:#4338CA; }
.cf-parse-empty b{ display:block; font-size:20px; margin:8px 0 4px; }
.cf-parse-empty span{ font-size:15.5px; color:var(--cf-muted); }

/* ---------- 05 排班效益 ---------- */
.cf-impact{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; margin:8px 0 18px; }
.cf-impact.three{ grid-template-columns:repeat(3,minmax(0,1fr)); }
.cf-impact.three .n{ font-size:46px; }
.cf-impact > div{ position:relative; background:var(--cf-card); border:1px solid var(--cf-line); border-radius:18px; padding:22px 24px; box-shadow:var(--cf-shadow); overflow:hidden; }
.cf-impact > div:before{ content:""; position:absolute; inset:0 0 auto 0; height:6px; background:linear-gradient(90deg,var(--cf-primary),var(--cf-primary-2)); }
.cf-impact > div.ai:before{ background:linear-gradient(90deg,var(--cf-ai-1),var(--cf-ai-2)); }
.cf-impact .t{ font-size:18px; font-weight:700; color:var(--cf-muted); }
.cf-impact .n{ font-size:56px; font-weight:900; line-height:1.1; margin:6px 0 4px; letter-spacing:-.02em; font-variant-numeric:tabular-nums;
  background:linear-gradient(135deg,var(--cf-primary),var(--cf-primary-2)); -webkit-background-clip:text; background-clip:text; color:transparent; }
.cf-impact .ai .n{ background-image:linear-gradient(135deg,var(--cf-ai-1),var(--cf-ai-2)); }
.cf-impact .vs{ display:inline-flex; gap:8px; align-items:center; font-size:19px; font-weight:700; color:var(--cf-ink); background:#F1F5F9; border-radius:10px; padding:5px 12px; }
.cf-impact .s{ display:block; font-size:15px; color:var(--cf-muted); margin-top:10px; line-height:1.6; }

/* ---------- 熱圖圖例與 AI 建議 ---------- */
.cf-legend{ display:flex; align-items:center; gap:12px; margin:6px 0 10px; flex-wrap:wrap; }
.cf-legend .bar{ flex:1 1 260px; max-width:460px; height:16px; border-radius:999px; background:linear-gradient(90deg,#FFF7EC,#FDD49E,#FC8D59,#D7301F,#7F0000); border:1px solid #FED7AA; }
.cf-legend span{ font-size:15.5px; font-weight:700; color:var(--cf-text); white-space:nowrap; }
.cf-advice{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; margin:10px 0; }
.cf-advice > div{ background:var(--cf-card); border:1px solid #C7D2FE; border-left:5px solid var(--cf-ai-2); border-radius:14px; padding:14px 16px; box-shadow:var(--cf-shadow); }
.cf-advice b{ display:block; font-size:18px; color:var(--cf-ink); margin:6px 0 4px; }
.cf-advice span{ display:block; font-size:15.5px; color:var(--cf-text); line-height:1.6; }

@media (max-width:900px){ .cf-ready, .cf-impact, .cf-impact.three{ grid-template-columns:1fr; } .cf-header{ padding:10px 14px; } .cf-brand b{ font-size:19px; } .cf-impact .n{ font-size:44px; } }
</style>
"""


def _e(text):
    from html import escape
    return escape(str(text))


def side_brand():
    """側邊欄頂端的小 Logo。"""
    st.markdown(f'<div class="cf-side-brand">{LOGO_SVG}<b>HomeCare AI</b></div>', unsafe_allow_html=True)


def ready_cards(items):
    """檔案載入後的 3 連狀態卡。items：[(標題, 說明, ok:bool)]。"""
    html = ''.join(f'<div class="{"" if ok else "warn"}"><div class="ic">{"✓" if ok else "…"}</div><div><b>{_e(t)}</b><span>{_e(d)}</span></div></div>'
                   for t, d, ok in items)
    st.markdown(f'<div class="cf-ready">{html}</div>', unsafe_allow_html=True)


def kpi_cards(items):
    """KPI 卡：數字與標籤分行顯示，不會截斷。items：[dict(label, value, unit, sub, tone)]，tone：good／warn／bad／ai。"""
    cards = []
    for it in items:
        unit = f'<small>{_e(it["unit"])}</small>' if it.get('unit') else ''
        sub = f'<span class="sub">{_e(it["sub"])}</span>' if it.get('sub') else ''
        cards.append(f'<div class="cf-kpi {_e(it.get("tone", "good"))}" title="{_e(it.get("help", ""))}">'
                     f'<span class="lb">{_e(it["label"])}</span><span class="v">{_e(it["value"])}{unit}</span>{sub}</div>')
    st.markdown('<div class="cf-kpis">' + ''.join(cards) + '</div>', unsafe_allow_html=True)


def conn_card(title, detail, latency=None, tone='ok'):
    """交通主機等外部連線的狀態卡。tone：ok／warn／bad。"""
    ms = f'<div class="ms">回應 {_e(latency)}</div>' if latency else ''
    st.markdown(f'<div class="cf-conn {_e(tone)}"><div class="dot"></div><div><b>{_e(title)}</b><span>{_e(detail)}</span></div>{ms}</div>',
                unsafe_allow_html=True)


def badges(items):
    """Badge 列。items：[(文字, tone)]，tone：red／amber／green／slate／ai。"""
    items = [(t, tone) for t, tone in (items or []) if str(t).strip()]
    if items:
        st.markdown('<div class="cf-badges">' + ''.join(f'<span class="cf-badge {_e(tone)}">{_e(t)}</span>' for t, tone in items) + '</div>',
                    unsafe_allow_html=True)


def badge_html(text, tone='slate'):
    return f'<span class="cf-badge {_e(tone)}">{_e(text)}</span>'


# 衝突原因 → 短 Badge（長句收到 Badge 下方的說明）。依序比對，先中先用。
_REASON_BADGES = [
    (('趕到', '轉場', '交通', '空檔'), '🔴 交通轉場不足', 'red'),
    (('重疊',), '🔴 時段重疊', 'red'),
    (('資格', '證照', '訓練', '限女', '限男', '失智'), '🟡 證照資格不符', 'amber'),
    (('連續上班', '連續工作天數'), '🟠 連續上班天數', 'amber'),
    (('連續工作', '休息'), '🟠 連續工作超限', 'amber'),
    (('月加班', '加班', '工時'), '🟠 工時超限', 'amber'),
    (('請假',), '🟡 居服員請假', 'amber'),
    (('不排班', '休息日', '星期'), '⚪ 非排班日', 'slate'),
]


def reason_badge(text, category=None):
    """把冗長的衝突原因轉成 (Badge 文字, tone)。"""
    t = f'{category or ""} {text or ""}'
    for keys, label, tone in _REASON_BADGES:
        if any(k in t for k in keys):
            return label, tone
    return '⚪ 其他原因', 'slate'


def time_shift_html(title):
    """從方案標題擷取「12:30～14:30 → 13:00～15:00」並轉成 12:30 ➔ 13:00 (+30m) 標籤；找不到時回傳空字串。"""
    import re
    m = re.search(r'(\d{1,2}):(\d{2})～\d{1,2}:\d{2}\s*→\s*(\d{1,2}):(\d{2})', str(title or ''))
    if not m:
        return ''
    a = int(m.group(1)) * 60 + int(m.group(2))
    b = int(m.group(3)) * 60 + int(m.group(4))
    d = b - a
    sign = '+' if d >= 0 else '−'
    dur = f'{abs(d) // 60}h{abs(d) % 60:02d}m' if abs(d) >= 60 and abs(d) % 60 else (f'{abs(d) // 60}h' if abs(d) >= 60 else f'{abs(d)}m')
    return (f'<span class="cf-shift">{m.group(1).zfill(2)}:{m.group(2)} <span class="ar">➔</span> '
            f'{m.group(3).zfill(2)}:{m.group(4)} <span class="d">({sign}{dur})</span></span>')


# 長照給付 BA 碼常見項目名稱（顯示用；查不到時只顯示代碼）
BA_NAMES = {
    'BA01': '基本身體清潔', 'BA02': '基本日常照顧', 'BA03': '測量生命徵象', 'BA04': '協助進食或管灌',
    'BA05': '餐食照顧', 'BA07': '協助沐浴及洗頭', 'BA08': '足部照護', 'BA09': '到宅沐浴車',
    'BA10': '翻身拍背', 'BA11': '肢體關節活動', 'BA12': '協助上下樓梯', 'BA13': '陪同外出',
    'BA14': '陪同就醫', 'BA15': '家務協助', 'BA16': '代購代領代送', 'BA18': '安全看視',
    'BA20': '陪伴服務', 'BA22': '巡視服務', 'BA23': '協助洗頭', 'BA24': '協助排泄',
}


def line_preview(meta, geo, address, service_codes, slot_count=0, first_slot=''):
    """LINE 派案 AI 解析的結構化 Preview（只顯示已遮蔽的資料）。"""
    name = meta.get('name_masked') or '（未提供姓名）'
    who = ' '.join(x for x in [meta.get('client_gender') or '', f"{meta['age']} 歲" if meta.get('age') else ''] if x) or '—'
    level = meta.get('disability_level')
    level_html = f'<span class="cf-level">CMS <b>{_e(level)}</b> 級</span>' if level else badge_html('失能等級未提供', 'amber')
    flags = [badge_html('失智：有', 'amber') if meta.get('dementia') else badge_html('失智：無', 'slate'),
             badge_html('身障：有', 'amber') if meta.get('disabled') else badge_html('身障：無', 'slate')]
    if meta.get('caregiver_gender') and meta.get('caregiver_gender') != '男女不拘':
        flags.append(badge_html(f"指定{meta['caregiver_gender']}性居服員", 'amber'))
    flags += [badge_html(f, 'amber') for f in (meta.get('flags') or [])[:4]]
    if geo.get('lat') is None:
        pin_cls, pin_title, pin_sub = 'bad', '尚未定位', f"{geo.get('status', '')}　請在下方「調整地址／位置」補座標"
    elif geo.get('status') in ('精確門牌', '人工座標'):
        pin_cls, pin_title, pin_sub = 'ok', geo.get('matched') or address, f"✓ {geo.get('status')}　{geo['lat']:.5f}, {geo['lon']:.5f}"
    else:
        pin_cls, pin_title, pin_sub = 'warn', geo.get('matched') or address, f"{geo.get('status')}　誤差約 {geo.get('radius_m', '?')} 公尺內"
    codes = list(dict.fromkeys(c for c in service_codes if c))
    tags = ''.join(f'<span class="cf-tag"><code>{_e(c)}</code>{_e(BA_NAMES.get(c.upper()[:4], ""))}</span>' for c in codes) or badge_html('未讀到服務碼', 'amber')
    slot_text = f'{slot_count} 個時段' + (f'（首筆 {first_slot}）' if first_slot else '') if slot_count else '未讀到時段'
    st.markdown(
        '<div class="cf-parse"><div class="cf-parse-head"><b>✨ AI 結構化解析結果</b>' + badge_html('已遮蔽個資', 'green') + '</div>'
        '<div class="cf-parse-body">'
        f'<div class="cf-parse-row"><span>案主</span><div><div class="cf-parse-name">{_e(name)}</div>{_e(who)}</div></div>'
        f'<div class="cf-parse-row"><span>失能等級</span><div>{level_html}<div class="cf-badges" style="margin-top:8px">{"".join(flags)}</div></div></div>'
        f'<div class="cf-parse-row"><span>服務地址</span><div><div class="cf-pin {pin_cls}"><div class="pin">📍</div><div><b>{_e(pin_title)}</b><span>{_e(pin_sub)}</span></div></div></div></div>'
        f'<div class="cf-parse-row"><span>照護項目</span><div>{tags}</div></div>'
        f'<div class="cf-parse-row"><span>服務時段</span><div>{_e(slot_text)}</div></div>'
        '</div></div>', unsafe_allow_html=True)


def line_preview_empty():
    st.markdown('<div class="cf-parse-empty"><div style="font-size:34px">✨</div><b>AI 解析結果會顯示在這裡</b>'
                '<span>左側貼上 LINE 派案訊息，按「✨ 解析並定位」，即時帶出姓名、失能等級、地址圖釘與照護項目。</span></div>',
                unsafe_allow_html=True)


def impact_cards(items, cols=2):
    """效益大數字卡。items：[dict(title, number, before, after, note, ai:bool)]。"""
    html = ''.join(
        f'<div class="{"ai" if it.get("ai") else ""}"><div class="t">{_e(it["title"])}</div><div class="n">{_e(it["number"])}</div>'
        + (f'<span class="vs">{_e(it["before"])}'
           + (f' <span style="color:#6366F1">➔</span> {_e(it["after"])}' if it.get('after') else '') + '</span>' if it.get('before') else '')
        + (f'<span class="s">{_e(it["note"])}</span>' if it.get('note') else '') + '</div>'
        for it in items)
    st.markdown(f'<div class="cf-impact{" three" if cols == 3 else ""}">{html}</div>', unsafe_allow_html=True)


def heat_legend(low='人力充裕', high='極度缺工'):
    st.markdown(f'<div class="cf-legend"><span>🟧 {_e(low)}</span><div class="bar" role="img" aria-label="色階：由淺橙到深紅"></div><span>🟥 {_e(high)}</span></div>',
                unsafe_allow_html=True)


def advice_cards(items):
    """AI 增聘／調派建議卡。items：[(標題, 說明)]。"""
    if not items:
        return
    html = ''.join(f'<div>{badge_html("✨ AI 建議", "ai")}<b>{_e(t)}</b><span>{_e(d)}</span></div>' for t, d in items)
    st.markdown(f'<div class="cf-advice">{html}</div>', unsafe_allow_html=True)


# =====================================================================
# 方案 C「暖心大字」覆寫層（2026.11 第二版）
#   暖杏底 #FBF7F0、白卡、深藍綠主色 #1F5F7A、琥珀提醒 #B45309、成功綠 #2F855A
#   AI 功能：靛藍 #4338CA（單色，不用漸層）
#   所有字級 = 基準 px × --cf-s（標準 1.0／大 1.12／特大 1.25），由頁首「字體大小」切換
#   對比：主要文字 #2B2622、次要 #6B5E52（白底約 6:1），皆 ≥ 4.5:1
# =====================================================================
LOGO_ROUND_SVG = ('<svg class="cf-logo" viewBox="0 0 48 48" width="48" height="48" aria-hidden="true">'
                  '<circle cx="24" cy="24" r="24" fill="#1F5F7A"/>'
                  '<path d="M24 34s-10-6.2-10-14a5.6 5.6 0 0110-3.6A5.6 5.6 0 0134 20c0 7.8-10 14-10 14z" fill="none" '
                  'stroke="#fff" stroke-width="2.6" stroke-linejoin="round"/></svg>')

WARM_CSS = """
<style>
:root{
  --cf-s:1.12;
  --cf-primary:#1F5F7A; --cf-primary-2:#2C7A99; --cf-primary-soft:#E3EEF3; --cf-primary-ink:#143F52;
  --cf-ok:#2F855A; --cf-ok-soft:#E8F4EC; --cf-ok-line:#9FD3B2;
  --cf-amber:#B45309; --cf-amber-soft:#FFF6E8; --cf-amber-ink:#92400E; --cf-amber-line:#F3D9B1;
  --cf-red:#B42318; --cf-red-soft:#FDECEA; --cf-red-ink:#912018;
  --cf-ai-1:#4338CA; --cf-ai-2:#4338CA; --cf-ai-soft:#EEF2FF;
  --cf-bg:#FBF7F0; --cf-card:#FFFFFF; --cf-ink:#2B2622; --cf-text:#3A322B; --cf-muted:#6B5E52; --cf-line:#EADFCF; --cf-line-2:#D9CBB6;
  --cf-radius:20px; --cf-shadow:0 1px 2px rgba(43,38,34,.04),0 8px 24px rgba(43,38,34,.05);
  --cf-teal:#1F5F7A; --cf-teal-dark:#143F52; --cf-mint:#E3EEF3; --cf-acc:#1F5F7A; --cf-acc-soft:#E3EEF3; --cf-acc-ink:#143F52;
}
.stApp, [data-testid="stAppViewContainer"]{ background:var(--cf-bg) !important; color:var(--cf-ink); }
[data-testid="stMainBlockContainer"]{ max-width:1280px; padding-top:.8rem; }
[data-testid="stMain"] p, [data-testid="stMain"] li, [data-testid="stMain"] [data-testid="stMarkdownContainer"]{ font-size:calc(19px * var(--cf-s)); line-height:1.7; color:var(--cf-text); }
[data-testid="stMain"] [data-testid="stCaptionContainer"], [data-testid="stMain"] [data-testid="stCaptionContainer"] p{ font-size:calc(17px * var(--cf-s)); color:var(--cf-muted); }
[data-testid="stMain"] [data-testid="stWidgetLabel"] p{ font-size:calc(18px * var(--cf-s)) !important; font-weight:700; color:var(--cf-ink); }
[data-testid="stMain"] h1{ font-size:calc(34px * var(--cf-s)); } [data-testid="stMain"] h2{ font-size:calc(28px * var(--cf-s)); }
[data-testid="stMain"] h3{ font-size:calc(24px * var(--cf-s)); } [data-testid="stMain"] h4, [data-testid="stMain"] h5{ font-size:calc(21px * var(--cf-s)); }
h1,h2,h3,h4,h5{ color:var(--cf-ink) !important; }
:focus-visible{ outline:3px solid var(--cf-primary) !important; outline-offset:3px; }

/* Header */
.cf-header{ background:var(--cf-card); border:1px solid var(--cf-line); border-radius:24px; padding:16px 26px; box-shadow:var(--cf-shadow); margin-bottom:10px; }
.cf-brand b{ font-size:calc(26px * var(--cf-s)); color:var(--cf-ink); font-weight:800; }
.cf-brand span{ font-size:calc(15px * var(--cf-s)); color:var(--cf-muted); }
.cf-brand .cf-logo{ width:calc(48px * var(--cf-s)); height:calc(48px * var(--cf-s)); }
.cf-pill{ font-size:calc(17px * var(--cf-s)); background:#FFFFFF; border:1px solid var(--cf-line-2); color:var(--cf-text); padding:8px 16px; }
.cf-pill.ok{ background:var(--cf-ok-soft); color:#1D5C3C; border-color:var(--cf-ok-line); } .cf-pill.ok i{ background:var(--cf-ok); box-shadow:0 0 0 4px #2F855A26; }
.cf-pill.warn{ background:var(--cf-amber-soft); color:var(--cf-amber-ink); border-color:var(--cf-amber-line); } .cf-pill.warn i{ background:var(--cf-amber); }
[class*="st-key-cf_font_scale"] [data-testid="stWidgetLabel"] p{ font-size:calc(15px * var(--cf-s)) !important; color:var(--cf-muted); }

/* 1→5 步驟導引 */
[class*="st-key-cfsteps"]{ margin:6px 0 4px; }
[class*="st-key-cfstep_"] button{ min-height:calc(78px * var(--cf-s)) !important; border-radius:20px !important; border:2px solid var(--cf-line-2) !important; background:#FFFFFF !important; box-shadow:none !important; }
[class*="st-key-cfstep_"] button p{ font-size:calc(20px * var(--cf-s)) !important; font-weight:700 !important; color:var(--cf-muted) !important; }
[class*="st-key-cfstep_done"] button{ background:var(--cf-ok-soft) !important; border-color:var(--cf-ok-line) !important; }
[class*="st-key-cfstep_done"] button p{ color:#1D5C3C !important; }
[class*="st-key-cfstep_now"] button{ background:var(--cf-primary) !important; border-color:var(--cf-primary) !important; box-shadow:0 0 0 6px #D6E6EE !important; }
[class*="st-key-cfstep_now"] button p{ color:#FFFFFF !important; font-weight:900 !important; }
[class*="st-key-cfstep_"] button:hover{ border-color:var(--cf-primary) !important; }
[class*="st-key-cfstep_warn"] button, [class*="st-key-cfstep_warn"] .stButton button{ background:var(--cf-amber-soft) !important; border-color:var(--cf-amber-line) !important; }
[class*="st-key-cfstep_warn"] button p{ color:var(--cf-amber-ink) !important; font-weight:800 !important; }
[class*="st-key-cfstep_lock"] button, [class*="st-key-cfstep_lock"] .stButton button,
[class*="st-key-cfstep_lock"] button:hover, [class*="st-key-cfstep_lock"] button:disabled{ background:#F4F1EC !important; border:2px dashed var(--cf-line-2) !important; opacity:1 !important; cursor:not-allowed; }
[class*="st-key-cfstep_lock"] button p{ color:#A39686 !important; }
[class*="st-key-cfstep_"][class*="_mgr_"] button{ border-radius:999px !important; }
[class*="st-key-cfstep_todo_mgr_"] button, [class*="st-key-cfstep_todo_mgr_"] .stButton button{ background:#FBF7F0 !important; }
/* 底部固定操作列 */
[class*="st-key-cfactionbar_"]{ position:sticky; bottom:0; z-index:60; margin-top:28px; padding:14px 16px;
  background:#FFFFFFF2; border:1px solid var(--cf-line); border-radius:20px; box-shadow:0 -6px 20px #2B21170F; backdrop-filter:blur(4px); }
[class*="st-key-cfactionbar_warn"]{ border-color:var(--cf-amber-line); background:#FFF9F0F2; }
.cf-bar-hint{ font-size:calc(17px * var(--cf-s)); color:var(--cf-text); text-align:center; line-height:1.5; }
[class*="st-key-cfactionbar_warn"] .cf-bar-hint{ color:var(--cf-amber-ink); font-weight:700; }
[class*="st-key-cfactionbar_"] button[kind="primary"]{ min-height:calc(58px * var(--cf-s)) !important; }
[class*="st-key-cfactionbar_"] button[kind="primary"] p{ font-size:calc(19px * var(--cf-s)) !important; font-weight:800 !important; }
[class*="st-key-cfactionbar_"] button[kind="primary"]:disabled{ background:#E9E3DA !important; border-color:#E9E3DA !important; }
[class*="st-key-cfactionbar_"] button[kind="primary"]:disabled p{ color:#8A7C6F !important; }
/* ② 開始排班：排班前大卡 */
[class*="st-key-cfrun_card"]{ border-radius:24px !important; background:var(--cf-card); padding:8px 6px; }
.cf-runcard b{ display:block; font-size:calc(32px * var(--cf-s)); color:var(--cf-ink); font-weight:900; line-height:1.3; }
.cf-runcard span{ display:block; margin-top:4px; font-size:calc(18px * var(--cf-s)); color:var(--cf-muted); }
/* ④ 確認班表：定稿狀態列 */
.cf-final{ padding:12px 18px; border-radius:16px; border:1px solid var(--cf-line); background:#FBF7F0; font-size:calc(18px * var(--cf-s)); color:var(--cf-text); margin:4px 0 10px; }
.cf-final.ok{ background:var(--cf-ok-soft); border-color:var(--cf-ok-line); color:#1D5C3C; font-weight:800; }
.cf-final.warn{ background:var(--cf-amber-soft); border-color:var(--cf-amber-line); color:var(--cf-amber-ink); font-weight:800; }
/* ① 匯入資料：三張打勾卡片 */
[class*="st-key-cfimport_card_"]{ border-radius:22px !important; background:var(--cf-card); margin-bottom:12px; }
.cf-icard{ display:flex; gap:16px; align-items:center; padding:2px 0 4px; }
.cf-icard-mark{ flex:none; width:calc(46px * var(--cf-s)); height:calc(46px * var(--cf-s)); border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-size:calc(22px * var(--cf-s)); font-weight:900; background:var(--cf-primary); color:#FFFFFF; box-shadow:0 0 0 5px #D6E6EE; }
.cf-icard b{ display:block; font-size:calc(22px * var(--cf-s)); color:var(--cf-ink); }
.cf-icard span:not(.cf-icard-mark){ display:block; font-size:calc(17px * var(--cf-s)); color:var(--cf-muted); line-height:1.5; }
.cf-icard.done .cf-icard-mark{ background:var(--cf-ok); box-shadow:0 0 0 5px #2F855A26; }
.cf-icard.done span:not(.cf-icard-mark){ color:#1D5C3C; font-weight:700; }
.cf-icard.warn .cf-icard-mark{ background:var(--cf-amber); box-shadow:0 0 0 5px var(--cf-amber-soft); }
.cf-icard.warn span:not(.cf-icard-mark){ color:var(--cf-amber-ink); font-weight:700; }
.cf-icard.lock .cf-icard-mark{ background:#F4F1EC; color:#A39686; box-shadow:none; border:2px dashed var(--cf-line-2); }
.cf-icard.lock b, .cf-icard.lock span:not(.cf-icard-mark){ color:#A39686 !important; }

/* 側邊欄：收合時保留設定 */
[data-testid="stSidebar"]{ background:#FFFDF9 !important; border-right:1px solid var(--cf-line); }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){ background:var(--cf-primary-soft) !important; border-left:5px solid var(--cf-primary) !important; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p{ color:var(--cf-primary-ink) !important; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover{ background:#F6EFE4 !important; }

/* 模組頁首與小節 */
.cf-module{ background:var(--cf-card) !important; border:1px solid var(--cf-line) !important; border-left:1px solid var(--cf-line) !important; border-radius:24px !important; padding:22px 28px !important; box-shadow:var(--cf-shadow); }
.cf-module .cf-number{ background:var(--cf-primary) !important; border-radius:50% !important; min-width:calc(52px * var(--cf-s)) !important; height:calc(52px * var(--cf-s)); padding:0 !important; display:flex; align-items:center; justify-content:center; font-size:calc(22px * var(--cf-s)) !important; box-shadow:0 0 0 6px #D6E6EE !important; }
.cf-module h2{ font-size:calc(30px * var(--cf-s)) !important; }
.cf-module p{ font-size:calc(17px * var(--cf-s)) !important; color:var(--cf-muted) !important; }
.cf-module .cf-role{ display:none; }
.cf-subhead{ font-size:calc(26px * var(--cf-s)) !important; font-weight:800 !important; border-left:0 !important; padding:0 !important; margin:30px 0 12px !important; color:var(--cf-ink) !important; background:none !important; }
[data-testid="stVerticalBlockBorderWrapper"]{ border-radius:20px !important; }
[data-testid="stExpander"]{ background:var(--cf-card) !important; border:1px solid var(--cf-line) !important; border-radius:18px !important; box-shadow:none; }
[data-testid="stExpander"] summary p{ font-size:calc(19px * var(--cf-s)) !important; font-weight:700; }
[data-testid="stAlert"]{ border-radius:16px !important; border-left-width:0 !important; }
[data-testid="stAlert"] p{ font-size:calc(18px * var(--cf-s)) !important; }

/* 按鈕：大、圓、一頁一個主要動作 */
.stButton button, .stDownloadButton button{ min-height:calc(56px * var(--cf-s)); border-radius:16px; border-width:2px; }
.stButton button p, .stDownloadButton button p{ font-size:calc(19px * var(--cf-s)) !important; font-weight:700; }
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"]{ background:var(--cf-primary) !important; border-color:var(--cf-primary) !important; color:#fff !important; box-shadow:none !important; }
.stButton button[kind="primary"]:hover{ background:var(--cf-primary-ink) !important; border-color:var(--cf-primary-ink) !important; filter:none; }
.stButton button[kind="secondary"], .stDownloadButton button[kind="secondary"]{ background:#FFFFFF !important; border-color:var(--cf-line-2) !important; color:var(--cf-ink) !important; }
.stButton button[kind="secondary"]:hover{ border-color:var(--cf-primary) !important; color:var(--cf-primary-ink) !important; background:#FFFFFF !important; }
[class*="st-key-cfai"] .stButton button, [class*="st-key-cfai"] button[kind]{ background:var(--cf-ai-1) !important; box-shadow:none !important; }
[class*="st-key-cfai"] button:after{ display:none; }
[class*="st-key-cfai"] button p{ font-size:calc(20px * var(--cf-s)) !important; }
[class*="st-key-cfai_xl"] button{ min-height:calc(84px * var(--cf-s)) !important; border-radius:22px !important; }
[class*="st-key-cfai_xl"] button p{ font-size:calc(25px * var(--cf-s)) !important; }

/* 指標卡 */
[data-testid="stMetric"]{ border-radius:20px; border-color:var(--cf-line); box-shadow:none; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] > div{ font-size:calc(36px * var(--cf-s)) !important; color:var(--cf-ink) !important; }
[data-testid="stMetricLabel"] p{ font-size:calc(17px * var(--cf-s)) !important; }
.cf-kpi{ border-radius:20px; border:1px solid var(--cf-line); border-top:1px solid var(--cf-line); box-shadow:none; padding:20px 22px; }
.cf-kpi .lb{ font-size:calc(18px * var(--cf-s)); color:var(--cf-muted); }
.cf-kpi .v{ font-size:calc(46px * var(--cf-s)); font-weight:900; }
.cf-kpi .v small{ font-size:calc(22px * var(--cf-s)); }
.cf-kpi .sub{ font-size:calc(17px * var(--cf-s)); }
.cf-kpi.good .v{ color:var(--cf-primary); } .cf-kpi.bad{ border-color:#F5C2BC; } .cf-kpi.warn{ border-color:var(--cf-amber-line); }
.cf-kpi.warn .v{ color:var(--cf-amber); } .cf-kpi.bad .v{ color:var(--cf-red); }

/* 3 連狀態卡、連線卡、Badge */
.cf-ready > div{ border-radius:20px; border-color:var(--cf-line); box-shadow:none; }
.cf-ready .ic{ background:var(--cf-ok-soft); color:var(--cf-ok); width:calc(50px * var(--cf-s)); height:calc(50px * var(--cf-s)); }
.cf-ready b{ font-size:calc(22px * var(--cf-s)); } .cf-ready span{ font-size:calc(16px * var(--cf-s)); }
.cf-conn{ border-radius:20px; box-shadow:none; border-color:var(--cf-line); }
.cf-conn b{ font-size:calc(20px * var(--cf-s)); } .cf-conn span{ font-size:calc(16px * var(--cf-s)); }
.cf-conn .dot{ background:var(--cf-ok); } .cf-conn .ms{ background:var(--cf-ok-soft); color:#1D5C3C; font-size:calc(17px * var(--cf-s)); }
.cf-badge{ font-size:calc(16px * var(--cf-s)); padding:5px 14px; }
.cf-badge.green{ background:var(--cf-ok-soft); color:#1D5C3C; border-color:var(--cf-ok-line); }
.cf-badge.red{ background:var(--cf-red-soft); color:var(--cf-red-ink); border-color:#F5C2BC; }
.cf-badge.amber{ background:var(--cf-amber-soft); color:var(--cf-amber-ink); border-color:var(--cf-amber-line); }
.cf-badge.slate{ background:#F4EFE6; color:#4A4038; border-color:var(--cf-line); }
.cf-badge.ai{ background:var(--cf-ai-1); }
.cf-shift{ font-size:calc(22px * var(--cf-s)); background:var(--cf-amber-soft); border-color:var(--cf-amber-line); }
.cf-shift .ar{ color:var(--cf-amber); } .cf-shift .d{ color:var(--cf-amber-ink); }
[class*="st-key-cfplan"]{ border-left:0 !important; }

/* 01 拖曳區 */
[class*="st-key-cf_dropzone"] [data-testid="stFileUploaderDropzone"]{ border:3px dashed var(--cf-line-2) !important; background:#FFFFFF !important; border-radius:24px !important; min-height:calc(240px * var(--cf-s)); }
[class*="st-key-cf_dropzone"] [data-testid="stFileUploaderDropzone"]:hover{ border-color:var(--cf-primary) !important; background:#FFFDF9 !important; }
[class*="st-key-cf_dropzone"] [data-testid="stFileUploaderDropzone"]::before{ color:var(--cf-ink); font-size:calc(28px * var(--cf-s)); }

/* 02 結果主卡（一句話講結果） */
.cf-hero2{ display:flex; flex-wrap:wrap; align-items:center; gap:28px; background:var(--cf-card); border:1px solid var(--cf-line); border-radius:28px; padding:30px 36px; margin:8px 0 14px; }
.cf-hero2 .main{ flex:1 1 420px; min-width:0; }
.cf-hero2 .eyebrow{ font-size:calc(20px * var(--cf-s)); font-weight:700; color:var(--cf-muted); }
.cf-hero2 .big{ font-size:calc(42px * var(--cf-s)); font-weight:900; line-height:1.3; color:var(--cf-ink); margin-top:6px; }
.cf-hero2 .big em{ font-style:normal; color:var(--cf-primary); }
.cf-hero2 .bar{ margin-top:16px; height:18px; border-radius:999px; background:#EFE6D8; overflow:hidden; }
.cf-hero2 .bar i{ display:block; height:100%; background:var(--cf-primary); border-radius:999px; }
.cf-hero2 .foot{ margin-top:10px; font-size:calc(20px * var(--cf-s)); color:var(--cf-text); }
.cf-hero2 .side{ flex:0 1 300px; display:grid; gap:10px; }
.cf-hero2 .side div{ background:#FBF7F0; border-radius:18px; padding:14px 18px; }
.cf-hero2 .side b{ display:block; font-size:calc(34px * var(--cf-s)); font-weight:900; color:var(--cf-ink); line-height:1.2; }
.cf-hero2 .side span{ font-size:calc(17px * var(--cf-s)); color:var(--cf-muted); }
.cf-hero2 .side .warn b{ color:var(--cf-amber); }
.cf-family{ font-size:calc(30px * var(--cf-s)); font-weight:800; color:var(--cf-ink); margin:26px 0 10px; }
.cf-family em{ font-style:normal; color:var(--cf-amber); }

/* 03 案家卡片 */
/* 03 收件匣 */
.cf-inbox-progress{ font-size:calc(18px * var(--cf-s)); color:var(--cf-text); margin:6px 0 2px; }
.cf-inbox-progress b{ font-size:calc(24px * var(--cf-s)); color:var(--cf-primary-ink); }
[class*="st-key-cfinbox_"]{ background:#FFFFFF; border:1px solid var(--cf-line); border-left:5px solid var(--cf-amber-line);
  border-radius:16px; padding:12px 14px 10px; gap:6px !important; }
[class*="st-key-cfinbox_sel"]{ background:var(--cf-primary-soft); border-color:var(--cf-primary); border-left-color:var(--cf-primary);
  box-shadow:0 0 0 3px #D6E6EE; }
.cf-inbox-name{ font-size:calc(20px * var(--cf-s)); font-weight:800; color:var(--cf-ink); line-height:1.3; }
.cf-inbox-meta{ font-size:calc(15px * var(--cf-s)); color:var(--cf-muted); margin-top:2px; }
.cf-inbox-meta .cf-badge{ font-size:calc(13.5px * var(--cf-s)); padding:1px 8px; }
.cf-inbox-why{ font-size:calc(16px * var(--cf-s)); color:var(--cf-text); line-height:1.5; margin-top:4px; }
[class*="st-key-cfinbox_"] button{ min-height:0 !important; padding:4px 10px !important; }
[class*="st-key-cfinbox_sel"] button:disabled{ background:transparent !important; border:0 !important; opacity:1 !important; }
[class*="st-key-cfinbox_sel"] button:disabled p{ color:var(--cf-primary-ink) !important; font-weight:800 !important; }
.cf-inbox-done{ font-size:calc(16px * var(--cf-s)); color:#8A9A90; padding:8px 14px; border-radius:12px; background:#F3F7F4; margin:6px 0;
  text-decoration:line-through; text-decoration-color:#B9C8BE; }
[class*="st-key-cfcase_"]{ background:#FFFFFF; border:2px solid var(--cf-amber-line) !important; border-radius:22px !important; }
.cf-case-name{ font-size:calc(26px * var(--cf-s)); font-weight:800; color:var(--cf-ink); line-height:1.3; }
.cf-case-meta{ font-size:calc(17px * var(--cf-s)); color:var(--cf-muted); }
.cf-case-why{ font-size:calc(19px * var(--cf-s)); color:var(--cf-text); line-height:1.6; margin:6px 0; }
.cf-case-tip{ font-size:calc(19px * var(--cf-s)); line-height:1.6; background:var(--cf-amber-soft); border-radius:14px; padding:12px 14px; margin:6px 0 10px; color:var(--cf-ink); }

/* LINE 解析、Impact、熱圖建議：沿用結構，換暖色 */
.cf-parse{ border-color:var(--cf-line); border-radius:22px; box-shadow:none; }
.cf-parse-head{ background:#FBF7F0; border-bottom-color:var(--cf-line); } .cf-parse-head b{ color:var(--cf-ink); font-size:calc(20px * var(--cf-s)); }
.cf-parse-row{ grid-template-columns:calc(110px * var(--cf-s)) 1fr; }
.cf-parse-row > span{ font-size:calc(17px * var(--cf-s)); } .cf-parse-row > div{ font-size:calc(20px * var(--cf-s)); }
.cf-parse-name{ font-size:calc(28px * var(--cf-s)) !important; }
.cf-level{ background:var(--cf-primary); font-size:calc(17px * var(--cf-s)); } .cf-level b{ font-size:calc(24px * var(--cf-s)); }
.cf-pin b{ font-size:calc(19px * var(--cf-s)); } .cf-pin span{ font-size:calc(16px * var(--cf-s)); }
.cf-pin.ok{ background:var(--cf-ok-soft); border-color:var(--cf-ok-line); } .cf-pin{ background:#FBF7F0; border-color:var(--cf-line); }
.cf-tag{ background:var(--cf-primary-soft); color:var(--cf-primary-ink); border-color:#B9D3DF; font-size:calc(17px * var(--cf-s)); }
.cf-tag code{ color:var(--cf-primary); font-size:calc(15px * var(--cf-s)); }
.cf-parse-empty{ border-color:var(--cf-line-2); background:#FFFFFF; color:var(--cf-ink); border-radius:22px; }
.cf-parse-empty b{ font-size:calc(22px * var(--cf-s)); } .cf-parse-empty span{ font-size:calc(17px * var(--cf-s)); }
.cf-impact > div{ border-radius:24px; box-shadow:none; border-color:var(--cf-line); }
.cf-impact > div:before{ background:var(--cf-primary); } .cf-impact > div.ai:before{ background:var(--cf-ai-1); }
.cf-impact .n{ font-size:calc(60px * var(--cf-s)); background:none; color:var(--cf-primary); -webkit-background-clip:border-box; background-clip:border-box; }
.cf-impact .ai .n{ background:none; color:var(--cf-ai-1); }
.cf-impact .t{ font-size:calc(20px * var(--cf-s)); } .cf-impact .vs{ font-size:calc(20px * var(--cf-s)); background:#FBF7F0; } .cf-impact .s{ font-size:calc(16px * var(--cf-s)); }
.cf-legend span{ font-size:calc(17px * var(--cf-s)); }
.cf-advice > div{ border-left:1px solid var(--cf-line); border-color:var(--cf-line); border-radius:20px; box-shadow:none; }
.cf-advice b{ font-size:calc(20px * var(--cf-s)); } .cf-advice span{ font-size:calc(17px * var(--cf-s)); }

/* 方案 D 週班表（大字版） */
.cf-wk-wrap{ overflow-x:auto; border:1px solid var(--cf-line); border-radius:24px; background:#FFFFFF; }
.cf-wk{ display:grid; grid-template-columns:repeat(7, minmax(150px, 1fr)); min-width:1050px; }
.cf-wk-day{ padding:14px 12px 12px; border-bottom:1px solid var(--cf-line); border-right:1px solid #F3ECE1; background:#FFFDF9; }
.cf-wk-day:nth-child(7){ border-right:0; }
.cf-wk-day b{ display:block; font-size:calc(22px * var(--cf-s)); color:var(--cf-ink); }
.cf-wk-day span{ display:block; font-size:calc(16px * var(--cf-s)); color:var(--cf-muted); margin-top:2px; }
.cf-wk-day.today{ background:var(--cf-primary-soft); } .cf-wk-day.today b{ color:var(--cf-primary-ink); }
.cf-wk-day.off b, .cf-wk-day.off span{ color:#8A7C6F; }
.cf-wk-col{ padding:10px; border-right:1px solid #F3ECE1; display:flex; flex-direction:column; gap:8px; min-height:260px; }
.cf-wk-col:nth-child(7n){ border-right:0; }
.cf-wk-col.today{ background:#F7FAFC; }
.cf-wk-c{ border-radius:14px; padding:10px 12px; background:#F6F1E9; border:1px solid #EADFCF; }
.cf-wk-c .t{ display:block; font-size:calc(22px * var(--cf-s)); font-weight:900; color:var(--cf-ink); font-variant-numeric:tabular-nums; line-height:1.2; }
.cf-wk-c .t small{ font-size:calc(15px * var(--cf-s)); font-weight:700; color:var(--cf-muted); }
.cf-wk-c .w{ display:block; font-size:calc(18px * var(--cf-s)); font-weight:700; color:var(--cf-text); margin-top:2px; line-height:1.4; overflow-wrap:anywhere; }
.cf-wk-c .k{ display:block; font-size:calc(14.5px * var(--cf-s)); color:var(--cf-muted); margin-top:2px; overflow-wrap:anywhere; }
.cf-wk-c.miss{ background:var(--cf-amber-soft); border:2px solid #E7A962; } .cf-wk-c.miss .t, .cf-wk-c.miss .w{ color:var(--cf-amber-ink); }
.cf-wk-c.adj{ background:var(--cf-primary-soft); border:2px dashed var(--cf-primary); } .cf-wk-c.adj .t{ color:var(--cf-primary-ink); }
.cf-wk-c .tag{ display:inline-block; font-size:calc(14px * var(--cf-s)); font-weight:800; border-radius:999px; padding:1px 9px; margin-bottom:4px; background:#fff; }
.cf-wk-c.miss .tag{ color:var(--cf-amber-ink); border:1px solid #E7A962; } .cf-wk-c.adj .tag{ color:var(--cf-primary-ink); border:1px solid var(--cf-primary); }
.cf-wk-sum{ border-radius:14px; padding:10px 12px; background:#FFFFFF; border:1px solid var(--cf-line); }
.cf-wk-sum b{ display:block; font-size:calc(30px * var(--cf-s)); font-weight:900; color:var(--cf-primary); line-height:1.15; }
.cf-wk-sum span{ font-size:calc(15px * var(--cf-s)); color:var(--cf-muted); }
.cf-wk-sum.miss b{ color:var(--cf-amber); }
.cf-wk-more{ font-size:calc(15px * var(--cf-s)); color:var(--cf-muted); text-align:center; padding:4px 0; }
.cf-wk-empty{ font-size:calc(16px * var(--cf-s)); color:#8A7C6F; text-align:center; padding:18px 0; }
.cf-wk-legend{ display:flex; flex-wrap:wrap; gap:16px; margin:10px 2px 0; font-size:calc(16px * var(--cf-s)); color:var(--cf-muted); }
.cf-wk-legend i{ display:inline-block; width:18px; height:14px; border-radius:4px; vertical-align:-1px; margin-right:6px; background:#F6F1E9; border:1px solid #EADFCF; }
.cf-wk-legend i.miss{ background:var(--cf-amber-soft); border:2px solid #E7A962; } .cf-wk-legend i.adj{ background:var(--cf-primary-soft); border:2px dashed var(--cf-primary); }
/* 週班表右側：AI 提醒 */
.cf-aip{ background:#FFFFFF; border:1px solid var(--cf-line); border-radius:24px; overflow:hidden; }
.cf-aip-head{ display:flex; align-items:center; gap:12px; padding:16px 20px; border-bottom:1px solid var(--cf-line); }
.cf-aip-head .ic{ width:40px; height:40px; border-radius:12px; background:var(--cf-ai-1); display:flex; align-items:center; justify-content:center; flex:none; }
.cf-aip-head b{ display:block; font-size:calc(20px * var(--cf-s)); color:var(--cf-ink); }
.cf-aip-head span{ display:block; font-size:calc(15px * var(--cf-s)); color:var(--cf-muted); }
.cf-aip-body{ padding:14px 18px 18px; display:grid; gap:12px; }
.cf-aip-item{ background:#FBF7F0; border-radius:16px; padding:14px 16px; }
.cf-aip-item.warn{ background:var(--cf-amber-soft); }
.cf-aip-item b{ display:block; font-size:calc(21px * var(--cf-s)); color:var(--cf-ink); line-height:1.4; }
.cf-aip-item.warn b{ color:var(--cf-amber-ink); }
.cf-aip-item span{ display:block; font-size:calc(17px * var(--cf-s)); color:var(--cf-text); margin-top:4px; line-height:1.6; }
@media (max-width:900px){ .cf-hero2{ padding:22px; } .cf-hero2 .big{ font-size:calc(32px * var(--cf-s)); } }
</style>
"""


STEP_LABELS = {'import': '匯入資料', 'schedule': '開始排班', 'issues': '處理問題', 'review': '確認班表', 'analytics': '看成效',
               'accounts': '帳號管理'}
_CIRCLED = '①②③④⑤'


FLOW_KEYS = ['import', 'schedule', 'issues', 'review']   # 排班作業 1→4；analytics 為主管報表，獨立放右側


def render_stepper(current, done=(), locked=None, warn=None):
    """方案 A：頂部步驟列是唯一的換頁方式。

    done：已完成的模組；locked：{模組: 尚未解鎖原因}；warn：{模組: 提醒文字}（例如資料已變更需重新排班）。
    每顆按鈕 key 固定為 cfnav_<模組>；外層容器 key 帶狀態（cfstep_now／done／todo／lock／warn）供 CSS 上色。
    """
    locked, warn = dict(locked or {}), dict(warn or {})
    with st.container(key='cfsteps'):
        cols = st.columns([1, 1, 1, 1, 0.08, 0.9], gap='small')
        for i, key in enumerate(FLOW_KEYS + ['analytics']):
            col = cols[i] if i < 4 else cols[5]
            if key in locked:
                state, mark = 'lock', '🔒'
            elif key == current:
                state, mark = 'now', ('⚠' if key in warn else _CIRCLED[i] if i < 4 else '📊')
            elif key in warn:
                state, mark = 'warn', '⚠'
            elif key in done:
                state, mark = 'done', '✓'
            else:
                state, mark = 'todo', (_CIRCLED[i] if i < 4 else '📊')
            label = STEP_LABELS[key] if i < 4 else '主管報表'
            tip = locked.get(key) or warn.get(key) or module_label(key)
            with col.container(key=f'cfstep_{state}_{"mgr_" if i == 4 else ""}{key}'):
                st.button(f'{mark}  {label}', key=f'cfnav_{key}', on_click=go_to_module, args=(key,),
                          disabled=key in locked, width='stretch', help=tip)


def _action_click(target, callback):
    if callback:
        callback()
    if target:
        st.session_state['cf_module'] = target


def step_action_bar(current, label=None, target=None, hint='', disabled=False, help=None, on_click=None, tone='info'):
    """每頁底部固定的操作列：左＝上一步、中＝這一頁還差什麼、右＝唯一的主按鈕。

    target：主按鈕要前往的模組；on_click：額外的回呼（先於換頁執行）。label 為 None 時不顯示主按鈕。
    """
    index = FLOW_KEYS.index(current) if current in FLOW_KEYS else None
    prev = FLOW_KEYS[index - 1] if index else ('review' if current == 'analytics' else None)
    with st.container(key=f'cfactionbar_{tone}'):
        left, middle, right = st.columns([1, 2.1, 1.5], vertical_alignment='center')
        if prev:
            left.button(f'← 上一步：{STEP_LABELS[prev]}', key=f'cfbar_prev_{current}', on_click=go_to_module,
                        args=(prev,), width='stretch')
        if hint:
            middle.markdown(f'<div class="cf-bar-hint">{_e(hint)}</div>', unsafe_allow_html=True)
        if label:
            right.button(label, key=f'cfbar_next_{current}', type='primary', disabled=disabled, help=help,
                         on_click=_action_click, args=(target, on_click), width='stretch')


_CARD_MARK = {'done': '✓', 'warn': '!', 'lock': '🔒'}


def import_card(number, title):
    """① 匯入資料的打勾卡片。回傳 (容器, set_head)；set_head(state, summary) 可在資料讀完後再更新標題列。

    state：done（✓ 已完成）／now（進行中）／warn（需要處理）／lock（要先完成前一張）。
    """
    box = st.container(key=f'cfimport_card_{number}', border=True)
    head = box.empty()

    def set_head(state, summary=''):
        mark = _CARD_MARK.get(state, _CIRCLED[number - 1])
        head.markdown(f'<div class="cf-icard {state}"><span class="cf-icard-mark">{_e(mark)}</span>'
                      f'<div><b>{_e(title)}</b><span>{_e(summary)}</span></div></div>', unsafe_allow_html=True)

    set_head('now')
    return box, set_head


# ② 開始排班：執行過程的五個步驟（st.status 內逐步打勾）
RUN_STEPS = ['讀取資料', '查詢交通時間', '篩選資格', '最佳化求解', '完成']


def run_stage_of(text):
    """把排班引擎的進度文字對應到 RUN_STEPS 的位置（只會往前，由呼叫端取最大值）。"""
    text = str(text or '')
    if '全期間排班完成' in text:
        return 4
    if any(word in text for word in ('配對', '請假代班', '轉場最佳化', '最終交通')):
        return 3
    if any(word in text for word in ('首選', '核對')):
        return 2
    return 1


def run_steps_markdown(stage, detail=''):
    """步驟清單：已完成 ✅、進行中 ⏳（附目前細節）、尚未開始 ○。"""
    lines = []
    for i, name in enumerate(RUN_STEPS):
        if i < stage or stage == len(RUN_STEPS) - 1:
            lines.append(f'✅ {name}')
        elif i == stage:
            lines.append(f'⏳ **{name}**' + (f'　·　{detail}' if detail else ''))
        else:
            lines.append(f'○ {name}')
    return '  \n'.join(lines)


def run_card_html(title, sub):
    """② 排班前的大卡標題。"""
    return f'<div class="cf-runcard"><b>{_e(title)}</b><span>{_e(sub)}</span></div>'


def signoff_head_html(finalized_at=None, stale=False):
    """④ 簽核清單上方的定稿狀態列。"""
    if finalized_at and not stale:
        return f'<div class="cf-final ok">✅ 已定稿　·　{_e(finalized_at)}　·　可在下方「匯出」下載班表；班表仍可修改，修改後需重新定稿。</div>'
    if finalized_at and stale:
        return f'<div class="cf-final warn">⚠ {_e(finalized_at)} 定稿後班表又有修改，請重新勾選並定稿。</div>'
    return '<div class="cf-final">尚未定稿：逐項確認後，按下方「✅ 定稿並匯出班表」。</div>'


def result_hero(title, total, assigned, rate, families_left=0, avg_travel=None):
    """02 結果主卡：一句話講結果＋進度條＋右側兩個大數字。"""
    left = max(0, int(total) - int(assigned))
    travel = f'{avg_travel:.1f}' if avg_travel is not None else '—'
    st.markdown(
        f'<section class="cf-hero2" aria-label="排班結果"><div class="main"><div class="eyebrow">{_e(title)}</div>'
        f'<div class="big">{int(total):,} 筆服務中，<br>已安排 <em>{int(assigned):,}</em> 筆</div>'
        f'<div class="bar" role="img" aria-label="完成 {rate:.1f}%"><i style="width:{max(0.0, min(100.0, rate)):.1f}%"></i></div>'
        f'<div class="foot">完成 <b>{rate:.1f}%</b>　·　平均每段交通 <b>{_e(travel)} 分鐘</b></div></div>'
        f'<div class="side"><div class="{"warn" if left else ""}"><b>{left:,} 筆</b><span>還沒排進'
        + (f'（{int(families_left)} 個家庭）' if families_left else '') + '</span></div>'
        f'<div><b>{_e(travel)} 分</b><span>平均每段交通</span></div></div></section>', unsafe_allow_html=True)


def family_heading(n):
    """「還有 N 個家庭需要您看一下」大標。"""
    if n:
        st.markdown(f'<div class="cf-family">還有 <em>{int(n)} 個家庭</em>需要您看一下</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="cf-family">所有家庭的服務都已排好 ✓</div>', unsafe_allow_html=True)


# ---------- 登入（第一次使用時建立主管帳號） ----------
_AUTH_TEXT = {
    'login': ('登入 HomeCare AI', '請輸入主管或居督的帳號與密碼。', '登入',
              '忘記密碼或帳號被鎖定，請主管在「👥 帳號管理」重設密碼。'),
    'setup': ('第一次使用：建立主管帳號', '系統還沒有任何帳號。先建立一位主管，之後由主管在「👥 帳號管理」新增居督帳號。',
              '建立主管帳號並登入', '主管可以使用全部功能，包含主管報表與帳號管理；請妥善保管密碼。'),
}


def auth_card(mode, min_length=8):
    """置中的登入卡片（只負責畫面，驗證在 app.py 呼叫 auth）。

    mode：login（帳號、密碼）／setup（第一次使用：帳號、姓名、密碼兩次）。
    元件 key：login_user、login_pw／setup_user、setup_name、setup_pw1、setup_pw2。
    回傳 (送出的欄位 dict 或 None, 訊息容器)；訊息容器給呼叫端放 st.error／st.success。
    """
    title, sub, button, foot = _AUTH_TEXT[mode]
    _, middle, _ = st.columns([1, 1.3, 1])
    with middle:
        st.markdown(run_card_html(title, sub), unsafe_allow_html=True)
        with st.form(f'cf_auth_{mode}', clear_on_submit=False):
            if mode == 'setup':
                username = st.text_input('帳號（英文或數字）', key='setup_user', placeholder='例如 boss01')
                name = st.text_input('姓名', key='setup_name', placeholder='畫面右側顯示用')
                password = st.text_input(f'密碼（至少 {min_length} 個字）', type='password', key='setup_pw1')
                confirm = st.text_input('再輸入一次密碼', type='password', key='setup_pw2')
            else:
                username = st.text_input('帳號', key='login_user')
                password = st.text_input('密碼', type='password', key='login_pw')
                name = confirm = None
            submitted = st.form_submit_button(button, type='primary', width='stretch')
        note = st.container()
        st.caption(foot)
    if not submitted:
        return None, note
    return {'username': username, 'name': name, 'password': password, 'confirm': confirm}, note
