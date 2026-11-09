"""試辦 KPI（kpi_metrics.py）：3 組 8 項，每項用小資料手算核對分子、分母與數值，另測基準月／試辦月儲存與比較。"""
import pandas as pd

import kpi_metrics as km


def _tasks():
    return pd.DataFrame({
        '任務ID': ['T1', 'T2', 'T3', 'T4'],
        '案家ID': ['C1', 'C1', 'C2', 'C3'],
        '日期': ['2026-10-01', '2026-10-01', '2026-10-01', '2026-10-02'],
        '時間窗_開始': ['08:00', '10:00', '09:30', '08:00'],
        '時間窗_結束': ['09:00', '11:00', '10:30', '09:00'],
    })


def _assign():
    # T1、T3 給 A（時段不重疊），T2 給 B，T4 未派
    return pd.DataFrame({'任務ID': ['T1', 'T2', 'T3', 'T4'], '派單居服員': ['A', 'B', 'A', '未指派']})


# ================ A 服務量能 ================

def test_a1_dispatch_rate():
    r = km.dispatch_rate(_tasks(), _assign())
    assert (r['分子'], r['分母'], r['數值']) == (3, 4, 75.0)          # 3 ÷ 4 × 100 = 75.0
    assert r['期間'] == '2026/10/01～2026/10/02' and r['組別'] == '服務量能'
    assert r['detail'].iloc[0]['任務ID'] == 'T4' and r['detail'].iloc[0]['結果'] == '未派'   # 未派排最前面


def test_a1_duplicate_task_rows_count_once():
    tasks = pd.concat([_tasks(), _tasks().iloc[[0]]], ignore_index=True)
    assert km.dispatch_rate(tasks, _assign())['分母'] == 4


def test_a2_unassigned_hours_and_reasons():
    tasks = pd.concat([_tasks(), pd.DataFrame([{'任務ID': 'T5', '案家ID': 'C3', '日期': '2026-10-02',
                                                '時間窗_開始': '13:00', '時間窗_結束': '13:30'}])], ignore_index=True)
    tasks['服務歷時(分鐘)'] = [60, 60, 60, 90, None]                  # T4 用服務歷時 90 分；T5 沒有，改用起迄 30 分
    diagnostics = [{'任務ID': 'T4', '問題分類': '時段重疊'}, {'任務ID': 'T5', '問題分類': '必要證照'}]
    r = km.unassigned_hours(tasks, _assign(), diagnostics)
    # 全部 60＋60＋60＋90＋30 = 300 分 = 5 小時；未派 T4 1.5＋T5 0.5 = 2 小時 → 2 ÷ 5 × 100 = 40.0
    assert (r['分子'], r['分母'], r['數值']) == (2.0, 5.0, 40.0)
    b = r['breakdown'].set_index('問題類型')
    assert (b.loc['班次重疊', '筆數'], b.loc['班次重疊', '時數'], b.loc['班次重疊', '占未派時數(%)']) == (1, 1.5, 75.0)
    assert (b.loc['條件不符', '時數'], b.loc['條件不符', '占未派時數(%)']) == (0.5, 25.0)
    assert list(r['breakdown']['問題類型']) == ['班次重疊', '條件不符']       # 時數多的排前面
    assert r['備註'] == '未派 2 筆'


def test_a2_all_assigned_is_zero():
    assign = pd.DataFrame({'任務ID': ['T1', 'T2', 'T3', 'T4'], '派單居服員': ['A', 'B', 'A', 'B']})
    r = km.unassigned_hours(_tasks(), assign)
    assert (r['分子'], r['分母'], r['數值'], r['備註']) == (0.0, 4.0, 0.0, '全部已派')


