"""試辦 KPI 畫面（05 人力與效益分析 › 🎯 試辦 KPI，只有主管看得到）。

計算全部在 kpi_metrics.py；這裡只負責顯示與「儲存」按鈕。顯示 ID 的表格、匯出、下載都由 app.py 傳入的
show_table／export_frame／download（download_button_quiet）處理，遵守個資遮罩設定。
"""
CAREFLOW_BUILD = '2026.10.18-v19'
import pandas as pd
import streamlit as st

import kpi_metrics as km
from careflow_ui import kpi_cards, subhead

CURRENT = '本期（尚未儲存）'
_NOTICE = '_kpi_notice'


def _num(value, digits=1):
    """1234 → 1,234；12.34 → 12.3；None → —。"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return '—'
    value = float(value)
    return f'{value:,.0f}' if value.is_integer() else f'{value:,.{digits}f}'


def value_text(result):
    """數值加單位：「75.0%」「52.5 分鐘／回合」；沒有資料時「待量測」。"""
    if result['數值'] is None:
        return '待量測'
    unit = result['單位']
    return f"{result['數值']:.1f}%" if unit == '%' else f"{result['數值']:,.1f} {unit}"


def _parts_text(result):
    spec = km.SPEC_BY_CODE[result['代碼']]
    return f"{_num(result['分子'])} {spec.num_unit} ／ {_num(result['分母'])} {spec.den_unit}"


def _notify(text, ok=True):
    st.session_state[_NOTICE] = (ok, text)


def _save_month_cb(scope, month, kind, records, source, account, path, on_saved):
    error = km.save_month(scope, (month or '').strip(), kind, records, source, account, path)
    if error:
        _notify(error, ok=False)
        return
    count = sum(1 for r in records.values() if km.to_number(r.get('value')) is not None)
    _notify(f'已把 {count} 項 KPI 存成 {month} {kind}（{source}）；待量測的項目不存。')
    if on_saved:
        on_saved('save_month', month=month, kind=kind, items=count, source=source)


def _save_manual_cb(scope, month, rows, account, path, on_saved):
    records = {}
    for row in rows:
        if km.to_number(row.get('分母')) is None:
            continue
        records[row['代碼']] = km.as_records([km.manual_result(row['代碼'], row.get('分子'), row.get('分母'),
                                                                f'{month} 人工登錄')])[row['代碼']]
    if not records:
        _notify('請至少填一項的分子與分母再儲存。', ok=False)
        return
    _save_month_cb(scope, month, km.BASELINE, records, km.MANUAL, account, path, on_saved)


def _render_detail(result, show_table):
    """一項 KPI 的展開區內容：分子、分母、期間、計算方式，再列明細。"""
    spec = km.SPEC_BY_CODE[result['代碼']]
    a, b = st.columns(2)
    a.markdown(f"**分子**：{_num(result['分子'])} {spec.num_unit}\n\n{result['分子說明']}")
    b.markdown(f"**分母**：{_num(result['分母'])} {spec.den_unit}\n\n{result['分母說明']}")
    st.markdown(f"**期間**：{result['期間']}　·　**資料來源**：{result['資料來源']}")
    st.markdown(f"**計算方式**：{result['計算方式']}")
    if result['備註'] and result['數值'] is None:
        st.info(result['備註'])
    elif result['備註']:
        st.caption(result['備註'])
    breakdown = result.get('breakdown')
    if breakdown is not None and not breakdown.empty:
        st.markdown('##### 原因分布')
        show_table(breakdown, hide_index=True, width='stretch')
        st.markdown('##### 逐筆明細')
    detail = result['detail']
    if detail is None or detail.empty:
        st.caption('沒有明細。')
        return
    st.caption(f'明細 {len(detail):,} 筆')
    show_table(detail, hide_index=True, width='stretch')


def _render_months(results, scope, default_month, account, path, on_saved, show_table):
    saved = km.saved_months(scope, path)
    current = km.as_records(results)
    st.caption('基準月＝試辦前、人工排班的月份；試辦月＝用本系統排班的月份。'
               '把本期數值存成某個月份後，就能任選一個基準月和試辦月比較。')
    c1, c2, c3 = st.columns([1.2, 1, 1.4], vertical_alignment='bottom')
    kind = c1.segmented_control('本期數值存成', list(km.KINDS), default=km.PILOT, key='cf_kpi_save_kind')
    month = c2.text_input('月份（YYYY-MM）', value=default_month, key='cf_kpi_save_month')
    c3.button(f'💾 存成 {month} {kind or ""}'.strip(), key='cf_kpi_save', type='primary', width='stretch',
              disabled=not kind, on_click=_save_month_cb,
              args=(scope, month, kind, current, km.SYSTEM, account, path, on_saved))

    with st.expander('✏️ 人工登錄基準月（試辦前人工排班的實測值）', expanded=False):
        prev = (pd.Period(default_month, 'M') - 1).strftime('%Y-%m') if km.valid_month(default_month) else ''
        manual_month = st.text_input('基準月份（YYYY-MM）', value=prev, key='cf_kpi_manual_month')
        old = km.month_values(saved, manual_month, km.BASELINE)
        frame = pd.DataFrame([{'組別': km.GROUP_NAME[s.group], '代碼': s.code, '指標': s.name, '分子說明': s.numerator, '分子': (old.get(s.code) or {}).get('numerator'),
                               '分母說明': s.denominator, '分母': (old.get(s.code) or {}).get('denominator')}
                              for s in km.KPI_SPECS])
        edited = st.data_editor(frame, hide_index=True, width='stretch', key=f'cf_kpi_manual_{manual_month}',
                                disabled=['組別', '代碼', '指標', '分子說明', '分母說明'],
                                column_config={'分子': st.column_config.NumberColumn('分子'),
                                               '分母': st.column_config.NumberColumn('分母'),
                                               '分子說明': st.column_config.TextColumn(width='large'),
                                               '分母說明': st.column_config.TextColumn(width='large')})
        st.caption('只填量得到的項目即可；分母空白的項目不存。C3 填「工時落在平均 ±20% 的人數」和「有排班人數」，C4 填「沒有超過上限的人數」和「有排班人數」。')
        st.button('💾 儲存基準月', key='cf_kpi_manual_save', width='stretch', on_click=_save_manual_cb,
                  args=(scope, manual_month, edited.to_dict('records'), account, path, on_saved))

    base_months = km.month_options(saved, km.BASELINE)
    if not base_months:
        st.info('還沒有基準月。請先「人工登錄基準月」，或把本期數值存成基準月，才能比較。')
        return None
    d1, d2 = st.columns(2)
    base_month = d1.selectbox('基準月', base_months, key='cf_kpi_base_month')
    pilot_month = d2.selectbox('試辦月', [CURRENT] + km.month_options(saved, km.PILOT), key='cf_kpi_pilot_month')
    pilot = current if pilot_month == CURRENT else km.month_values(saved, pilot_month, km.PILOT)
    table = km.compare_table(km.month_values(saved, base_month, km.BASELINE), pilot, base_month, pilot_month)
    if table.empty:
        st.info('這兩個月份沒有共同的 KPI 可以比較。')
        return None
    better = int((table['變化'] == '改善').sum())
    worse = int((table['變化'] == '變差').sum())
    st.caption(f'差異＝試辦月 − 基準月。{len(table)} 項中改善 {better} 項、變差 {worse} 項（依各指標的方向判斷）。')
    show_table(table.drop(columns=['基準月', '試辦月']), hide_index=True, width='stretch')
    with st.expander('已儲存的月份', expanded=False):
        show = saved.rename(columns={'month': '月份', 'kind': '種類', 'code': '代碼', 'numerator': '分子',
                                     'denominator': '分母', 'value': '數值', 'period': '期間', 'source': '來源',
                                     'saved_at': '儲存時間', 'account': '儲存帳號'})
        show_table(show.sort_values(['月份', '種類', '代碼'], ascending=[False, True, True]), hide_index=True, width='stretch')
    return table


def render_pilot_kpis(inputs, scope, db_path, account, show_table, export_frame, download, on_saved=None):
    """試辦 KPI 頁：3 組大字 KPI 卡 → 逐項指標表 → 各項明細 → 基準月 vs 試辦月 → 下載。

    inputs：kpi_metrics.compute_all() 的參數（tasks、assignments、routes、monthly_payroll、primary_map、
            diagnostics、caregivers、start、end、normal_daily_hours、leaves）。
    scope：機構代碼；db_path：KPI 資料檔（示範模式給暫存檔，None＝正式檔）；account：目前登入帳號。
    show_table／export_frame／download：app.py 的 show_table、export_frame、download_button_quiet。
    on_saved(action, **detail)：儲存成功後呼叫（app.py 用來寫存取稽核紀錄）。
    """
    notice = st.session_state.pop(_NOTICE, None)
    if notice:
        (st.success if notice[0] else st.error)(notice[1])
    results = km.compute_all(**inputs)
    groups = km.by_group(results)

    st.caption(f"統計期間：{km.period_label(inputs.get('tasks'))}。全部由系統班表與工時計算；定義見 PILOT_KPI.md。"
               '每項都列出分子、分母、期間與計算方式，展開可看明細；沒有資料的項目顯示「待量測」，不自行假設數字。')
    for code, name, question, items in groups:
        subhead(f'{code}　{name}')
        st.caption(question)
        kpi_cards([dict(label=f"{r['代碼']} {r['指標']}", value=value_text(r), sub=_parts_text(r),
                        tone='good' if r['數值'] is not None else 'warn', help=r['計算方式']) for r in items])
        hints = [km.SPEC_BY_CODE[r['代碼']].hint for r in items if km.SPEC_BY_CODE[r['代碼']].hint]
        if hints:
            st.caption('\n\n'.join(hints))

    subhead('逐項指標：分子、分母、期間、計算方式')
    table = km.kpi_table(results)
    show_table(table, hide_index=True, width='stretch', column_config={
        '分子說明': st.column_config.TextColumn(width='medium'), '分母說明': st.column_config.TextColumn(width='medium'),
        '計算方式': st.column_config.TextColumn(width='large')})
    for code, name, _, items in groups:
        st.markdown(f'##### {code}　{name}：明細')
        for r in items:
            with st.expander(f"{r['代碼']}　{r['指標']}　{value_text(r)}　（{_parts_text(r)}）", expanded=False):
                _render_detail(r, show_table)

    subhead('基準月 vs 試辦月')
    compare = _render_months(results, scope, km.period_month(inputs.get('tasks')), account, db_path, on_saved, show_table)

    subhead('下載')
    d1, d2, d3 = st.columns(3)
    with d1:
        download('⬇️ 下載 KPI 總表 CSV', export_frame(table).to_csv(index=False).encode('utf-8-sig'),
                 '試辦KPI_總表.csv', 'text/csv', key='cf_kpi_download_table', width='stretch')
    with d2:
        download('⬇️ 下載 KPI 明細 CSV', export_frame(km.detail_table(results)).to_csv(index=False).encode('utf-8-sig'),
                 '試辦KPI_明細.csv', 'text/csv', key='cf_kpi_download_detail', width='stretch')
    with d3:
        if compare is not None:
            download('⬇️ 下載基準月比較 CSV', compare.to_csv(index=False).encode('utf-8-sig'),
                     '試辦KPI_基準月比較.csv', 'text/csv', key='cf_kpi_download_compare', width='stretch')
        else:
            st.button('⬇️ 下載基準月比較 CSV', key='cf_kpi_download_compare_off', disabled=True, width='stretch',
                      help='先存一個基準月才能比較。')
    return results
