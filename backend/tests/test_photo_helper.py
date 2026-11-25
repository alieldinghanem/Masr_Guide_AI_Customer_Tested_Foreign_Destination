import base64
from datetime import date, timedelta
from io import BytesIO
import json
import pytest
from PIL import Image
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app import photo_helper as helper, security
from app.main import app


def image():
    output = BytesIO()
    Image.new('RGB', (4, 4), 'white').save(output, format='PNG')
    return base64.b64encode(output.getvalue()).decode()


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    monkeypatch.delenv('PRICE_REFERENCE_FILE', raising=False)
    monkeypatch.setenv('AI_PROVIDER', 'offline')
    security._guard_hits.clear()


def observation(monkeypatch, confidence='high'):
    monkeypatch.setattr(helper, 'enabled', lambda: True)
    calls = []
    def generate(*args, **kwargs):
        calls.append(kwargs)
        return json.dumps({'title': 'Papyrus print', 'category': 'papyrus', 'confidence': confidence,
                           'price': 999999, 'url': 'https://invented.example'})
    monkeypatch.setattr(helper, 'generate', generate)
    return calls


def body(**changes):
    return helper.PhotoRequest(image_base64=image(), provider_consent=True, city='Cairo', material='papyrus', size='20 x 30 cm', **changes)


def refs(monkeypatch, tmp_path, age=0, same_host=False):
    records = [dict(category='papyrus', material='papyrus', size='20 x 30 cm', city='Cairo',
                    price_egp=p, currency='EGP', approved=True,
                    observed_on=(date.today() - timedelta(days=age)).isoformat(),
                    source_url=f'https://{("one" if same_host else host)}.example/product')
               for host, p in [('one', 100), ('two', 140)]]
    path = tmp_path / 'references.json'; path.write_text(json.dumps(records), encoding='utf-8')
    monkeypatch.setenv('PRICE_REFERENCE_FILE', str(path))
    return records


def test_photo_without_references_never_uses_model_price(monkeypatch):
    calls = observation(monkeypatch)
    result = helper.compare(body(quoted_egp=500))
    assert result['estimate'] is None and result['references'] == []
    assert 'price' not in result['observation']
    assert calls[0]['inline_image']['mime_type'] == 'image/jpeg'
    with Image.open(BytesIO(base64.b64decode(calls[0]['inline_image']['data']))) as cleaned:
        assert cleaned.format == 'JPEG' and not cleaned.getexif()


def test_approved_matching_samples_produce_sourced_range(monkeypatch, tmp_path):
    observation(monkeypatch); records = refs(monkeypatch, tmp_path)
    result = helper.compare(body(quoted_egp=500))
    assert result['estimate'] == {'min_egp': 100, 'max_egp': 140, 'comparison': 'above_reference_range'}
    assert [r['source_url'] for r in result['references']] == [r['source_url'] for r in records]


@pytest.mark.parametrize('age,same_host,confidence', [(31, False, 'high'), (-1, False, 'high'), (0, True, 'high'), (0, False, 'low')])
def test_stale_future_duplicate_or_uncertain_data_cannot_price(monkeypatch, tmp_path, age, same_host, confidence):
    observation(monkeypatch, confidence); refs(monkeypatch, tmp_path, age, same_host)
    assert helper.compare(body())['estimate'] is None


def test_mismatched_specs_do_not_price(monkeypatch, tmp_path):
    observation(monkeypatch); refs(monkeypatch, tmp_path)
    request = body().model_copy(update={'size': '50 x 70 cm'})
    assert helper.compare(request)['estimate'] is None


def test_invalid_image_and_missing_consent_rejected_before_provider(monkeypatch):
    calls = observation(monkeypatch)
    with TestClient(app) as client:
        data = body().model_dump(); data['provider_consent'] = False
        assert client.post('/api/photo-helper/compare', json=data).status_code == 422
        data['provider_consent'] = True; data['image_base64'] = base64.b64encode(b'not an image at all').decode()
        assert client.post('/api/photo-helper/compare', json=data).status_code == 422
    assert not calls


def test_provider_failure_is_honest(monkeypatch):
    monkeypatch.setattr(helper, 'enabled', lambda: True)
    monkeypatch.setattr(helper, 'generate', lambda *a, **k: 'not JSON')
    with pytest.raises(HTTPException) as exc:
        helper.compare(body())
    assert exc.value.status_code == 502


def test_unconfigured_provider_returns_unavailable():
    with pytest.raises(HTTPException) as exc:
        helper.compare(body())
    assert exc.value.status_code == 503


def test_decoded_dimensions_are_bounded_before_provider(monkeypatch):
    calls = observation(monkeypatch)
    output = BytesIO()
    Image.new('RGB', (3000, 2000), 'white').save(output, format='PNG')
    request = body().model_copy(update={'image_base64':base64.b64encode(output.getvalue()).decode()})
    with pytest.raises(HTTPException) as exc:
        helper.compare(request)
    assert exc.value.status_code == 422 and not calls


def test_photo_endpoint_is_rate_limited(monkeypatch):
    observation(monkeypatch)
    with TestClient(app) as client:
        codes = [client.post('/api/photo-helper/compare', json=body().model_dump()).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 200, 429]


def test_gemini_transport_sends_inline_image_in_final_user_turn(monkeypatch):
    from app import gemini_client
    monkeypatch.setenv('GEMINI_API_KEY', 'unit-test-only-placeholder')
    monkeypatch.setenv('GEMINI_MODEL', 'unit-test-vision')
    monkeypatch.setattr(gemini_client, '_check_cooldown', lambda model: None)
    monkeypatch.setattr(gemini_client, '_track_availability', lambda *a: None)
    seen = []
    class Response:
        def __enter__(self): return BytesIO(json.dumps({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'result'}]}}]}).encode())
        def __exit__(self, *args): pass
    def open_request(request, timeout):
        seen.append(json.loads(request.data))
        return Response()
    monkeypatch.setattr(gemini_client, 'urlopen', open_request)
    photo = {'mime_type':'image/jpeg', 'data':'unit-test-encoded-image'}
    assert gemini_client.generate('Identify product', 'JSON only', inline_image=photo) == 'result'
    assert seen[0]['contents'][-1]['role'] == 'user'
    assert seen[0]['contents'][-1]['parts'][-1] == {'inline_data':photo}
