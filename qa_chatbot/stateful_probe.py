import os,sys
from pathlib import Path
os.environ['GEMINI_API_KEY']='';os.environ['OPENAI_API_KEY']='';os.environ['CHAT_RATE_LIMIT_PER_MINUTE']='999'
sys.path.insert(0,str(Path(os.environ.get('MASR_BACKEND_DIR', str(Path(__file__).resolve().parent.parent / 'backend'))).resolve()))
from fastapi.testclient import TestClient
from app.main import app
journeys=[
('clear14','Plan a 14 day trip: first 7 days in Cairo and Luxor for history, second 7 days on Red Sea beaches in Hurghada',
['Replace Hurghada with Sharm El Sheikh','Add one more day in Luxor','Change to 20 days','My budget is 15000 EGP','I want to add Aswan']),
('clear20ar','عايز رحلة 20 يوم 13 يوم في القاهرة و7 أيام على البحر',
['بدل الغردقة بشرم الشيخ','زود يوم للأقصر','خلي الرحلة 15 يوم','ميزانيتي 15000 جنيه', 'خلينا نزود 3 أيام في القاهرة'])
]
with TestClient(app) as c:
 for journey,start,turns in journeys:
  print('\n###',journey)
  state=None
  for m in [start]+turns:
   r=c.post('/api/consult',json={'message':m,**({'trip_state':state} if state else {})})
   data=r.json()
   old=state
   if data.get('trip_state'): state=data['trip_state']
   print('\nQUESTION',m,'HTTP',r.status_code)
   print('NEW_STATE?', bool(data.get('trip_state')), 'ITIN?',bool(data.get('itinerary')),'MODE',data.get('mode'))
   print('STATE',state)
   print('ANSWER',data.get('answer','')[:200].replace('\n',' / '))
