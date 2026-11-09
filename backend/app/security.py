"""Local abuse protection for credential and partner endpoints.

This is defense in depth, NOT a distributed/production edge limiter. With several
worker processes each process has its own counters; enforce quotas at the trusted
reverse proxy too. Peer addresses are not user-supplied forwarded headers.
"""
import os
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

_guard_lock = Lock()
_guard_hits = defaultdict(deque)
_MAX_KEYS = 4096


def _limit(name: str, default: int) -> int:
    try:
        return max(1, min(10000, int(os.getenv(name, str(default)))))
    except (ValueError, OverflowError):
        return default


def sensitive_requests(request) -> int:
    path, method = request.url.path, request.method
    if method == 'POST' and path == '/api/auth/login':
        bucket, limit = 'login', _limit('AUTH_LOGIN_RATE_PER_MINUTE', 15)
    elif method == 'POST' and path in ('/api/auth/google', '/api/auth/google/link'):
        bucket, limit = 'google-auth', _limit('AUTH_GOOGLE_RATE_PER_MINUTE', 12)
    elif method == 'POST' and path == '/api/auth/register':
        bucket, limit = 'register', _limit('AUTH_REGISTER_RATE_PER_MINUTE', 12)
    elif method == 'POST' and path == '/api/partners/apply':
        bucket, limit = 'partner', _limit('PARTNER_RATE_PER_MINUTE', 10)
    elif method == 'POST' and path.startswith('/api/ratings/'):
        bucket, limit = 'rating', _limit('RATING_RATE_PER_MINUTE', 6)
    elif path.startswith('/api/admin/'):
        bucket, limit = 'admin', _limit('ADMIN_RATE_PER_MINUTE', 60)
    else:
        return 0
    peer = request.client.host if request.client else 'unknown'
    key = (bucket, peer)
    now = monotonic()
    with _guard_lock:
        # Remove idle buckets to bound memory across a broad source-IP attack.
        if len(_guard_hits) >= _MAX_KEYS:
            for k in list(_guard_hits):
                events = _guard_hits[k]
                if not events or now - events[-1] >= 60:
                    del _guard_hits[k]
            # Fail closed rather than allocating unbounded memory when every
            # tracked IP has sent a recent request.
            if len(_guard_hits) >= _MAX_KEYS and key not in _guard_hits:
                return 60
        recent = _guard_hits[key]
        while recent and now - recent[0] >= 60:
            recent.popleft()
        if len(recent) >= limit:
            return max(1, int(61 - (now - recent[0])))
        recent.append(now)
    return 0
