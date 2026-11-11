"""復原上一步：班表有變動就記一步；按復原回到變動前（含請假紀錄）。"""

import pandas as pd

import undo_stack as undo


class FakeStore:
    def __init__(self):
        self.items, self.next = [], 1

    def blocks(self):
        return [dict(b) for b in self.items]

    def add_blocks(self, cg, day, spans, reason):
        for a, b in spans:
            self.items.append({'id': self.next, 'cg': cg, 'start': f'{day}T{a}:00', 'end': f'{day}T{b}:00', 'reason': reason})
            self.next += 1

    def remove_block(self, bid):
        self.items = [b for b in self.items if b['id'] != bid]


def _state():
    res = {'input_signature': 'S1', 'df_tasks': pd.DataFrame({'任務ID': ['T1', 'T2']}),
           'phase2': {'df_result': pd.DataFrame({'任務ID': ['T1'], '派單居服員': ['A']})}}
    return {'last_result': res, 'overrides': {}, 'dynamic_adjustment_log': []}


def _track(state, store):
    token = repr((sorted(state['overrides'].items()), len(state['dynamic_adjustment_log']),
                  [b['id'] for b in store.blocks()], list(state['last_result']['df_tasks']['任務ID'])))
    return undo.track(state, token, state['last_result']['input_signature'],
                      lambda: undo.snapshot(state, state['last_result'], store.blocks()), store.blocks())


def test_each_change_becomes_one_step_and_undo_restores_it():
    state, store = _state(), FakeStore()
    assert not _track(state, store)                               # 第一次：只記下起點
    assert not _track(state, store)                               # 沒變：不記
    state['overrides']['T2'] = {'cg_id': 'B', 'reason': '交通'}
    assert _track(state, store) and state['_undo_stack'][-1]['label'] == '人工改派（1 筆）'
    store.add_blocks('A', '2026-11-02', [('09:00', '12:00')], '請假')
    state['overrides']['T1'] = {'cg_id': None, 'reason': '已登錄請假'}
    assert _track(state, store) and state['_undo_stack'][-1]['label'] == '登錄請假'
    assert len(state['_undo_stack']) == 2

    assert '已復原' in undo.undo(state, store)                     # 退回：請假移除、T1 覆寫消失
    assert store.blocks() == [] and 'T1' not in state['overrides'] and state['overrides']['T2']['cg_id'] == 'B'
    assert not _track(state, store)                               # 復原後那次重跑不算新的一步
    assert undo.undo(state, store) and state['overrides'] == {}
    assert undo.undo(state, store) == ''                          # 沒有步驟了


def test_new_schedule_clears_steps_and_labels():
    state, store = _state(), FakeStore()
    _track(state, store)
    state['dynamic_adjustment_log'].append({'事件類型': '週計畫異動（新增）'})
    _track(state, store)
    assert state['_undo_stack'][-1]['label'] == '週計畫異動'
    state['last_result']['input_signature'] = 'S2'                # 重新排班
    state['overrides']['X'] = {'cg_id': 'A'}
    assert not _track(state, store) and state['_undo_stack'] == []
    for i in range(15):
        state['overrides'][f'T{i}'] = {'cg_id': 'A', 'reason': '以居服員排班：勾選'}
        _track(state, store)
    assert len(state['_undo_stack']) == undo.MAX_STEPS and state['_undo_stack'][-1]['label'].startswith('以居服員排班')
