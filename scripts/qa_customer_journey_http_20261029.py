"""Real-HTTP buyer/visitor journey against a running localhost API.

Runs with temporary databases and no Gemini credentials; raises on failures.
Use this to regress backend actions, not to claim Gemini or React success.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:18765'


def call(path, method='GET', data=None, token=None):
    payload = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = Request(BASE + path, data=payload, headers=headers, method=method)
    try:
        with urlopen(request, timeout=6) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


def assert_allocation(data, expected):
    assert data['itinerary']['day_allocation'] == expected, data
    assert sum(expected.values()) == data['trip_state']['days']


def main():
    with tempfile.TemporaryDirectory(prefix='masr_customer_') as root:
        env = dict(os.environ, DATABASE_PATH=str(Path(root)/'places.sqlite3'),
                   MASR_USER_DB=str(Path(root)/'users.sqlite3'), APP_ENV='development',
                   GEMINI_API_KEY='', OPENAI_API_KEY='', CHAT_RATE_LIMIT_PER_MINUTE='60')
        with open(Path(root)/'server.log','w') as log:
            server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app',
                                       '--host', '127.0.0.1', '--port', '18765', '--no-proxy-headers'],
                                      cwd=ROOT/'backend', env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(80):
                    if server.poll() is not None:
                        raise RuntimeError('Local API did not start')
                    try:
                        if call('/api/ready')[0] == 200:
                            break
                    except (URLError, TimeoutError):
                        time.sleep(0.1)
                else:
                    raise RuntimeError('Local API readiness timeout')
                passed = 0
                def check(result):
                    nonlocal passed
                    assert result
                    passed += 1
                check(call('/api/health')[0] == 200)
                status, initial = call('/api/consult', 'POST',
                    {'message':'أنا جاي مصر 6 أيام: 4 أيام القاهرة ويومين الأقصر مع زوجتي وطفلي', 'language':'Arabic'})
                assert_allocation(initial, {'Cairo': 4, 'Luxor': 2}); check(status == 200)
                status, changed = call('/api/consult', 'POST',
                    {'message':'غيرها إلى 3 أيام القاهرة و3 أيام أسوان', 'language':'Arabic', 'trip_state':initial['trip_state']})
                assert_allocation(changed, {'Cairo':3,'Aswan':3}); check(status == 200)
                status, no_auth = call('/api/consult','POST',
                    {'message':'احفظ الرحلة في حسابي','language':'Arabic','trip_state':changed['trip_state']})
                check(status == 200 and no_auth['mode'] == 'needs-authentication')
                status, register = call('/api/auth/register','POST',
                    {'email':'visitor@example.com', 'password':'strong-demo-password-001'})
                check(status == 201)
                status, saved = call('/api/consult','POST',
                    {'message':'ممكن تحفظ الرحلة باسمي','language':'Arabic','trip_state':changed['trip_state']}, register['token'])
                check(status == 200 and saved['mode'] == 'trip-saved' and bool(saved['saved_trip_id']))
                status, loaded = call('/api/my/trips/'+saved['saved_trip_id'],token=register['token'])
                check(status == 200 and loaded['itinerary']['day_allocation'] == {'Cairo':3,'Aswan':3})
                status, transport = call('/api/consult','POST',
                    {'message':'ازاي اروح من مطار القاهرة للزمالك؟','language':'Arabic'})
                check(status == 200 and 'الزمالك' in transport['answer'])
                status, family = call('/api/consult','POST',
                    {'message':'أنا أول مرة أزور مصر مع زوجتي وطفلين، تنصحنا بإيه؟','language':'Arabic'})
                check(status == 200 and 'الأهرامات' in family['answer'])
                status, logout = call('/api/auth/logout','POST',token=register['token'])
                check(status == 200 and logout['ok'])
                status, denied = call('/api/my/trips/'+saved['saved_trip_id'],token=register['token'])
                check(status == 401)
                print(f'PASS {passed}/{passed} live HTTP customer journey assertions (offline AI mode)')
            finally:
                server.terminate()
                try: server.wait(timeout=8)
                except subprocess.TimeoutExpired: server.kill()


if __name__ == '__main__':
    main()
