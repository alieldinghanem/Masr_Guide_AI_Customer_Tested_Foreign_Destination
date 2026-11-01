"""Run real HTTP acceptance on an isolated local FastAPI process (offline AI).

Usage: python scripts/ai_backend_customer_http_20261031.py
No API keys or customer data required. Temporary databases are deleted afterward.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PORT = 18793
BASE = f'http://127.0.0.1:{PORT}'


def request(path, payload=None, *, token=None, method=None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(BASE + path, data=data, headers=headers,
                                 method=method or ('POST' if data is not None else 'GET'))
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as err:
        return err.code, json.load(err)


def main():
    completed = []
    def check(label, condition):
        completed.append({'test': label, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(label)
    with tempfile.TemporaryDirectory(prefix='masr_customer_http_') as temp:
        env = dict(os.environ, APP_ENV='development', AI_PROVIDER='offline', GEMINI_API_KEY='',
                   OPENAI_API_KEY='', DATABASE_PATH=temp+'/catalog.sqlite3',
                   MASR_USER_DB=temp+'/users.sqlite3', CHAT_RATE_LIMIT_PER_MINUTE='300')
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app',
                                    '--host', '127.0.0.1', '--port', str(PORT), '--no-proxy-headers'],
                                   cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                try:
                    if request('/api/ready')[0] == 200:
                        break
                except Exception:
                    time.sleep(.1)
            else:
                raise RuntimeError('Uvicorn failed to start')
            check('Server readiness', request('/api/ready')[0] == 200)
            def ask(message, state=None, language='Arabic', token=None):
                body = {'message': message, 'language': language}
                if state is not None:
                    body['trip_state'] = state
                return request('/api/consult', body, token=token)
            code, week = ask('أنا جاي مصر أسبوع مع زوجتي وطفلين، عايز القاهرة والأقصر والغردقة')
            check('Arabic family week returns 7 days', code == 200 and week.get('trip_state',{}).get('days') == 7)
            check('Week actual itinerary contains 7 days', len(week.get('itinerary',{}).get('days',[])) == 7)
            code, month = ask('خطط 30 يوم: 10 أيام القاهرة و5 أيام الأقصر و7 أيام أسوان و8 أيام الغردقة')
            state = month.get('trip_state') or {}
            check('Explicit month city allocations', code == 200 and [p['days'] for p in state['phases']] == [10,5,7,8])
            code, edit = ask('انقل يومين من القاهرة للغردقة', state)
            state = edit.get('trip_state') or {}
            check('Arabic transfer preserves total and updates cities', code == 200 and state['days'] == 30 and [p['days'] for p in state['phases']] == [8,5,7,10])
            check('Travel days match updated state', len(edit.get('itinerary',{}).get('days',[])) == 30 and edit['itinerary']['day_allocation']['Hurghada'] == 10)
            code, en = ask('Move 2 days from Cairo to Hurghada', state, language='English')
            check('English multi-turn transfer', code == 200 and [p['days'] for p in en['trip_state']['phases']] == [6,5,7,12])
            state = en['trip_state']
            code, too_many = ask('انقل 6 أيام من القاهرة للغردقة', state)
            check('Invalid transfer never overwrites itinerary', code == 200 and too_many.get('trip_state') == state and too_many.get('itinerary') is None)
            code, side = ask('رشح فندق في القاهرة لعيلة مع طفلين', state)
            check('Hotel side-question leaves itinerary unchanged', code == 200 and side.get('trip_state') == state and side.get('itinerary') is None)
            code, safety = ask('ممكن ادفع بالكارت داخل الشات؟', state)
            check('Card payments are refused and trip unchanged', code == 200 and safety.get('trip_state') == state and 'لا يمكنني' in safety.get('answer',''))
            code, noauth = ask('احفظ الرحلة في حسابي', state)
            check('Anonymous save explicitly refused', code == 200 and noauth.get('mode') == 'needs-authentication' and not noauth.get('saved_trip_id'))
            code, register = request('/api/auth/register', {'email':'qa.customer@example.com', 'password':'TestingPassword123#'})
            check('Account registration', code == 201 and bool(register.get('token')))
            token = register['token']
            code, saved = ask('احفظ الرحلة في حسابي', state, token=token)
            check('Authenticated chatbot save returns id', code == 200 and saved.get('mode') == 'trip-saved' and bool(saved.get('saved_trip_id')))
            trip_id=saved['saved_trip_id']
            code, read = request('/api/my/trips/' + trip_id, token=token)
            check('Persisted itinerary returns correct 30-day allocation', code == 200 and len(read['itinerary']['days']) == 30 and read['itinerary']['day_allocation']['Hurghada'] == 12)
            code, another = request('/api/auth/register', {'email':'qa.other@example.com','password':'TestingPassword123#'})
            check('Separate account registration', code == 201 and bool(another.get('token')))
            code, cross = request('/api/my/trips/' + trip_id, token=another['token'])
            check('Cross-account access is forbidden', code == 404)
            code, logout = request('/api/auth/logout', {}, token=token)
            check('Logout revokes session', code == 200 and logout.get('ok'))
            code, after = request('/api/my/trips/' + trip_id, token=token)
            check('Revoked token cannot access trip', code == 401)
            code, oversized = ask('a'*1201)
            check('Oversized chat input is rejected', code == 422)
            code, unknown = ask('هل يوجد مطعم نباتي مفتوح حاليًا في الزمالك؟')
            check('Offline mode does not fabricate live restaurant status', code == 200 and unknown.get('mode') == 'restaurant-guide-limited')
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    output = {'mode':'OFFLINE HTTP acceptance (no external AI API calls)',
              'passed':sum(item['passed'] for item in completed), 'total':len(completed), 'checks':completed}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if output['passed'] != output['total']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
