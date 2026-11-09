# Masr Guide AI v2.1 — ابدأ من هنا

المشروع فيه واجهتين لنفس الـBackend: **React Frontend** الأساسية، و**Free Quick Demo** تعمل بدون Node.js أو npm. المحادثة تقدر تنشئ رحلة فعلية من 1 إلى 30 يومًا وتعدلها. مرشد Gemini اختياري ويستخدم Free Tier إذا كان متاحًا لحسابك.

## أسرع تشغيل على Windows — بدون Node.js

1. ثبّت Python 3.10 أو أحدث وفك ضغط الملف.
2. شغّل `RUN_FREE_DEMO_WINDOWS.bat` من جذر المشروع.
3. افتح `http://localhost:8000/demo`.
4. اطلب: **I am visiting Egypt for two weeks, first week history in Cairo and Luxor, second week beaches in Hurghada**.
5. عدّل الخطة بالرسالة: **Replace Hurghada with Sharm El Sheikh**.

الـPlanner بدون مفتاح API يعتمد على قواعد وكتالوج محلي؛ **ليس نموذج ذكاء اصطناعي توليديًا**. أما أسئلة المرشد التوليدية فتحتاج مفتاح Gemini.

## تفعيل Gemini Flash (اختياري)

- افتح https://aistudio.google.com/apikey وأنشئ مفتاحًا لمشروع Free Tier إن كان متاحًا.
- انسخ `backend/.env.example` إلى `backend/.env` وضع `GEMINI_API_KEY=...` داخله، ولا تشارك المفتاح.
- أعد تشغيل الـBackend وجرب سؤالاً عن الأهرامات وسؤالاً لتخطيط رحلة.
- **Google لديها حدود استخدام مجانية؛ تحقق من الحصة ونوع الفوترة في AI Studio. لا تفعل مشروع مدفوعًا إن كنت لا تريد رسومًا.**
- عند انقطاع Gemini، إنشاء الرحلة يُحاول العودة إلى مخطط محلي. الإجابات المفتوحة التوليدية تحتاج الاتصال بالمزود.

## الواجهة الرئيسية React

شغّل `RUN_BACKEND_WINDOWS.bat` ثم `RUN_FRONTEND_WINDOWS.bat`، وافتح `http://localhost:5173`. لأول مرة يلزم اتصال لتنزيل مكتبات npm. الـDemo السريعة تعمل بدون npm.

## أوامر الاختبار

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

الاختبارات لا تثبت اتصال Gemini الحي. المشروع ما زال MVP تجريبيًا، بدون أسعار أو حجوزات فورية أو تشغيل حجز فنادق، وتقديرات الطريق تقريبية.

## ما لا يجب ادعاؤه

لا تصف النظام كأنه يحجز فنادق أو يضمن الوقت أو السعر أو الأمان أو يعلم بمواعيد التشغيل اللحظية. القاعدة 40 مكانًا فقط في مصر، والبيانات تحتاج توسعًا وتحديثًا قبل إطلاق Startup عام. لا تنشر صورًا دون تدقيق الرخص والملكية.

## إعداد Gemini بأسهل طريقة على Windows

1. افتح https://aistudio.google.com/apikey وسجل الدخول بحساب Google الخاص بك، وأنشئ API Key على Free Tier إذا كان متاحًا.
2. شغّل `SETUP_GEMINI_WINDOWS.bat` من جذر المشروع.
3. الصق المفتاح في الإدخال المخفي. السكربت يحفظه في `backend/.env` محليًا ويفحص الاتصال الحقيقي بـGemini.
4. عند ظهور `[PASS]`، شغّل `RUN_FREE_DEMO_WINDOWS.bat` وجرّب المرشد.

لا تُرسل المفتاح بالبريد أو المحادثة، ولا ترفع ملف `.env` إلى GitHub. وجود مفتاح لا يضمن مجانية الاستخدام إلى الأبد؛ راقب حدود الحصة في Google AI Studio.
