"""週班表（大字版，取自 HomeCare AI 版本並調整樣式）：一週 7 欄、重點大字，右側 AI 提醒欄。

只負責畫面：讀 calendar_view.cached_schedule_rows() 已整理好的班次列，不重新排班、不呼叫外部服務。
- 全部居服員：每天一張大數字總覽（已排／未排），只列出「未排」與「代班／已調整」等需要注意的班次。
- 單一居服員：列出該員當週全部班次，每天標示總時數。
"""
from datetime import date, timedelta
from html import escape

import pandas as pd
import streamlit as st

_WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']
_ALL = '__all__'
_SPARK = ('<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round" aria-hidden="true">'
          '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/></svg>')


def _minutes(hhmm):
    try:
        h, m = str(hhmm)[:5].split(':')
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return None


def _client(row):
    text = str(row.get('client_label') or row.get('client') or '')
    return text.split('｜', 1)[1] if text.startswith('姓名未對照｜') else text


def _worker(labels, cg):
    text = str(labels.get(cg) or cg or '')
    return text.split('｜', 1)[1] if text.startswith('姓名未對照｜') else text.lstrip('｜')


def _short(text):
    """「王○明｜C0041」→ 只取姓名；沒有姓名就用代碼。"""
    return text.split('｜', 1)[0] if '｜' in text and not text.startswith('｜') else text.lstrip('｜')


def _chip(row, labels, person_mode):
    miss = not row.get('cg')
    adj = row.get('tag') in ('代班', '已調整')
    cls = 'miss' if miss else ('adj' if adj else '')
    tag = '<span class="tag">未排</span>' if miss else (f'<span class="tag">{escape(row["tag"])}</span>' if adj else '')
    if person_mode or miss:
        who = _short(_client(row))
    else:
        who = f"{_short(_worker(labels, row['cg']))} → {_short(_client(row))}"
    kind = ' · '.join(x for x in [row.get('code') or '', '' if (miss or adj) else row.get('tag', '')] if x)
    return (f'<div class="cf-wk-c {cls}">{tag}<span class="t">{escape(row["start"])} <small>–{escape(row["end"])}</small></span>'
            f'<span class="w">{escape(who)}</span>' + (f'<span class="k">{escape(kind)}</span>' if kind else '') + '</div>')


def _ai_items(week_rows, labels, days):
    items = []
    miss = [r for r in week_rows if not r.get('cg')]
    if miss:
        by_day = pd.Series([r['date'] for r in miss]).value_counts()
        worst = pd.Timestamp(by_day.index[0])
        families = len({r.get('client') for r in miss})
        items.append(('warn', f'本週還有 {len(miss)} 筆沒排進',
                      f'涉及 {families} 個家庭，最多在週{_WEEKDAYS[worst.weekday()]}（{by_day.iloc[0]} 筆）。系統已備好替代方案。'))
    adj = [r for r in week_rows if r.get('cg') and r.get('tag') in ('代班', '已調整')]
    if adj:
        items.append(('', f'本週 {len(adj)} 筆為代班或已調整', '請記得通知居服員與案家新的安排。'))
    counts = pd.Series([r['date'] for r in week_rows]).value_counts() if week_rows else pd.Series(dtype=int)
    if len(counts) >= 2 and counts.iloc[0] > counts.mean() * 1.15:
        busy = pd.Timestamp(counts.index[0])
        items.append(('', f'週{_WEEKDAYS[busy.weekday()]}最忙：{int(counts.iloc[0])} 筆服務',
                      f'比本週平均多 {int(round(counts.iloc[0] - counts.mean()))} 筆，建議當天安排 1 位備援待命。'))
    hours = {}
    for r in week_rows:
        a, b = _minutes(r['start']), _minutes(r['end'])
        if r.get('cg') and a is not None and b is not None and b > a:
            hours[r['cg']] = hours.get(r['cg'], 0) + (b - a) / 60
    if hours:
        top = max(hours, key=hours.get)
        items.append(('', f'{_short(_worker(labels, top))} 本週 {hours[top]:.1f} 小時',
                      '是本週服務時數最高的居服員；新增服務時可優先考慮其他人。'))
    if not items:
        items.append(('', '本週一切正常', '所有服務都已排進，也沒有需要通知的異動。'))
    return items


