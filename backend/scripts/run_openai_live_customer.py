"""Real OpenAI customer probe: run `python scripts/run_openai_live_customer.py` from backend/.
Does not print or save any credentials. Makes three billable API calls with a valid key.
"""
from pathlib import Path
import os
import sys
import tempfile
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)
if not os.getenv('OPENAI_API_KEY', '').strip():
    print('BLOCKED: OPENAI_API_KEY is not configured in backend/.env or environment.')
    sys.exit(2)
os.environ['AI_PROVIDER'] = 'openai'
with tempfile.TemporaryDirectory(prefix='masr-gpt-live-') as folder:
    os.environ['DATABASE_PATH'] = str(Path(folder) / 'places.sqlite3')
    os.environ['MASR_USER_DB'] = str(Path(folder) / 'accounts.sqlite3')
    os.environ['APP_ENV'] = 'development'
    from fastapi.testclient import TestClient
    from app.main import app
    cases = [
        ('EN tourism', '/api/chat', {'language': 'English',
          'message': 'I am visiting Luxor with my kids. Explain Karnak Temple using your verified sources.'}, 'openai-rag'),
        ('AR tourism', '/api/chat', {'language': 'Arabic',
          'message': 'عايز أعرف تاريخ معبد الكرنك بطريقة بسيطة لطفل 10 سنين وبمصادر.'}, 'openai-rag'),
        ('AR planner', '/api/consult', {'language': 'Arabic',
          'message': 'خطط لي رحلة 6 أيام: 4 أيام في القاهرة ويومين في الأقصر، مع طفلين.'}, 'openai-intent+local-planner'),
    ]
    failed = 0
    with TestClient(app) as client:
        for label, url, body, expected in cases:
            resp = client.post(url, json=body)
            doc = resp.json()
            answer = doc.get('answer', '')
            valid = (resp.status_code == 200 and doc.get('mode') == expected
                     and isinstance(answer, str) and bool(answer.strip()))
            if label == 'AR planner':
                valid = valid and doc.get('itinerary', {}).get('day_allocation') == {'Cairo':4,'Luxor':2}
            print(f"{'PASS' if valid else 'FAIL'} {label}: HTTP={resp.status_code}, mode={doc.get('mode', 'none')}")
            print(str(answer).replace('\n', ' ')[:350])
            failed += not valid
    if failed:
        sys.exit(1)
print('PASS: 3/3 real OpenAI customer scenarios')
