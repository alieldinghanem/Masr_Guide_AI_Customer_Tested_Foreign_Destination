"""The browser tab must receive SVG bytes, not the React index fallback."""

from pathlib import Path

from app import main


def test_favicon_url_returns_the_logo_with_svg_content_type(client, tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[2] / 'frontend' / 'public' / 'favicon.svg'
    (tmp_path / 'favicon.svg').write_bytes(source.read_bytes())
    monkeypatch.setattr(main, '_FRONTEND_DIST', tmp_path)
    response = client.get('/favicon.svg')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('image/svg+xml')
    assert b'<svg' in response.content and b'Masr Guide AI' in response.content
    assert b'<!doctype html>' not in response.content
