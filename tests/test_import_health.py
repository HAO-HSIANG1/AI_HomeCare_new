import pandas as pd

from import_health import build_health_items, health_status, issue_light, RED, AMBER, GREEN


def _frames():
    cg = pd.DataFrame({'居服員ID': ['A', 'B'], '服務起點_緯度(家)': [25.0, None], '服務起點_經度(家)': [121.5, 121.5]})
    cl = pd.DataFrame({'案家ID': ['C'], '服務地點_緯度': [25.0], '服務地點_經度': [121.5]})
    tasks = pd.DataFrame({'任務ID': ['T1'], '案家ID': ['C']})
    return cg, cl, tasks


def test_issue_light():
    assert issue_light('缺案號或無法對應個案表，暫不產生任務') == RED
    assert issue_light('請假區間無效或零時數；此員工暫停派單') == RED
    assert issue_light('歷史首選無法對應員工編號；該案暫不換人') == AMBER
    assert issue_light('是否失智空白或無法辨識，請填是／否') == AMBER


def test_items_lights_and_privacy():
    cg, cl, tasks = _frames()
    issues = pd.DataFrame([
        {'資料表': '員工資料', '來源列': None, '問題': '個資保護：排班運算已移除直接識別欄位：姓名'},
        {'資料表': '週服務', '來源列': 5, '問題': '頻率無法辨識，暫不產生任務'},
        {'資料表': '個案', '來源列': 3, '問題': '是否失智空白或無法辨識，請填是／否'},
    ])
    ba = pd.DataFrame({'任務ID': ['T1'], '案家ID': ['C'], 'BA代碼檢核異常': [None], '含違規代碼': [False]})
    items, privacy = build_health_items(issues, cg, cl, tasks, ba)
    by_key = {i['key']: i for i in items}
    assert '姓名' in privacy
    assert by_key['caregivers']['light'] == AMBER          # 1 位缺座標
    assert by_key['clients']['light'] == AMBER             # 是否失智空白
    assert by_key['tasks']['light'] == RED                 # 週服務列暫不產生任務
    assert len(by_key['tasks']['issues']) == 1
    assert by_key['service_code']['light'] == GREEN
    overall, reds, ambers = health_status(items)
    assert (overall, reds, ambers) == (RED, 1, 2)


def test_empty_tasks_is_red_and_clean_data_is_green():
    cg, cl, _ = _frames()
    cg['服務起點_緯度(家)'] = 25.0
    items, _ = build_health_items(pd.DataFrame(columns=['資料表', '來源列', '問題']), cg, cl, pd.DataFrame())
    by_key = {i['key']: i for i in items}
    assert by_key['tasks']['light'] == RED
    assert by_key['caregivers']['light'] == GREEN and by_key['clients']['light'] == GREEN
