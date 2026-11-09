"""Fail-closed end-to-end release verifier for Masr Guide AI.

  python scripts/verify_release_v78.py --install-frontend
  python scripts/verify_release_v78.py --browser
  python scripts/verify_release_v78.py --live-gemini   # explicit real API call
  python scripts/verify_release_v78.py --install-frontend --browser --live-gemini

This tool never prints API keys. A full PASS requires a frontend build, component tests
and lint, offline Backend/QA gates, and optionally real Chromium and Gemini checks.
Skip results NEVER count as passes. A failed gate returns a nonzero exit code.
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def execute(label, args, cwd, *, env=None):
    print(f'\n>>> {label}', flush=True)
    try:
        result = subprocess.run(args, cwd=cwd, env=env, check=False)
        outcome = 'PASS' if result.returncode == 0 else 'FAIL'
    except FileNotFoundError:
        outcome = 'BLOCKED'
    print(f'[{outcome}] {label}', flush=True)
    return outcome


def available_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def browser_e2e():
    # Only test the actually compiled React release; require a real browser.
    if not (ROOT / 'frontend' / 'dist' / 'index.html').is_file():
        print('BLOCKED browser: compiled frontend/dist/index.html missing')
        return 'BLOCKED'
    with tempfile.TemporaryDirectory(prefix='masr-release-') as d:
        port = available_port()
        # Isolated E2E must permit temporary test-user registration. Portfolio mode
        # intentionally blocks signups on ephemeral disks; that is correct for
        # public previews but would invalidate this local account-flow test.
        env = {**os.environ, 'APP_ENV': 'development', 'DATABASE_PATH': str(Path(d) / 'catalog.sqlite3'),
               'MASR_USER_DB': str(Path(d) / 'traveler.sqlite3'), 'GEMINI_API_KEY': '', 'OPENAI_API_KEY': '',
               'CHAT_RATE_LIMIT_PER_MINUTE': '1000', 'AUTH_REGISTER_RATE_PER_MINUTE': '1000'}
        server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
                                   '--port', str(port), '--log-level', 'error'],
                                  cwd=ROOT/'backend', env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            import urllib.request
            import time
            ready = False
            for _ in range(75):
                if server.poll() is not None:
                    break
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/ready', timeout=0.6) as r:
                        if r.status == 200:
                            ready = True
                            break
                except Exception:
                    time.sleep(0.15)
            if not ready:
                print('FAIL browser: isolated backend did not become ready')
                return 'FAIL'
            return execute('Real Chromium desktop/mobile E2E', [sys.executable, 'scripts/qa_browser_e2e.py'], ROOT,
                           env={**env, 'FRONTEND_URL': f'http://127.0.0.1:{port}'})
        finally:
            server.terminate()
            try: server.wait(timeout=4)
            except subprocess.TimeoutExpired: server.kill()
            server.stderr.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-frontend', action='store_true', help='Run npm ci first (requires npm registry access)')
    parser.add_argument('--browser', action='store_true', help='Test compiled React in real Chromium desktop and mobile')
    parser.add_argument('--live-gemini', action='store_true', help='Make charged/limited REAL Gemini API requests with private key')
    args = parser.parse_args()
    checks = {}
    def run(label, command, cwd, env=None):
        checks[label] = execute(label, command, cwd, env=env)
    run('Backend automated tests', [sys.executable, '-m', 'pytest', '-q'], ROOT/'backend')
    run('Grounded retrieval evaluation', [sys.executable, '-m', 'evaluation.run_eval'], ROOT/'backend')
    run('Corrected 52-case QA', [sys.executable, 'qa_chatbot/acceptance_evaluation.py'], ROOT)
    run('Deterministic planner stress', [sys.executable, 'scripts/qa_planner_stress.py'], ROOT)
    run('Secret scanner', [sys.executable, 'scripts/check_no_secrets_v75.py'], ROOT)
    run('Frontend data-integrity contract (Node without npm)', ['node', '--test', 'scripts/validate_trip_contract.test.mjs'], ROOT/'frontend')
    run('Real HTTP server + mock AI integration', [sys.executable, 'scripts/qa_live_http.py'], ROOT)
    npm = 'npm.cmd' if sys.platform == 'win32' else 'npm'
    if args.install_frontend:
        run('Install frontend dependencies', [npm, 'ci', '--no-audit', '--no-fund'], ROOT/'frontend')
    local_vite = ROOT / 'frontend' / 'node_modules' / '.bin' / ('vite.cmd' if sys.platform == 'win32' else 'vite')
    if local_vite.exists():
        run('React component/a11y tests', [npm, 'test'], ROOT/'frontend')
        run('Frontend lint', [npm, 'run', 'lint'], ROOT/'frontend')
        run('React production build', [npm, 'run', 'build'], ROOT/'frontend')
    else:
        print('BLOCKED: node_modules/.bin/vite missing. Run with --install-frontend where npm internet works.')
        checks['React component/a11y tests'] = 'BLOCKED'
        checks['Frontend lint'] = 'BLOCKED'
        checks['React production build'] = 'BLOCKED'
    checks['Browser E2E'] = browser_e2e() if args.browser else 'NOT_EXECUTED'
    if args.live_gemini:
        run('Real Gemini API and chat integration', [sys.executable, 'scripts/qa_gemini_live.py'], ROOT,
            env={**os.environ, 'MASR_LIVE_AI_QA':'1'})
    else:
        checks['Real Gemini API'] = 'NOT_EXECUTED'
    data = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'checks': checks,
            'ready_for_portfolio_review': all(v == 'PASS' for v in checks.values())}
    outfile = ROOT / 'release-verification-local.json'
    # Only gate names and outcomes: never secrets or personal conversation data.
    outfile.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nRelease verification: {outfile} [do not commit unverified statuses as evidence]')
    print('ALL GATES PASSED' if data['ready_for_portfolio_review'] else 'NOT ACCEPTED: some checks failed or were not executed')
    return 0 if data['ready_for_portfolio_review'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
