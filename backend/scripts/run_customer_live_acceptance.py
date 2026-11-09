"""Live, public-data-only customer smoke test against a running FastAPI server.

This script tests the REAL /api/chat -> Gemini + Google Search path. It does not
know/read/print secrets, does not write accounts or books anything, and will
fail closed if the endpoint is offline or lacks sourced Google Search responses.

Usage:
  python backend/scripts/run_customer_live_acceptance.py --base-url http://127.0.0.1:8000
Exit: 0=all source-backed calls passed (NOT a general quality certification),
      1=one or more failures, 2=blocked/not configured.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

PUBLIC_SCENARIOS = [
    ('Arabic: venue details', 'Arabic', 'ما الموقع الرسمي لزيارة معبد الكرنك في الأقصر؟ ابحث عن أحدث تفاصيل الزيارة واستشهد بمصدر.'),
    ('English: museum details', 'English', 'Find the official visitor information for the Grand Egyptian Museum in Giza. Use current web sources and cite them.'),
    ('Arabic: restaurant discovery', 'Arabic', 'رشحلي مطاعم مناسبة لعائلة في الزمالك بالقاهرة، واذكر المصادر الحالية التي بنيت عليها الترشيحات دون تأكيد التوافر أو السعر.'),
]


def get_json(base, route, body=None, timeout=45):
    url = base.rstrip('/') + route
    payload = json.dumps(body, ensure_ascii=False).encode('utf-8') if body is not None else None
    req = Request(url, data=payload, headers={'Content-Type': 'application/json'} if body else {},
                  method='POST' if body is not None else 'GET')
    with urlopen(req, timeout=timeout) as response:
        return json.load(response)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--report', default='qa_reports/live_customer_acceptance.json')
    args = parser.parse_args(argv)
    parsed = urlparse(args.base_url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password:
        print('BLOCKED: invalid base URL')
        return 2
    try:
        health = get_json(args.base_url, '/api/health', timeout=8)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        print('BLOCKED: backend is not accessible; start FastAPI first')
        return 2
    if not health.get('gemini_search_configured') or health.get('guide_mode') != 'gemini-configured':
        print('BLOCKED: select AI_PROVIDER=gemini with GEMINI_API_KEY and GEMINI_SEARCH_GROUNDING=true on the server')
        return 2
    report = {'time_utc': datetime.now(timezone.utc).isoformat(), 'provider': 'gemini',
              'type': 'live HTTP customer smoke, public questions only', 'scenarios': []}
    failed = False
    for label, language, message in PUBLIC_SCENARIOS:
        item = {'scenario': label, 'language': language, 'status': 'FAIL', 'sources': [], 'mode': None}
        try:
            result = get_json(args.base_url, '/api/chat', {'language': language, 'message': message})
            item['mode'] = result.get('mode')
            cited = [s for s in result.get('sources', []) if s.get('type') == 'google_search'
                     and urlparse(s.get('url', '')).scheme == 'https']
            item['sources'] = [{'title': str(s.get('title', ''))[:120], 'url': s['url']} for s in cited]
            # Public test questions only. Save the actual answer so the team
            # can inspect relevance/accuracy rather than trusting status codes.
            item['answer'] = str(result.get('answer', ''))[:3000]
            item['status'] = ('PASS_SOURCE_BACKED' if result.get('mode') == 'gemini-search-grounded'
                              and cited and result.get('grounding', {}).get('search_performed') else 'FAIL')
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            item['error_kind'] = type(exc).__name__
        failed |= item['status'] != 'PASS_SOURCE_BACKED'
        report['scenarios'].append(item)
        print(f"{label}: {item['status']} ({item['mode'] or 'no response'}) sources={len(item['sources'])}")
    report['technical_result'] = 'FAIL' if failed else 'PASS_SOURCE_BACKED_ONLY'
    report['quality_review'] = 'MANUAL_REVIEW_REQUIRED'
    report['note'] = 'Citations alone do not prove that each factual claim is correct; review the saved responses.'
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Report saved:', path)
    print('Result:', report['technical_result'], '| Manual factual review still required')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
