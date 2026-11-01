"""Opt-in LIVE Gemini Search smoke test. No mock, runs only with a local key.

Run from repo root:
    cd backend && python scripts/smoke_gemini_grounding.py
Exit codes: 0=verified source evidence, 2=blocked configuration, 1=provider failure.
Never prints the key, untrusted tool HTML, or entire user conversations.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.gemini_client import gemini_key, generate_grounded, search_grounding_enabled  # noqa: E402


def main():
    if not gemini_key() or not search_grounding_enabled():
        print('BLOCKED: Configure GEMINI_API_KEY and GEMINI_SEARCH_GROUNDING=true in backend/.env')
        return 2
    try:
        # Public data only. The response must contain actual provider web sources.
        result = generate_grounded(
            'What is the official website of the Egyptian Ministry of Tourism and Antiquities? ' 
            'Use Google Search and cite a source URL.',
            'You are a travel assistant for Egypt. Answer in English with attributed web evidence.',
            max_tokens=400,
        )
    except Exception as exc:
        print('FAILED: provider request unsuccessful (credentials, quota, permissions or connectivity).')
        return 1
    grounding = result['grounding']
    if not grounding['grounded']:
        print('NOT VERIFIED: Gemini answered, but returned no usable web citations.')
        return 1
    print('PASS: Gemini returned grounded citations.')
    print('Source count:', len(result['sources']))
    print('Cited domains:', ', '.join(sorted({__import__('urllib.parse', fromlist=['urlsplit']).urlsplit(s['url']).netloc for s in result['sources']})))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
