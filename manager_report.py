"""主管報表（一頁式）：三大數字、人力負荷、AI 增聘／調派建議，以及可下載的報告圖檔。

純函式，不呼叫 Streamlit；畫面在 app.py，圖檔用 matplotlib 物件導向 API（不經 pyplot，
可以在 download_button 的背景執行緒裡安全產生）。
"""
import io
import math
import pathlib

import pandas as pd

_FONT_PATH = pathlib.Path(__file__).parent / 'assets' / 'fonts' / 'NotoSansTC-Regular.ttf'
STATUS_ORDER = ['正常', '接近上限', '超過上限']
STATUS_COLORS = {'正常': '#1F5F7A', '接近上限': '#B45309', '超過上限': '#B91C1C'}


# ---------------------------------------------------------------- 三大數字
def headline_cards(summary, travel_hours=None, total_hours=None, avg_leg_minutes=None, run_seconds=None):
    """回傳三張大數字卡（dict：title, number, before, after, note, ai），全部由這次班表實際算出、沒有假設值。

    summary：dashboard_metrics.build_dashboard()['summary']（total、assigned、owned、primary、primary_share、travel_share）。
    1. 排班完成率＝已派筆數 ÷ 全部服務筆數（是「排進班表」的比例；實際有沒有到勤看 ④ 打卡看板）。
    2. 固定人選服務比例＝由固定居服員本人服務的筆數 ÷ 有固定居服員的已派筆數（照顧連續性）。
    3. 轉場佔總工時＝轉場工時 ÷（服務＋轉場）工時（路線效率，越低越好）。"""
    s = summary or {}
    total, assigned = int(s.get('total') or 0), int(s.get('assigned') or 0)
    rate = (assigned / total * 100) if total else 0.0
    ran = f'本次 AI 排班 {run_seconds:.0f} 秒。' if run_seconds else ''
    share = s.get('primary_share')
    share_ok = share is not None and share == share
    travel = s.get('travel_share')
    travel_ok = travel is not None and travel == travel
    leg = f'平均每段 {avg_leg_minutes:.0f} 分鐘；' if avg_leg_minutes else ''
    return [
        dict(title='排班完成率', number=f'{rate:.1f}%', ai=True, tone='ai', icon='📅', ring=rate,
             before=f'已派 {assigned:,}／{total:,} 筆', after='',
             note=ran + ('所有服務都已排進班表。' if total and assigned >= total
                         else f'尚有 {total - assigned:,} 筆未派，可回到 ③ 處理問題。')),
        dict(title='固定人選服務比例', number=(f'{share:.1f}%' if share_ok else '—'), tone='primary', icon='🤝',
             ring=(share if share_ok else None),
             before=(f"固定居服員本人服務 {int(s.get('primary') or 0):,}／{int(s.get('owned') or 0):,} 筆" if share_ok else '沒有固定人選資料'),
             after='', note='越高代表案家越少換人，照顧越連續。'),
        dict(title='轉場佔總工時', number=(f'{travel * 100:.1f}%' if travel_ok else '—'), tone='ok', icon='🛵',
             ring=(travel * 100 if travel_ok else None),
             before=(f'轉場 {float(travel_hours or 0):,.0f}／總工時 {float(total_hours or 0):,.0f} 小時' if travel_ok else '交通尚未計算'),
             after='', note=leg + '越低代表路線越順、居服員花在路上的時間越少。'),
    ]


# ---------------------------------------------------------------- 熱圖
def heat_view(D):
    """報表與圖檔共用的熱圖：有可上班人數時看吃緊度，否則看需求量。回傳 (表, 標題, 格式)。"""
    pressure, demand = D.get('heat_pressure'), D.get('heat_demand')
    if pressure is not None and not pressure.empty:
        return pressure, '吃緊度（需求 ÷ 可上班人數）', '{:.0%}'
    if demand is not None and not demand.empty:
        return demand, '需求量（平均同時要幾位居服員）', '{:.1f}'
    return pd.DataFrame(), '', '{}'


# ---------------------------------------------------------------- 人力負荷
def load_distribution(workload, label=str):
    """每位居服員的總工時，依加班狀態分欄（給堆疊長條圖）。index＝居服員顯示名稱。"""
    if workload is None or workload.empty:
        return pd.DataFrame(columns=STATUS_ORDER)
    w = workload.copy()
    w['名稱'] = w['居服員'].map(label)
    w = w.sort_values('總工時', ascending=False, kind='stable')
    table = pd.DataFrame(0.0, index=w['名稱'], columns=STATUS_ORDER)
    for name, status, hours in zip(w['名稱'], w['狀態'], pd.to_numeric(w['總工時'], errors='coerce').fillna(0)):
        table.loc[name, status if status in STATUS_ORDER else '正常'] = float(hours)
    table.index.name = '居服員'
    return table


