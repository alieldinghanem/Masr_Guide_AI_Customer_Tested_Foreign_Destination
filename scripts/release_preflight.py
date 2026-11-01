"""Local release preflight: runs automated backend tests and checks frontend build.

This never calls the LLM provider and never asserts browser end-to-end success.
Usage: python scripts/release_preflight.py
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []

def run(name, cmd, path):
    print(f"\n== {name} ==", flush=True)
    try:
        result = subprocess.run(cmd, cwd=path, check=False)
    except FileNotFoundError as exc:
        print(f"FAIL: {exc}")
        errors.append(name)
        return
    if result.returncode:
        print(f"FAIL: {name} (exit {result.returncode})")
        errors.append(name)
    else:
        print(f"PASS: {name}")

if importlib.util.find_spec('ruff'):
    run('Backend lint (ruff)', [sys.executable, '-m', 'ruff', 'check', '.'], ROOT/'backend')
if importlib.util.find_spec('pytest'):
    run('Backend API tests', [sys.executable, '-m', 'pytest', '-q'], ROOT/'backend')
else:
    errors.append('Backend tests (pytest missing)')

if importlib.util.find_spec('pytest'):
    run('Retrieval quality set', [sys.executable, '-m', 'evaluation.run_eval', '--verbose'], ROOT/'backend')

node_modules = ROOT/'frontend'/'node_modules'
if not (node_modules / '.bin' / ('vite.cmd' if sys.platform == 'win32' else 'vite')).exists():
    print('\nFAIL: Frontend dependencies incomplete. Run npm ci in frontend/.')
    errors.append('Frontend dependencies')
else:
    run('Frontend lint', ['npm', 'run', 'lint'], ROOT/'frontend')
    run('Frontend unit/component/a11y tests', ['npm', 'test'], ROOT/'frontend')
    run('Frontend production build', ['npm', 'run', 'build'], ROOT/'frontend')

print('\n' + ('AUTOMATED CHECKS PASSED (live LLM/browser verification still required)' if not errors
              else 'NOT ACCEPTED: ' + ', '.join(errors)))
raise SystemExit(bool(errors))
