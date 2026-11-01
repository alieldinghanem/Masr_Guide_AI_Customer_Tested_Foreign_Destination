"""OpenAI Responses API adapter for the Masr Guide AI server.

No client-side secret; all calls originate in FastAPI. The model may propose
text or a JSON intent; database writes remain deterministic and authenticated.
"""
import os
import re

from fastapi import HTTPException
from .conversation_router import redact_payment_data


def openai_key() -> str:
    return os.getenv('OPENAI_API_KEY', '').strip()


def generate(prompt: str, instructions: str, *, json_mode: bool = False,
             max_tokens: int = 1300, history=None) -> str:
    key = openai_key()
    if not key:
        raise ValueError('OPENAI_API_KEY is not configured')
    model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini').strip()
    if not model or not re.fullmatch(r'[A-Za-z0-9._-]{1,100}', model):
        raise ValueError('Invalid OPENAI_MODEL')

    turns = []
    for turn in (history or [])[-8:]:
        role = getattr(turn, 'role', None)
        content = getattr(turn, 'content', None)
        if role in ('user', 'assistant') and isinstance(content, str) and content.strip():
            turns.append({'role': role, 'content': redact_payment_data(content[:1500])})
    # The current message is always an explicit new user turn.
    turns.append({'role': 'user', 'content': redact_payment_data(prompt[:16000])})

    try:
        from openai import OpenAI
        with OpenAI(api_key=key, timeout=26.0, max_retries=1) as client:
            request = {
                'model': model,
                'instructions': instructions[:6000],
                'input': turns,
                'max_output_tokens': max_tokens,
                # Travel conversations are user data; do not store API responses by default.
                'store': False,
            }
            if json_mode:
                request['text'] = {'format': {'type': 'json_object'}}
            response = client.responses.create(**request)
        # The Responses API can return a non-empty partial output when it
        # exhausts max_output_tokens or is interrupted. Never tell a traveller
        # that a truncated itinerary or travel warning is a complete answer.
        status = getattr(response, 'status', None)
        if status is not None and status != 'completed':
            raise ValueError('OpenAI response did not complete')
        if getattr(response, 'incomplete_details', None) is not None:
            raise ValueError('OpenAI response is incomplete')
        output = (response.output_text or '').strip()
        if not output:
            raise ValueError('Empty provider response')
        return output
    except Exception as exc:
        # Never send provider errors, request contents, or credentials to a traveler.
        raise HTTPException(502, 'OpenAI is temporarily unavailable. Check the server API key, quota and connectivity.') from exc
