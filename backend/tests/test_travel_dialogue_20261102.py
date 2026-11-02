"""Quality gates for model narrative over immutable backend itinerary state."""
from copy import deepcopy

from app import travel_dialogue
from app.travel_agent import _with_verified_dialogue
from app.schemas import ConsultRequest


def _trip():
    state = {'days': 3, 'family': True, 'pace': 'balanced',
             'budget_usd': 3000, 'budget_egp': None,
             'phases': [{'kind': 'history', 'days': 3, 'cities': ['Cairo'], 'interests': ['history']}]}
    itinerary = {'days': [{'day': i + 1, 'city': 'Cairo', 'stops': [],
                           'note': 'Draft'} for i in range(3)],
                 'day_allocation': {'Cairo': 3}}
    return state, itinerary


def test_no_model_key_keeps_offline_deterministic_itinerary(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    state, itinerary = _trip()
    original = {'answer': 'Three Cairo days.', 'mode': 'local-planner',
                'trip_state': state, 'itinerary': itinerary}
    reply = _with_verified_dialogue(ConsultRequest(message='Plan Cairo trip'), 'Plan Cairo trip', original)
    assert reply == original


def test_configured_model_adds_human_style_without_mutating_validated_state(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'mock-no-network')
    monkeypatch.setenv('AI_TRIP_NARRATION_ENABLED', 'true')
    seen = []

    def fake_generate(prompt, instructions, **kwargs):
        seen.append((prompt, instructions, kwargs))
        return 'تمام، نقدر نخلي اليوم الأول هادي وبعدها نزور المعالم. تحب نبدأ بدري؟'

    monkeypatch.setattr(travel_dialogue, 'generate', fake_generate)
    state, itinerary = _trip()
    original = deepcopy({'answer': 'Three Cairo days.', 'mode': 'local-planner',
                         'trip_state': state, 'itinerary': itinerary})
    reply = _with_verified_dialogue(ConsultRequest(message='خلّي يوم القاهرة هادي', language='Arabic'),
                                     'خلّي يوم القاهرة هادي', original)
    assert reply['trip_state'] == state and reply['itinerary'] == itinerary
    assert reply['mode'] == 'gemini-dialogue+local-planner'
    assert reply['answer'].startswith('تمام')
    assert 'Three Cairo days.' in reply['answer']
    assert seen and '3000' in seen[0][0] and 'Cairo' in seen[0][0]


def test_upstream_failure_never_drops_valid_trip(monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setenv('AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'mock-no-network')
    monkeypatch.setenv('AI_TRIP_NARRATION_ENABLED', 'true')

    def down(*args, **kwargs):
        raise HTTPException(502, 'Model unavailable')

    monkeypatch.setattr(travel_dialogue, 'generate', down)
    state, plan = _trip()
    raw = {'mode': 'local-planner', 'answer': 'Trip prepared', 'itinerary': plan, 'trip_state': state}
    assert _with_verified_dialogue(ConsultRequest(message='Plan Cairo trip'), 'Plan Cairo trip', raw) == raw
