"""從 AI_HomeCare_Atrust 移植的功能（整頁測試）：週計畫異動、復原上一步、CSMS 申報、異動紀錄、錯誤紀錄。

用 tmp_path 產生最小機構 Excel（2 位居服員、2 個案家），交通查詢一律換成固定 5 分鐘。
"""
from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

AppTest = pytest.importorskip('streamlit.testing.v1').AppTest
import streamlit as st

import caregiver_engine as engine
import error_log
import plan_versions as pv


def _setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('CAREFLOW_AGENCY_DIR', str(tmp_path))
    monkeypatch.setattr(error_log, 'LOG_DIR', tmp_path / 'logs')
    monkeypatch.setattr(engine, 'calc_travel_minutes', lambda *a, **k: 5.0)
    import traffic_wake
    monkeypatch.setattr(traffic_wake, 'is_ready', lambda host: True)   # 測試不等真的交通主機開機
    monkeypatch.setattr(engine, 'prefetch_osrm_travel_times', lambda *a, **k: None)
    monkeypatch.setattr(engine, 'prefetch_google_transit_pairs', lambda *a, **k: None)
    import monthly_scheduler
    monkeypatch.setattr(monthly_scheduler, 'prefetch_osrm_travel_times', lambda *a, **k: None)
    monkeypatch.setattr(st, 'pyplot', lambda *a, **k: None)
    employees = pd.DataFrame([{'編號': i, '性別': '女', '休息日': '星期日', '取得資格': '失智症照顧服務20小時',
                               '交通工具': '機車', '經度 (WGS84_Lon)': 121.53, '緯度 (WGS84_Lat)': 25.03} for i in ['A', 'B']])
    clients = pd.DataFrame([{'內部案號': c, '歷史首選': 'A', '是否失智': '否', '經度 (WGS84_Lon)': 121.54,
                             '緯度 (WGS84_Lat)': 25.04} for c in ['C', 'D']])
    weekly = pd.DataFrame([{'案號': c, '星期': d, '開始時間': s, '結束時間': e, '服務分鐘': 60, '頻率': '每週',
                            '生效日': '2026-11-02', '服務項目': 'SA10(1)', '費用類型': '自費',
                            '經度 (WGS84_Lon)': 121.54, '緯度 (WGS84_Lat)': 25.04}
                           for c, d, s, e in [('C', '星期一', '09:00', '10:00'), ('C', '星期三', '15:00', '16:00'),
                                              ('D', '星期二', '09:00', '10:00')]])
    master = pd.DataFrame([{'系統代碼': 'SA10', '服務名稱': '自費服務', '目前給付價格(元)': 350,
                            'CareFlow排班分鐘(暫定)': 60, '是否納入CareFlow': '是'}])
    with pd.ExcelWriter(tmp_path / '居服機構資料_三工作表.xlsx', engine='openpyxl') as writer:
        for name, frame in [('員工資料', employees), ('個案資料', clients), ('週服務計畫', weekly), ('Service_code', master),
                            ('案家姓名對照', pd.DataFrame(columns=['案家ID', '姓名'])),
                            ('居服員姓名對照', pd.DataFrame(columns=['居服員ID', '姓名']))]:
            frame.to_excel(writer, sheet_name=name, index=False)


def _scheduled_app():
    app = AppTest.from_file(str(Path(engine.__file__).with_name('app.py')), default_timeout=120).run()
    app.date_input(key='cf_period_range').set_value((date(2026, 11, 1), date(2026, 11, 30))).run()
    app.button(key='cfnav_schedule').click().run()
    app.button(key='run_full_period').click().run()
    assert not app.exception, [e.message for e in app.exception]
    return app


def _open_plan_change(app):
    """③ 處理問題 › 臨時異動 › 🕒 案家臨時改期 › 從某天起都改。"""
    app.button(key='cfnav_issues').click().run()
    app.button(key='cf_issue_view__tab2').click().run()
    app.button(key='dynamic_event_type_selector__tab2').click().run()
    app.button(key='cf_resched_mode__tab1').click().run()
    assert not app.exception, [e.message for e in app.exception]
    app.selectbox(key='cf_pv_client').select('C').run()
    app.date_input(key='cf_pv_effective').set_value(date(2026, 11, 16)).run()
    assert not app.exception, [e.message for e in app.exception]


