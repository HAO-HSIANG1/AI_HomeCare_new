"""方案 D 週班表（大字版）：一週 7 欄、重點大字，右側 AI 提醒欄。

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
        who = _client(row)
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


def render_week_board(rows, labels, period_start=None, on_go_issues=None, max_exceptions=6):
    """畫出週班表＋AI 提醒欄。rows／labels 來自 calendar_view.cached_schedule_rows()。"""
    if not rows:
        st.info('目前沒有帶日期和時段的服務任務。')
        return
    dates = sorted({r['date'] for r in rows})
    first = pd.Timestamp(period_start or dates[0]).date()
    first_monday = first - timedelta(days=first.weekday())
    if not isinstance(st.session_state.get('cfwb_week'), date):
        st.session_state['cfwb_week'] = first_monday

    def _shift(n):
        st.session_state['cfwb_week'] = st.session_state['cfwb_week'] + timedelta(days=n)

    active = sorted({r['cg'] for r in rows if r.get('cg')})
    options = [_ALL] + active + sorted(set(labels) - set(active))
    c1, c2, c3, c4 = st.columns([3, 2.2, 1.1, 1.1], vertical_alignment='bottom')
    person = c1.selectbox('看誰的班表', options, key='cfwb_person',
                          format_func=lambda x: '全部居服員（每日總覽）' if x == _ALL else _worker(labels, x))
    start = c2.date_input('週起日', key='cfwb_week')
    c3.button('‹ 上一週', key='cfwb_prev', on_click=_shift, args=(-7,), width='stretch')
    c4.button('下一週 ›', key='cfwb_next', on_click=_shift, args=(7,), width='stretch', type='primary')

    days = [(start + timedelta(days=i)).isoformat() for i in range(7)]
    week_rows = sorted([r for r in rows if r['date'] in days], key=lambda r: (r['date'], r['start']))
    person_mode = person != _ALL
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
            body = (f'<div class="cf-wk-sum"><b>{done}</b><span>筆已排</span></div>'
                    + (f'<div class="cf-wk-sum miss"><b>{len(missing)}</b><span>筆未排</span></div>' if missing else ''))
            notable = missing + adjusted
            body += ''.join(_chip(r, labels, False) for r in notable[:max_exceptions])
            rest = len(day_rows) - min(len(notable), max_exceptions)
            if rest > 0:
                body += f'<div class="cf-wk-more">＋ 其餘 {rest} 筆正常班次</div>'
        cols.append(f'<div class="cf-wk-col{cls}">{body}</div>')

    grid_col, ai_col = st.columns([3.3, 1.25], gap='medium')
    with grid_col:
        st.markdown('<div class="cf-wk-wrap" role="region" aria-label="週班表"><div class="cf-wk">' + ''.join(head) + ''.join(cols)
                    + '</div></div><div class="cf-wk-legend"><span><i></i>正常班次</span><span><i class="adj"></i>代班／已調整</span>'
                    '<span><i class="miss"></i>未排（需處理）</span></div>', unsafe_allow_html=True)
    with ai_col:
        items = _ai_items(week_rows, labels, days)
        st.markdown('<aside class="cf-aip" aria-label="AI 排班提醒"><div class="cf-aip-head"><div class="ic">' + _SPARK + '</div>'
                    '<div><b>AI 排班提醒</b><span>依本週班表自動整理</span></div></div><div class="cf-aip-body">'
                    + ''.join(f'<div class="cf-aip-item {tone}"><b>{escape(t)}</b><span>{escape(d)}</span></div>' for tone, t, d in items)
                    + '</div></aside>', unsafe_allow_html=True)
        if on_go_issues and any(r for r in week_rows if not r.get('cg')):
            st.button('前往處理未排服務 →', key='cfwb_go_issues', on_click=on_go_issues, type='primary', width='stretch')