def test_a3_capacity_utilization_with_leave():
    caregivers = pd.DataFrame({'居服員ID': ['A', 'B', 'C'], '可排班星期': ['1,2,3,4,5', '1,2,3', ''],
                               '每日可服務時段_起': ['08:00', '09:00', ''], '每日可服務時段_迄': ['21:00', '13:00', ''],
                               '請假日期': ['', '', '2026-11-08']})
    leaves = [{'cg': 'A', 'start': '2026-11-03 10:00', 'end': '2026-11-03 17:00', 'reason': '請假'},     # 13 − 7 = 6 小時
              {'cg': 'A', 'start': '2026-11-04 08:00', 'end': '2026-11-04 21:00', 'reason': '看診'},     # 不是請假：不扣
              {'cg': 'B', 'start': '2026-11-02 00:00', 'end': '2026-11-02 23:59', 'reason': '請假'},     # 整天：0 小時
              {'cg': 'B', 'start': '2026-11-02 09:00', 'end': '2026-11-02 10:00', 'reason': '請假（補）'}]  # 重疊只算一次
    payroll = pd.DataFrame({'居服員ID': ['A', 'B', 'B'], '服務工時': [20, 4, 2], '轉場工時': [4, 1, 0]})
    r = km.capacity_utilization(caregivers, payroll, '2026-11-02', '2026-11-08', leaves=leaves)   # 星期一～星期日共 7 天
    # 可上班：A 5 天 8＋6＋8＋8＋8 = 38；B 3 天 0＋4＋4 = 8；C 每天但 11/08 請假日期 → 6 × 8 = 48 → 94 小時
    # 已排工時（服務＋轉場）：A 20＋4 = 24；B 4＋2＋1 = 7 → 31 ÷ 94 × 100 = 32.98 → 33.0
    assert (r['分子'], r['分母'], r['數值']) == (31.0, 94.0, 33.0)
    d = r['detail'].set_index('居服員ID')
    assert (d.loc['A', '可上班時數'], d.loc['A', '請假扣除時數'], d.loc['A', '利用率(%)']) == (38.0, 2.0, 63.2)
    assert (d.loc['B', '請假扣除時數'], d.loc['B', '利用率(%)'], d.loc['C', '請假扣除時數']) == (4.0, 87.5, 8.0)
    assert r['備註'] == '3 位居服員，其中 1 位本期沒有排班；已扣請假 14.0 小時'   # 2 + 4 + 8


def test_a3_without_caregivers_is_blank():
    assert km.capacity_utilization(None, None, '2026-11-02', '2026-11-08')['數值'] is None


# ================ B 照顧品質 ================

def test_b1_continuity_only_counts_clients_with_primary():
    r = km.continuity(_tasks(), _assign(), {'C1': 'A', 'C2': 'A'})
    # C1：T1 由 A（主責本人）、T2 由 B（其他人）；C2：T3 由 A（主責本人）；C3 沒有主責、T4 未派，都不算
    assert (r['分子'], r['分母'], r['數值']) == (2, 3, 66.7)          # 2 ÷ 3 × 100 = 66.67 → 66.7


# ================ C 人力負荷與成本 ================

def test_c1_average_travel_includes_first_leg():
    routes = pd.DataFrame({
        '任務ID': ['T1', 'T3', 'T2', 'T5', 'T6'],
        '預估車程(分)': [12.0, 8.0, 0.0, 20.0, None],
        '路段緩衝(分)': [0.0, 5.0, 0.0, 5.0, 5.0],
        '轉場時段檢查': ['首案，請確認出門時間', '轉場時間足夠', '轉場時間足夠', '轉場時間不足，需調班', ''],
    })
    r = km.transition_time(routes)
    # 首案出門 12 也算；車程 0、未算出不算；緩衝不算 → (12 + 8 + 20) ÷ 3 段 = 13.33 → 13.3
    assert (r['分子'], r['分母'], r['數值']) == (40.0, 3, 13.3)
    assert dict(zip(r['detail']['任務ID'], r['detail']['不計入原因'])) == \
        {'T1': '', 'T3': '', 'T2': '車程 0（同一案家接續或同地點）', 'T5': '', 'T6': '交通未算出'}


def test_c1_matches_manager_report_average():
    import numpy as np
    legs = pd.Series([12.0, 8.0, 0.0, 20.0, np.nan, 3.5])
    expected = legs[legs > 0].dropna().mean()            # dashboard_metrics.build_dashboard 的「交通 › 平均」
    assert km.transition_time(pd.DataFrame({'預估車程(分)': legs}))['數值'] == round(expected, 1)


def test_c2_transition_share():
    payroll = pd.DataFrame({'居服員ID': ['A', 'A', 'B', 'C'], '轉場工時': [3, 1, 1, 0], '總工時': [16, 8, 8, 0]})
    r = km.transition_share(payroll)
    # A 轉場 4／總 24、B 1／8、C 總工時 0 不算 → 5 ÷ 32 × 100 = 15.625 → 15.6
    assert (r['分子'], r['分母'], r['數值']) == (5.0, 32.0, 15.6)
    assert list(r['detail']['居服員ID']) == ['A', 'B'] and r['detail'].iloc[0]['轉場占比(%)'] == 16.7   # 4 ÷ 24


