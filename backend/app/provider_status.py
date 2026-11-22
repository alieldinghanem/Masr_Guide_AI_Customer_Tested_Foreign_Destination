"""Recent observed connectivity, scoped to this process and current configuration."""
from datetime import datetime, timezone
from hashlib import sha256
import os
from threading import Lock
from time import monotonic

_lock = Lock()
_observations = {}


def _identity(model):
    return sha256((os.getenv('GEMINI_API_KEY', '') + '\0' + model).encode()).hexdigest()


def observe(model, success):
    with _lock:
        if len(_observations) > 20:
            _observations.clear()
        _observations[_identity(model)] = (monotonic(), bool(success), datetime.now(timezone.utc).isoformat())


def snapshot():
    provider = os.getenv('AI_PROVIDER', 'auto').strip().lower()
    if provider not in ('auto', 'gemini'):
        return {'state': 'disabled', 'scope': 'this_process'}
    if not os.getenv('GEMINI_API_KEY', '').strip():
        return {'state': 'not_configured', 'scope': 'this_process'}
    model = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite').strip()
    with _lock:
        observation = _observations.get(_identity(model))
    if not observation:
        return {'state': 'unverified', 'scope': 'this_process'}
    when, success, checked_at = observation
    return {'state': ('verified' if success else 'unavailable') if monotonic() - when < 900 else 'stale',
            'checked_at': checked_at, 'scope': 'this_process'}
