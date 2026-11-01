"""Regression tests for v1.7 hardening: atomic catalogue rebuild, thread-safe index, trusted-proxy limiter."""
import threading


def test_rebuild_is_atomic_for_concurrent_readers(client):
    """Readers must never observe a missing/empty places table while initialize() rebuilds it."""
    from app.database import all_places, initialize
    from app.catalog import PLACES
    errors, stop = [], threading.Event()

    def reader():
        while not stop.is_set():
            try:
                if len(all_places()) != len(PLACES):
                    errors.append("partial table")
            except Exception as exc:  # noqa: BLE001 - any failure is a test failure
                errors.append(repr(exc))

    threads = [threading.Thread(target=reader) for _ in range(4)]
    for t in threads:
        t.start()
    try:
        for _ in range(40):
            initialize()
    finally:
        stop.set()
        for t in threads:
            t.join()
    assert not errors, errors[:3]


def test_retrieval_index_is_thread_safe(client):
    from app.guide import _get_index, _index_cache, retrieve
    _index_cache.clear()
    results, errors = [], []

    def work():
        try:
            results.append(tuple(p["id"] for p in retrieve("Karnak temple in Luxor")))
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))

    threads = [threading.Thread(target=work) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors and len(set(results)) == 1
    assert _get_index() is _get_index()  # built once, then served from cache


def test_limiter_uses_real_client_ip_only_when_proxy_is_trusted(client, monkeypatch):
    from app import main
    monkeypatch.setenv("CHAT_RATE_LIMIT_PER_MINUTE", "2")
    body = {"message": "Tell me about Karnak", "language": "English", "history": []}

    # Default: headers are ignored, so every request shares the direct peer's budget.
    main._chat_calls.clear()
    codes = [client.post("/api/chat", json=body, headers={"X-Real-IP": f"10.0.0.{i}"}).status_code for i in range(3)]
    assert codes == [200, 200, 429]

    # Behind a trusted proxy each real client gets its own budget.
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
    main._chat_calls.clear()
    codes = [client.post("/api/chat", json=body, headers={"X-Real-IP": ip}).status_code
             for ip in ("10.0.0.1", "10.0.0.2", "10.0.0.1", "10.0.0.1")]
    assert codes == [200, 200, 200, 429]
    main._chat_calls.clear()


def test_places_have_arabic_tips(client):
    for p in client.get("/api/places").json()["places"]:
        assert p["tip_ar"].strip(), p["id"]