_PERIODS = (('上午', 0, 12 * 60), ('下午', 12 * 60, 17 * 60), ('晚上', 17 * 60, 24 * 60))


def _period_counts(day_rows):
    """上午／下午／晚上各有幾筆服務（以開始時間計）。"""
    return [(name, sum(1 for r in day_rows if lo <= (_minutes(r['start']) or 0) < hi)) for name, lo, hi in _PERIODS]


def _heat_html(day_rows, peak=None):
    """當天哪個時段最忙：上午／下午／晚上三格色塊，顏色越深服務越多（h0～h4，peak＝整週最多的一格，各天可互相比較）。"""
    counts = _period_counts(day_rows)
    peak = peak or max((n for _, n in counts), default=0) or 1
    cells = ''.join(f'<div class="cell h{min(4, round(n / peak * 4)) if n else 0}"><span>{name}</span><b>{n}</b></div>'
                    for name, n in counts)
    return f'<div class="cf-wk-heat" title="各時段開始的服務數">{cells}</div>'


def render_week_board(rows, labels, period_start=None, on_go_issues=None, max_exceptions=6, on_open=None):
    """畫出週班表＋AI 提醒欄。rows／labels 來自 calendar_view.cached_schedule_rows()。
    on_open(task_id)：有傳入時（新版操作），未排／代班的服務會變成可點的按鈕，點了開啟改派視窗。"""
    if not rows:
        st.info('目前沒有帶日期和時段的服務任務。')
        return
    dates = sorted({r['date'] for r in rows})
    first = pd.Timestamp(period_start or dates[0]).date()
    # 期間第一天若是週六／週日，從下週一開始看（不然第一週幾乎都是空的）；其餘從那週的週一開始。
    first_monday = first - timedelta(days=first.weekday()) if first.weekday() < 5 else first + timedelta(days=7 - first.weekday())
    if not isinstance(st.session_state.get('cfwb_week'), date) or st.session_state.get('_cfwb_period') != str(first):
        st.session_state['cfwb_week'] = first_monday
        st.session_state['_cfwb_period'] = str(first)

    def _shift(n):
        st.session_state['cfwb_week'] = st.session_state['cfwb_week'] + timedelta(days=n)

    active = sorted({r['cg'] for r in rows if r.get('cg')})
    options = [_ALL] + active + sorted(set(labels) - set(active))
    if st.session_state.get('cfwb_view') not in ('週', '月'):
        st.session_state['cfwb_view'] = '週'
    c0, c1, c2, c3, c4 = st.columns([1.3, 3, 2.2, 1.1, 1.1], vertical_alignment='bottom')
    view = c0.segmented_control('檢視', ['週', '月'], key='cfwb_view', help='月：整段期間一格一天，點一天回到那一週')
    person = c1.selectbox('看誰的班表', options, key='cfwb_person',
                          format_func=lambda x: '全部居服員（每日總覽）' if x == _ALL else _worker(labels, x))
    if view == '月':
        _month_grid(rows, person, labels, date.today().isoformat())
        return
    start = c2.date_input('週起日', key='cfwb_week')
    c3.button('‹ 上一週', key='cfwb_prev', on_click=_shift, args=(-7,), width='stretch')
    c4.button('下一週 ›', key='cfwb_next', on_click=_shift, args=(7,), width='stretch', type='primary')

    days = [(start + timedelta(days=i)).isoformat() for i in range(7)]
    week_rows = sorted([r for r in rows if r['date'] in days], key=lambda r: (r['date'], r['start']))
    person_mode = person != _ALL
    person_label = _worker(labels, person) if person_mode else ''
    shown = [r for r in week_rows if r.get('cg') == person] if person_mode else week_rows
    today = date.today().isoformat()

    head, cols = [], []
    for d in days:
        day = pd.Timestamp(d)
        day_rows = [r for r in shown if r['date'] == d]
        cls = ' today' if d == today else (' off' if not day_rows else '')
        if person_mode:
            mins = sum(max(0, (_minutes(r['end']) or 0) - (_minutes(r['start']) or 0)) for r in day_rows)
            sub = f'{len(day_rows)} 筆 · {mins / 60:.1f} 小時' if day_rows else '休息'
        else:
            sub = f'{len(day_rows)} 筆服務' if day_rows else '沒有服務'
        head.append(f'<div class="cf-wk-day{cls}"><b>{_WEEKDAYS[day.weekday()]} {day:%m/%d}</b><span>{sub}</span></div>')
        if person_mode:
            body = ''.join(_chip(r, labels, True) for r in day_rows) or '<div class="cf-wk-empty">這天沒有排班</div>'
        elif not day_rows:
            body = '<div class="cf-wk-empty">—</div>'
        else:
            missing = [r for r in day_rows if not r.get('cg')]
            adjusted = [r for r in day_rows if r.get('cg') and r.get('tag') in ('代班', '已調整')]
            done = len(day_rows) - len(missing)
            pct = done / len(day_rows) * 100
            body = (f'<div class="cf-wk-sum"><b>{done}</b><span>筆已排</span>'
                    f'<div class="cf-wk-bar" title="{pct:.0f}%"><i style="width:{pct:.1f}%"></i></div></div>'
                    + (f'<div class="cf-wk-sum miss"><b>{len(missing)}</b><span>筆未排</span></div>' if missing else ''))
            notable = missing + adjusted
            body += ''.join(_chip(r, labels, False) for r in notable[:max_exceptions])
            rest = len(day_rows) - min(len(notable), max_exceptions)
            if rest > 0:
                body += f'<div class="cf-wk-more">＋ 其餘 {rest} 筆正常班次</div>'
        cols.append(f'<div class="cf-wk-col{cls}">{body}</div>')

    if st.session_state.get('cfwb_day'):
        _day_dialog(rows, labels, st.session_state['cfwb_day'], on_open)
    end_day = pd.Timestamp(days[-1])
    total_note = (f'{person_label} · 本週 {len(shown)} 筆服務' if person_mode
                  else f'全部居服員 · 本週 {len(shown)} 筆服務，{sum(1 for r in shown if not r.get("cg"))} 筆未排')
    st.markdown(f'<div class="cf-wk-range">{pd.Timestamp(days[0]):%m/%d}（{_WEEKDAYS[pd.Timestamp(days[0]).weekday()]}）～ '
                f'{end_day:%m/%d}（{_WEEKDAYS[end_day.weekday()]}）<span>{escape(total_note)}</span></div>',
                unsafe_allow_html=True)
    grid_col, ai_col = st.columns([4.3, 1], gap='medium')
    if on_open is not None:
        with grid_col:
            _interactive_grid(days, shown, labels, person_mode, today, max_exceptions, on_open)
    else:
      with grid_col:
        st.markdown('<div class="cf-wk-wrap" role="region" aria-label="週班表"><div class="cf-wk">' + ''.join(head) + ''.join(cols)
                    + '</div></div><div class="cf-wk-legend"><span><i></i>正常班次</span><span><i class="adj"></i>代班／已調整</span>'
                    '<span><i class="miss"></i>未排（需處理）</span></div>', unsafe_allow_html=True)
        if not person_mode:
            st.caption('點下面的日期，看那一天每位居服員的完整班表：')
            _dcols = st.columns(7, gap='small')
            for _c, _d in zip(_dcols, days):
                _c.button(f'{pd.Timestamp(_d):%m/%d} ›', key=f'cfwk_dayb_{_d}', on_click=_open_day, args=(_d,), width='stretch')
    with ai_col:
        items = _ai_items(week_rows, labels, days)
        st.markdown('<aside class="cf-aip" aria-label="AI 排班提醒"><div class="cf-aip-head"><div class="ic">' + _SPARK + '</div>'
                    '<div><b>AI 排班提醒</b><span>依本週班表自動整理</span></div></div><div class="cf-aip-body">'
                    + ''.join(f'<div class="cf-aip-item {tone}"><b>{escape(t)}</b><span>{escape(d)}</span></div>' for tone, t, d in items)
                    + '</div></aside>', unsafe_allow_html=True)
        if on_go_issues and any(r for r in week_rows if not r.get('cg')):
            st.button('前往處理未排服務 →', key='cfwb_go_issues', on_click=on_go_issues, type='primary', width='stretch')


