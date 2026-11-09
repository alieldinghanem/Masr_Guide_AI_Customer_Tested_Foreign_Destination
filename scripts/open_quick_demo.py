"""Start only the real FastAPI quick demo (NOT the React tourism website).

Useful while React/npm dependencies are being installed or diagnosed.
The browser opens only after the API and demo HTML pass real HTTP readiness.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
import webbrowser

from open_local_website import BACKEND, LOG_DIR, VENV_PYTHON, fetch, healthy_backend, log_tail, run_checked

DEMO = 'http://127.0.0.1:8000/demo'
READY = 'http://127.0.0.1:8000/api/ready'


def verify_demo(response: tuple[int, str] | None) -> bool:
    return bool(response and response[0] == 200 and
                'Masr Guide AI' in response[1] and 'id="headline"' in response[1]
                and 'id="form"' in response[1])


def ensure_backend() -> None:
    if sys.version_info < (3, 11):
        raise RuntimeError('Python 3.11+ required (Python 3.12 recommended).')
    LOG_DIR.mkdir(exist_ok=True)
    if not VENV_PYTHON.is_file():
        run_checked([sys.executable, '-m', 'venv', str(BACKEND / '.venv')],
                    logfile=LOG_DIR / 'python-venv.log')
    probe = subprocess.run([str(VENV_PYTHON), '-c', 'import fastapi, uvicorn, dotenv, pydantic'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if probe.returncode:
        print('[SETUP] Installing backend libraries; internet is required for the first setup.', flush=True)
        run_checked([str(VENV_PYTHON), '-m', 'pip', 'install', '-r', 'requirements.txt'],
                    cwd=BACKEND, logfile=LOG_DIR / 'pip-install.log')


def main() -> int:
    print('MASR GUIDE AI - API TRAVEL CONSULTANT PREVIEW', flush=True)
    print('This is the limited /demo page, NOT the complete React website.', flush=True)
    ensure_backend()
    if fetch(DEMO) is not None or fetch(READY) is not None:
        raise RuntimeError('Port 8000 already in use. Close the previous backend window and retry.')
    path = LOG_DIR / 'demo-backend.log'
    with path.open('w', encoding='utf-8') as log:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        proc = subprocess.Popen([str(VENV_PYTHON), '-m', 'uvicorn', 'app.main:app', '--no-proxy-headers',
                                 '--host', '127.0.0.1', '--port', '8000'],
                                cwd=BACKEND, stdout=log, stderr=subprocess.STDOUT,
                                creationflags=flags)
        try:
            for _ in range(60):
                if proc.poll() is not None:
                    break
                if healthy_backend(fetch(READY)) and verify_demo(fetch(DEMO)):
                    print('[READY] Quick demo available ONLY on this computer:', DEMO, flush=True)
                    print('Leave this console open. Press Ctrl+C to stop.', flush=True)
                    webbrowser.open(DEMO)
                    while proc.poll() is None:
                        time.sleep(1)
                    print('[FAILED] Preview server stopped unexpectedly.', flush=True)
                    return 1
                time.sleep(1)
            print('[FAILED] Quick demo did not start. Log:', path, flush=True)
            print(log_tail(path), flush=True)
            return 1
        except KeyboardInterrupt:
            print('[STOP] Preview stopped.', flush=True)
            return 0
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print('[FAILED]', error, flush=True)
        print('Inspect .local-logs for setup/server diagnostics.', flush=True)
        sys.exit(1)
