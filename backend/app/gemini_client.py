"""Minimal dependency-free Gemini Developer API REST client.

No paid account, provider SDK, or outgoing request is necessary to run the demo.
The free API key is optional. Do not log keys, provider errors or prompt contents.
"""
import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit

from fastapi import HTTPException
from .conversation_router import redact_payment_data

logger = logging.getLogger(__name__)


def gemini_key():
    return os.getenv('GEMINI_API_KEY', '').strip()


def _require_complete_candidate(candidate: dict) -> None:
    """Reject truncated/blocked provider output instead of displaying partial advice.

    Legacy test fixtures sometimes omit finishReason; real Gemini responses
    include it. When the provider specifies a non-success finish reason, an
    incomplete response must not be presented as a finished recommendation.
    """
    reason = candidate.get('finishReason')
    if reason is not None and reason != 'STOP':
        raise ValueError(f'Gemini completion status: {reason}')


def generate(prompt: str, instructions: str, *, json_mode: bool = False, max_tokens: int = 1300, history=None) -> str:
    key = gemini_key()
    if not key:
        raise ValueError('GEMINI_API_KEY is not configured')
    # Restrict dynamic model names to alphanumeric model IDs: no arbitrary URL injection.
    model = os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite').strip()
    if not model or any(ch not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._' for ch in model):
        raise ValueError('Invalid GEMINI_MODEL')
    # The API receives genuine conversation roles, rather than a textual
    # transcript in one user turn. History is untrusted visitor data; only the
    # fixed system instruction defines the assistant's operating rules.
    contents = []
    for turn in (history or [])[-8:]:
        role = getattr(turn, 'role', None)
        content = getattr(turn, 'content', None)
        if role not in ('user', 'assistant') or not isinstance(content, str) or not content.strip():
            continue
        api_role = 'model' if role == 'assistant' else 'user'
        if not contents and api_role == 'model':
            # A restored chat may begin with an assistant greeting; Gemini
            # conversation history must start with an actual user message.
            continue
        text = redact_payment_data(content[:1500])
        if contents and contents[-1]['role'] == api_role:
            contents[-1]['parts'][0]['text'] += '\n' + text
        else:
            contents.append({'role': api_role, 'parts': [{'text': text}]})
    if contents and contents[-1]['role'] == 'user':
        # The new user question must be its own final turn.
        # Avoid relying on a disallowed user/user role boundary.
        contents[-1]['parts'][0]['text'] += '\n\n' + redact_payment_data(prompt[:16000])
    else:
        contents.append({'role': 'user', 'parts': [{'text': redact_payment_data(prompt[:16000])}]})
    payload = {
        'system_instruction': {'parts': [{'text': instructions[:6000]}]},
        'contents': contents,
        'generationConfig': {'temperature': 0.15 if json_mode else 0.35, 'maxOutputTokens': max_tokens},
    }
    # Never attach a generation setting based on a mutable *-latest alias.
    # Google can retarget aliases to models that reject thinkingBudget=0.
    # Explicitly pinned 2.5 Flash variants support zero budget. Older/newer
    # aliases and all other models use the provider's default settings.
    if model in {'gemini-2.5-flash', 'gemini-2.5-flash-lite'}:
        payload['generationConfig']['thinkingConfig'] = {'thinkingBudget': 0}
    if json_mode:
        payload['generationConfig']['responseMimeType'] = 'application/json'
    request = Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'x-goog-api-key': key},
        method='POST',
    )
    try:
        with urlopen(request, timeout=26) as resp:
            data = json.load(resp)
        candidate = (data.get('candidates') or [{}])[0]
        _require_complete_candidate(candidate)
        parts = candidate.get('content', {}).get('parts', [])
        text = ''.join(p.get('text', '') for p in parts).strip()
        if not text:
            raise ValueError('Empty provider response')
        return text
    except (HTTPError, URLError, OSError, ValueError, KeyError, IndexError) as exc:
        # Never disclose API key or provider response body to the browser.
        logger.warning('Gemini generation failed: model=%s type=%s status=%s completion=%s',
                       model, type(exc).__name__, getattr(exc, 'code', None),
                       str(exc) if isinstance(exc, ValueError) else None)
        raise HTTPException(502, 'Gemini is currently unavailable. Check your API key, free-tier quota and connectivity.') from exc