def _open_day(day):
    st.session_state['cfwb_day'] = day


def _close_day():
    st.session_state.pop('cfwb_day', None)


def _pick_from_day(task_id, on_open):
    """在「當天班表」視窗點了某一筆：關掉這個視窗，改開安排居服員視窗。"""
    st.session_state.pop('cfwb_day', None)
    on_open(task_id)


@st.dialog('當天班表', width='large', on_dismiss=_close_day)
def _day_dialog(rows, labels, day, on_open):
    d = pd.Timestamp(day)
    day_rows = sorted([r for r in rows if r['date'] == day], key=lambda r: (r['start'], r['end']))
    missing = [r for r in day_rows if not r.get('cg')]
    st.markdown(f"<div class='cf-dd-head'><b>{d.month}/{d.day}（{_WEEKDAYS[d.weekday()]}）</b>"
                f"<span>{len(day_rows)} 筆服務 · {len({r['cg'] for r in day_rows if r.get('cg')})} 位居服員上班"
                + (f" · <em>{len(missing)} 筆未排</em>" if missing else '') + "</span></div>", unsafe_allow_html=True)
    f1, f2 = st.columns([2, 1.3], vertical_alignment='center')
    who = f1.text_input('找人', key='cfwb_day_find', placeholder='🔍 打居服員或案家姓名篩選', label_visibility='collapsed')
    only = f2.toggle('只看未排／代班', key='cfwb_day_only')
    groups = {}
    for r in day_rows:
        if only and r.get('cg') and r.get('tag') not in ('代班', '已調整'):
            continue
        groups.setdefault(r.get('cg') or '', []).append(r)
    order = sorted(groups, key=lambda cg: (cg != '', groups[cg][0]['start']))
    shown = 0
    for cg in order:
        items = groups[cg]
        name = '🟠 還沒排人' if not cg else _worker(labels, cg)
        if who and who not in name and not any(who in _client(r) for r in items):
            continue
        mins = sum(max(0, (_minutes(r['end']) or 0) - (_minutes(r['start']) or 0)) for r in items)
        chips = ''.join(
            f"<span class='cf-dd-chip {'miss' if not r.get('cg') else ('adj' if r.get('tag') in ('代班', '已調整') else '')}'>"
            f"<b>{escape(r['start'])}–{escape(r['end'])}</b>{escape(_short(_client(r)))}"
            + (f"<i>{escape(str(r.get('code') or ''))}</i>" if r.get('code') else '')
            + (f"<i>{escape(str(r.get('tag')))}</i>" if r.get('tag') in ('代班', '已調整') else '') + '</span>'
            for r in items)
        st.markdown(f"<div class='cf-dd-row{' miss' if not cg else ''}'><div class='who'><b>{escape(name)}</b>"
                    f"<span>{len(items)} 筆 · {mins / 60:.1f} 小時</span></div><div class='list'>{chips}</div></div>",
                    unsafe_allow_html=True)
        if on_open is not None and (not cg or any(r.get('tag') in ('代班', '已調整') for r in items)):
            pick = [r for r in items if not r.get('cg') or r.get('tag') in ('代班', '已調整')]
            cols = st.columns(min(4, len(pick)))
            for c, r in zip(cols * 10, pick):
                c.button(f"安排 {r['start']} {_short(_client(r))}", key=f'cfwb_day_pick_{r["id"]}', width='stretch',
                         on_click=_pick_from_day, args=(r['id'], on_open))
        shown += 1
    if not shown:
        st.info('沒有符合的班次。')


