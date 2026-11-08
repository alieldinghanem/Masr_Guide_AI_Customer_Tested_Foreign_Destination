"""Dependency-free check of deployed Nginx CSP against first-party frontend assets.

This protects the actual photo-led discovery experience: a production CSP must
not block image hosts actively used by our own React/CSS code. It intentionally
checks explicit, narrowly-scoped hosts rather than permitting all https URLs.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
nginx = (ROOT / 'frontend' / 'nginx.conf').read_text(encoding='utf-8')
editorial = (ROOT / 'frontend' / 'src/components/EditorialMedia.jsx').read_text(encoding='utf-8')
css = (ROOT / 'frontend' / 'src/styles.css').read_text(encoding='utf-8')

csp = re.search(r'Content-Security-Policy\s+"([^"]+)"', nginx)
assert csp, 'Nginx must set a Content-Security-Policy header'
directives = {}
for item in csp.group(1).split(';'):
    words = item.strip().split()
    if words:
        directives[words[0]] = set(words[1:])

assert 'commons.wikimedia.org' in editorial and 'images.unsplash.com' in css, 'Update test if editorial sources change'
assert {'https://images.unsplash.com', 'https://commons.wikimedia.org', 'https://upload.wikimedia.org'} <= directives.get('img-src', set()), (
    'Deployed Nginx img-src blocks editorial photos/CSS background imagery from images.unsplash.com')
assert "'unsafe-inline'" not in directives.get('script-src', set()), 'Do not allow inline scripts'
assert "'unsafe-eval'" not in directives.get('script-src', set()), 'Do not allow dynamic eval'
assert 'https://www.openstreetmap.org' in directives.get('frame-src', set()), 'Maps iframe blocked by CSP'
print('PASS: Nginx image/map allowlist matches React assets without unsafe scripts')
