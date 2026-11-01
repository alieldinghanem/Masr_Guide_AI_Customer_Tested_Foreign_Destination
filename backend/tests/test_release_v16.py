"""Regression tests for v1.6 fixes: planner warnings, DB handle cleanup, rate-limit pruning."""
def test_underfilled_plan_returns_warning(client):
    r = client.post("/api/plan", json={"cities": ["Giza"], "days": 14, "interests": ["history"]})
    assert r.status_code == 200
    body = r.json()
    assert body["warnings"] and "14" in body["warnings"][0]


def test_full_plan_has_no_warning(client):
    r = client.post("/api/plan", json={"cities": ["Cairo", "Luxor"], "days": 3, "interests": ["history"]})
    assert r.status_code == 200
    assert r.json()["warnings"] == []


def test_database_connections_are_closed(client, monkeypatch):
    import sqlite3
    from app import database
    opened, closed = [], []
    real_connect = sqlite3.connect

    class Tracked(sqlite3.Connection):
        def close(self):
            closed.append(self)
            super().close()

    def tracking_connect(*args, **kwargs):
        conn = real_connect(*args, factory=Tracked, **kwargs)
        opened.append(conn)
        return conn

    monkeypatch.setattr(database.sqlite3, "connect", tracking_connect)
    database.all_places()
    database.get_place("karnak")
    database.initialize()
    assert opened and len(opened) == len(closed)


def test_rate_limit_table_is_pruned(monkeypatch):
    from app import main
    main._chat_calls.clear()
    t = [1000.0]
    monkeypatch.setattr(main, "monotonic", lambda: t[0])
    for i in range(1100):
        main.check_chat_limit(f"peer-{i}")
    t[0] += 120  # all windows expire
    main.check_chat_limit("fresh-peer")
    assert len(main._chat_calls) < 100
    main._chat_calls.clear()


def test_plan_includes_intercity_travel(client):
    body = client.post("/api/plan", json={"cities": ["Cairo", "Luxor"], "days": 3}).json()
    first_luxor = next(d for d in body["days"] if d["city"] == "Luxor")
    assert first_luxor["travel"]["from_city"] == "Cairo"
    assert 0 < first_luxor["estimated_travel_minutes"] <= 360
    assert body["total_travel_minutes"] == first_luxor["estimated_travel_minutes"]
    assert body["days"][0]["travel"] is None
    # Travel time is deducted from the day's sightseeing budget.
    for d in body["days"]:
        assert d["estimated_activity_minutes"] + d["estimated_travel_minutes"] <= 360 + 30


def test_travel_day_note_when_no_time_left(client):
    body = client.post("/api/plan", json={"cities": ["Cairo", "Siwa"], "days": 2, "pace": "relaxed"}).json()
    siwa = body["days"][1]
    assert siwa["travel"]["mode"] == "road"          # no airport assumed for Siwa
    assert not siwa["stops"] and "travel day" in siwa["note"].lower()
    assert any("Siwa" in w for w in body["warnings"])  # long-transfer warning


def test_route_optimisation_reduces_travel(client):
    cities = ["Cairo", "Abu Simbel", "Aswan", "Luxor"]
    plain = client.post("/api/plan", json={"cities": cities, "days": 6}).json()
    opt = client.post("/api/plan", json={"cities": cities, "days": 6, "optimize_route": True}).json()
    assert opt["route"][0] == "Cairo"
    assert set(opt["route"]) == set(cities)
    assert opt["total_travel_minutes"] <= plain["total_travel_minutes"]
    assert opt["route_optimized"] is True and plain["route_optimized"] is False


def test_retrieval_quality_regression_guard():
    from evaluation.run_eval import evaluate
    r = evaluate()
    assert r["hit@3"] >= 0.95, r["misses"]
    assert r["hit@1"] >= 0.90, r["misses"]
    assert r["no_answer"] == 1.0
    assert min(r["per_language_hit@3"].values()) >= 0.9


def test_arabic_spelling_variants_match_same_place(client):
    from app.guide import retrieve
    for q in ["الأقصر", "الاقصر", "بالأقصر", "الْأُقْصُر"]:
        assert {p["city"] for p in retrieve(q)} == {"Luxor"}, q
    assert retrieve("شاطىء دهب")[0]["city"] == "Dahab"
    assert retrieve("شاطئ دهب")[0]["city"] == "Dahab"


def test_plan_arabic_messages_and_matched_tags(client):
    body = client.post("/api/plan", json={"cities": ["Giza"], "days": 4, "interests": ["history"], "language": "ar"}).json()
    assert "ميزانية" in body["disclaimer"] or "الميزانية" in body["disclaimer"]
    assert sum(bool(day["stops"]) for day in body["days"]) >= 3
    if any(not day["stops"] and not day.get("travel") for day in body["days"]):
        assert body["warnings"] and any("الكتالوج" in w for w in body["warnings"])
    first = body["days"][0]["stops"][0]
    assert first["matched"] and first["why"].startswith("يطابق")
    en = client.post("/api/plan", json={"cities": ["Giza"], "days": 1}).json()
    assert en["days"][0]["stops"][0]["why"].startswith("Matches")


def test_plan_rejects_unknown_language(client):
    assert client.post("/api/plan", json={"cities": ["Giza"], "days": 1, "language": "de"}).status_code == 422


def test_cities_endpoint_exposes_arabic_names(client):
    data = client.get("/api/cities").json()
    assert data["city_names_ar"]["Luxor"] == "الأقصر"
    assert set(data["city_names_ar"]) >= set(data["cities"])
    assert set(data["interest_names_ar"]) == set(data["interests"])
    place = client.get("/api/places/karnak").json()
    assert place["name_ar"] == "معبد الكرنك" and place["tip"] and place["details"]
