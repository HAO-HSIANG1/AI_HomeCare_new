"""居服員手機打卡網頁（Flask）。

    python -m checkin.server            # http://本機:8600（HomeCare AI 開著時會自動在背景啟動，不必另外執行）

流程：掃 QR Code → 第一次輸入員工編號，這支手機就綁定給他 → 之後打開直接看到今天的班，按「上班」「下班」「未遇」。
- 打卡時間一律用主機時間（store.now()），不信任手機時間。
- 只有 https 連線才記錄 GPS（手機瀏覽器在 http 下本來就不給定位；伺服器端也再檢查一次）。
- 手機只存一組隨機綁定碼（cookie），資料庫只存它的雜湊；居督在 04 頁可以核准或解除。
"""
from __future__ import annotations

import argparse
import os
import secrets
from datetime import timedelta
from functools import wraps

from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for

from checkin import store

DEVICE_COOKIE = 'hc_device'
WEEKDAYS = '一二三四五六日'


def _secure_request():
    """這次連線是不是 https（架在 Caddy／Cloudflare 後面時看轉送標頭），或是本機測試。"""
    if request.is_secure or request.host.split(':')[0] in ('localhost', '127.0.0.1'):
        return True
    # Cloudflare Tunnel 另外帶 Cf-Visitor: {"scheme":"https"}（以防轉送時沒有 X-Forwarded-Proto）
    return '"scheme":"https"' in request.headers.get('Cf-Visitor', '').replace(' ', '')


