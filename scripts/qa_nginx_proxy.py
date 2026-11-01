"""Optional nginx local smoke test; needs nginx executable but NOT Docker or npm.

Uses an ephemeral high port, a temporary static file, and a local FastAPI instance.
This validates proxy forwarding and edge throttling. It does not prove Docker,
React rendering, HTTPS or public deployment.
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

ROOT=Path(__file__).resolve().parents[1]
nginx=shutil.which('nginx')
if not nginx:
    print('SKIP: nginx binary not found (not a pass)')
    raise SystemExit(2)

def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0))
        return s.getsockname()[1]

def request(url):
    try:
        with urlopen(url,timeout=3) as r: return r.status, r.read().decode('utf-8')
    except HTTPError as e: return e.code, e.read().decode('utf-8')

def wait(url,proc):
    for _ in range(70):
        if proc.poll() is not None: raise RuntimeError(f'Process terminated unexpectedly: {proc.returncode}')
        try:
            if request(url)[0] == 200: return
        except (URLError, ConnectionError): pass
        time.sleep(.08)
    raise RuntimeError('Startup timed out')

with tempfile.TemporaryDirectory(prefix='masr-nginx-qa-') as tmp:
    t=Path(tmp)
    t.chmod(0o755)
    (t/'www').mkdir()
    (t/'www').chmod(0o755)
    (t/'www/index.html').write_text('MASR_NGINX_STATIC_OK')
    (t/'logs').mkdir()
    api_port=port(); frontend_port=port()
    site=(ROOT/'frontend/nginx.conf').read_text()
    site=site.replace('listen 80;',f'listen {frontend_port};').replace('root /usr/share/nginx/html;', f'root {t}/www;')
    site=site.replace('proxy_pass http://backend:8000',f'proxy_pass http://127.0.0.1:{api_port}')
    (t/'site.conf').write_text(site)
    (t/'nginx.conf').write_text(f'pid {t}/nginx.pid;\nevents {{ worker_connections 128; }}\nhttp {{ access_log off; error_log {t}/logs/error.log warn; include {t}/site.conf; }}\n')
    env={**os.environ,'OPENAI_API_KEY':'','CHAT_RATE_LIMIT_PER_MINUTE':'1000','DATABASE_PATH':str(t/'tourism.sqlite')}
    api=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(api_port),'--log-level','error'],cwd=ROOT/'backend',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    web=None
    try:
        wait(f'http://127.0.0.1:{api_port}/api/health',api)
        syntax=subprocess.run([nginx,'-t','-c',str(t/'nginx.conf'),'-p',str(t)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        assert syntax.returncode == 0, syntax.stderr
        print('PASS nginx syntax')
        web=subprocess.Popen([nginx,'-c',str(t/'nginx.conf'),'-p',str(t),'-g','daemon off;'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            wait(f'http://127.0.0.1:{frontend_port}/',web)
        except Exception:
            print('NGINX DEBUG', (t/'logs/error.log').read_text(errors='replace') if (t/'logs/error.log').exists() else '(no log)')
            raise
        status,body=request(f'http://127.0.0.1:{frontend_port}/')
        assert status==200 and 'MASR_NGINX_STATIC_OK' in body
        print('PASS nginx static routing')
        status,body=request(f'http://127.0.0.1:{frontend_port}/api/health')
        assert status==200 and 'offline-preview' in body
        print('PASS nginx backend proxy')
        statuses=[request(f'http://127.0.0.1:{frontend_port}/api/chat')[0] for _ in range(24)]
        # 405 is expected for GET on a POST endpoint, while 429 confirms edge throttle.
        assert 405 in statuses and 429 in statuses, statuses
        print('PASS edge throttling (429 response after burst)')
        print('LOCAL NGINX PROXY: 4/4 passed (not a Docker or browser test)')
    finally:
        if web is not None:
            web.terminate()
            try: web.wait(timeout=5)
            except subprocess.TimeoutExpired: web.kill()
        api.terminate()
        try: api.wait(timeout=5)
        except subprocess.TimeoutExpired: api.kill()
