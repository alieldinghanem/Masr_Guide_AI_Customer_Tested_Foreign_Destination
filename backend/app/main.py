from collections import defaultdict, deque
from contextlib import asynccontextmanager, closing
from threading import Lock
from time import monotonic
import os
import re
from pathlib import Path
import sqlite3
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from .security import sensitive_requests
from .http_limits import LimitApiBody
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import Response
from .catalog import INTERESTS
from .catalog_extra import CITY_AR, INTEREST_AR
from .database import all_places, get_place, initialize, connect
from .discovery import get_destinations, get_experiences, ESSENTIALS
from .guide import answer_chat
from .gemini_client import gemini_key, search_grounding_enabled
from .openai_client import openai_key
from .travel_agent import consult_travel, _make_plan
from .planner import build_plan
from .schemas import ChatRequest, PlanRequest, ConsultRequest, TripState
from .accounts import router as account_router, setup as setup_accounts
from . import accounts
from .commerce import router as commerce_router, setup as setup_commerce

# Read the backend-local .env for local development; environment variables take priority.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

def validate_deployment_settings():
    """Fail closed on common public-company deployment misconfigurations.

    This validates operator declarations, NOT actual disk durability, backup
    recovery, provider credentials or compliance. Those need independent tests.
    Portfolio/local modes intentionally remain usable without live AI.
    """
    if os.getenv('APP_ENV', '').lower() != 'production':
        return

    accepted = ('1', 'yes', 'true')
    if os.getenv('MASR_DURABLE_STORAGE_CONFIRMED', '').lower() not in accepted:
        raise RuntimeError('Production requires confirmed persistent database storage and backups')
    if os.getenv('BACKUP_RECOVERY_VERIFIED', '').lower() not in accepted:
        raise RuntimeError('Production requires a successfully tested backup and recovery procedure')

    # Require explicit separate absolute paths; otherwise the service can
    # silently place customer data inside a disposable image filesystem.
    db_paths = []
    for key in ('MASR_USER_DB', 'DATABASE_PATH'):
        value = os.getenv(key, '').strip()
        if not value or not Path(value).is_absolute():
            raise RuntimeError(f'Production requires an explicit absolute {key} path on verified durable storage')
        path = Path(value).resolve()
        source_root = Path(__file__).resolve().parents[1]
        if path == source_root or source_root in path.parents:
            raise RuntimeError(f'Production {key} cannot be stored inside the backend source tree')
        db_paths.append(path)
    if db_paths[0] == db_paths[1]:
        raise RuntimeError('Production account and tourism databases must use separate files')

    provider = os.getenv('AI_PROVIDER', 'auto').strip().lower()
    if provider not in ('auto', 'openai', 'gemini'):
        raise RuntimeError('Production AI_PROVIDER must be auto, openai, or gemini')
    if not ((provider in ('auto', 'gemini') and gemini_key()) or
            (provider in ('auto', 'openai') and openai_key())):
        raise RuntimeError('Production AI companion needs a selected provider key')
    if os.getenv('TRUST_PROXY_HEADERS', '').lower() in accepted and not os.getenv('TRUSTED_PROXY_IPS', '').strip():
        raise RuntimeError('Production trusted-proxy mode requires explicit TRUSTED_PROXY_IPS')


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_deployment_settings()
    initialize()
    setup_accounts()
    setup_commerce()
    yield

app = FastAPI(title="Masr Guide AI", version="7.8.1", lifespan=lifespan,
              description="A curated Egypt travel guide with optional LLM-grounded RAG chat.")
origins = [v.strip() for v in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if v.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "PUT", "DELETE"],
                   allow_headers=["Content-Type", "Authorization"], allow_credentials=False)
app.include_router(account_router)
app.include_router(commerce_router)
# Outer ASGI guard measures actual received bytes, not only the advertised length.
app.add_middleware(LimitApiBody)


@app.middleware('http')
async def protect_sensitive_endpoints(request: Request, call_next):
    """Small single-process defense-in-depth limiter for credential and partner endpoints.

    Always keys on the socket peer; the trusted edge proxy MUST enforce the real
    client IP itself. No X-Forwarded-* or X-Real-IP header is trusted here.
    """
    if request.url.path.startswith('/api/'):
        length = request.headers.get('content-length', '')
        if length.isdecimal() and int(length) > 524288:
            return JSONResponse(status_code=413,
                                content={'detail': 'Request body exceeds the 512 KB API limit'},
                                headers={'Cache-Control': 'no-store'})
    denied = sensitive_requests(request)
    if denied:
        return JSONResponse(status_code=429,
                            content={'detail': 'Too many requests. Please try again later.'},
                            headers={'Retry-After': str(denied), 'Cache-Control': 'no-store'})
    response = await call_next(request)
    if request.url.path.startswith(('/api/auth/', '/api/my/', '/api/admin/')):
        response.headers['Cache-Control'] = 'no-store'
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    return response

