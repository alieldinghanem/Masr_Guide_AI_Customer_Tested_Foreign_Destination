"""Integration QA against locally launched FastAPI and a local mock of OpenAI Responses API.
Requires backend requirements-dev (and requests). No paid API calls, no public network.
Usage from project root: python scripts/qa_live_http.py
"""
import json
import importlib
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RESULTS = {}


def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextmanager
def fastapi_server(env):
    p = port()
    command = [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(p), '--log-level', 'error']
    proc = subprocess.Popen(command, cwd=ROOT/'backend', env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    base = f'http://127.0.0.1:{p}'
    try:
        for _ in range(90):
            if proc.poll() is not None:
                raise RuntimeError(f'FastAPI startup failed: {proc.stderr.read().decode(errors="replace")}')
            try:
                if requests.get(base+'/api/health', timeout=0.8).ok:
                    break
            except requests.RequestException:
                time.sleep(0.08)
        else:
            raise TimeoutError('Timed out waiting for FastAPI startup')
        yield base
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill()
        proc.stderr.close()


def check(label, expected, more=None):
    RESULTS[label] = bool(expected)
    if not expected:
        print(f'FAIL {label}: {more}')
    else:
        print(f'PASS {label}')


class MockOpenAI(BaseHTTPRequestHandler):
    logs = []
    def do_POST(self):
        payload = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        body = json.loads(payload)
        self.logs.append({'path':self.path, 'body':body,'auth':self.headers.get('Authorization')})
        response = {'id':'resp_qa','object':'response','created_at':1700000000,'status':'completed',
            'model':body['model'],'output':[{'type':'message','id':'msg_qa',
            'role':'assistant','status':'completed',
            'content':[{'type':'output_text','text':'Karnak is in Luxor [1].','annotations':[]}]}]}
        content=json.dumps(response).encode('utf8')
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(content)))
        self.end_headers()
        self.wfile.write(content)
    def log_message(self,*args):
        pass


