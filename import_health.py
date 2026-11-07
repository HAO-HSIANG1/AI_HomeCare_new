"""① 匯入資料的「資料健檢」：把匯入問題、座標與服務碼組合檢查整理成燈號清單。

純函式、不碰 Streamlit，方便測試。每一項對應一張可編輯的資料表（sheet 為 app.py 的 session key），
週服務計畫的匯入問題只能改原始 Excel（那些列根本沒有產生任務，編輯任務表救不回來）。
"""
import pandas as pd

RED, AMBER, GREEN = 'red', 'amber', 'green'
LIGHT_ICON = {RED: '🔴', AMBER: '🟡', GREEN: '🟢'}
_RANK = {GREEN: 0, AMBER: 1, RED: 2}

# Import_Issues 的「資料表」欄 → 健檢項目
_ISSUE_TABLE = {'員工': 'caregivers', '員工資料': 'caregivers', '個案': 'clients', '個案資料': 'clients',
                '週服務': 'tasks', '週服務計畫': 'tasks'}


_NOT_SCHEDULED = ('暫不產生任務', '暫不匯入', '暫不派單', '暫停派單')   # 「該案暫不換人」仍會排班，不算紅燈


def issue_light(text):
    """匯入問題的嚴重度：該列資料因此不排班（暫不匯入／暫不產生任務／暫不派單／暫停派單）為紅燈，其餘為黃燈。"""
    text = str(text or '')
    return RED if any(word in text for word in _NOT_SCHEDULED) else AMBER


def _worst(lights):
    return max(lights, key=_RANK.get) if lights else GREEN


def _missing_coords(frame, lat, lon):
    if frame is None or frame.empty or lat not in frame or lon not in frame:
        return pd.Series(False, index=getattr(frame, 'index', None))
    return pd.to_numeric(frame[lat], errors='coerce').isna() | pd.to_numeric(frame[lon], errors='coerce').isna()


def build_health_items(import_issues, caregivers, clients, tasks, ba_preview=None):
    """回傳 (items, privacy_note)。

    items：依序為 居服員資料、案家資料、服務任務、服務碼清單，每項 dict：
      key, title, sheet（可編輯的 session key 或 None）, light, summary（一句話）, findings（[(燈號, 文字)]）,
      issues（該項的匯入問題 DataFrame，可能為空）, extra（額外表格，例如服務碼組合提醒，可能為 None）, fix（修正方式）。
    privacy_note：個資欄位自動移除的說明（沒有則為空字串），不算問題。
    """
    issues = import_issues if import_issues is not None else pd.DataFrame(columns=['資料表', '來源列', '問題'])
    is_privacy = issues['問題'].astype(str).str.startswith('個資保護')
    privacy_note = '；'.join(issues.loc[is_privacy, '問題'].astype(str).str.replace('個資保護：', '', regex=False)
                             + '（' + issues.loc[is_privacy, '資料表'].astype(str) + '）')
    issues = issues.loc[~is_privacy].copy()
    issues['燈號'] = [LIGHT_ICON[issue_light(t)] for t in issues['問題']]
    group = issues['資料表'].map(lambda v: _ISSUE_TABLE.get(str(v), 'tasks'))

    def table_findings(name):
        part = issues.loc[group.eq(name), ['燈號', '資料表', '來源列', '問題']].reset_index(drop=True)
        findings = []
        for light in (RED, AMBER):
            rows = part.loc[part['燈號'].eq(LIGHT_ICON[light])]
            if not rows.empty:
                verb = '筆這次不會排班' if light == RED else '筆需要補正'
                findings.append((light, f'匯入時有 {len(rows)} {verb}'))
        return part, findings

    items = []

    # 居服員資料
    cg_issues, cg_find = table_findings('caregivers')
    n_cg = 0 if caregivers is None else len(caregivers)
    if n_cg == 0:
        cg_find.insert(0, (RED, '沒有任何居服員資料'))
    cg_coord = _missing_coords(caregivers, '服務起點_緯度(家)', '服務起點_經度(家)')
    if cg_coord.any():
        cg_find.append((AMBER, f'{int(cg_coord.sum())} 位居服員缺住家座標，交通時間可能查不到'))
    items.append(dict(key='caregivers', title='居服員資料', sheet='edit_cg', issues=cg_issues, extra=None,
                      findings=cg_find, ok=f'{n_cg:,} 位居服員，資料完整',
                      fix='資格、休息日、交通工具與座標可在下方表格直接修改；修改只套用到這次排班，原始 Excel 不會變。'))

    # 案家資料
    cl_issues, cl_find = table_findings('clients')
    n_cl = 0 if clients is None else len(clients)
    if n_cl == 0:
        cl_find.insert(0, (RED, '沒有任何案家資料'))
    cl_coord = _missing_coords(clients, '服務地點_緯度', '服務地點_經度')
    if cl_coord.any():
        cl_find.append((AMBER, f'{int(cl_coord.sum())} 戶案家缺服務地點座標，交通時間可能查不到'))
    items.append(dict(key='clients', title='案家資料', sheet='edit_cl', issues=cl_issues, extra=None,
                      findings=cl_find, ok=f'{n_cl:,} 戶案家，資料完整',
                      fix='「暫不匯入」的案家（例如缺內部案號）不在下方表格裡，請補好原始 Excel 後重新上傳；其餘可直接修改。'))

    # 服務任務（週服務計畫展開後）
    tk_issues, tk_find = table_findings('tasks')
    n_tk = 0 if tasks is None else len(tasks)
    if n_tk == 0:
        tk_find.insert(0, (RED, '排班期間內沒有任何服務任務，請確認排班期間或週服務計畫的生效日'))
    extra = None
    if ba_preview is not None and '含違規代碼' in ba_preview:
        flagged = ba_preview.loc[ba_preview['含違規代碼'].astype(bool)]
        if not flagged.empty:
            tk_find.append((AMBER, f'{len(flagged)} 筆服務碼組合需要複核（只提醒，不影響排班）'))
            extra = flagged[[c for c in ['任務ID', '案家ID', 'BA代碼檢核異常'] if c in flagged]].reset_index(drop=True)
    items.append(dict(key='tasks', title='服務任務', sheet='edit_tasks', issues=tk_issues, extra=extra,
                      findings=tk_find, ok=f'{n_tk:,} 筆服務，沒有需要處理的項目',
                      fix='匯入時被略過的週服務列沒有產生任務，下方表格改不到，請修正原始 Excel 後重新上傳；'
                          '服務碼組合提醒由居督複核即可，可直接在下方表格修正服務代碼。'))

    # 服務碼清單：目前沒有自動檢查，保留編輯入口
    items.append(dict(key='service_code', title='服務碼清單', sheet='edit_service_code', issues=None, extra=None,
                      findings=[], ok='機構資料採週服務計畫的服務分鐘，此表只供檢視',
                      fix='機構資料採已提供服務分鐘，不用未核定的 Master 覆蓋。'))

    for item in items:
        item['light'] = _worst([light for light, _ in item['findings']])
        item['summary'] = '；'.join(text for _, text in item['findings']) or item['ok']
    return items, privacy_note


def health_status(items):
    """整體燈號與紅燈項目數。"""
    reds = sum(1 for item in items if item['light'] == RED)
    ambers = sum(1 for item in items if item['light'] == AMBER)
    return _worst([item['light'] for item in items]), reds, ambers