# Demo-level safety valve against accidentally exhausting a paid API key.
# Uses the direct peer address, NOT the spoofable X-Forwarded-For request header.
# A public deployment still needs a trusted reverse-proxy / edge rate limiter,
# per-user quotas, provider spending limits and monitoring.
_chat_calls = defaultdict(deque)
_chat_lock = Lock()

def client_key(request: Request) -> str:
    """Rate-limit key. Behind a TRUSTED reverse proxy (TRUST_PROXY_HEADERS=1) use the real client
    address the proxy puts in X-Real-IP; otherwise ignore client-supplied headers (spoofable)."""
    if os.getenv("TRUST_PROXY_HEADERS", "").strip().lower() in {"1", "true", "yes"}:
        # In production require an explicit trusted socket peer allowlist to
        # defeat direct-client header spoofing. Legacy development configuration
        # is retained for existing local QA; do NOT deploy it publicly.
        if os.getenv('APP_ENV', '').lower() == 'production':
            allowed = {h.strip() for h in os.getenv('TRUSTED_PROXY_IPS', '').split(',') if h.strip()}
            if not request.client or request.client.host not in allowed:
                return request.client.host if request.client else 'unknown'
        real = request.headers.get("x-real-ip", "").strip()
        if real:
            return real[:64]
    return request.client.host if request.client else "unknown"


def check_chat_limit(peer: str) -> None:
    try:
        limit = max(1, int(os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "20")))
    except ValueError:
        limit = 20
    now = monotonic()
    with _chat_lock:
        # Bound memory even under rapid requests from many distinct peers.
        # Previously the map could grow without limit while all peers were active.
        if len(_chat_calls) >= 4096 and peer not in _chat_calls:
            for key in [k for k, v in _chat_calls.items() if not v or now - v[-1] >= 60]:
                del _chat_calls[key]
            if len(_chat_calls) >= 4096:
                raise HTTPException(status_code=429, detail="Guide is temporarily busy. Please try again later.")
        recent = _chat_calls[peer]
        while recent and now - recent[0] >= 60:
            recent.popleft()
        if len(recent) >= limit:
            raise HTTPException(status_code=429, detail="Too many guide requests. Please try again in a minute.")
        recent.append(now)
        # Prune expired source buckets after a burst as well as before reaching
        # the hard cap, preserving existing release behavior.
        if len(_chat_calls) > 1000:
            for key in [k for k, v in _chat_calls.items() if not v or now - v[-1] >= 60]:
                del _chat_calls[key]

@app.get("/api/health")
def health():
    provider = os.getenv('AI_PROVIDER', 'auto').strip().lower()
    if provider == 'openai':
        mode = 'openai-configured' if openai_key() else 'offline-preview'
    elif provider == 'gemini':
        mode = 'gemini-configured' if gemini_key() else 'offline-preview'
    elif provider == 'offline':
        mode = 'offline-preview'
    else:
        mode = 'gemini-configured' if gemini_key() else ('llm-configured' if openai_key() else 'offline-preview')
    return {"status":"ok", "version":"7.8.1", "guide_mode": mode,
            "gemini_search_configured": bool(search_grounding_enabled() and gemini_key()
                                             and provider in ('gemini', 'auto')),
            "registration_enabled": accounts.registration_enabled()}

@app.get('/api/ready')
def ready():
    """Database-backed readiness probe; distinct from process-only liveness."""
    try:
        with accounts._open() as c:
            c.execute('SELECT 1 FROM account_users LIMIT 1').fetchone()
            c.execute('SELECT 1 FROM editorial_articles LIMIT 1').fetchone()
        with closing(connect()) as c:
            c.execute('SELECT 1 FROM places LIMIT 1').fetchone()
    except (OSError, ValueError, sqlite3.Error) as exc:
        raise HTTPException(503, detail='Storage is not ready') from exc
    return {'status': 'ready'}


@app.get("/api/cities")
def cities():
    return {"cities": sorted({p["city"] for p in all_places()}), "interests": INTERESTS,
            "city_names_ar": CITY_AR, "interest_names_ar": INTEREST_AR}

@app.get("/api/discover/destinations")
def discover_destinations():
    return {"destinations": get_destinations()}

@app.get("/api/discover/experiences")
def discover_experiences():
    return {"experiences": get_experiences()}

