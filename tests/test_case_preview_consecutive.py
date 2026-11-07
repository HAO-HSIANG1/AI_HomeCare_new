"""③ 整案試算與 AI 主排班的「連續上班天數」規則一致性，以及上班日帳本的期間覆寫。"""
import pandas as pd

import caregiver_engine as engine
from dispatch_workflow import WorkflowStore
from pending_clients import preview_client_assignment
from test_agency_rules import worker, task, mocked_routes  # noqa: F401  (autouse：不連外查路網)


def cfg(**values):
    return engine.PipelineConfig(**values)


def clients(*ids, **fields):
    return pd.DataFrame([{'案家ID': identifier, **fields} for identifier in ids])


def test_case_preview_blocks_7th_consecutive_day_like_ai_dispatch():
    """③ 整案試算要和 AI 主排班同一條規則：其他案家已讓 A 連續上班 6 天，第 7 天的這一筆不能判為「可排進」。
    以前整案試算沒檢查連續上班天數，AI 擋下的案家在試算裡卻顯示全部排得進去。"""
    others = [task(f'd{i}', client='D', day=f'2026-11-{3 + i:02}') for i in range(6)]   # 11/03～11/08
    visits = pd.DataFrame(others + [task('c0', client='C', day='2026-11-09')])
    assignments = pd.DataFrame([{'任務ID': f'd{i}', '派單居服員': 'A'} for i in range(6)])
    people = pd.DataFrame([worker(), worker('B')])
    demands = pd.concat([clients('C', 歷史首選='A'), clients('D', 歷史首選='A')], ignore_index=True)
    blocked = preview_client_assignment(visits, assignments, people, demands, cfg(), 'C', 'A')
    assert blocked['accepted'].empty
    assert '連續上班 7 天' in blocked['failed'].iloc[0]['原因']
    # 換成沒有連續上班問題的 B 就排得進去
    other = preview_client_assignment(visits, assignments, people, demands, cfg(), 'C', 'B')
    assert other['failed'].empty and other['accepted']['派單居服員'].eq('B').all()
    # 手動流程若要「只提醒不擋」，可關閉此檢查
    manual = preview_client_assignment(visits, assignments, people, demands, cfg(), 'C', 'A', enforce_consecutive_days=False)
    assert manual['failed'].empty


def test_case_preview_uses_cross_month_seed_and_counts_days_after():
    """跨月種子也要算進去；補進中間空檔讓前後連成 7 天以上，同樣要擋。"""
    seed = {'A': {f'2026-10-{d:02}' for d in range(28, 32)}}           # 10/28～10/31 共 4 天
    others = [task(f'd{i}', client='D', day=f'2026-11-{2 + i:02}') for i in range(3)]   # 11/02～11/04
    visits = pd.DataFrame(others + [task('c0', client='C', day='2026-11-01')])   # 補上 11/01 → 連續 8 天
    assignments = pd.DataFrame([{'任務ID': f'd{i}', '派單居服員': 'A'} for i in range(3)])
    people = pd.DataFrame([worker(), worker('B')])
    demands = pd.concat([clients('C', 歷史首選='A'), clients('D', 歷史首選='A')], ignore_index=True)
    preview = preview_client_assignment(visits, assignments, people, demands, cfg(worker_workday_seed=seed), 'C', 'A')
    assert preview['accepted'].empty and '連續上班 8 天' in preview['failed'].iloc[0]['原因']


def test_replace_workdays_overwrites_only_the_period(tmp_path):
    """上班日帳本：重新排班後，本期間以新班表為準（舊的上班日被移除），期間外的紀錄保留。"""
    store = WorkflowStore('test', path=tmp_path / 'wf.sqlite3')
    store.record_workdays([('A', '2026-10-30'), ('A', '2026-11-02'), ('A', '2026-11-03'), ('B', '2026-11-04')])
    store.replace_workdays([('A', '2026-11-05'), ('B', '2026-12-01')], '2026-11-01', '2026-11-30')
    days = store.recent_workdays('2026-12-05', lookback=60)
    assert days == {'A': {'2026-10-30', '2026-11-05'}}