def main():
    with tempfile.TemporaryDirectory(prefix='masr-qa-') as data_dir:
        env={**os.environ,'DATABASE_PATH':str(Path(data_dir)/'places.sqlite'),
             'MASR_USER_DB':str(Path(data_dir)/'traveler.sqlite3'),
             'OPENAI_API_KEY':'', 'CHAT_RATE_LIMIT_PER_MINUTE':'1000'}
        with fastapi_server(env) as base:
            get=lambda path, **kw: requests.get(base+path,timeout=7,**kw)
            post=lambda path, data, **kw: requests.post(base+path,json=data,timeout=7,**kw)
            check('health offline', get('/api/health').json()['guide_mode']=='offline-preview')
            spec=get('/openapi.json')
            check('OpenAPI documentation', spec.status_code==200 and '/api/chat' in spec.json()['paths'])
            places=get('/api/places'); dataset=places.json().get('places',[])
            check('catalog response', places.ok and len(dataset)>=50)
            check('cities response', len(get('/api/cities').json().get('cities',[]))==12)
            check('search and filter', all(p['city']=='Luxor' for p in get('/api/places?city=Luxor').json()['places']))
            check('existing landmark', get('/api/places/karnak').status_code==200)
            check('missing landmark 404', get('/api/places/not-found').status_code==404)
            check('SQL injection input harmless', get('/api/places?q=%27%20OR%201%3D1--').status_code==200 and len(get('/api/places').json()['places'])==len(dataset))
            plan=post('/api/plan',{'cities':['Cairo','Luxor','Aswan'], 'days':6, 'interests':['history','culture'],'pace':'balanced'})
            pd=plan.json() if plan.ok else {}
            check('multi-city plan',plan.ok and len(pd.get('days',[]))==6 and pd.get('total_places',0)>2)
            check('cities contiguous',plan.ok and [day['city'] for day in pd['days']] == [city for city in ['Cairo','Luxor','Aswan'] for _ in range(pd['day_allocation'][city])])
            check('impossible plan 422', post('/api/plan',{'cities':['Cairo','Luxor'],'days':1}).status_code==422)
            check('blank chat 422',post('/api/chat',{'message':'   '}).status_code==422)
            answer=post('/api/chat',{'message':'احكيلي عن المتحف النوبي','language':'Arabic'})
            check('Arabic offline grounded answer',answer.ok and answer.json()['sources'][0]['id']=='nubian-museum' and answer.json()['mode']=='offline-preview')
            check('French chat accepted',post('/api/chat',{'message':'Parlez-moi des pyramides de Gizeh','language':'French'}).status_code==200)
            # Real HTTP account integration: server DB -> authenticated favorites
            # -> privacy export -> account erasure. Uses disposable test storage.
            registration = post('/api/auth/register', {
                'email': 'live-http@example.org', 'password': 'QA-local-long-password-2026'
            })
            check('real HTTP registration', registration.status_code == 201)
            if registration.status_code == 201:
                auth = {'Authorization': 'Bearer ' + registration.json()['token']}
                check('anonymous favorite rejected', get('/api/my/favorites').status_code == 401)
                favorite = requests.post(base+'/api/my/favorites/karnak', headers=auth, timeout=7)
                check('authenticated favorite write', favorite.status_code == 200)
                check('authenticated favorite read', get('/api/my/favorites', headers=auth).json().get('place_ids') == ['karnak'])
                export = get('/api/my/export', headers=auth)
                check('privacy export without credential disclosure',
                      export.status_code == 200 and export.json().get('favorites', [{}])[0].get('place_id') == 'karnak'
                      and registration.json()['token'] not in export.text and export.headers.get('Cache-Control') == 'no-store')
                deleted = requests.delete(base+'/api/my/account', headers=auth, json={
                    'password': 'QA-local-long-password-2026', 'confirmation': 'DELETE MY ACCOUNT'
                }, timeout=7)
                check('account deletion revokes access',
                      deleted.status_code == 200 and get('/api/my/favorites', headers=auth).status_code == 401)
            else:
                for label in ('anonymous favorite rejected', 'authenticated favorite write',
                              'authenticated favorite read', 'privacy export without credential disclosure',
                              'account deletion revokes access'):
                    check(label, False, 'Registration failed')
            cors=get('/api/health',headers={'Origin':'https://evil.invalid'})
            check('CORS unexpected origin blocked',cors.headers.get('Access-Control-Allow-Origin') is None)
            cors2=get('/api/health',headers={'Origin':'http://localhost:5173'})
            check('CORS local development allowed',cors2.headers.get('Access-Control-Allow-Origin')=='http://localhost:5173')
            with ThreadPoolExecutor(max_workers=12) as pool:
                responses=list(pool.map(lambda _:post('/api/plan',{'cities':['Giza','Cairo'],'days':3}),range(80)))
            check('80 concurrent itinerary requests',all(r.status_code==200 for r in responses))
        # The HTTP stub checks our API adapter contract, not a live provider or the vendor SDK.
        try:
            sdk_available = hasattr(importlib.import_module('openai'), 'OpenAI')
        except ImportError:
            sdk_available = False
        if not sdk_available:
            print('BLOCKED: Real OpenAI SDK not installed. API key/live OpenAI calls not tested.')
        MockOpenAI.logs=[]
        mock=ThreadingHTTPServer(('127.0.0.1',0),MockOpenAI)
        thread=threading.Thread(target=mock.serve_forever,daemon=True);thread.start()
        env['OPENAI_API_KEY']='qa-not-secret-do-not-use'
        env['OPENAI_BASE_URL']=f'http://127.0.0.1:{mock.server_port}/v1'
        if not sdk_available:
            # Test only a minimal adapter. This does NOT prove actual OpenAI SDK compatibility.
            shim = Path(data_dir)/'openai.py'
            shim.write_text('''import os, requests
from types import SimpleNamespace
class OpenAI:
    def __init__(self, api_key, timeout=25., max_retries=1):
        self.api_key = api_key
        self.responses = self
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def create(self, **kwargs):
        reply = requests.post(os.environ['OPENAI_BASE_URL']+'/responses', json=kwargs,
                              headers={'Authorization': 'Bearer '+self.api_key},timeout=6)
        reply.raise_for_status()
        result = reply.json()
        return SimpleNamespace(output_text=result['output'][0]['content'][0]['text'], status=result.get('status'), incomplete_details=None)
''')
            env['PYTHONPATH']=str(Path(data_dir))+os.pathsep+str(ROOT/'backend')
        try:
            with fastapi_server(env) as base:
                check('LLM configured not yet verified', requests.get(base+'/api/health', timeout=7).json()['guide_mode']=='llm-configured')
                r=requests.post(base+'/api/chat',json={'message':'Tell me about Karnak Temple'},timeout=12)
                data=r.json()
                check(('real SDK simulated provider' if sdk_available else 'shim simulated provider'),r.status_code==200 and data.get('mode')=='llm-rag' and '[1]' in data.get('answer',''),data)
                check(('real SDK request contract' if sdk_available else 'shim request contract'),bool(MockOpenAI.logs) and MockOpenAI.logs[0]['path']=='/v1/responses' and any('Karnak' in item.get('content', '') for item in MockOpenAI.logs[0]['body'].get('input', []) if isinstance(item, dict)))
                check('server-side auth header only',bool(MockOpenAI.logs) and MockOpenAI.logs[0]['auth']=='Bearer qa-not-secret-do-not-use' and 'qa-not-secret-do-not-use' not in r.text)
        finally:
            mock.shutdown();mock.server_close()
    ok=sum(RESULTS.values())
    print(f'HTTP AND MOCK ADAPTER: {ok}/{len(RESULTS)} checks passed')
    print('REAL OPENAI PROVIDER: NOT TESTED (requires real credentials and provider availability)')
    return 0 if ok==len(RESULTS) else 1

if __name__ == '__main__':
    raise SystemExit(main())
