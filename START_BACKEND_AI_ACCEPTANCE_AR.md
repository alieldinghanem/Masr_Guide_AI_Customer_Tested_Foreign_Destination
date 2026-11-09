# Masr Guide AI — Backend + AI / Release acceptance

## ماذا تم بالفعل؟
- أبقينا FastAPI وGemini 2.5 Flash مع Google Search Grounding وRAG والمخطط الحتمي؛ واحتفظنا بـOpenAI كمزوّد اختياري.
- أصلحنا عودة `/api/chat` بخطأ 502 عند توقف مزود AI: المسار يرجع الآن مرجعًا محليًا واضحًا بحالة `offline-fallback` من دون اختلاق أسعار أو القول إن البحث جرى.
- جعلنا استدعاء OpenAI في وضع `AI_PROVIDER=auto` يستخدم نفس المهايئ الذي يضبط `store=False`، بدل مسار قديم قد يرسل طلبًا دون هذا الإعداد.
- حدّثنا التعليمات حتى يسمح Google Search Grounding باستخدام مصادر ويب حقيقية للمعلومات المتغيرة، مع الإبقاء على قيود الحقائق التاريخية.
- أضفنا اختبارات لأعطال المزود والـGrounding والتصنيف الصادق ومراجع البحث. أضفنا فحص عميل عبر HTTP فعلي وملف اختبار حي لا يشارك الأسرار.

## النتائج في بيئة العمل بتاريخ 30 أكتوبر 2026
- `python -m pytest -q` داخل `backend`: **332/332 PASS** بعد التعديلات.
- تشغيل Uvicorn على loopback محلي مع قواعد بيانات مؤقتة: **13/13 PASS** في رحلة عميل شملت الترشيح وتعديل الرحلة والحساب والحفظ والاسترجاع وتسجيل الخروج.
- Gemini + Google Search الحقيقي: **BLOCKED** (لم يُعثر على `GEMINI_API_KEY` في بيئة التنفيذ). اختبارات Google Search البرمجية تستخدم ردودًا محاكية ولا تثبت الدقة الحية.
- React Build ومتصفح E2E والاستضافة العامة والتخزين طويل الأمد: **NOT VERIFIED** في هذه الجولة.

## التشغيل المحلي الآمن على Windows
1. فك المشروع، افتح PowerShell من `Masr_Guide_AI`.
2. أنشئ `backend/.env` من `backend/.env.example` وأدخل المفتاح محليًا فقط، ولا تشاركه مع الفريق أو GitHub.
3. استخدم:

```dotenv
APP_ENV=development
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
GEMINI_SEARCH_GROUNDING=true
GEMINI_API_KEY=YOUR_SECRET_KEY
```

4. نفّذ:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m pytest -q
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

5. في نافذة ثانية، من جذر المشروع:

```powershell
python backend/scripts/run_customer_live_acceptance.py --base-url http://127.0.0.1:8000
```

أو اضغط `TEST_REAL_CHAT_ON_SERVER_WINDOWS.bat` بعد تشغيل السيرفر. الأداة تختبر 3 أسئلة عامة فقط دون بيانات مستخدمين، وتخرج `BLOCKED` إذا لم يكن Gemini+Search معدًا، و`FAIL` عند فشل المزود أو غياب مراجع الويب. تحفظ نصوص الإجابات والمراجع في `qa_reports/live_customer_acceptance.json` لمراجعة دقتها يدويًا؛ **نجاح وجود المراجع ليس ضمانًا لصحة كل ادعاء في الإجابة**.

## قبل فتحه للعملاء
- تأكد من نتيجة **PASS_SOURCE_BACKED_ONLY** على الجهاز المستهدف، ثم راجع الإجابات بالعربية والإنجليزية يدويًا وتأكد أن كل معلومة تستند للمصدر الموافق لها.
- لا تُدخل بيانات شخصية أو حجوزات حساسة في الفئة المجانية دون تقييم الخصوصية وموافقة المستخدم المناسبة؛ راجع سياسة معالجة البيانات لدى مزود النموذج.
- أخضع النظام لاختبارات browser/UI إن كانت الواجهة ستُنشر، واختبر العزل بين المستخدمين، والمراقبة، وحدود الحصص، ومخطط النسخ الاحتياطي والاستعادة.
- لا تعلن عن حجوزات أو أسعار مباشرة دون عقد/API موثوق مع مشغّلي الخدمات.
- في نشر شركة حقيقي استخدم تخزينًا دائمًا مُختبر الاستعادة، وحدود استخدام على الـEdge وربط مراقبة للمزود؛ ملف `APP_ENV=production` يفرض بعض ضوابط التهيئة لكنه لا يثبت جاهزية البنية التحتية.

**قرار الإطلاق الحالي: TECHNICAL PREVIEW ONLY / COMMERCIAL RELEASE BLOCKED.**
