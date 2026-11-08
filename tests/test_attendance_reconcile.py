"""執行對照：排班 vs 打卡，遲到、漏打卡、未遇、補登待覆核、排外打卡；位置只提醒、不算異常。"""
from datetime import date, datetime
from types import SimpleNamespace

import pandas as pd
import pytest

import attendance_reconcile as att
from checkin import store

CFG = SimpleNamespace(attendance_late_grace_mins=10, attendance_early_leave_grace_mins=10, attendance_gps_radius_m=300)
DAY = date(2026, 11, 9)


def _schedule():
    return pd.DataFrame({
        '任務ID': ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8'],
        '日期': ['2026-11-09'] * 8,
        '開始時間': ['08:00', '10:00', '13:00', '14:00', '15:00', '16:00', '20:00', '09:00'],
        '結束時間': ['09:00', '12:00', '14:00', '15:00', '16:00', '17:00', '21:00', '10:00'],
        '案號': ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8'],
        '最終派單居服員': ['A', 'A', 'B', 'B', 'C', 'C', 'A', '未指派'],
        '服務地點_緯度': [25.0] * 8, '服務地點_經度': [121.5] * 8,
    })


@pytest.fixture
def punches(tmp_path, monkeypatch):
    """用真的打卡資料庫產生紀錄，確保 punch_frame 的格式和對照邏輯一致。"""
    path = str(tmp_path / 'checkin.sqlite3')
    def punch(hh, mm, *args, **kw):
        monkeypatch.setattr(store, 'now', lambda: datetime(2026, 11, 9, hh, mm))
        ok, msg = store.add_punch(*args, path=path, **kw)
        assert ok, msg
    # 先發布一筆後來被改掉的班並打卡，再重新發布正式班表（X1 從班表移除，打卡留著 → 排外打卡）
    store.publish_shifts(pd.DataFrame({'任務ID': ['X1'], '日期': ['2026-11-09'], '開始時間': ['11:00'], '結束時間': ['12:00'],
                                       '案號': ['C9'], '最終派單居服員': ['A']}), DAY, path=path)
    punch(11, 0, 'A', 'X1', '上班')
    store.publish_shifts(_schedule(), DAY, path=path)
    punch(8, 2, 'A', 'T1', '上班', lat=25.0, lon=121.5)
    punch(9, 0, 'A', 'T1', '下班')                                     # T1 正常
    punch(10, 25, 'A', 'T2', '上班')
    punch(11, 40, 'A', 'T2', '下班')                                   # T2 遲到 25 分、早退 20 分
    punch(13, 5, 'B', 'T3', '未遇')                                    # T3 未遇
    # T4 整筆沒打
    punch(15, 1, 'C', 'T5', '上班', lat=25.02, lon=121.5)              # T5 漏打下班＋位置提醒
    punch(16, 30, 'C', 'T6', '上班', at='16:00', note='手機沒電')      # T6 補登待覆核
    punch(17, 0, 'C', 'T6', '下班')
    monkeypatch.setattr(store, 'now', lambda: datetime(2026, 11, 9, 18, 0))
    return store.punch_frame(path=path)


def _result(punches, now=datetime(2026, 11, 9, 18, 0)):
    return att.reconcile(_schedule(), punches, CFG, now=now).set_index('任務ID')


def test_each_service_classified(punches):
    out = _result(punches)
    assert out.loc['T1', '狀態'] == att.STATUS_OK and out.loc['T1', '遲到(分)'] == 2
    assert set(out.loc['T2', '異常項目'].split('、')) == {'遲到', '早退'}
    assert out.loc['T2', '遲到(分)'] == 25 and out.loc['T2', '早退(分)'] == 20
    assert out.loc['T3', '狀態'] == '未遇' and out.loc['T3', '嚴重度'] == '高'
    assert out.loc['T4', '狀態'] == att.NO_RECORD and out.loc['T4', '嚴重度'] == '高'
    assert out.loc['T5', '狀態'] == att.NO_OUT and '位置提醒' in out.loc['T5', '異常項目']
    assert out.loc['T5', '上班距案家(公尺)'] > 2000
    assert out.loc['T6', '狀態'] == att.PENDING and out.loc['T6', '上班'] == '16:00' and out.loc['T6', '補登'] == '是'
    assert out.loc['T7', '狀態'] == att.STATUS_NOT_YET                # 20:00 的班還沒到
    assert 'T8' not in out.index                                        # 未派的不對照
    assert out.loc['X1', '狀態'] == att.EXTRA and out.loc['X1', '打卡居服員'] == 'A'
    assert list(att.reconcile(_schedule(), punches, CFG, now=datetime(2026, 11, 9, 18, 0))['嚴重度'])[:2] == ['高', '高']


def test_far_location_alone_is_only_a_reminder(punches):
    sched = _schedule().iloc[[4]]
    punches = punches[punches['任務ID'] == 'T5']
    extra = punches.iloc[[0]].assign(打卡類型='下班', 打卡時間='2026-11-09 16:00:00', 緯度=None, 經度=None)
    out = att.reconcile(sched, pd.concat([punches, extra]), CFG, now=datetime(2026, 11, 9, 18, 0))
    assert out.loc[0, '狀態'] == att.STATUS_OK and out.loc[0, '嚴重度'] == '提醒'


def test_missing_clock_out_waits_until_service_ends(punches):
    out = _result(punches, now=datetime(2026, 11, 9, 15, 30))
    assert out.loc['T5', '狀態'] == att.STATUS_OK and out.loc['T5', '異常項目'] == '位置提醒'   # 16:00 才結束，還不算漏打下班
    assert out.loc['T4', '狀態'] == att.NO_RECORD                     # 14:00～15:00 已結束


def test_rejected_late_entry_is_ignored(punches):
    pid = punches.loc[punches['補登'], '紀錄ID'].iloc[0]
    rejected = punches.copy()
    rejected.loc[rejected['紀錄ID'] == pid, '覆核'] = store.REVIEW_REJECTED
    out = _result(rejected)
    assert out.loc['T6', '狀態'] == att.NO_IN


def test_summary_and_by_caregiver(punches):
    result = att.reconcile(_schedule(), punches, CFG, now=datetime(2026, 11, 9, 18, 0))
    s = att.summary(result)
    assert s['應對照'] == 6 and s['正常'] == 1                          # T1～T6；T7 尚未結束
    assert (s['遲到'], s['漏打卡'], s['未遇'], s['補登待覆核'], s['排外打卡'], s['位置提醒']) == (1, 2, 1, 1, 1, 1)
    assert s['準時率'] == 75.0                                         # 有上班打卡 4 筆（T1 T2 T5 T6），遲到 1 → 3/4
    per = att.by_caregiver(result).set_index('居服員ID')
    assert per.loc['A', '服務數'] == 2 and per.loc['A', '遲到'] == 1
    assert per.loc['B', '漏打卡'] == 1 and per.loc['B', '未遇'] == 1
    assert att.by_caregiver(result.iloc[0:0]).empty


def test_schedule_in_range():
    sched = _schedule().assign(日期=['2026-11-08', '2026-11-09', '2026-11-10'] + ['2026-11-09'] * 5)
    assert len(att.schedule_in_range(sched, date(2026, 11, 9), date(2026, 11, 9))) == 6
