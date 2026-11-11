"""04 頁的居服員打卡面板與執行對照：整頁 AppTest（需要 streamlit）。"""
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

st = pytest.importorskip('streamlit')
AppTest = pytest.importorskip('streamlit.testing.v1').AppTest

import caregiver_engine as engine  # noqa: E402
from checkin import store  # noqa: E402


def _workbook(tmp_path):
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
                            ('案家姓名對照', pd.DataFrame([{'案家ID': 'C', '姓名': '王小明'}])),
                            ('居服員姓名對照', pd.DataFrame(columns=['居服員ID', '姓名']))]:
            frame.to_excel(writer, sheet_name=name, index=False)


def test_review_page_publishes_today_and_shows_board(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('CAREFLOW_AGENCY_DIR', str(tmp_path))
    monkeypatch.setattr(engine, 'calc_travel_minutes', lambda *a, **k: 5.0)
    monkeypatch.setattr(engine, 'prefetch_osrm_travel_times', lambda *a, **k: None)
    monkeypatch.setattr(engine, 'prefetch_google_transit_pairs', lambda *a, **k: None)
    import monthly_scheduler
    monkeypatch.setattr(monthly_scheduler, 'prefetch_osrm_travel_times', lambda *a, **k: None)
    monkeypatch.setattr(st, 'pyplot', lambda *a, **k: None)
    monkeypatch.setattr(store, 'now', lambda: datetime(2026, 11, 2, 9, 20))      # 星期一 09:20，09:00 的班已逾時
    _workbook(tmp_path)
    app = AppTest.from_file(str(Path(engine.__file__).with_name('app.py')), default_timeout=90).run()
    app.date_input(key='cf_period_range').set_value((date(2026, 11, 1), date(2026, 11, 30))).run()
    app.button(key='cfnav_schedule').click().run()
    app.button(key='run_full_period').click().run()
    app.button(key='cfnav_review').click().run()
    assert not app.exception, [e.message for e in app.exception]
    page = ' '.join(m.value for m in app.markdown)
    assert '居服員打卡' in page and '③ 打卡看板' in page
    # 新順序：① 發布 → ② 打卡網址／手機綁定／補登 → ③ 打卡看板（今天／整段期間對照分頁）
    assert page.index('① 發布班表') < page.index('② 打卡網址、手機綁定與補登覆核') < page.index('③ 打卡看板')
    app.button(key='cf_checkin_view__tab0').click().run()                       # ② 打卡網址
    assert not app.exception, [e.message for e in app.exception]
    app.button(key='checkin_publish_today').click().run()                       # ① 發布班表（不在分頁裡）
    assert not app.exception, [e.message for e in app.exception]
    assert any('已發布 2026/11/02 的班 1 筆' in s.value for s in app.success)
    assert store.shifts_for('A', date(2026, 11, 2)) or store.shifts_for('B', date(2026, 11, 2))
    raw = ' '.join(str(v) for row in store.connect().execute('SELECT * FROM shifts') for v in row)
    assert '小明' not in raw                                                    # 只存遮罩姓名
    assert not app.exception, [e.message for e in app.exception]                 # ③ 打卡看板預設「今天」
    assert any('逾時未打卡' in ' '.join(map(str, df.value['狀態'])) for df in app.dataframe if '狀態' in df.value)
