"""Evidence-based Masr Guide AI commercial release gate.

No upload, deploy or paid provider request is made by this command.
Run: python scripts/check_company_release.py
This deliberately exits nonzero whenever the platform is not fully verified.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
checks = []


def record(name, status, note):
    checks.append({'name': name, 'status': status, 'note': note})
    print(f'{status:<13} {name}: {note}', flush=True)


def execute(name, command, cwd, timeout=120):
    try:
        p = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        record(name, 'BLOCKED', f'Command could not complete: {type(exc).__name__}')
        return False
    output = (p.stdout or '').strip().splitlines()
    last = output[-1] if output else 'No command output'
    record(name, 'PASS' if p.returncode == 0 else 'FAIL', last[:220])
    return p.returncode == 0


execute('Backend API/regression', [sys.executable, '-m', 'pytest', '-q'], ROOT/'backend')
execute('HTTP real customer flow', [sys.executable, 'scripts/qa_customer_journey_http_20261029.py'], ROOT)
execute('Planner invariant fuzz cases', [sys.executable, 'scripts/qa_planner_stress.py'], ROOT)
node = shutil.which('node')
npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
if node:
    execute('Frontend static contract', [node, '--test',
             'scripts/validate_trip_contract.test.mjs', 'scripts/chat_ui_modes.test.mjs'], ROOT/'frontend')
else:
    record('Frontend static contract', 'BLOCKED', 'Node.js unavailable')

vite = ROOT / 'frontend' / 'node_modules' / '.bin' / ('vite.cmd' if os.name == 'nt' else 'vite')
if npm and vite.is_file():
    execute('React production build', [npm, 'run', 'build'], ROOT/'frontend')
    execute('React unit/component tests', [npm, 'test'], ROOT/'frontend')
    execute('React lint', [npm, 'run', 'lint'], ROOT/'frontend')
else:
    for name in ('React production build', 'React unit/component tests', 'React lint'):
        record(name, 'BLOCKED', 'Requires successful npm ci and verified dependencies')

# Configuring an AI key does not establish real accuracy or the success of an API call.
record('Live Gemini conversation', 'NOT EXECUTED',
       'Requires separately executed real-provider evaluation with a local key and QA results')
record('Chromium end-to-end', 'NOT EXECUTED',
       'Requires a running compiled React app and real desktop/mobile browser assertions')
record('Production storage/backup', 'NOT VERIFIED',
       'Real durable storage and an independently verified restore drill are not shown by a source archive')
record('Commercial launch/legal/partners', 'NOT VERIFIED',
       'Requires business, privacy, partner and operating reviews external to this codebase')

report = {
    'application': 'Masr Guide AI',
    'purpose': 'Evidence-based commercial release check, not a compliance certification',
    'status': 'RELEASE BLOCKED' if any(c['status'] != 'PASS' for c in checks) else 'ALL CHECKS VERIFIED',
    'checks': checks,
}
folder = ROOT / 'qa_reports'
folder.mkdir(exist_ok=True)
path = folder / 'company_release_gate.json'
path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(f"\n{report['status']} | report: {path.relative_to(ROOT)}")
raise SystemExit(0 if report['status'] == 'ALL CHECKS VERIFIED' else 2)
