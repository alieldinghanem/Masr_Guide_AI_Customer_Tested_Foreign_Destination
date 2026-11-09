"""Opt-in REAL Gemini connectivity / grounded-chat smoke test.

Run ONLY after creating a fresh private key in backend/.env (never commit it):
  MASR_LIVE_AI_QA=1 python scripts/qa_gemini_live.py

This sends real data to Google and may incur provider usage. It is intentionally
excluded from automatic push CI and is not a comprehensive AI quality evaluation.
No credential, raw request headers, or raw provider errors are printed.
"""
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from dotenv import load_dotenv
load_dotenv(ROOT / 'backend' / '.env', override=False)


def main():
    if os.getenv('MASR_LIVE_AI_QA') != '1':
        raise SystemExit('SKIPPED: set MASR_LIVE_AI_QA=1 explicitly to authorize real Gemini API calls')
    if not os.getenv('GEMINI_API_KEY', '').strip():
        raise SystemExit('BLOCKED: configure a new private GEMINI_API_KEY in backend/.env (do not paste it in logs)')
    from app.gemini_client import generate
    from fastapi import HTTPException
    checks = [
        ('English', 'Answer with a short greeting about Egypt.', 'You are a helpful, factual Egyptian tourism assistant.'),
        ('Arabic', 'رحب بالسائح بالعربية في جملة قصيرة.', 'أجب باللغة العربية فقط. كن موجزا ومرحبا.'),
    ]
    for label, question, instructions in checks:
        start = time.monotonic()
        try:
            response = generate(question, instructions, max_tokens=160)
        except (HTTPException, ValueError) as error:
            print(f'FAIL {label}: provider unavailable or rejected request; status={getattr(error, "status_code", "config")}. No secrets printed.')
            raise SystemExit(1)
        if not response or not response.strip():
            raise SystemExit(f'FAIL {label}: empty provider content')
        if label == 'Arabic' and not any('\u0621' <= c <= '\u064a' for c in response):
            raise SystemExit('FAIL Arabic: no Arabic script in provider response')
        print(f'PASS {label}: live Gemini replied, length={len(response)} characters, latency={time.monotonic()-start:.1f}s')
    # Exercise actual Masr Guide AI request processing (retrieval + FastAPI +
    # Gemini). This is stronger than a raw provider ping but still not React E2E.
    import tempfile
    from fastapi.testclient import TestClient
    with tempfile.TemporaryDirectory(prefix='masr-live-gemini-') as folder:
        os.environ['DATABASE_PATH'] = str(Path(folder) / 'catalog.sqlite3')
        os.environ['MASR_USER_DB'] = str(Path(folder) / 'accounts.sqlite3')
        os.environ['APP_ENV'] = 'portfolio'
        from app.main import app
        with TestClient(app) as client:
            response = client.post('/api/chat', json={
                'message': 'Tell me one sourced fact about Karnak Temple in Luxor.',
                'language': 'English', 'history': []
            }, timeout=55)
            if response.status_code != 200:
                raise SystemExit(f'FAIL FastAPI -> RAG -> Gemini: HTTP {response.status_code} (no response body or credential printed)')
            data = response.json()
            if data.get('mode') != 'gemini-rag' or not data.get('answer') or not data.get('sources'):
                raise SystemExit('FAIL FastAPI -> RAG -> Gemini: mode, response or sources missing')
            print(f'PASS FastAPI -> RAG -> Live Gemini: sources={len(data["sources"])}; answer_length={len(data["answer"])}')
    print('PASS: Live AI connectivity + backend integration. React/browser interaction must be tested separately.')


if __name__ == '__main__':
    main()