def test_c3_share_within_twenty_percent_of_mean():
    payroll = pd.DataFrame({'居服員ID': ['A', 'B', 'B', 'C', 'D', 'E'], '總工時': [100, 30, 20, 0, 80, 70]})
    r = km.workload_spread(payroll)
    # A 100、B 50、D 80、E 70（C 0 不算）；平均 75，±20% → 60～90：D、E 接近平均 → 2 ÷ 4 × 100 = 50.0
    assert (r['分子'], r['分母'], r['數值']) == (2, 4, 50.0)
    assert list(zip(r['detail']['居服員ID'], r['detail']['結果'])) == \
        [('A', '偏高'), ('B', '偏低'), ('D', '接近平均'), ('E', '接近平均')]
    assert list(r['detail']['和平均差距(%)']) == [33.3, -33.3, 6.7, -6.7]     # 100 ÷ 75 − 1 = 33.3%
    assert r['備註'] == '平均每人 75.0 小時，±20% 為 60.0～90.0 小時；偏高 1 人、偏低 1 人'


def test_c3_boundaries_count_as_near():
    r = km.workload_spread(pd.DataFrame({'居服員ID': ['A', 'B', 'C'], '總工時': [64, 80, 96]}))
    assert r['數值'] == 100.0                           # 平均 80；64 和 96 剛好在 80%、120%


def test_c3_single_worker_is_near_average():
    r = km.workload_spread(pd.DataFrame({'居服員ID': ['A'], '總工時': [80]}))
    assert (r['分子'], r['分母'], r['數值']) == (1, 1, 100.0)


def test_c4_overtime_compliance():
    payroll = pd.DataFrame({'居服員ID': ['A', 'B', 'B', 'D', 'E'], '總工時': [100, 40, 40, 120, 0],
                            '合計加班時數': [9, 0, 2, 12, 20], '月加班上限': [10, 10, 10, 10, 10]})
    r = km.overtime_compliance(payroll)
    # A 9 ÷ 10 = 90% 接近（仍合規）；B 取最大 2 ÷ 10 = 20% 正常；D 12 ÷ 10 = 120% 超過；E 沒排班不算
    # 沒有超過上限：A、B → 2 ÷ 3 × 100 = 66.7
    assert (r['分子'], r['分母'], r['數值']) == (2, 3, 66.7)
    assert list(r['detail']['居服員ID']) == ['D', 'A', 'B']                 # 超過 → 接近 → 正常
    assert list(r['detail']['狀態']) == ['超過上限', '接近上限', '正常']
    assert r['備註'] == '超過上限 1 人（不合規）、接近上限 1 人（合規但要留意）；加班合計 23.0 小時（含期外）'   # 9 + 2 + 12


def test_c4_near_limit_is_still_compliant():
    payroll = pd.DataFrame({'居服員ID': ['A', 'B'], '總工時': [10, 10], '合計加班時數': [8, 10], '月加班上限': [10, 10]})
    r = km.overtime_compliance(payroll)
    # A 80% 接近、B 剛好 100% 仍是接近（沒有超過）→ 2 ÷ 2 = 100.0
    assert list(r['detail']['狀態']) == ['接近上限', '接近上限'] and r['數值'] == 100.0


# ================ 組合、表格 ================

def test_compute_all_groups_and_table():
    results = km.compute_all(_tasks(), _assign())
    assert [r['代碼'] for r in results] == ['A1', 'A2', 'A3', 'B1', 'C1', 'C2', 'C3', 'C4']
    groups = km.by_group(results)
    assert [(g[0], g[1], len(g[3])) for g in groups] == [('A', '服務量能', 3), ('B', '照顧品質', 1), ('C', '人力負荷與成本', 4)]
    table = km.kpi_table(results)
    assert list(table.columns) == km.TABLE_COLUMNS
    row = table.set_index('代碼').loc['A1']
    assert (row['組別'], row['分子'], row['分母'], row['期間']) == ('服務量能', 3, 4, '2026/10/01～2026/10/02')
    assert row['計算方式'].startswith('已派 ÷ 全部服務')
    assert table.set_index('代碼').loc['C1', '備註'] == '尚無資料'      # 沒有交通資料：留空，不自行假設