def _button_label(row, labels, person_mode):
    miss = not row.get('cg')
    mark = '🟠 未排' if miss else ('🔁 ' + str(row.get('tag')))
    if person_mode or miss:
        who = _short(_client(row))
    else:
        who = f"{_short(_worker(labels, row['cg']))}→{_short(_client(row))}"
    return f"{mark}  {row['start']}–{row['end']}  {who}"


def _popover(label, key):
    """收合用的小視窗按鈕；舊版 Streamlit 沒有 width 參數時退回預設寬度。"""
    with st.container(key=key):
        try:
            return st.popover(label, width='stretch')
        except TypeError:
            return st.popover(label)


def _task_button(r, labels, person_mode, on_open):
    tone = 'miss' if not r.get('cg') else ('adj' if r.get('tag') in ('代班', '已調整') else 'norm')
    with st.container(key=f'cfwkb_{tone}_{r["id"]}'):
        st.button(_button_label(r, labels, person_mode), key=f'cfwk_open_{r["id"]}', on_click=on_open,
                  args=(r['id'],), width='stretch', help='點一下：查看可派人選、改派或改時間')


def _grouped_buttons(items, kind, d, labels, on_open):
    """未排或代班的服務：只有 1 筆就直接放按鈕；2 筆以上收成一顆「🟠 3 筆未排」小視窗，每天高度一致。"""
    if not items:
        return
    if len(items) == 1:
        _task_button(items[0], labels, False, on_open)
        return
    label = f'🟠 {len(items)} 筆未排 ›' if kind == 'miss' else f'🔁 {len(items)} 筆代班／已調整 ›'
    with _popover(label, f'cfwkpop_{kind}_{d}'):
        for r in items:
            _task_button(r, labels, False, on_open)


