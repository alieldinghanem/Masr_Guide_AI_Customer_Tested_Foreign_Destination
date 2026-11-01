"""Nonstandard, local-only black-box assurance checks.

No third-party APIs, real accounts or production credentials are used.
Runs FastAPI on an ephemeral port with temporary isolated SQLite databases.
Usage: python scripts/qa_adversarial_extra.py
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
import json
import os
import random
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

import requests

ROOT = Path(__file__).resolve().parents[1]
CASES = []


def check(category, name, ok, detail=None):
    CASES.append({'category': category, 'name': name, 'status': 'PASS' if ok else 'FAIL', 'detail': detail})
    print(f'{"PASS" if ok else "FAIL"}: [{category}] {name}' + (f' -- {detail}' if detail and not ok else ''))


def unused_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextmanager
def serve(env):
    port = unused_port()
    proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--no-proxy-headers', '--host', '127.0.0.1', '--port', str(port), '--log-level', 'warning'],
                            cwd=ROOT / 'backend', env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    base = f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            if proc.poll() is not None:
                raise RuntimeError(proc.stderr.read().decode(errors='replace')[:1500])
            try:
                if requests.get(base + '/api/ready', timeout=0.4).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.08)
        else:
            raise RuntimeError('Uvicorn failed readiness check')
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        proc.stderr.close()


def main():
    with tempfile.TemporaryDirectory(prefix='masr-nonstandard-') as temp:
        env = {**os.environ,
               'DATABASE_PATH': str(Path(temp)/'catalog.sqlite'),
               'MASR_USER_DB': str(Path(temp)/'accounts.sqlite'),
               'GEMINI_API_KEY': '', 'OPENAI_API_KEY': '',
               'APP_ENV': 'local', 'ADMIN_API_TOKEN': 'local-test-admin-credential-never-use-real',
               'AUTH_LOGIN_RATE_PER_MINUTE': '5', 'AUTH_REGISTER_RATE_PER_MINUTE': '50',
               'ADMIN_RATE_PER_MINUTE': '200', 'CHAT_RATE_LIMIT_PER_MINUTE': '300'}
        # Catch a regression where the QA runner is hardened but actual product
        # commands silently revert to Uvicorn's implicit localhost proxy trust.
        launch_files = ('Dockerfile', 'backend/Dockerfile', 'RUN_BACKEND_WINDOWS.bat',
                        'scripts/open_local_website.py', 'scripts/open_quick_demo.py')
        check('Deployment / launch configuration',
              'All production and Windows Uvicorn entry points explicitly disable implicit proxy trust',
              all('--no-proxy-headers' in (ROOT / path).read_text(encoding='utf-8') for path in launch_files))
        with serve(env) as base:
            def req(method, path, **kwargs):
                return requests.request(method, base + path, timeout=12, **kwargs)
            def post(path, body, **kwargs):
                return req('POST', path, json=body, **kwargs)
            category = 'AUTHZ / cross-account isolation'
            a = post('/api/auth/register', {'email':'nonstandard-alice@example.com', 'password':'Alice-Long-Passphrase-2026!'});
            b = post('/api/auth/register', {'email':'nonstandard-bob@example.com', 'password':'Bob-Long-Passphrase-2026!'});
            check(category, 'Two isolated users register', a.status_code == b.status_code == 201, f'{a.status_code}/{b.status_code}')
            if a.status_code != 201 or b.status_code != 201:
                return 1
            alice={'Authorization':'Bearer '+a.json()['token']}
            bob={'Authorization':'Bearer '+b.json()['token']}
            plan = post('/api/plan', {'cities':['Cairo','Luxor'], 'days':5, 'language':'en', 'pace':'balanced'})
            check('Planner', 'Control itinerary generated', plan.status_code == 200 and len(plan.json().get('days', [])) == 5)
            data={'title':'Alice holiday','itinerary':plan.json()}
            trip=post('/api/my/trips', data, headers=alice)
            check(category, 'Trip created for owner', trip.status_code == 201)
            tid=trip.json()['id']
            check(category, 'Other user cannot view trip',req('GET', f'/api/my/trips/{tid}', headers=bob).status_code==404)
            check(category, 'Other user cannot overwrite trip',req('PUT', f'/api/my/trips/{tid}', headers=bob, json=data).status_code==404)
            check(category, 'Other user cannot delete trip',req('DELETE', f'/api/my/trips/{tid}', headers=bob).status_code==404)
            check(category, 'Anonymous cannot read export',req('GET', '/api/my/export').status_code==401)
            check(category, 'Anonymous cannot read admin dashboard',req('GET', '/api/admin/overview').status_code in (403, 503))
            check(category, 'Fake staff token denied',req('GET', '/api/admin/overview', headers={'X-Admin-Key':'bad'}).status_code==403)
            check(category, 'Owner retains trip after access probes',req('GET',f'/api/my/trips/{tid}',headers=alice).status_code==200)

            category = 'Concurrent / stale writes'
            version = req('GET',f'/api/my/trips/{tid}',headers=alice).json()['updated_at']
            def compete(i):
                body={'title':f'Concurrent edit {i}', 'itinerary':plan.json()}
                return req('PUT',f'/api/my/trips/{tid}',headers={**alice, 'If-Match':version},json=body).status_code
            with ThreadPoolExecutor(max_workers=10) as pool:
                results=list(pool.map(compete,range(10)))
            check(category, '10 simultaneous writes: exactly one wins and others conflict', results.count(200)==1 and results.count(409)==9, str(results))
            updated=req('GET',f'/api/my/trips/{tid}',headers=alice)
            check(category, 'No duplicate trip after update collision',updated.status_code==200 and len(req('GET','/api/my/trips',headers=alice).json()['trips'])==1)
            check(category, 'If-Match stale replay rejected',req('PUT',f'/api/my/trips/{tid}',headers={**alice,'If-Match':version},json=data).status_code==409)

            category='Malformed input / abuse resistance'
            malformed=req('POST','/api/plan',data='{invalid-json',headers={'Content-Type':'application/json'})
            check(category, 'Malformed JSON rejected without server failure',malformed.status_code==422,str(malformed.status_code))
            oversized = req('POST','/api/chat',data=b'X'*(550*1024),headers={'Content-Type':'application/json'})
            check(category,'Body above 512 KiB rejected',oversized.status_code==413, str(oversized.status_code))
            streamed=req('POST','/api/chat',data=(b'Z'*8192 for _ in range(68)),headers={'Content-Type':'application/json'})
            check(category,'Streaming body above limit rejected',streamed.status_code==413,str(streamed.status_code))
            malicious = [
                {'cities':['Cairo'], 'days':0},
                {'cities':['Cairo'], 'days':31},
                {'cities':['Cairo','Luxor'], 'days':1},
                {'cities':['Cairo'], 'days':'NaN'},
                {'cities':['<script>alert(1)</script>'], 'days':3},
                {'cities':[], 'days':3},
                {'cities':['Cairo'], 'days':1,'pace':'rocket'},
                {'cities':['Cairo'], 'days':1,'budget_usd':-100},
            ]
            responses=[post('/api/plan', v).status_code for v in malicious]
            check(category,'8 invalid planner variants safely rejected',all(c==422 for c in responses),str(responses))
            poor_trip={'title':'Harmful plan','itinerary':{'days':[{'day':1,'city':'Cairo','stops':[], 'travel':{'from_city':'Luxor','minutes':-5}}]}}
            check(category,'Negative travel duration cannot be persisted',post('/api/my/trips',poor_trip,headers=alice).status_code==422)
            check(category,'Bad input leaves storage usable',req('GET','/api/ready').status_code==200)

            category='Rate limiting / spoofed headers'
            attempts=[post('/api/auth/login',{'email':'nonstandard-alice@example.com','password':'incorrect-password-123'},
                           headers={'X-Forwarded-For':f'198.51.100.{i}','X-Real-IP':f'203.0.113.{i}'}).status_code
                      for i in range(7)]
            check(category,'Brute-force attempts throttled despite spoofed client headers',
                  attempts[:5]==[401]*5 and attempts[5:]==[429]*2, str(attempts))

            category='Browser/API boundary'
            r=req('GET','/api/auth/me',headers=alice)
            check(category,'Sensitive endpoint no-store',r.headers.get('Cache-Control')=='no-store')
            check(category,'No MIME sniffing',r.headers.get('X-Content-Type-Options')=='nosniff')
            check(category,'Clickjacking response header',r.headers.get('X-Frame-Options')=='DENY')
            untrusted=req('GET','/api/health',headers={'Origin':'https://untrusted.example'})
            check(category,'Untrusted CORS origin denied',not untrusted.headers.get('Access-Control-Allow-Origin'))
            accepted=req('GET','/api/health',headers={'Origin':'http://localhost:5173'})
            check(category,'Development-origin CORS accepted',accepted.headers.get('Access-Control-Allow-Origin')=='http://localhost:5173')

            category='Partner URL safety'
            admin={'X-Admin-Key': env['ADMIN_API_TOKEN']}
            template={'title':'Affiliate local QA','city':'Cairo','description':'Sample partner description for QA',
                      'partner':'QA Partner','disclosure':'External provider disclosure', 'enabled':False}
            unsafe=['http://example.com/book','https://127.0.0.1/book','https://localhost/book','https://user:pass@example.com/book']
            statuses=[post('/api/admin/offers',{**template,'target_url':url},headers=admin).status_code for url in unsafe]
            check(category,'4 unsafe partner targets rejected',statuses==[422]*4,str(statuses))
            check(category,'Public offer redirects unknown ID safely',req('GET','/api/go/qa-missing-offer',allow_redirects=False).status_code==404)

            category='Randomized planner properties'
            rng=random.Random(20261017)
            cities=['Cairo','Giza','Luxor','Aswan','Alexandria','Hurghada','Sharm El Sheikh']
            test_runs=90
            errors=[]
            for i in range(test_runs):
                n=rng.randint(1, min(5,len(cities)))
                selection=rng.sample(cities,n)
                days=rng.randint(n,30)
                payload={'cities':selection,'days':days, 'family':bool(i%2),
                         'pace':rng.choice(['relaxed','balanced','packed']),
                         'language':rng.choice(['en','ar']), 'optimize_route':bool(i%3)}
                try:
                    response=post('/api/plan',payload)
                    if response.status_code!=200:
                        errors.append(f'{i}:HTTP {response.status_code} {response.text[:100]}')
                        continue
                    value=response.json()
                    outdays=value['days']
                    actual=[d['city'] for d in outdays]
                    visits=[s['place']['id'] for d in outdays for s in d['stops']]
                    valid=(len(outdays)==days and [d['day'] for d in outdays]==list(range(1,days+1))
                           and len(set(visits))==len(visits)
                           and set(actual)==set(selection)
                           and all(actual.count(c)==value['day_allocation'][c] for c in selection)
                           and all(not d.get('travel') or d['travel']['minutes']>=0 for d in outdays))
                    if not valid:errors.append(f'{i}:invariant violation')
                except Exception as exc:
                    errors.append(f'{i}:{exc}')
            check(category, f'{test_runs} deterministic randomized itineraries preserve invariants',not errors, '; '.join(errors[:8]))

            category='Local HTTP load (not an internet-scale benchmark)'
            total=140
            def bench(i):
                path='/api/places' if i%3 else '/api/cities'
                start=time.perf_counter()
                try:
                    r=req('GET',path)
                    return r.status_code,time.perf_counter()-start
                except requests.RequestException:
                    return -1,time.perf_counter()-start
            with ThreadPoolExecutor(max_workers=16) as pool:
                measurements=list(pool.map(bench,range(total)))
            statuses=[s for s,_ in measurements]
            lat=sorted(t*1000 for _,t in measurements)
            p95=lat[max(0,int(total*.95)-1)]
            check(category, f'{total} requests / 16 workers complete without HTTP errors',all(s==200 for s in statuses),str({s:statuses.count(s) for s in set(statuses)}))
            print(f'PERFORMANCE: count={total} p50={statistics.median(lat):.1f}ms p95={p95:.1f}ms max={max(lat):.1f}ms')
            # No arbitrary performance PASS threshold for unknown dev VM hardware.
            CASES.append({'category':category,'name':'Observed latency in dev environment',
                          'status':'MEASURED','detail':{'count':total,'concurrency':16,'p50_ms':round(statistics.median(lat),2),
                                                      'p95_ms':round(p95,2),'max_ms':round(max(lat),2)}})

            category='Credential revocation'
            check(category, 'Logout invalidates bearer',req('POST','/api/auth/logout',headers=bob).status_code==200 and req('GET','/api/auth/me',headers=bob).status_code==401)
            deletion=req('DELETE','/api/my/account', headers=alice,json={'password':'Alice-Long-Passphrase-2026!','confirmation':'DELETE MY ACCOUNT'})
            check(category,'Account erasure revokes token',deletion.status_code==200 and req('GET','/api/auth/me',headers=alice).status_code==401)
            # Inspect only our disposable QA database to verify a genuine cascade,
            # rather than mistaking a healthy readiness response for data erasure.
            import sqlite3
            from contextlib import closing
            with closing(sqlite3.connect(env['MASR_USER_DB'])) as db:
                persisted_trip_count = db.execute('SELECT COUNT(*) FROM account_trips').fetchone()[0]
                persisted_alice_count = db.execute("SELECT COUNT(*) FROM account_users WHERE email='nonstandard-alice@example.com'").fetchone()[0]
            check(category, 'Account deletion cascades to stored trips',
                  persisted_trip_count == 0 and persisted_alice_count == 0,
                  f'trips={persisted_trip_count}, deleted_user_count={persisted_alice_count}')

            category = 'Restart recovery / local SQLite persistence'
            charlie = post('/api/auth/register', {'email':'nonstandard-charlie@example.com',
                                                   'password':'Charlie-Long-Passphrase-2026!'})
            check(category, 'Account can be created before restart',charlie.status_code==201)
            saved_token=charlie.json()['token']
            charlie_auth={'Authorization':'Bearer '+saved_token}
            charlie_trip=post('/api/my/trips', data, headers=charlie_auth)
            check(category, 'Trip stored prior to server shutdown',charlie_trip.status_code==201)
            saved_trip_id=charlie_trip.json()['id']
        # Start a new Uvicorn process on a new port with the same disposable DB.
        with serve(env) as base:
            me=requests.get(base+'/api/auth/me', headers=charlie_auth, timeout=12)
            trip_back=requests.get(base+f'/api/my/trips/{saved_trip_id}', headers=charlie_auth, timeout=12)
            check('Restart recovery / local SQLite persistence',
                  'Session and saved trip survive one local process restart',
                  me.status_code==200 and trip_back.status_code==200 and
                  trip_back.json().get('itinerary',{}).get('days')==plan.json().get('days'),
                  f'account={me.status_code}, trip={trip_back.status_code}')
    passed=sum(case['status']=='PASS' for case in CASES)
    failed=sum(case['status']=='FAIL' for case in CASES)
    output = Path(os.getenv('MASR_EXTRA_QA_REPORT', str(ROOT/'qa_reports'/'qa_adversarial_extra_2026-10-17.json')))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'timestamp':datetime.now(timezone.utc).isoformat(),'results':CASES,
                                 'summary':{'pass':passed, 'fail':failed, 'measured':len(CASES)-passed-failed}},
                                indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'NONSTANDARD QA: {passed} PASS / {failed} FAIL; report={output}')
    return 1 if failed else 0


if __name__=='__main__':
    raise SystemExit(main())
