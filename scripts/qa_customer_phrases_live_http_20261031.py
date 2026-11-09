"""Independent real-HTTP offline trip/payment regression (no keys, temp databases)."""
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def run():
    with tempfile.TemporaryDirectory(prefix='masr_customer_phrases_') as tmp:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        env = os.environ.copy()
        env.update(DATABASE_PATH=str(Path(tmp)/'catalog.db'),
                   MASR_USER_DB=str(Path(tmp)/'account.db'),
                   AI_PROVIDER='offline', GEMINI_API_KEY='', OPENAI_API_KEY='',
                   CHAT_RATE_LIMIT_PER_MINUTE='999')
        proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app',
            '--host', '127.0.0.1', '--port', str(port), '--log-level', 'error'],
            cwd=ROOT/'backend', env=env, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        base = f'http://127.0.0.1:{port}'
        count = 0
        def check(label, condition):
            nonlocal count
            assert condition, label
            count += 1
            print('PASS', label)
        def talk(message, lang='Arabic', state=None):
            payload = {'message': message, 'language': lang}
            if state is not None:
                payload['trip_state'] = state
            response = requests.post(base+'/api/consult', json=payload, timeout=8)
            assert response.status_code == 200, (response.status_code, response.text[:150])
            return response.json()
        try:
            for _ in range(70):
                try:
                    if requests.get(base+'/api/ready', timeout=1).status_code == 200:
                        break
                except requests.RequestException:
                    pass
                assert proc.poll() is None, 'server exited'
                time.sleep(.1)
            else:
                raise AssertionError('server did not become ready')
            start = talk('خططلي رحلة 12 يوم 4 أيام القاهرة و4 أيام الأقصر و4 أيام الغردقة')
            state = start['trip_state']
            check('12-day itinerary has 3 named cities', [p['days'] for p in state['phases']] == [4, 4, 4])
            changed = talk('شيل يومين من الأقصر وحطهم في الغردقة', state=state)
            check('colloquial transfer really persists 4+2+6',
                  [p['days'] for p in changed['trip_state']['phases']] == [4, 2, 6])
            check('transfer preserves 12 days', changed['trip_state']['days'] == 12
                  and len(changed['itinerary']['days']) == 12)
            invalid = talk('شيل 9 أيام من الأقصر وحطهم في الغردقة', state=state)
            check('overdraw cannot mutate trip', invalid['trip_state'] == state
                  and invalid['mode'] == 'needs-clarification')
            pay = talk('هل أقدر أدفع بالفيزا هنا؟', state=state)
            check('visa payment receives safe response', pay['mode'] == 'local-assistant'
                  and 'لا يمكنني' in pay['answer'])
            pan = talk('ده رقم بطاقتي 4111 1111 1111 1111', state=state)
            check('card number not reflected in response', '4111' not in pan['answer']
                  and pan['mode'] == 'local-assistant')
            check('side payment question preserves trip', pay['trip_state'] == state)
            french = talk('Je veux visiter l’Egypte pendant dix jours, Le Caire et Louxor', lang='French')
            check('French ten days recognized', french['trip_state']['days'] == 10)
            check('French two named cities preserved',
                  {'Cairo', 'Luxor'} <= {c for p in french['trip_state']['phases'] for c in p['cities']})
            visa = talk('هل أحتاج فيزا دخول مصر؟')
            check('entry visa not mistaken for a payment', 'بطاقتك البنكية' not in visa['answer'])
            print(f'TOTAL {count}/{count} PASS (local offline; no live Gemini)')
        finally:
            proc.terminate()
            try: proc.wait(timeout=4)
            except subprocess.TimeoutExpired: proc.kill()


if __name__ == '__main__':
    run()