def test_detail_table_has_codes():
    out = km.detail_table(km.compute_all(_tasks(), _assign()))
    assert set(out['代碼']) >= {'A1', 'A2'} and list(out.columns[:3]) == ['組別', '代碼', '指標']


# ================ 基準月／試辦月 ================

def test_manual_baseline_value():
    r = km.manual_result('A1', 70, 100, '2026-09 人工排班')
    assert (r['數值'], r['備註']) == (70.0, '人工登錄')
    assert km.manual_result('C1', 300, 20)['數值'] == 15.0           # 300 分 ÷ 20 段
    assert km.manual_result('A1', 5, 0)['數值'] is None


def test_save_and_compare_months(tmp_path):
    db = tmp_path / 'k.sqlite3'
    base = {'A1': {'numerator': 70, 'denominator': 100, 'value': 70.0},
            'C1': {'numerator': 300, 'denominator': 20, 'value': 15.0},
            'B1': {'numerator': 80, 'denominator': 100, 'value': 80.0}}
    assert km.save_month('中化', '2026-09', km.BASELINE, base, km.MANUAL, path=db) is None
    base['A1'] = {'numerator': 72, 'denominator': 100, 'value': 72.0}
    assert km.save_month('中化', '2026-09', km.BASELINE, base, km.MANUAL, path=db) is None   # 重存：以最後一次為準
    pilot = km.as_records(km.compute_all(_tasks(), _assign()))
    assert km.save_month('中化', '2026-10', km.PILOT, pilot, path=db) is None
    assert km.save_month('中化', '2026/10', km.PILOT, pilot, path=db) is not None             # 月份格式錯
    assert km.save_month('中化', '2026-10', km.PILOT, {'A3': {'value': None}}, path=db) == '沒有可以儲存的 KPI 數值。'
    saved = km.saved_months('中化', path=db)
    assert km.month_options(saved, km.BASELINE) == ['2026-09'] and km.month_options(saved, km.PILOT) == ['2026-10']
    assert set(km.month_values(saved, '2026-10', km.PILOT)) == {'A1', 'A2'}                  # 尚無資料的項目不存
    b = km.month_values(saved, '2026-09', km.BASELINE)
    p = {'A1': {'value': 75.0}, 'C1': {'value': 18.0}, 'B1': {'value': 80.0}}
    table = km.compare_table(b, p, '2026-09', '2026-10').set_index('代碼')
    assert (table.loc['A1', '基準月數值'], table.loc['A1', '差異'], table.loc['A1', '變化']) == (72.0, 3.0, '改善')
    assert (table.loc['C1', '差異'], table.loc['C1', '變化']) == (3.0, '變差')                # 轉場越低越好
    assert table.loc['B1', '變化'] == '持平'
    assert 'A3' not in table.index                                                            # 兩邊都沒有就不列


def test_old_codes_in_database_are_ignored(tmp_path):
    db = tmp_path / 'k.sqlite3'
    km.save_month('中化', '2026-09', km.BASELINE, {'A1': {'value': 70.0}}, path=db)
    import sqlite3
    with sqlite3.connect(db) as con:                                       # 分組前存的舊代碼
        con.execute("INSERT INTO records(scope, month, kind, code, value, saved_at) VALUES ('中化','2026-09','基準月','K2',30,'x')")
    assert set(km.saved_months('中化', path=db)['code']) == {'A1'}


def test_demo_db_path_sits_next_to_demo_store():
    assert km.demo_db_path('output_results/demo_workflow/abc.sqlite3').replace('\\', '/') == \
        'output_results/demo_workflow/abc_kpi.sqlite3'
    assert km.demo_db_path(None) is None


def test_spec_codes_unique_and_documented():
    import pathlib
    codes = [s.code for s in km.KPI_SPECS]
    assert len(codes) == len(set(codes)) and {s.group for s in km.KPI_SPECS} == {'A', 'B', 'C'}
    doc = (pathlib.Path(__file__).resolve().parent.parent / 'PILOT_KPI.md').read_text(encoding='utf-8')
    for spec in km.KPI_SPECS:
        assert f'| {spec.code} | {spec.name} |' in doc
