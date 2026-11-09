"""05 › 🎯 試辦 KPI 整頁測試（AppTest）：排班後切到試辦 KPI，3 組都出現、A1 數字正確、存成試辦月會寫進 KPI 資料檔。

需要 streamlit；沒裝時整檔略過。資料與 KPI 資料檔都在 tmp_path（conftest 設 CAREFLOW_KPI_DB）。
"""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip('streamlit.testing.v1')
import streamlit as st  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

import caregiver_engine as engine  # noqa: E402
import kpi_metrics as km  # noqa: E402


def _app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('CAREFLOW_AGENCY_DIR', str(tmp_path))
    monkeypatch.setattr(engine, 'calc_travel_minutes', lambda *a, **k: 5.0)
    monkeypatch.setattr(engine, 'prefetch_osrm_travel_times', lambda *a, **k: None)
    monkeypatch.setattr(engine, 'prefetch_google_transit_pairs', lambda *a, **k: None)
    import monthly_scheduler
    monkeypatch.setattr(monthly_scheduler, 'prefetch_osrm_travel_times', lambda *a, **k: None)
    monkeypatch.setattr(st, 'pyplot', lambda *a, **k: None)
    employees = pd.DataFrame([{'編號': i, '性別': '女', '休息日': '星期日', '取得資格': '失智症照顧服務20小時',
                               '交通工具': '機車', '經度 (WGS84_Lon)': 121.53, '緯度 (WGS84_Lat)': 25.03} for i in ['A', 'B']])
    clients = pd.DataFrame([{'內部案號': 'C', '經度 (WGS84_Lon)': 121.54, '緯度 (WGS84_Lat)': 25.04}])
    weekly = pd.DataFrame([{'案號': 'C', '星期': wd, '開始時間': s, '結束時間': e, '服務分鐘': 60, '頻率': '每週',
                            '生效日': '2026-11-02', '服務項目': 'SA10(1)', '費用類型': '基本',
                            '經度 (WGS84_Lon)': 121.54, '緯度 (WGS84_Lat)': 25.04}
                           for wd, s, e in [('星期一', '09:00', '10:00'), ('星期三', '15:00', '16:00')]])
    master = pd.DataFrame([{'系統代碼': 'SA10', '服務名稱': '自費服務', '目前給付價格(元)': 350,
                            'CareFlow排班分鐘(暫定)': 60, '是否納入CareFlow': '是'}])
    with pd.ExcelWriter(tmp_path / '居服機構資料_三工作表.xlsx', engine='openpyxl') as writer:
        for name, frame in [('員工資料', employees), ('個案資料', clients), ('週服務計畫', weekly), ('Service_code', master),
                            ('案家姓名對照', pd.DataFrame(columns=['案家ID', '姓名'])),
                            ('居服員姓名對照', pd.DataFrame(columns=['居服員ID', '姓名']))]:
            frame.to_excel(writer, sheet_name=name, index=False)
    app = AppTest.from_file(str(Path(engine.__file__).with_name('app.py')), default_timeout=90).run()
    app.date_input(key='cf_period_range').set_value((date(2026, 11, 1), date(2026, 11, 30))).run()
    app.button(key='cfnav_schedule').click().run()
    app.button(key='run_full_period').click().run()
    app.button(key='cfnav_analytics').click().run()
    return app


def test_pilot_kpi_page_renders_and_saves(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    assert not app.exception, [e.message for e in app.exception]
    app.button(key='cf_analytics_view__tab1').click().run()           # 🎯 試辦 KPI
    assert not app.exception, [e.message for e in app.exception]
    page = ' '.join(m.value for m in app.markdown)
    for text in ('服務量能', '照顧品質', '人力負荷與成本', 'A1 派案成功率', 'C4 加班合規', '逐項指標', '基準月 vs 試辦月'):
        assert text in page, text
    assert '100.0%' in page                                          # 9 筆全部派出 → A1 = 100.0%
    app.button(key='cf_kpi_save').click().run()                       # 預設存成本期月份的試辦月
    assert not app.exception, [e.message for e in app.exception]
    saved = km.saved_months('中化')
    assert km.month_options(saved, km.PILOT) == ['2026-11']
    assert km.month_values(saved, '2026-11', km.PILOT)['A1']['value'] == 100.0