def create_app(db_path=None, secure_cookie=None):
    """建立打卡網頁。db_path：打卡資料庫（預設 CAREFLOW_CHECKIN_DB 或 output_results/checkin.sqlite3）。"""
    app = Flask(__name__)
    secure = bool(secure_cookie if secure_cookie is not None
                  else os.getenv('CAREFLOW_CHECKIN_SECURE', '').strip().lower() in ('1', 'true', 'yes', 'on'))
    app.config.update(
        SECRET_KEY=store.secret_key(db_path),
        SESSION_COOKIE_NAME='hc_checkin',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=secure,
        PERMANENT_SESSION_LIFETIME=timedelta(days=365),   # 綁定後一年內打開就能打卡；居督解除綁定會立刻失效
        MAX_CONTENT_LENGTH=16 * 1024,
        CHECKIN_DB=db_path,
    )
    # 架在 Caddy／Cloudflare Tunnel 後面時，依轉送標頭判斷 https 與子路徑
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    def db():
        return app.config['CHECKIN_DB']

    def current_device():
        return store.device_for_token(request.cookies.get(DEVICE_COOKIE), db())

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            device = current_device()
            # 每次都核對綁定狀態：居督解除綁定或核准了別支手機，這支就要重新登入
            if not session.get('cg') or not device or device['status'] != store.DEVICE_ACTIVE \
                    or device['caregiver_id'] != session.get('cg'):
                session.pop('cg', None)
                if request.path.endswith('/punch'):
                    return jsonify(ok=False, message='這支手機已不能打卡，請重新輸入員工編號。'), 401
                return redirect(url_for('login'))
            return view(*args, **kwargs)
        return wrapped

    def remember_device(resp, token):
        resp.set_cookie(DEVICE_COOKIE, token, max_age=400 * 24 * 3600, httponly=True, samesite='Lax',
                        secure=app.config['SESSION_COOKIE_SECURE'])
        return resp

    def csrf_token():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(24)
        return session['csrf']

    def check_csrf(token):
        if not token or not secrets.compare_digest(str(token), session.get('csrf', '')):
            abort(400, '頁面已過期，請重新整理。')

    app.jinja_env.globals['csrf_token'] = csrf_token

    @app.after_request
    def no_cache(resp):
        resp.headers['Cache-Control'] = 'no-store'
        resp.headers['X-Content-Type-Options'] = 'nosniff'
        resp.headers['Referrer-Policy'] = 'no-referrer'
        resp.headers['X-Frame-Options'] = 'DENY'
        return resp

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        device = current_device()
        if request.method == 'GET' and device and device['status'] == store.DEVICE_ACTIVE:
            session.permanent = True
            session['cg'] = device['caregiver_id']
            return redirect(url_for('today'))
        if request.method == 'GET' and device and device['status'] == store.DEVICE_PENDING:
            return redirect(url_for('pending'))
        error = ''
        if request.method == 'POST':
            check_csrf(request.form.get('csrf'))
            cg = store.resolve_caregiver(request.form.get('cg', ''), db())
            if cg is None:
                error = '查不到這個員工編號，或居督還沒發布你的班表。'
            elif device and device['caregiver_id'] == cg and device['status'] == store.DEVICE_ACTIVE:
                session.permanent = True
                session['cg'] = cg
                return redirect(url_for('today'))
            else:
                token, status = store.request_device(cg, request.headers.get('User-Agent', ''), db())
                session.pop('cg', None)
                if status == store.DEVICE_ACTIVE:
                    session.permanent = True
                    session['cg'] = cg
                    session['flash'] = '這支手機已綁定，以後打開就能直接打卡。'
                    return remember_device(redirect(url_for('today')), token)
                return remember_device(redirect(url_for('pending')), token)
        return render_template('login.html', error=error)

    @app.get('/pending')
    def pending():
        device = current_device()
        if not device:
            return redirect(url_for('login'))
        if device['status'] == store.DEVICE_ACTIVE:
            session.permanent = True
            session['cg'] = device['caregiver_id']
            return redirect(url_for('today'))
        return render_template('pending.html', device=device, rejected=device['status'] != store.DEVICE_PENDING)

    @app.get('/device-status')
    def device_status():
        device = current_device()
        return jsonify(status=device['status'] if device else 'none')

    @app.post('/logout')
    def logout():
        """登出只清這次的登入；綁定還在，下次輸入同一個編號就直接進來。"""
        check_csrf(request.form.get('csrf'))
        session.clear()
        return redirect(url_for('login'))

    @app.get('/')
    @login_required
    def today():
        cg = session['cg']
        day = store.now().date()
        shifts = store.shifts_for(cg, day, db())
        punches = store.punches_for_tasks([s['task_id'] for s in shifts], db())
        for s in shifts:
            mine = [p for p in punches.get(s['task_id'], []) if p.get('review') != store.REVIEW_REJECTED]
            s['punches'] = store.effective_punches(mine)
            s['state'] = store.shift_state(s['punches'])
            s['pending'] = [p for p in mine if p['late_entry'] and p['review'] == store.REVIEW_PENDING]
        return render_template('today.html', cg=cg, day=day, weekday=WEEKDAYS[day.weekday()], shifts=shifts,
                               secure=_secure_request(), flash=session.pop('flash', ''))

    @app.post('/punch')
    @login_required
    def punch():
        data = request.get_json(silent=True) or {}
        check_csrf(request.headers.get('X-CSRF-Token'))
        ok, msg = store.add_punch(session['cg'], str(data.get('task_id', '')), str(data.get('kind', '')),
                                  lat=data.get('lat'), lon=data.get('lon'), accuracy=data.get('accuracy'),
                                  at=data.get('at') or None, note=data.get('note', ''),
                                  gps_allowed=_secure_request(), path=db())
        return jsonify(ok=ok, message=msg), (200 if ok else 409)

    @app.get('/healthz')
    def healthz():
        return 'ok'

    @app.errorhandler(400)
    def bad_request(err):
        if request.path.endswith('/punch'):
            return jsonify(ok=False, message=err.description), 400
        return redirect(url_for('login'))

    return app


def main():
    parser = argparse.ArgumentParser(description='HomeCare AI 居服員打卡網頁')
    parser.add_argument('--host', default=os.getenv('CAREFLOW_CHECKIN_HOST', '0.0.0.0'))
    parser.add_argument('--port', type=int, default=int(os.getenv('CAREFLOW_CHECKIN_PORT', '8600')))
    args = parser.parse_args()
    app = create_app()
    print(f'HomeCare AI 打卡網頁：http://<這台電腦的 IP>:{args.port}（Ctrl+C 結束）')
    try:
        from waitress import serve
    except ImportError:
        app.run(host=args.host, port=args.port)
    else:
        serve(app, host=args.host, port=args.port, threads=8)


if __name__ == '__main__':
    main()
