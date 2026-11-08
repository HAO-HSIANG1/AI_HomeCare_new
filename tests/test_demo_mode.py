"""示範模式：只用 Excel，不讀也不寫正式的工作紀錄。"""
from pathlib import Path

import dispatch_workflow as wf
from dispatch_workflow import WorkflowStore, discard_demo_store, fresh_demo_store_path, history_summary


def test_demo_store_starts_empty_and_leaves_real_store_untouched(tmp_path, monkeypatch):
    monkeypatch.setattr(wf, 'DEMO_STORE_DIR', str(tmp_path / 'demo'))
    real = WorkflowStore('中化', tmp_path / 'real.sqlite3')
    real.set_reviewed_primary('C1', 'A', '測試')
    real.add_blocks('A', '2026-10-05', [('08:00', '21:00')], '請假')
    real.replace_workdays([('A', '2026-09-28'), ('A', '2026-09-29')], '2026-09-01', '2026-09-30')
    assert history_summary(real, '2026-10-01', '2026-10-31') == {'blocks': 1, 'primary': 1, 'seed_workers': 1}

    path = fresh_demo_store_path(wf.DEMO_STORE_DIR)
    demo = WorkflowStore('中化', path)
    assert history_summary(demo, '2026-10-01', '2026-10-31') == {'blocks': 0, 'primary': 0, 'seed_workers': 0}
    demo.replace_workdays([('B', '2026-10-01')], '2026-10-01', '2026-10-31')
    assert real.recent_workdays('2026-10-02', lookback=10) == {'A': {'2026-09-28', '2026-09-29'}}

    discard_demo_store(path)
    assert not Path(path).exists()


def test_discard_never_deletes_files_outside_demo_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(wf, 'DEMO_STORE_DIR', str(tmp_path / 'demo'))
    real = tmp_path / 'dispatch_workflow.sqlite3'
    WorkflowStore('中化', real)
    discard_demo_store(str(real))
    assert real.exists()
