"""Run isolated, real HTTP acceptance checks on stateful travel chat.

Uses temporary databases; NEVER calls Gemini/OpenAI. Intended for repeatable
CI checks alongside the main test suite. Execute from the repository root:
    python scripts/qa_chat_edit_live_http_20261031.py
"""
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def check(condition, description):
    assert condition, description
    print('PASS', description, flush=True)


def run():
    with tempfile.TemporaryDirectory(prefix='masr_chat_edit_http_') as tmp:
        env = os.environ.copy()
        env.update(DATABASE_PATH=str(Path(tmp) / 'places.sqlite'),
                   MASR_USER_DB=str(Path(tmp) / 'users.sqlite'),
                   GEMINI_API_KEY='', OPENAI_API_KEY='',
                   AI_PROVIDER='offline', CHAT_RATE_LIMIT_PER_MINUTE='999')
        port = free_port()
        base = f'http://127.0.0.1:{port}'
        proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app',
                                 '--host', '127.0.0.1', '--port', str(port), '--log-level', 'error'],
                                cwd=ROOT / 'backend', env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            for _ in range(80):
                if proc.poll() is not None:
                    raise AssertionError('FastAPI failed to launch')
                try:
                    if requests.get(base + '/api/ready', timeout=1).status_code == 200:
                        break
                except requests.RequestException:
                    pass
                time.sleep(0.1)
            else:
                raise AssertionError('FastAPI readiness timed out')
            check(requests.get(base + '/api/health', timeout=4).json()['guide_mode'] == 'offline-preview',
                  'API health reports offline AI rather than fake Gemini Live')

            def talk(message, state=None):
                data = {'message': message}
                if state is not None:
                    data['trip_state'] = state
                resp = requests.post(base + '/api/consult', json=data, timeout=8)
                assert resp.status_code == 200, (message, resp.status_code, resp.text[:250])
                return resp.json()

            first = talk('Plan 15 days: 10 days in Cairo and 5 days in Sharm El Sheikh')
            original = first['trip_state']
            check(len(first['itinerary']['days']) == 15 and
                  [p['days'] for p in original['phases']] == [10, 5],
                  '15-day itinerary preserves explicit 10+5 allocation')
            for utterance in ('خلينا نزود 3 أيام في القاهرة', 'زود 3 أيام القاهرة',
                              'Add 3 days in Cairo', 'Increase Cairo by 3 days'):
                response = talk(utterance, original)
                check(response['mode'] == 'needs-clarification' and
                      response['trip_state'] == original and response['itinerary'] is None,
                      f'ambiguous city increase preserves trip: {utterance}')
            transfer = talk('انقل ٣ أيام من القاهرة لشرم الشيخ', original)
            check([p['days'] for p in transfer['trip_state']['phases']] == [7, 8] and
                  len(transfer['itinerary']['days']) == 15,
                  'explicit Arabic transfer safely produces 7+8')
            side = talk('إزاي أروح من المطار للفندق؟', transfer['trip_state'])
            check(side['trip_state'] == transfer['trip_state'] and side['itinerary'] is None,
                  'airport transport question does not change itinerary')
            no_auth = talk('احفظ الرحلة', transfer['trip_state'])
            check(no_auth['mode'] == 'needs-authentication' and not no_auth.get('saved_trip_id'),
                  'unauthenticated save never claims persistence')
            month = talk('Plan 30 days: 10 days in Cairo, 8 days in Luxor, 6 days in Aswan, 6 days in Hurghada')
            check(month['trip_state']['days'] == 30 and len(month['itinerary']['days']) == 30 and
                  [p['days'] for p in month['trip_state']['phases']] == [10, 8, 6, 6],
                  '30-day four-city itinerary preserves complete allocation')
            week = talk('عايز رحلة أسبوع في القاهرة والأقصر مع طفلين')
            check(week['trip_state']['days'] == 7 and week['trip_state']['family'] is True and
                  len(week['itinerary']['days']) == 7,
                  'Arabic family week has seven itinerary days')
            print('TOTAL: 11/11 verified real HTTP checks (offline AI, not provider live)')
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == '__main__':
    run()
