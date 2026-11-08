"""存取稽核紀錄：雜湊鏈、只能附加、竄改偵測、不記個資、寫入失敗不中斷。"""
import sqlite3

import pytest

import audit_log


def test_chain_append_only_and_tamper_detection(tmp_path):
    folder = str(tmp_path / 'audit')
    assert audit_log.verify(folder) == {'ok': True, 'count': 0, 'first_bad_seq': None, 'last_hash': audit_log.GENESIS}
    assert audit_log.record('login', account='boss', folder=folder, role='主管')
    assert audit_log.record('login_failed', account='amy01', folder=folder)
    assert audit_log.record('account', account='boss', folder=folder, action='create', target='amy01', role='居督')
    rows = audit_log.entries(folder=folder)
    assert [r['event'] for r in rows] == ['login', 'login_failed', 'account']
    assert rows[0]['prev_hash'] == audit_log.GENESIS and rows[1]['prev_hash'] == rows[0]['hash']   # 每筆接前一筆
    assert audit_log.verify(folder)['ok'] and audit_log.verify(folder)['count'] == 3

    db = sqlite3.connect(audit_log.db_path(folder))
    with pytest.raises(sqlite3.DatabaseError, match='append-only'):
        db.execute("UPDATE audit SET account='x' WHERE seq=2")
    with pytest.raises(sqlite3.DatabaseError, match='append-only'):
        db.execute('DELETE FROM audit WHERE seq=2')
    db.execute('DROP TRIGGER audit_no_update')                          # 繞過觸發器直接改檔
    db.execute("UPDATE audit SET account='someone' WHERE seq=2")
    db.commit()
    db.close()
    state = audit_log.verify(folder)
    assert not state['ok'] and state['first_bad_seq'] == 2


def test_personal_fields_are_dropped(tmp_path):
    folder = str(tmp_path / 'audit')
    audit_log.record('account', account='boss', folder=folder, action='create', target='amy01',
                     name='林小美', 姓名='林小美', 地址='台北市', phone='0912', note='x' * 500)
    detail = audit_log.entries(folder=folder)[0]['detail']
    assert '林小美' not in detail and '台北市' not in detail and '0912' not in detail
    assert '"target":"amy01"' in detail and len(detail) < 300           # 長字串截斷


def test_record_never_raises(tmp_path):
    blocker = tmp_path / 'not_a_folder'
    blocker.write_text('x')
    assert audit_log.record('login', account='boss', folder=str(blocker)) is False   # 寫不進去只回傳 False


def test_table_newest_first(tmp_path):
    folder = str(tmp_path / 'audit')
    for event in ('login', 'logout'):
        audit_log.record(event, account='boss', folder=folder)
    table = audit_log.as_table(folder=folder)
    assert list(table.columns) == ['序號', '時間', '帳號', '事件', '內容']
    assert list(table['事件']) == ['登出', '登入']
