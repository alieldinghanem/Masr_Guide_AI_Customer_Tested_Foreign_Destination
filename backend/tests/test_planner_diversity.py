"""Visitor-facing diversity preserves interests, cities and time budgets."""
import pytest
from app import planner
from app.schemas import PlanRequest


def worship(place):
    return any(word in place['id'] for word in ('mosque', 'church', 'synagogue', 'monastery')) or place['id'] == 'coptic-cairo'


@pytest.mark.parametrize('family', [False, True])
@pytest.mark.parametrize('language', ['en', 'ar'])
def test_short_history_visit_is_not_a_sequence_of_worship_sites(family, language):
    plan = planner.build_plan(PlanRequest(cities=['Cairo'], days=2, interests=['history'], family=family, language=language))
    stops = [s['place'] for d in plan['days'] for s in d['stops']]
    assert len(stops) >= 3
    assert sum(worship(p) for p in stops) <= 2
    assert any(p['category'] == 'Museum' for p in stops)
    assert len({p['id'] for p in stops}) == len(stops)
    assert all(d['city'] == 'Cairo' for d in plan['days'])
    assert all(d['estimated_activity_minutes'] + d['rest_minutes'] <= 360 for d in plan['days'])
    if family:
        assert all(len(d['stops']) <= 2 and d['rest_minutes'] == 45 for d in plan['days'])


def test_museum_only_preference_is_not_diluted():
    plan = planner.build_plan(PlanRequest(cities=['Cairo'], days=2, interests=['museums']))
    assert all(s['place']['category'] == 'Museum' for d in plan['days'] for s in d['stops'])


def test_small_same_type_catalog_still_fills_available_days(monkeypatch):
    from app.catalog import PLACES
    places = [dict(p) for p in PLACES if 'mosque' in p['id']][:3]
    monkeypatch.setattr(planner, 'all_places', lambda: places)
    plan = planner.build_plan(PlanRequest(cities=['Cairo'], days=3, interests=['history']))
    assert all(d['stops'] for d in plan['days'])
    assert plan['total_places'] == 3
