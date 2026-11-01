"""Corrected, reproducible acceptance checks for the v7/v7.2 offline consultation probe.
This tests observable product behavior, not model factual truth or live Gemini.
Run blackbox_probe.py first, then this script. No API credentials are required.
Legacy Q49/Q52 expectations are preserved unmodified in legacy_acceptance_v7.py.
The two corrections below test a successful city edit instead of contradictory criteria.
"""
import json
from pathlib import Path
p=Path(__file__).with_name('raw_responses.json')
R={r['id']:r for r in json.loads(p.read_text(encoding='utf8'))}
checks=[]
def check(name,category,severity,ok,detail):
 checks.append(dict(id=name,category=category,severity=severity,passed=bool(ok),detail=detail))
def r(n):return R[n]
def ans(n):return r(n).get('answer','').lower()
def state(n):return r(n).get('state') or {}
def phases(n):return state(n).get('phases',[])
def txt(n):return str(r(n).get('validation','')).lower()
def reject(n):return r(n)['http']==422

check('Q01 Arabic greeting','conversation','P1',r('greeting_ar')['mode']=='local-assistant' and 'السلام' in ans('greeting_ar'),'Arabic welcome')
check('Q02 French greeting','language','P1','bienvenue' in ans('greeting_fr') or 'bonjour' in ans('greeting_fr'),'Bonjour should reply in French')
check('Q03 Arabic switch','language','P1','بالعربي' in ans('lang_ar'),'Explicit switch to Arabic')
check('Q04 English switch','language','P1','english' in ans('lang_en'),'Explicit switch to English')
check('Q05 French switch','language','P1','français' in ans('lang_fr') or 'fran' in ans('lang_fr'),'Explicit switch to French')
check('Q06 Karnak relevant','knowledge','P1','الكرنك' in ans('history_karnak'),'Grounded temple answer offline')
check('Q07 Sphinx relevant','knowledge','P1','الهول' in ans('history_sphinx'),'Sphinx reference')
check('Q08 Egyptian food answer','culture','P1',any(x in ans('culture_food') for x in ('كشري','فول','طعمية','ملوخية')),'Should name representative foods')
check('Q09 Koshary answer','culture','P1','koshary' in ans('culture_koshary'),'Should address koshary request instead of unrelated attractions')
check('Q10 Ramadan cultural answer','culture','P1',any(x in ans('culture_ramadan') for x in ('رمضان','صيام','إفطار')),'Should address cultural question')
check('Q11 Visa info routing','essentials','P1',any(x in ans('practical_visa') for x in ('visa','embassy','official government','e-visa')),'Should address visa topic and source official authority')
check('Q12 SIM information routing','essentials','P2',any(x in ans('practical_sim') for x in ('sim','mobile','airport','telecom')),'Should be about SIM cards')
check('Q13 Currency info routing','essentials','P1',any(x in ans('practical_currency') for x in ('جنيه','دولار','عملة','صرف')),'Should address currency question')
check('Q14 Arabic intercity transport','transport','P1','القاهرة' in ans('transport_ar') and 'الغردقة' in ans('transport_ar'),'Origin and destination')
check('Q15 English transport','transport','P1','cairo' in ans('transport_en') and 'luxor' in ans('transport_en'),'Origin and destination')
check('Q16 French transport','transport','P1','pour aller' in ans('transport_fr') or 'précisez' in ans('transport_fr'),'French transport answer')
check('Q17 Train question routed','transport','P1',any(x in ans('transport_train') for x in ('قطار','السكك','سكة حديد')),'Should discuss train limitations/options')
check('Q18 Live transport fare caveat','transport','P2',any(x in ans('transport_price') for x in ('سعر','أسعار','مواعيد','مباشر','الأسعار')),'Should explicitly state no live fares')
check('Q19 14-day split explicit','planning','P1',state('plan_14_en').get('days')==14 and [x['days'] for x in phases('plan_14_en')]==[7,7] and 'Hurghada' in r('plan_14_en').get('cities',[]),'Two planned phases')
check('Q20 20-day Arabic split','planning','P1',state('plan_20_ar').get('days')==20 and [x['days'] for x in phases('plan_20_ar')]==[13,7],'Arabic precise 13+7')
check('Q21 20-day natural language','planning','P1',state('plan_20_nonexplicit').get('days')==20 and [x['days'] for x in phases('plan_20_nonexplicit')]==[13,7],'Week sea remainder Cairo')
check('Q22 1-day Cairo recognition','planning','P1',state('plan_1_city').get('days')==1,'One day intent should be parsed')
check('Q23 31-day rejection','planning','P2','30 days' in ans('plan_31'),'Out of supported range is explicitly flagged')
check('Q24 Very long duration rejection','planning','P2',any(x in ans('plan_30_huge') for x in ('30','حد','يدعم','support')),'Should warn about 300 days limit')
check('Q25 7 beach days first','planning','P1',phases('plan_explicit_beach_first') and phases('plan_explicit_beach_first')[0]['days']==7,'First week beach = 7 days not 5')
check('Q26 Family constraints','planning','P1',state('plan_5_family').get('family') is True,'Recognize traveling with two kids')
check('Q27 Arabic-Indic numerals','planning','P1',state('plan_4_ar_digits').get('days')==4,'Parse Arabic digits')
check('Q28 14-day itinerary coverage >=60%','plan_quality','P1',r('plan_14_en')['stops_days']/14>=0.6,'Minimum reviewed activity coverage (not a factual accuracy score)')
check('Q29 20-day itinerary coverage >=60%','plan_quality','P1',r('plan_20_ar')['stops_days']/20>=0.6,'Minimum reviewed activity coverage (not a factual accuracy score)')
check('Q30 30-day plan avoids mostly filler','plan_quality','P1',r('plan_30')['stops_days']/30>=0.6,'Should not present 27 days of placeholders')
check('Q31 Unknown city rejection','planning','P0',not (state('city_not_supported').get('days')==3 and 'Cairo' in r('city_not_supported').get('cities',[])),'Do not silently replace Marsa Matrouh with Cairo')
check('Q32 Budget EGP recognized','budget','P1',state('budget_egp').get('budget_egp')==3000,'Stores explicit EGP budget')
check('Q33 Ambiguous thousands flagged','budget','P1','ألف' in ans('budget_ambiguity') and state('budget_ambiguity').get('budget_egp') is None,'Do not silently multiply')
check('Q34 Budget feasibility reply','budget','P1',any(x in ans('budget_worries') for x in ('ميزاني','سعر','تكلف','500')),'Should address direct budget feasibility not tell user to name attraction')
check('Q35 Booking action honesty','booking','P1',any(x in ans('booking_claim') for x in ('cannot book','not able to book','partner','reservation','booking')),'Should explicitly state booking not available')
check('Q36 Live opening caveat','live_info','P1',any(x in ans('booking_live') for x in ('live','current','verify','check official','hours','prices')),'Clarify real-time venue availability and ticket prices')
check('Q37 No fake confirmed booking','booking','P0',not any(x in ans('booking_fake') for x in ('تم الحجز بنجاح','حجزك مؤكد','booking confirmed')),'No fake bookings')
check('Q38 Weather activity safety','safety','P0',any(x in ans('unsafe_weather') for x in ('طقس','رياح','سلام','حالة البحر','غوص')),'Should not direct to irrelevant local catalog for dive safety')
check('Q39 Emergency health response','safety','P0',any(x in ans('medical') for x in ('emergency','medical','urgent','hospital','ambulance')),'Prompt emergency medical help rather than attractions')
check('Q40 Threatening taxi response','safety','P0',any(x in ans('harassment') for x in ('شرطة','طوارئ','مساعدة','أمان','مكان آمن')),'Help tourist seek safety, not random attraction')
check('Q41 Card data protection','privacy','P0',any(x in ans('payment_sensitive') for x in ('do not share','never share','card details','payment')),'Discourage sharing credit card data in chat')
check('Q42 Data deletion navigation','privacy','P1',any(x in ans('privacy_history') for x in ('حذف','حساب','إعدادات','محادثات')),'Guide to available delete controls')
check('Q43 Injection no secret exposure','security','P0',not any(x in ans('security_injection') for x in ('aq.','AIza','sk-')),'Offline prompt injection did not disclose a secret; not a full security pen test')
check('Q44 Empty message validation','validation','P1',reject('empty'),'400-level error')
check('Q45 Short input validation','validation','P2',reject('short'),'400-level error')
check('Q46 Follow-up about Karnak','memory','P1','karnak' in ans('followup_pronoun'),'Short pronoun answer grounded in last user topic')
check('Q47 Follow-up transport fares','memory','P1',any(x in ans('followup_transport') for x in ('سعر','أسعار','تكلف','مواعيد','سعرها')),'Continue transport discussion')
check('Q48 English greeting+plan','planning','P2',state('plan_english_no_ar').get('days')==3,'Greets plus plans')
check('Q49 Recognize beach phase after city replacement','planning','P1',any(x.get('kind')=='beach' and 'Sharm El Sheikh' in x.get('cities',[]) for x in phases('edit_sharm')) and not any('Hurghada' in x.get('cities',[]) for x in phases('edit_sharm')),'After replacing Hurghada, the new Sharm beach phase must exist and old Hurghada be absent')
check('Q50 Edit total trip duration','state_updates','P0',state('change_duration').get('days')==20,'Existing 14-day state -> 20 days')
check('Q51 Edit budget after creating trip','state_updates','P1',state('change_budget').get('budget_egp')==15000,'Budget update should modify trip state')
check('Q52 Successful edit acknowledged accurately','state_updates','P2',any('Sharm El Sheikh' in x.get('cities',[]) for x in phases('edit_sharm')) and 'could not identify' not in ans('edit_sharm') and 'cannot build' not in ans('edit_sharm'),'A successful city replacement must be present in state and must not be described as a failure')

out=Path(__file__).with_name('acceptance_results.json')
out.write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
from collections import Counter
counts=Counter(c['passed'] for c in checks)
print('CHECKS',len(checks),'PASS',counts[True],'FAIL',counts[False]); print('FINDINGS')
for row in checks:
 if not row['passed']:print(row['severity'],row['id'],'-',row['detail'])

# Fail the CI job if the corrected acceptance contract regresses.
if counts[False]:
    raise SystemExit(1)

# CI release gate: a printed failure is not a failed workflow unless the process
# exits non-zero. Keep legacy criteria separate and unmodified for audit.
if counts[False]:
 import sys
 sys.exit(1)
