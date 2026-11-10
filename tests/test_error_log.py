"""錯誤紀錄：寫進紀錄檔（含追蹤）並回傳錯誤代碼；整頁測試在 test_plan_change_ui.py。"""
import error_log


def test_log_error_writes_traceback_and_returns_code(tmp_path, monkeypatch):
    monkeypatch.setattr(error_log, 'LOG_DIR', tmp_path)
    for handler in list(error_log._logger.handlers):
        error_log._logger.removeHandler(handler)
    try:
        {}['missing']
    except KeyError as exc:
        state = {}
        code = error_log.log_error('測試位置', exc, state)
    assert state['_error_log'][0]['代碼'] == code
    text = (tmp_path / 'careflow_errors.log').read_text(encoding='utf-8')
    assert code.startswith('E') and code in text and '測試位置' in text and 'Traceback' in text and "KeyError: 'missing'" in text
    for handler in list(error_log._logger.handlers):
        error_log._logger.removeHandler(handler)