# Google Search is an explicitly configured *answering* tool, never an action
# tool. Keep stateful trip changes and account writes in deterministic FastAPI.
def search_grounding_enabled() -> bool:
    return os.getenv('GEMINI_SEARCH_GROUNDING', 'false').strip().lower() in ('1', 'true', 'yes', 'on')


def generate_grounded(prompt: str, instructions: str, *, max_tokens: int = 1200, history=None) -> dict:
    """Call the configured Gemini model with Google Search and expose source provenance.

    ``grounded`` is true only when the provider returns usable web citations.
    Merely requesting the tool is *not* proof that Google Search ran.
    REST is used to preserve the project's dependency-light Gemini client.
    """
    key = gemini_key()
    if not key:
        raise ValueError('GEMINI_API_KEY is not configured')
    model = os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite').strip()
    if not model or any(ch not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._' for ch in model):
        raise ValueError('Invalid GEMINI_MODEL')
    # Reuse the same role-preserving conversation rules as generate().
    contents = []
    for turn in (history or [])[-8:]:
        role, content = getattr(turn, 'role', None), getattr(turn, 'content', None)
        if role not in ('user', 'assistant') or not isinstance(content, str) or not content.strip():
            continue
        api_role = 'model' if role == 'assistant' else 'user'
        if not contents and api_role == 'model':
            continue
        if contents and contents[-1]['role'] == api_role:
            contents[-1]['parts'][0]['text'] += '\n' + redact_payment_data(content[:1500])
        else:
            contents.append({'role': api_role, 'parts': [{'text': redact_payment_data(content[:1500])}]})
    if contents and contents[-1]['role'] == 'user':
        contents[-1]['parts'][0]['text'] += '\n\n' + redact_payment_data(prompt[:16000])
    else:
        contents.append({'role': 'user', 'parts': [{'text': redact_payment_data(prompt[:16000])}]})
    payload = {
        'system_instruction': {'parts': [{'text': instructions[:6000]}]},
        'contents': contents,
        'generationConfig': {'temperature': 0.25, 'maxOutputTokens': max_tokens},
        'tools': [{'google_search': {}}],
    }
    if model in ('gemini-2.5-flash', 'gemini-2.5-flash-lite'):
        payload['generationConfig']['thinkingConfig'] = {'thinkingBudget': 0}
    request = Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'x-goog-api-key': key},
        method='POST',
    )
    try:
        with urlopen(request, timeout=30) as resp:
            data = json.load(resp)
        candidate = (data.get('candidates') or [{}])[0]
        _require_complete_candidate(candidate)
        parts = (candidate.get('content') or {}).get('parts') or []
        answer = ''.join(p.get('text', '') for p in parts if isinstance(p, dict)).strip()
        if not answer:
            raise ValueError('Empty Gemini response')
        metadata = candidate.get('groundingMetadata') or {}
        sources, seen = [], set()
        for chunk in (metadata.get('groundingChunks') or []):
            web = chunk.get('web', {}) if isinstance(chunk, dict) else {}
            uri = str(web.get('uri', '')).strip()
            parsed = urlsplit(uri)
            if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or uri in seen:
                continue
            seen.add(uri)
            sources.append({'number': len(sources) + 1, 'title': str(web.get('title') or parsed.netloc)[:180],
                            'url': uri, 'type': 'google_search'})
            if len(sources) >= 8:
                break
        queries = [str(q)[:200] for q in (metadata.get('webSearchQueries') or []) if isinstance(q, str)][:8]
        entry_point = (metadata.get('searchEntryPoint') or {}).get('renderedContent', '')
        return {
            'answer': answer,
            'sources': sources,
            'grounding': {
                'requested': True,
                'search_performed': bool(queries or sources),
                'grounded': bool(sources),
                'queries': queries,
                # Search suggestions are provider-supplied HTML. Public clients
                # must render as Google requires, in a safe isolated component.
                'search_suggestions_html': entry_point if isinstance(entry_point, str) else '',
            }
        }
    except (HTTPError, URLError, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise HTTPException(502, 'Gemini Search is unavailable. Check API access, rate limits and network.') from exc
