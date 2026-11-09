import os,sys,json
from unittest.mock import patch
os.environ.pop('GEMINI_API_KEY',None);os.environ.pop('OPENAI_API_KEY',None);os.environ['CHAT_RATE_LIMIT_PER_MINUTE']='999'
sys.path.insert(0,'/mnt/data/masr_v7_verify/Masr_Guide_AI/backend')
from fastapi.testclient import TestClient
from app.main import app
cases=[
('intent_correct','Plan a 14 day trip: 7 history days in Cairo and Luxor, 7 days at the sea',{'action':'plan','days':14,'history':True,'beach':True,'city_preferences':['Cairo','Luxor','Hurghada']}),
('intent_wrong_boolean','Plan 10 days in Cairo',{'action':'plan','days':True,'history':'false','beach':'true','city_preferences':'Luxor'}),
('intent_unknown_city','Plan 10 days in Marsa Matrouh',{'action':'plan','days':10,'history':False,'beach':False,'city_preferences':['Marsa Matrouh']}),
('intent_untrusted_action','What is the weather in Egypt?',{'action':'edit','days':14,'replace_from':'Cairo','replace_to':'Luxor'}),
('intent_malformed_prefs','Plan 5 days Cairo',{'action':'plan','days':5,'history':True,'beach':False,'city_preferences':[123,False,None]}),
('intent_bad_response','Plan 3 days Cairo',{'action':'plan','days':'three','history':True,'beach':False,'city_preferences':[]}),
('intent_json_null','Plan 3 days Cairo',{'action':'plan','days':None,'history':True,'beach':False,'city_preferences':[]}),
('intent_empty','Plan 3 days Cairo',{}),
('intent_big_days','Plan 10 days Cairo',{'action':'plan','days':99999,'history':False,'beach':False,'city_preferences':['Cairo']}),
]
with patch('app.travel_agent.gemini_key', return_value='STUB_NO_REAL_KEY'):
 with TestClient(app) as client:
  for name,prompt,hint in cases:
   with patch('app.travel_agent.generate',return_value=json.dumps(hint,ensure_ascii=False)):
    try:
     r=client.post('/api/consult',json={'message':prompt})
     d=r.json()
     print(name,r.status_code,d.get('mode','<none>'),str(d.get('answer',d.get('detail','')))[:200].replace('\n',' | '))
    except Exception as exc:
     print(name,'UNHANDLED_EXCEPTION',type(exc).__name__,str(exc)[:170])