@app.get("/api/discover/essentials")
def discover_essentials():
    return {"essentials": ESSENTIALS}

@app.get("/api/places")
def places(city: str | None = None, interest: str | None = None,
           q: str | None = Query(default=None, max_length=120)):
    return {"places": all_places(city=city, interest=interest, q=q)}

@app.get("/api/places/{slug}")
def detail(slug: str):
    item = get_place(slug)
    if item is None: raise HTTPException(404, detail="Place not found")
    return item

@app.post("/api/plan")
def plan(body: PlanRequest):
    try: return build_plan(body)
    except ValueError as exc: raise HTTPException(422, detail=str(exc)) from exc

@app.post("/api/chat")
def chat(body: ChatRequest, request: Request):
    check_chat_limit(client_key(request))
    return answer_chat(body)

def _is_trip_save_command(message: str) -> bool:
    """Explicit, narrow save action. Ordinary travel questions never cause writes."""
    return bool(re.match(
        r'^\s*(?:(?:ممكن|لو سمحت|من فضلك|please|can you)\s+)?'
        r'(?:احفظ(?:لي)?|تحفظ|سجل|خزن|save|store)\s+'
        r'(?:الرحلة|رحلتي|البرنامج|الخطة|itinerary|the trip|my trip|trip|this trip|plan)\b',
        message.strip(), flags=re.I
    ))


@app.post("/api/consult")
def consult(body: ConsultRequest, request: Request):
    """Conversational trip actions. Server writes only after explicit user intent
    and authenticated ownership; never delegates database writes to the LLM.
    """
    check_chat_limit(client_key(request))
    if _is_trip_save_command(body.message):
        language = 'Arabic' if re.search(r'[\u0600-\u06ff]{3,}', body.message) else body.language
        state = body.trip_state
        if state is None:
            return {'answer': ('جهز الرحلة الأول، وبعدها اطلب حفظها في حسابك.' if language == 'Arabic' else
                               'Create your itinerary first, then ask me to save it to your account.'),
                    'mode': 'needs-clarification', 'sources': [], 'trip_state': None, 'itinerary': None}
        if not request.headers.get('authorization'):
            return {'answer': ('سجّل الدخول من صفحة حسابي، وبعدها اطلب حفظ الرحلة. لم يتم حفظ أي بيانات.'
                               if language == 'Arabic' else
                               'Sign in from My Account, then ask me to save this trip. Nothing has been saved.'),
                    'mode': 'needs-authentication', 'sources': [], 'trip_state': state.model_dump(), 'itinerary': None}
        if not accounts.registration_enabled():
            raise HTTPException(503, detail='Persistent account storage is unavailable in this preview')
        # current_user checks the actual bearer token and resolves the account ID;
        # a supplied body or history can never choose another user's account.
        user = accounts.current_user(request.headers.get('authorization'))
        itinerary = _make_plan(state.model_dump(), 'ar' if language == 'Arabic' else 'en')
        accounts._check_phase_allocation(state, itinerary)
        title = (f'رحلتي في مصر - {state.days} يوم' if language == 'Arabic'
                 else f'My Egypt trip - {state.days} days')
        saved = accounts.save_trip(accounts.TripSave(title=title, itinerary=itinerary), user=user)
        return {'answer': (f'تم حفظ رحلتك المكوّنة من {state.days} يوم في حسابك بالفعل. تقدر تلاقيها في صفحة حسابي.'
                           if language == 'Arabic' else
                           f'Your {state.days}-day itinerary was saved to your account. You can find it in My Account.'),
                'mode': 'trip-saved', 'sources': [], 'trip_state': state.model_dump(),
                'itinerary': itinerary, 'saved_trip_id': saved['id']}
    return consult_travel(body)

@app.get("/demo", include_in_schema=False)
@app.get("/demo/", include_in_schema=False)
def quick_demo():
    """Dependency-free visitor demo; React/Vite app remains the primary frontend."""
    return FileResponse(Path(__file__).resolve().parents[1] / "quick_demo" / "index.html")


# Production single-origin deployment: one Render/Docker service serves both
# the compiled React app and the API. In development, Vite still proxies /api.
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
if (_FRONTEND_DIST / 'index.html').is_file():
    app.mount('/assets', StaticFiles(directory=_FRONTEND_DIST / 'assets'), name='site-assets')

    @app.get('/', include_in_schema=False)
    @app.get('/{path:path}', include_in_schema=False)
    def react_site(path: str = ''):
        if path.startswith('api/') or path == 'api':
            raise HTTPException(404, 'API route not found')
        # Only known compiled assets are exposed through /assets.
        return FileResponse(_FRONTEND_DIST / 'index.html')