def test_plan_change_replaces_only_tasks_from_effective_date_and_undo(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    app = _scheduled_app()
    before = app.session_state['last_result']['df_tasks'].copy()
    assert {'W0002_20261116', 'W0002_20261123', 'W0002_20261130'} <= set(before['任務ID'])
    assert not any(b.key == 'cf_undo_last' for b in app.sidebar.button)       # 剛排完班：沒有可復原的
    _open_plan_change(app)
    assert not any(b.key == 'cf_undo_last' for b in app.sidebar.button)       # 只是打開畫面不算一步
    assert app.button(key='cf_pv_preview').disabled                            # 還沒改任何東西

    # 「範例：改時間」：週一 09:00～10:00 往後 1 小時，週三不變
    app.button(key='cf_pv_ex_move_C_2026-11-16').click().run()
    assert app.selectbox(key='cf_pv_act_C_2026-11-16_0').value == '改時間'
    assert app.selectbox(key='cf_pv_s_C_2026-11-16_0').value == '10:00'
    app.button(key='cf_pv_preview').click().run()
    assert not app.exception, [e.message for e in app.exception]
    assert not app.error, [e.value for e in app.error]
    preview = app.session_state['_pv_preview']
    assert preview['removed'] == ['W0002_20261116', 'W0002_20261123', 'W0002_20261130']
    assert [p['task']['任務ID'] for p in preview['picks']] == ['W0005_20261116', 'W0005_20261123', 'W0005_20261130']
    assert all(p['cg_id'] == 'A' for p in preview['picks'])

    app.button(key='cf_pv_commit').click().run()
    assert not app.exception, [e.message for e in app.exception]
    result = app.session_state['last_result']
    ids = set(result['df_tasks']['任務ID'])
    assert not ids & set(preview['removed'])
    assert {'W0005_20261116', 'W0005_20261123', 'W0005_20261130'} <= ids
    assert result['plan_version_log'][0]['生效日'] == '2026-11-16'
    weekly = pv.read_weekly(result['plan_version_bytes'])
    assert weekly.loc[weekly['來源列'] == 2, '到期日'].astype(str).iloc[0].startswith('2026-11-15')
    reloaded = engine.load_agency_workbook(BytesIO(result['plan_version_bytes']), '2026-11-01', '2026-11-30')['Tasks']
    assert set(reloaded['任務ID']) == ids

    # 復原上一步：側邊欄按鈕，回到異動前
    app.run()
    button = next(b for b in app.sidebar.button if b.key == 'cf_undo_last')
    assert '週計畫異動' in button.label
    button.click().run()
    assert not app.exception, [e.message for e in app.exception]
    assert set(app.session_state['last_result']['df_tasks']['任務ID']) == set(before['任務ID'])
    assert not app.session_state['last_result'].get('plan_version_log')
    assert any('已復原：週計畫異動' in s.value for s in app.sidebar.success)


def test_review_page_has_billing_and_change_log(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    app = _scheduled_app()
    app.button(key='cfnav_review').click().run()
    assert not app.exception, [e.message for e in app.exception]
    assert app.selectbox(key='cf_billing_month').value == '2026-11'
    assert any(d.key == 'cf_billing_download' for d in app.get('download_button'))
    page = ' '.join(m.value for m in app.markdown)
    assert 'CSMS 申報與自付額試算' in page and '異動紀錄' in page


def test_swallowed_error_is_logged_and_listed_in_sidebar(tmp_path, monkeypatch):
    import session_store
    _setup(tmp_path, monkeypatch)

    def broken(*a, **k):
        raise RuntimeError('存檔資料庫壞了')
    monkeypatch.setattr(session_store, 'save', broken)
    app = _scheduled_app()                                                   # 自動存檔失敗，畫面照常
    errors = app.session_state['_error_log']
    assert any(e['位置'] == '自動存檔' and '存檔資料庫壞了' in e['錯誤'] for e in errors)
    assert '存檔資料庫壞了' in (tmp_path / 'logs' / 'careflow_errors.log').read_text(encoding='utf-8')
    app.run()                                                                # 下一次畫面重跑，側邊欄就看得到
    assert any('系統錯誤' in e.label for e in app.sidebar.expander)
