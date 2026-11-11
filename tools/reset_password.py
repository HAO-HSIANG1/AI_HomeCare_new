"""唯一的主管忘記密碼時用：在放 HomeCare AI 的這台電腦上重設某個帳號的密碼（同時解除鎖定）。

用法（在專案資料夾打開命令提示字元）：
    python tools/reset_password.py 帳號

會請你輸入兩次新密碼（畫面上不會顯示），完成後寫一筆稽核紀錄。能操作這台電腦的人才能用，所以不另外驗證身分。
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import audit_log  # noqa: E402
import auth  # noqa: E402


def main(argv):
    if len(argv) != 2:
        print('用法：python tools/reset_password.py 帳號')
        return 2
    username = auth.normalize_username(argv[1])
    if not any(u['username'] == username for u in auth.users()):
        print(f'找不到帳號 {username}。目前的帳號：' + '、'.join(u['username'] for u in auth.users()))
        return 1
    password = getpass.getpass('新密碼：')
    problem = auth.password_error(password, getpass.getpass('再輸入一次：')) or auth.set_password(username, password)
    if problem:
        print(problem)
        return 1
    audit_log.record('account', account='(本機重設工具)', action='reset_password', target=username)
    print(f'已重設 {username} 的密碼並解除鎖定，請用新密碼登入。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