def load_summary(workload):
    """一句話摘要用的數字。"""
    if workload is None or workload.empty:
        return {'people': 0, 'near': 0, 'over': 0, 'max_hours': float('nan'), 'min_hours': float('nan')}
    hours = pd.to_numeric(workload['總工時'], errors='coerce')
    return {'people': int(len(workload)), 'near': int((workload['狀態'] == '接近上限').sum()),
            'over': int((workload['狀態'] == '超過上限').sum()),
            'max_hours': float(hours.max()), 'min_hours': float(hours.min())}


# ---------------------------------------------------------------- AI 建議
def staffing_advice(D, label=str, n_slots=3):
    """缺工時段的增聘建議＋超時居服員的調派建議。回傳 [(標題, 說明)]，不會更動班表。"""
    from dashboard_metrics import peak_slots
    items = []
    table, _, _ = heat_view(D)
    supply, demand = D.get('heat_supply'), D.get('heat_demand')
    has_supply = supply is not None and not supply.empty
    for p in peak_slots(table, supply if has_supply else None, demand, n=n_slots):
        slot = f"{p['星期']} {p['時段']}"
        need, avail = p.get('需求'), p.get('可上班')
        if need is not None and avail is not None and not pd.isna(need):
            gap = math.ceil(float(need) - float(avail)) if float(need) > float(avail) else 0
            ratio = float(need) / float(avail) if avail else float('inf')
            if gap > 0:
                items.append((f'{slot}：建議增聘 {gap} 名',
                              f'需求約 {float(need):.1f} 位、可上班僅 {avail} 位。可招募此時段兼職居服員，或請鄰近區域備援待命。'))
            elif ratio >= 0.8:
                items.append((f'{slot}：建議調派備援 1 名',
                              f'吃緊度 {ratio:.0%}。把可挪動的服務移到人力寬鬆的時段，或安排 1 名備援待命。'))
        else:
            items.append((f'{slot}：需求高峰', '建議此時段多排 1～2 位居服員上班，或安排備援待命。'))

    wl = D.get('workload')
    if wl is not None and not wl.empty:
        busy = wl.loc[wl['狀態'] != '正常']
        idle = wl.loc[(wl['狀態'] == '正常') & (wl['工作天數'] > 0)].sort_values('日均工時', kind='stable')
        idle_names = [label(x) for x in idle['居服員'].head(2)]
        for _, r in busy.head(3).iterrows():
            target = '、'.join(idle_names) if idle_names else '工時較少的同仁'
            items.append((f"{label(r['居服員'])}：建議調出部分服務",
                          f"月加班已用 {float(r['加班使用率']) * 100:.0f}%（{r['狀態']}）。可把可挪動的服務改派給 {target}。"))

    s = D.get('summary', {})
    if s.get('unassigned'):
        reasons = D.get('reasons')
        top = reasons.iloc[0] if reasons is not None and not reasons.empty else None
        why = f"最常見原因：{top['原因']}（{int(top['未派筆數'])} 筆）。" if top is not None else ''
        items.append((f"尚有 {s['unassigned']} 筆服務未派出", why + '請到 ③ 處理問題逐案確認，或考慮增聘對應時段人力。'))
    if not items:
        items.append(('目前人力配置充足', '沒有吃緊時段，也沒有人接近加班上限，維持現有排班即可。'))
    return items


# ---------------------------------------------------------------- 報告圖檔
def _font_name():
    from matplotlib import font_manager as fm
    if _FONT_PATH.exists():
        fm.fontManager.addfont(str(_FONT_PATH))
        return fm.FontProperties(fname=str(_FONT_PATH)).get_name()
    return None


def _rc():
    name = _font_name()
    fonts = ([name] if name else []) + ['Microsoft JhengHei', 'PingFang TC', 'Noto Sans CJK TC', 'DejaVu Sans']
    return {'font.sans-serif': fonts, 'font.family': 'sans-serif', 'axes.unicode_minus': False, 'pdf.fonttype': 42,
            'axes.edgecolor': '#E7DED3', 'axes.labelcolor': '#6B5E52', 'xtick.color': '#6B5E52', 'ytick.color': '#6B5E52'}