def _day_kind(d, today):
    """欄位底色用：today（今天）／wkend（週六、週日）／wd（平日）。"""
    return 'today' if d == today else ('wkend' if pd.Timestamp(d).weekday() >= 5 else 'wd')


def _interactive_grid(days, shown, labels, person_mode, today, max_exceptions, on_open):
    """新版操作：7 欄週班表，需要注意的服務是按鈕，點了開啟改派視窗（與拖曳日曆共用同一個視窗與檢查）。

    全部居服員模式每天依序是：環形完成度＋已排筆數、「看當天班表」按鈕、上午／下午／晚上熱度色塊、
    未排與代班（2 筆以上收成小視窗）。週末淡色底、今天加外框。"""
    from careflow_ui import ring_html
    week_peak = max([_period_counts([r for r in shown if r['date'] == d])[i][1] for d in days for i in range(3)] or [0])
    with st.container(key='cfwkgrid'):
        cols = st.columns(7, gap='small')
        for col, d in zip(cols, days):
            day = pd.Timestamp(d)
            day_rows = [r for r in shown if r['date'] == d]
            kind = _day_kind(d, today)
            cls = (' today' if kind == 'today' else '') + (' wkend' if day.weekday() >= 5 else '') + ('' if day_rows else ' off')
            with col, st.container(key=f'cfwkcol_{kind}_{d}'):
                if person_mode:
                    mins = sum(max(0, (_minutes(r['end']) or 0) - (_minutes(r['start']) or 0)) for r in day_rows)
                    sub = f'{len(day_rows)} 筆 · {mins / 60:.1f} 小時' if day_rows else '休息'
                else:
                    sub = '' if day_rows else '沒有服務'
                badge = '<em>今天</em>' if kind == 'today' else ''
                st.markdown(f'<div class="cf-wk-day{cls}"><b>{_WEEKDAYS[day.weekday()]} {day:%m/%d}{badge}</b>'
                            + (f'<span>{sub}</span>' if sub else '') + '</div>', unsafe_allow_html=True)
                if not day_rows:
                    st.markdown('<div class="cf-wk-empty">' + ('這天沒有排班' if person_mode else '—') + '</div>', unsafe_allow_html=True)
                    continue
                if person_mode:
                    for r in day_rows:
                        _task_button(r, labels, True, on_open)
                    continue
                missing = [r for r in day_rows if not r.get('cg')]
                adjusted = [r for r in day_rows if r.get('cg') and r.get('tag') in ('代班', '已調整')]
                done = len(day_rows) - len(missing)
                pct = done / len(day_rows) * 100
                workers = len({r['cg'] for r in day_rows if r.get('cg')})
                tone = 'ok' if not missing else 'miss'
                # 大字是「服務筆數」（已排／全部），不是人數；人數另寫「位居服員」，和當天班表視窗同一說法。
                st.markdown(f'<div class="cf-wk-donut {tone}"><span class="ring">{ring_html(pct, f"已排 {pct:.0f}%")}'
                            f'<i>{pct:.0f}%</i></span><div><b>{done}<small>／{len(day_rows)} 筆</small></b>'
                            f'<span>👥 {workers} 位居服員</span></div></div>', unsafe_allow_html=True)
                with st.container(key=f'cfwkdaylink_{d}'):
                    st.button('看當天班表 ›', key=f'cfwk_day_{d}', on_click=_open_day, args=(d,), width='stretch',
                              help='點開看這一天每位居服員的完整班表')
                st.markdown(_heat_html(day_rows, week_peak), unsafe_allow_html=True)
                _grouped_buttons(missing, 'miss', d, labels, on_open)
                _grouped_buttons(adjusted, 'adj', d, labels, on_open)
                if not missing and not adjusted:
                    st.markdown('<div class="cf-wk-ok">✓ 全部排好</div>', unsafe_allow_html=True)
    st.markdown('<div class="cf-wk-legend"><span><i class="miss"></i>未排：點一下安排居服員</span>'
                '<span><i class="adj"></i>代班／已調整：點一下可再改</span>'
                '<span><i class="heat"></i>上午／下午／晚上：顏色越深服務越多</span>'
                '<span>選上方「看誰的班表」可看單一居服員整週，每筆都能點</span></div>',
                unsafe_allow_html=True)


