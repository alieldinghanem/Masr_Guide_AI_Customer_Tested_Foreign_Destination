"""Customer journeys discovered by an independently running HTTP tourist review."""

def consult(client, message, state=None, language='Arabic'):
    body = {'message':message,'language':language}
    if state is not None: body['trip_state'] = state
    response=client.post('/api/consult',json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_arabic_budget_and_city_allocation_survive_trip_edit(client):
    first=consult(client,'أنا جاي مصر 14 يوم مع زوجتي وطفلين وبميزانية 3000 دولار. عايز 6 أيام في القاهرة و4 أيام في الأقصر و4 أيام في الغردقة')
    assert first['trip_state']['budget_usd']==3000
    assert first['itinerary']['day_allocation']=={'Cairo':6,'Luxor':4,'Hurghada':4}
    changed=consult(client,'غيّر التوزيع: 5 أيام القاهرة و4 أيام الأقصر و5 أيام الغردقة، بس حافظ على 14 يوم',first['trip_state'])
    assert changed['trip_state']['days']==14
    assert changed['trip_state']['budget_usd']==3000
    assert changed['itinerary']['day_allocation']=={'Cairo':5,'Luxor':4,'Hurghada':5}


def test_current_trip_questions_about_hotel_and_airport_are_not_mutations(client):
    first=consult(client,'عايز رحلة 6 أيام: 4 أيام القاهرة ويومين الأقصر')
    state=first['trip_state']
    hotel=consult(client,'رشح لي فندق قريب من الأهرامات مناسب لطفلين وبميزانية متوسطة',state)
    assert hotel['mode'].startswith('hotel-')
    assert hotel['trip_state']==state
    assert hotel['itinerary'] is None
    airport=consult(client,'رحلتنا بتوصل مطار القاهرة الساعة 2 الفجر، نروح الزمالك إزاي بأمان مع طفلين؟',state)
    assert airport['mode']=='local-assistant'
    assert airport['trip_state']==state
    assert airport['itinerary'] is None


def test_usd_budget_not_converted_at_guessed_fx_and_preserved(client):
    plan=consult(client,'Plan a 4 day trip to Cairo with a total budget of $2,500',language='English')
    assert plan['trip_state']['budget_usd']==2500
    assert plan['trip_state']['budget_egp'] is None
    assert 'not a live cost estimate' in plan['answer']
    edited=consult(client,'Change my budget to 3000 USD',plan['trip_state'],language='English')
    assert edited['trip_state']['budget_usd']==3000
    assert edited['trip_state']['days']==4


def test_foreign_tourist_accessibility_kept_during_replan(client):
    first=consult(client,'I need a relaxed 6 day trip: 4 days in Cairo and 2 days in Luxor, my wife uses a wheelchair',language='English')
    assert first['trip_state']['accessibility_needs'] is True
    updated=consult(client,'Change Luxor to Aswan, keeping the same six days',first['trip_state'],language='English')
    assert updated['trip_state']['accessibility_needs'] is True
    assert updated['itinerary']['day_allocation']=={'Cairo':4,'Aswan':2}


def test_canadian_visitor_gets_official_visa_reference_not_unverified_eligibility(client):
    r=client.post('/api/chat',json={'language':'English','message':'I am Canadian, can I get an Egyptian visa on arrival?'})
    assert r.status_code==200
    assert 'visa2egypt.gov.eg' in r.json()['answer']
    assert 'cannot confirm' in r.json()['answer'].lower()


def test_offline_selected_openai_does_not_ask_visitor_to_supply_gemini_key(client, monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'openai')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    r=client.post('/api/chat', json={'message':'Tell me about Karnak Temple', 'language':'English'})
    assert r.status_code == 200
    assert r.json()['mode'] == 'offline-preview'
    assert 'GEMINI_API_KEY' not in r.json()['answer']
