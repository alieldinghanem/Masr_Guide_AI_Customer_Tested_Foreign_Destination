"""Opt-in LIVE Gemini conversational acceptance checks for local use.

This requires a locally configured GEMINI_API_KEY. It calls Google (quota may
be consumed), checks real API responses, and never stores credentials or raw
chat text in the report. All databases are isolated in a temporary directory.

This is not a substitute for a React browser test or a production readiness test.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from dotenv import load_dotenv
load_dotenv(ROOT / 'backend' / '.env', override=False)


def main() -> int:
    if not os.getenv('GEMINI_API_KEY', '').strip():
        print('[BLOCKED] Configure GEMINI_API_KEY locally in backend/.env; do not paste the key in chat.')
        return 2

    from fastapi.testclient import TestClient
    from app.main import app

    results = []

    def record(case: str, response, *, expected: str | tuple[str, ...], predicate=None) -> dict:
        try:
            data = response.json()
            mode = data.get('mode', '')
            sources = data.get('sources') or []
            allowed = (expected,) if isinstance(expected, str) else expected
            passed = (response.status_code == 200 and mode in allowed
                      and bool((data.get('answer') or '').strip())
                      and (predicate(data) if predicate else True))
            result = {'case': case, 'status': 'PASS' if passed else 'FAIL',
                      'http_status': response.status_code, 'mode': mode,
                      'sources': len(sources)}
        except (ValueError, KeyError, TypeError):
            data = {}
            result = {'case': case, 'status': 'FAIL', 'error': 'Malformed response'}
        results.append(result)
        print(f"[{result['status']}] {case} ({result.get('mode', 'invalid response')})")
        return data

    # A real request, not a monkeypatched generate() or a pretend provider.
    with tempfile.TemporaryDirectory(prefix='masr-gemini-qa-') as directory:
        os.environ['DATABASE_PATH'] = str(Path(directory) / 'tourism.sqlite3')
        os.environ['MASR_USER_DB'] = str(Path(directory) / 'accounts.sqlite3')
        os.environ['APP_ENV'] = 'portfolio'
        with TestClient(app) as client:
            try:
                first_question = 'رشح لي فندق في القاهرة قريب من الأهرامات'
                first = record('hotel initial', client.post('/api/consult', json={
                    'message': first_question, 'language': 'Arabic', 'history': []}, timeout=65),
                    expected='hotel-gemini-assisted', predicate=lambda d: bool(d.get('sources')))
                history = [
                    {'role': 'user', 'content': first_question},
                    {'role': 'assistant', 'content': first.get('answer', '')[:1500]},
                ]
                record('hotel budget follow-up', client.post('/api/consult', json={
                    'message': 'ميزانيتي 100 دولار في الليلة، ومحتاج غرفة للعيلة',
                    'language': 'Arabic', 'history': history}, timeout=65),
                    expected='hotel-gemini-assisted', predicate=lambda d: bool(d.get('sources')))

                record('historic fact with source', client.post('/api/consult', json={
                    'message': 'Tell me about Karnak Temple in Luxor.',
                    'language': 'English', 'history': []}, timeout=65),
                    expected='gemini-rag', predicate=lambda d: bool(d.get('sources')))

                planned = record('create 20-day itinerary', client.post('/api/consult', json={
                    'message': 'خطط رحلة 20 يوم، 13 يوم القاهرة و7 أيام الغردقة',
                    'language': 'Arabic', 'history': []}, timeout=65),
                    expected='gemini-intent+local-planner', predicate=lambda d:
                    d.get('trip_state', {}).get('days') == 20 and
                    d.get('itinerary', {}).get('day_allocation') == {'Cairo': 13, 'Hurghada': 7})
                if planned.get('trip_state'):
                    record('change destination without changing day count',
                           client.post('/api/consult', json={
                               'message': 'بدل الغردقة بشرم الشيخ', 'language': 'Arabic',
                               'trip_state': planned['trip_state']}, timeout=65),
                           expected='gemini-intent+local-planner', predicate=lambda d:
                           d.get('trip_state', {}).get('days') == 20 and
                           d.get('itinerary', {}).get('day_allocation') == {'Cairo': 13, 'Sharm El Sheikh': 7})
                else:
                    results.append({'case': 'change destination without changing day count',
                                    'status': 'BLOCKED', 'reason': 'Initial trip failed'})
            except Exception:
                # Do not include provider error response, headers, or credentials.
                results.append({'case': 'conversation interrupted', 'status': 'FAIL',
                                'error': 'Provider/HTTP call failed; check logs privately and verify quota.'})

    report = ROOT / 'qa_reports' / 'gemini_live_dialogue_results.json'
    report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Redacted report:', report)
    return 0 if results and all(r['status'] == 'PASS' for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