def _go_week(day):
    """月檢視點了某一天：切回週檢視，顯示那一週。"""
    d = pd.Timestamp(day).date()
    st.session_state['cfwb_week'] = d - timedelta(days=d.weekday())
    st.session_state['cfwb_view'] = '週'


def _month_grid(rows, person, labels, today):
    """月檢視：整段排班期間一格一天，只看完成度（全部居服員）或時數（單一居服員）；點一天切回那一週。"""
    shown = [r for r in rows if r.get('cg') == person] if person != _ALL else rows
    dates = sorted({r['date'] for r in rows})
    first, last = pd.Timestamp(dates[0]).date(), pd.Timestamp(dates[-1]).date()
    start = first - timedelta(days=first.weekday())
    weeks = (last - start).days // 7 + 1
    st.markdown('<div class="cf-wk-mhead">' + ''.join(f'<span>{w}</span>' for w in _WEEKDAYS) + '</div>',
                unsafe_allow_html=True)
    for w in range(weeks):
        cols = st.columns(7, gap='small')
        for i, col in enumerate(cols):
            d = (start + timedelta(days=w * 7 + i)).isoformat()
            day_rows = [r for r in shown if r['date'] == d]
            in_period = dates[0] <= d <= dates[-1]
            if not in_period:
                col.markdown('<div class="cf-wk-mout"></div>', unsafe_allow_html=True)
                continue
            day = pd.Timestamp(d)
            if not day_rows:
                state, text = 'off', '—'
            elif person != _ALL:
                mins = sum(max(0, (_minutes(r['end']) or 0) - (_minutes(r['start']) or 0)) for r in day_rows)
                state, text = 'ok', f'{mins / 60:.1f} 小時'
            else:
                miss = sum(1 for r in day_rows if not r.get('cg'))
                state = 'miss' if miss else 'ok'
                text = f'🟠 {miss} 筆未排' if miss else '✓ 全部排好'
            kind = _day_kind(d, today)
            with col, st.container(key=f'cfwkmon_{state}_{kind}_{d}'):
                st.button(f'**{day.month}/{day.day}**\n\n{text}', key=f'cfwk_mon_{d}', on_click=_go_week, args=(d,),
                          width='stretch', help='點一下切回週檢視，看這一週')
    st.markdown('<div class="cf-wk-legend"><span><i class="ok"></i>全部排好</span><span><i class="miss"></i>還有未排</span>'
                '<span>點任一天切回那一週</span></div>', unsafe_allow_html=True)
