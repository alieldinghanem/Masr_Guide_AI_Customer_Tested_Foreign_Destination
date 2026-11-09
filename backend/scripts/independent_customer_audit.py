"""Offline customer E2E HTTP smoke: requires running backend with isolated storage.

Usage: python backend/scripts/independent_customer_audit.py --base-url http://127.0.0.1:18843
Never contacts a model provider and never uses real account data.
"""
import argparse
import json
from pathlib import Path
import requests
from uuid import uuid4
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:18843')
    parser.add_argument('--report', default=None)
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    session = requests.Session()
    checks = []

    def check(name, condition, details=None):
        checks.append({'name': name, 'passed': bool(condition), 'details': details})
        print(('PASS' if condition else 'FAIL'), name)
        return condition

    def post(route, **kwargs):
        response = session.post(base+route, timeout=20, **kwargs)
        return response, response.json()

    health = session.get(base+'/api/health', timeout=10)
    check('health and offline mode', health.status_code == 200 and health.json().get('guide_mode') == 'offline-preview')
    ready = session.get(base+'/api/ready', timeout=10)
    check('database readiness', ready.status_code == 200)
    resp, week = post('/api/consult', json={'message': 'أنا جاي مصر أسبوع مع مراتي وطفلين وعايز القاهرة والأقصر والغردقة'})
    week_state = week.get('trip_state') or {}
    check('Arabic family 7-day plan', resp.status_code == 200 and week_state.get('days') == 7 and len((week.get('itinerary') or {}).get('days',[])) == 7)
    check('7-day sum', sum(x.get('days', 0) for x in week_state.get('phases',[])) == 7)
    resp, month = post('/api/consult', json={'message': 'أنا جاي مصر شهر مع أسرتي وعايز القاهرة والأقصر وأسوان والغردقة'})
    month_state = month.get('trip_state') or {}
    check('Arabic 30-day plan', resp.status_code == 200 and month_state.get('days') == 30 and len((month.get('itinerary') or {}).get('days',[])) == 30)
    check('30-day no place repeats', len([s['place']['id'] for d in month['itinerary']['days'] for s in d['stops']]) == len(set(s['place']['id'] for d in month['itinerary']['days'] for s in d['stops'])))
    resp, month_edit = post('/api/consult', json={'message': 'غير التوزيع: 8 أيام القاهرة و5 أيام الأقصر و7 أيام أسوان و10 أيام الغردقة', 'trip_state': month_state})
    edited = month_edit.get('trip_state') or {}
    check('exact 30-day reallocation', resp.status_code == 200 and [p['days'] for p in edited.get('phases', [])] == [8,5,7,10])
    check('30 day stays 30', len((month_edit.get('itinerary') or {}).get('days',[])) == 30)
    resp, hotel = post('/api/consult', json={'message': 'رشحلي فندق قريب من الأهرامات', 'trip_state': edited})
    check('hotel question does not change trip', resp.status_code == 200 and (hotel.get('trip_state') or {}).get('days') == 30)
    resp, airport = post('/api/chat', json={'message':'How can I reach Zamalek from Cairo Airport at night?', 'language':'English'})
    check('English transport assistance', resp.status_code == 200 and 'zamalek' in airport.get('answer','').lower())
    resp, payment = post('/api/chat', json={'message':'Can I give you my credit card details so you can book a hotel?', 'language':'English'})
    check('no payment data acceptance', resp.status_code == 200 and 'card' in payment.get('answer','').lower())
    resp, save_unauth = post('/api/consult', json={'message':'احفظ الرحلة في حسابي','trip_state': edited})
    check('save without login is not claimed', resp.status_code == 200 and save_unauth.get('mode') == 'needs-authentication')
    email = 'audit-' + uuid4().hex[:10]+'@example.com'
    resp, reg = post('/api/auth/register', json={'email':email, 'password':'LocalAuditOnlyPassword42!'})
    check('register temporary account', resp.status_code == 201 and reg.get('token') is not None, str(resp.status_code))
    token = reg.get('token')
    if token:
        h = {'Authorization': 'Bearer ' + token}
        resp, saved = post('/api/consult', json={'message':'احفظ الرحلة في حسابي','trip_state': edited}, headers=h)
        trip_id = saved.get('saved_trip_id')
        check('authenticated chat writes actual trip', resp.status_code == 200 and saved.get('mode') == 'trip-saved' and bool(trip_id))
        trips = session.get(base+'/api/my/trips',headers=h, timeout=10)
        check('saved trip is retrievable', trips.status_code == 200 and trip_id in [x['id'] for x in trips.json()['trips']])
        second_email = 'audit-' + uuid4().hex[:10]+'@example.com'
        resp, second = post('/api/auth/register', json={'email':second_email, 'password':'LocalAuditOnlyPassword42!'})
        other = session.get(base+'/api/my/trips/'+trip_id, headers={'Authorization':'Bearer '+second['token']}, timeout=10) if second.get('token') and trip_id else None
        check('cross-account isolation', other is not None and other.status_code == 404)
        logout = session.post(base+'/api/auth/logout', headers=h,timeout=10)
        rejected = session.get(base+'/api/my/trips',headers=h,timeout=10)
        check('logout invalidates token', logout.status_code==200 and rejected.status_code==401)
    report={'run_utc':datetime.now(timezone.utc).isoformat(),'mode':'offline only','results':checks,'passed':sum(r['passed'] for r in checks),'total':len(checks)}
    if args.report:
        target=Path(args.report);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('SUMMARY',report['passed'],'/',report['total'])
    return 0 if report['passed'] == report['total'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
