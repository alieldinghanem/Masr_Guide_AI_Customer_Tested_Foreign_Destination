"""Fail CI if private environment files or likely live API credentials enter the source tree.

Best-effort local scanner; not a replacement for GitHub secret-scanning/history review.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {'.git', '.venv', 'venv', 'node_modules', 'dist', '__pycache__', '.pytest_cache', 'coverage'}
SKIP_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.woff', '.woff2', '.ico', '.pdf', '.zip', '.sqlite', '.sqlite3', '.db'}
PATTERNS = [re.compile(r'(?<![\w])AQ\.[A-Za-z0-9_-]{40,}'), re.compile(r'(?<![\w])AIza[A-Za-z0-9_-]{35,}'),
            re.compile(r'(?<![\w])sk-[A-Za-z0-9_-]{40,}')]
issues=[]
for p in ROOT.rglob('*'):
    if not p.is_file() or any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
        continue
    rel=p.relative_to(ROOT).as_posix()
    if p.name in {'.env', '.env.local', '.env.production'} or p.suffix.lower() in {'.pem', '.p12', '.pfx', '.key'}:
        issues.append(f'Private file exists in release: {rel}')
    if p.suffix.lower() in SKIP_EXTENSIONS or p.stat().st_size > 2_000_000:
        continue
    try:
        content=p.read_text('utf8')
    except UnicodeError:
        continue
    if any(pattern.search(content) for pattern in PATTERNS):
        issues.append(f'Potential credential in: {rel}')
if issues:
    print('RELEASE BLOCKED: ' + '; '.join(issues))
    raise SystemExit(1)
print('PASS: source-tree best-effort credential check')