def build_report_figure(title, scope, cards, heat, heat_title, heat_fmt, load, advice):
    """A4 直式一頁報告。heat：星期×時段表；load：load_distribution() 結果；advice：[(標題, 說明)]。"""
    import matplotlib
    from matplotlib.figure import Figure
    import textwrap

    ink, muted, line = '#2B2622', '#6B5E52', '#E7DED3'
    with matplotlib.rc_context(_rc()):
        fig = Figure(figsize=(8.27, 11.69), dpi=150, facecolor='white')
        fig.text(0.06, 0.965, title, fontsize=19, weight='bold', color=ink, va='top')
        fig.text(0.06, 0.935, f'統計範圍：{scope}', fontsize=10, color=muted, va='top')

        # 三大數字
        for i, c in enumerate(cards[:3]):
            x = 0.06 + i * 0.30
            ax = fig.add_axes([x, 0.80, 0.28, 0.115])
            ax.set_axis_off()
            ax.add_patch(matplotlib.patches.FancyBboxPatch((0, 0), 1, 1, boxstyle='round,pad=0,rounding_size=0.06',
                                                           transform=ax.transAxes, facecolor='#FBF7F0', edgecolor=line))
            ax.text(0.07, 0.84, c['title'], fontsize=10, color=muted, weight='bold', transform=ax.transAxes, va='top')
            ax.text(0.07, 0.55, c['number'], fontsize=21, color='#4338CA' if c.get('ai') else '#1F5F7A',
                    weight='bold', transform=ax.transAxes, va='center')
            if c.get('before'):
                vs = f"{c['before']} → {c['after']}" if c.get('after') else c['before']
                ax.text(0.07, 0.16, vs, fontsize=8.5, color=ink, transform=ax.transAxes)

        # 需求熱圖
        fig.text(0.06, 0.775, f'需求熱圖：{heat_title}', fontsize=12, weight='bold', color=ink, va='top')
        ax = fig.add_axes([0.10, 0.555, 0.84, 0.195])
        if heat is not None and not heat.empty:
            values = heat.to_numpy(dtype=float)
            ax.imshow(values, cmap='OrRd', aspect='auto', vmin=0)
            ax.set_xticks(range(heat.shape[1]), [str(c).replace('時', '') for c in heat.columns], fontsize=8)
            ax.set_yticks(range(heat.shape[0]), list(heat.index), fontsize=9)
            ax.set_xlabel('時段（點）', fontsize=8)
            top = values.max() if values.size else 0
            if heat.shape[1] <= 16:
                for (r, k), v in pd.DataFrame(values).stack().items():
                    if v > 0:
                        ax.text(k, r, heat_fmt.format(v), ha='center', va='center', fontsize=6.5,
                                color='white' if top and v > top * 0.6 else ink)
            ax.tick_params(length=0)
            for spine in ax.spines.values():
                spine.set_visible(False)
        else:
            ax.set_axis_off()
            ax.text(0.5, 0.5, '沒有日期與時段資料', ha='center', va='center', color=muted, transform=ax.transAxes)

        # 人力負荷分布
        fig.text(0.06, 0.515, '人力負荷分布：每位居服員本期總工時（含轉場）', fontsize=12, weight='bold', color=ink, va='top')
        ax = fig.add_axes([0.10, 0.315, 0.84, 0.175])
        if load is not None and not load.empty:
            view = load.head(30)
            bottom = [0.0] * len(view)
            for status in STATUS_ORDER:
                vals = view[status].tolist()
                if any(vals):
                    ax.bar(range(len(view)), vals, bottom=bottom, color=STATUS_COLORS[status], label=status, width=0.72)
                    bottom = [b + v for b, v in zip(bottom, vals)]
            ax.set_xticks(range(len(view)), list(view.index), rotation=60, ha='right', fontsize=6.5)
            ax.set_ylabel('小時', fontsize=8)
            ax.tick_params(axis='y', labelsize=8)
            ax.spines[['top', 'right']].set_visible(False)
            ax.legend(fontsize=8, frameon=False, loc='upper right', ncol=3)
        else:
            ax.set_axis_off()
            ax.text(0.5, 0.5, '沒有工時資料', ha='center', va='center', color=muted, transform=ax.transAxes)

        # AI 建議
        fig.text(0.06, 0.225, 'AI 增聘／調派建議', fontsize=12, weight='bold', color='#4338CA', va='top')
        y = 0.198
        for head, body in advice[:6]:
            if y < 0.03:
                break
            fig.text(0.07, y, '• ' + head, fontsize=9.5, weight='bold', color=ink, va='top')
            wrapped = textwrap.wrap(body, 52)
            fig.text(0.09, y - 0.017, '\n'.join(wrapped[:2]), fontsize=8.5, color=muted, va='top', linespacing=1.4)
            y -= 0.017 + 0.0155 * min(2, len(wrapped)) + 0.008
        fig.text(0.06, 0.012, '效益數字依「調整假設」估算；正式報告請以機構實測數據替換。CareFlow AI 產生。',
                 fontsize=7, color=muted)
    return fig


def figure_bytes(fig, fmt='png'):
    import matplotlib
    buf = io.BytesIO()
    with matplotlib.rc_context(_rc()):          # 字型在存檔（繪製）時才決定，必須包在同一個設定裡
        fig.savefig(buf, format=fmt, facecolor='white')
    return buf.getvalue()
