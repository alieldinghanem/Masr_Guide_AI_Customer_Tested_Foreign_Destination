"""Deterministic independent planner invariant check (1500 seeded cases, 12 invariants each)."""
import os, random, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from app.catalog import INTERESTS
from app.database import initialize, all_places
from app.planner import build_plan, PACE_LIMITS
from app.schemas import PlanRequest

rng=random.Random(20261011)
with tempfile.TemporaryDirectory() as directory:
    os.environ['DATABASE_PATH'] = str(Path(directory)/'qa.sqlite')
    initialize()
    catalog=all_places()
    names=sorted({p['city'] for p in catalog})
    interest_list=list(INTERESTS)
    for i in range(1500):
        n=rng.randint(1, min(7,len(names)))
        destinations=rng.sample(names,n)
        days=rng.randint(n,14)
        family=rng.choice((False,True))
        pace=rng.choice(list(PACE_LIMITS))
        optimize=rng.choice((False,True))
        lang=rng.choice(('en','ar'))
        request=PlanRequest(cities=destinations,days=days,
                            interests=rng.sample(interest_list,rng.randint(0,len(interest_list))),
                            pace=pace,family=family,optimize_route=optimize,language=lang)
        result=build_plan(request)
        actual=[d['city'] for d in result['days']]
        order=result['route']
        expected=[name for name in order for _ in range(result['day_allocation'][name])]
        assert len(actual)==days, (i,'day count')
        assert actual == expected, (i,'city sequencing')
        assert sum(result['day_allocation'].values())==days, (i,'allocation total')
        assert all(d['estimated_activity_minutes']<=PACE_LIMITS[pace] for d in result['days']), (i,'time cap')
        stops=[s['place'] for d in result['days'] for s in d['stops']]
        assert len(stops)==len({p['id'] for p in stops})==result['total_places'], (i,'unique stops')
        assert all(p['city']==d['city'] for d in result['days'] for p in (s['place'] for s in d['stops'])), (i,'correct city')
        assert not family or all(p['family_friendly'] for p in stops), (i,'family rule')
        assert all(d['day']==idx+1 for idx,d in enumerate(result['days'])),(i,'day labels')
        # --- v1.7: travel, route optimisation, localisation ---
        limit=PACE_LIMITS[pace]
        assert all(d['estimated_activity_minutes']+d['estimated_travel_minutes']<=max(limit,d['estimated_travel_minutes']) for d in result['days']), (i,'travel+activity budget')
        prev=None
        for d in result['days']:
            changed = prev is not None and prev != d['city']
            assert (d['travel'] is not None) == changed, (i,'travel only on city change')
            assert d['estimated_travel_minutes'] == (d['travel']['minutes'] if d['travel'] else 0), (i,'travel minutes field')
            prev=d['city']
        assert result['total_travel_minutes']==sum(d['estimated_travel_minutes'] for d in result['days']), (i,'travel total')
        assert set(order)==set(destinations) and order[0]==destinations[0] and len(order)==n, (i,'route is a permutation, start fixed')
        if optimize:
            base=build_plan(request.model_copy(update={'optimize_route':False}))
            assert result['total_travel_minutes']<=base['total_travel_minutes'], (i,'optimised route not worse')
        if lang=='ar':
            assert any('\u0600'<=ch<='\u06ff' for ch in result['disclaimer']), (i,'arabic disclaimer')
print('PASS 1500 seeded itineraries x 12 invariants = 18000 verified assertions')
