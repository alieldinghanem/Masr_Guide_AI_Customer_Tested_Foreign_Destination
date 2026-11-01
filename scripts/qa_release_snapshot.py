"""Reproducible local release checks; no provider calls unless explicitly opted in.

Run from the repository root or any directory:
    python scripts/qa_release_snapshot.py
    python scripts/qa_release_snapshot.py --live-gemini

This command does not claim that missing frontend dependencies or credentials are
successful tests. Each result is explicitly PASS / FAIL / BLOCKED / NOT EXECUTED.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / 'qa_reports' / 'local_release_snapshot.json'


def run(name, cmd, *, cwd=ROOT, timeout=150, env=None):
    print(f'\n[RUN] {name}', flush=True)
    try:
        done = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                              errors='replace', timeout=timeout, check=False)
        lines = (done.stdout + '\n' + done.stderr).strip().splitlines()
        for line in lines[-14:]:
            print('  ' + line, flush=True)
        return {'status': 'PASS' if done.returncode == 0 else 'FAIL',
                'exit_code': done.returncode, 'summary': '\n'.join(lines[-14:])[:2800]}
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {'status': 'FAIL', 'reason': str(exc)[:300]}


def main():
    parser = argparse.ArgumentParser(description='Real local release checks; fail closed')
    parser.add_argument('--live-gemini', action='store_true', help='opt-in REAL Gemini API calls using backend/.env')
    args = parser.parse_args()
    checks = {}
    py = sys.executable
    if importlib.util.find_spec('pytest') is None:
        checks['backend_pytest'] = {'status': 'BLOCKED', 'reason': 'pytest is not installed'}
    else:
        checks['backend_pytest'] = run('Backend pytest', [py, '-m', 'pytest', '-q'], cwd=ROOT/'backend')
    checks['frontend_data_contract'] = (run('React contract (no dependencies required)',
        ['node', '--test', 'scripts/validate_trip_contract.test.mjs'], cwd=ROOT/'frontend')
        if shutil.which('node') else {'status': 'BLOCKED', 'reason': 'Node.js is not installed'})
    checks['chatbot_offline'] = run('Offline chatbot acceptance',
                                   [py, 'qa_chatbot/acceptance_evaluation.py'])
    checks['planner_invariants'] = run('Planner invariants', [py, 'scripts/qa_planner_stress.py'])
    checks['security_adversarial'] = run('Independent HTTP security and recovery',
                                          [py, 'scripts/qa_adversarial_extra.py'])
    checks['http_integration'] = run('Live local HTTP on disposable DBs', [py, 'scripts/qa_live_http.py'])
    checks['nginx_local'] = run('Local Nginx integration', [py, 'scripts/qa_nginx_proxy.py'])
    checks['credential_source_gate'] = run('Source secret gate', [py, 'scripts/check_no_secrets_v75.py'])
    vite = ROOT/'frontend'/'node_modules'/'.bin'/('vite.cmd' if os.name == 'nt' else 'vite')
    if not vite.is_file():
        msg = 'Frontend node_modules missing. Run npm ci --include=dev in frontend with working npm internet access.'
        for key in ('frontend_vitest', 'frontend_lint', 'frontend_production_build'):
            checks[key] = {'status': 'BLOCKED', 'reason': msg}
        print('\n[BLOCKED] React Build / Vitest / ESLint: node_modules not installed.', flush=True)
    else:
        npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
        if not npm:
            for key in ('frontend_vitest', 'frontend_lint', 'frontend_production_build'):
                checks[key] = {'status': 'BLOCKED', 'reason': 'npm executable missing'}
        else:
            command = [os.environ.get('ComSpec', 'cmd.exe'), '/d', '/c', npm] if os.name == 'nt' else [npm]
            for key, script in [('frontend_vitest','test'), ('frontend_lint','lint'),
                                ('frontend_production_build','build')]:
                checks[key] = run(f'React {script}', command + ['run',script], cwd=ROOT/'frontend')
    # Running a browser test requires actual running frontend and backend. Do not
    # substitute a check of a static HTML file or backend /demo for React E2E.
    checks['chromium_react_e2e'] = {'status': 'NOT EXECUTED',
        'reason': 'Run scripts/qa_browser_e2e.py against compiled React and a running backend; no browser claim made here.'}
    if args.live_gemini:
        env = dict(os.environ, MASR_LIVE_AI_QA='1')
        checks['real_gemini'] = run('REAL Gemini and FastAPI RAG smoke',
                                   [py, 'scripts/qa_gemini_live.py'], env=env, timeout=150)
    else:
        checks['real_gemini'] = {'status': 'NOT EXECUTED',
            'reason': 'Requires local backend/.env key and explicit --live-gemini; never ship the key.'}
    RESULT.parent.mkdir(exist_ok=True)
    data = {'generated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'scope': 'This machine and this execution only', 'checks': checks}
    RESULT.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    counts = {status: sum(v['status']==status for v in checks.values())
              for status in ('PASS','FAIL','BLOCKED','NOT EXECUTED')}
    print('\nRESULT:', ' '.join(f'{k}={v}' for k,v in counts.items()), flush=True)
    print('Detailed results:', RESULT, flush=True)
    return 1 if counts['FAIL'] else 0


if __name__ == '__main__':
    sys.exit(main())
