"""主管報表（一頁式）：三大數字、建議、報告圖檔，以及頁面能正常顯示。"""
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

import caregiver_engine as engine
import manager_report as mr


def _workload():
    return pd.DataFrame({'居服員': ['A', 'B', 'C'], '服務次數': [20, 5, 3], '工作天數': [20, 5, 3],
                         '總工時': [150.0, 40.0, 20.0], '日均工時': [7.5, 8.0, 6.7], '轉場工時': [10.0, 2.0, 1.0],
                         '月加班(含期外)': [50.0, 0.0, 0.0], '月加班上限': [46.0, 46.0, 46.0],
                         '加班使用率': [50 / 46, 0.0, 0.0], '狀態': ['超過上限', '正常', '正常']})


def _dashboard():
    cols = ['09時', '10時']
    demand = pd.DataFrame([[3.0, 1.0]], index=['週一'], columns=cols)
    supply = pd.DataFrame([[2.0, 2.0]], index=['週一'], columns=cols)
    return {'summary': {'total': 10, 'assigned': 8, 'unassigned': 2},
            'heat_demand': demand, 'heat_supply': supply, 'heat_pressure': demand / supply,
            'workload': _workload(),
            'reasons': pd.DataFrame([{'原因': '時段衝突', '未派筆數': 2, '涉及案家': 1, '建議處理': '改時段'}])}


def test_headline_cards_numbers():
    cards = mr.headline_cards(4, 3, 12.5, 70, 30, 10, 8, run_seconds=12.3)
    assert [c['title'] for c in cards] == ['省下的排班工時', '交通時間減少', '服務完成率']
    assert cards[0]['number'] == '4.0 小時'          # 4 − 3/60 = 3.95 → 4.0
    assert cards[1]['number'] == '12.5%'
    assert '每月省 10 小時' == cards[1]['before']     # 70 × 0.125 ÷ 0.875
    assert cards[2]['number'] == '80.0%' and '2 筆未派' in cards[2]['note']


def test_advice_and_load():
    D = _dashboard()
    advice = mr.staffing_advice(D)
    titles = [t for t, _ in advice]
    assert any('週一 09時：建議增聘 1 名' == t for t in titles)
    assert any(t.startswith('A：建議調出') for t in titles)
    assert any('2 筆服務未派出' in t for t in titles)
    load = mr.load_distribution(D['workload'])
    assert list(load.columns) == mr.STATUS_ORDER
    assert load.loc['A', '超過上限'] == 150.0 and load.loc['B', '正常'] == 40.0


def test_report_files():
    D = _dashboard()
    heat, title, fmt = mr.heat_view(D)
    fig = mr.build_report_figure('11 月 主管報表', '2026-11-01 ～ 2026-11-30', mr.headline_cards(4, 3, 12.5, 70, 30, 10, 8),
                                 heat, title, fmt, mr.load_distribution(D['workload']), mr.staffing_advice(D))
    assert mr.figure_bytes(fig, 'png')[:8] == b'\x89PNG\r\n\x1a\n'
    assert mr.figure_bytes(fig, 'pdf')[:5] == b'%PDF-'


def test_analytics_page_renders(tmp_path, monkeypatch):
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
    assert not app.exception, [e.message for e in app.exception]
    app.button(key='cfnav_analytics').click().run()
    assert not app.exception, [e.message for e in app.exception]
    page = ' '.join(m.value for m in app.markdown)
    for text in ('省下的排班工時', '交通時間減少', '服務完成率', '需求熱圖', '人力負荷分布', 'AI 增聘和調派建議', '下載報告'):
        assert text in page, text
    assert '100.0%' in page                       # 9 筆全部派出
    assert len(app.get('download_button')) >= 2   # PDF、PNG
