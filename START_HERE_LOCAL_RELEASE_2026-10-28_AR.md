# Masr Guide AI — تسليم السورس الكامل للاختبار المحلي (28 أكتوبر 2026)

هذا أرشيف المشروع كاملًا، متفرع من آخر تسليم Gemini Chat يوم 28 أكتوبر، وليس مجرد Patch. لا تعتبره نشرًا إنتاجيًا معتمدًا، لأن React Build وChromium E2E وGemini Live لم يثبت نجاحها في بيئة الفحص.

## التشغيل المحلي على Windows

1. فك ضغط ZIP كاملًا في مجلد قصير مثل `C:\Projects\Masr_Guide_AI`، ولا تشغل الملفات من داخل ZIP.
2. ثبّت Python 3.12 وNode.js 22 LTS. افتح اتصال الإنترنت لتثبيت حزم React.
3. من المجلد الرئيسي شغّل `OPEN_WEBSITE_WINDOWS.bat`. الملف يجهز Python وnpm، يبني React، يشغّل API وVite ثم يتأكد من الاستجابات قبل فتح المتصفح.
4. فقط بعد ظهور `[READY]` افتح `http://127.0.0.1:5173/` على نفس جهاز Windows في Chrome أو Edge.
5. إذا تعطل الإعداد، راجع `.local-logs/npm-install.log` أو `.local-logs/frontend-build.log` أو `.local-logs/backend.log` قبل تكرار فتح الرابط.

### Gemini الحقيقي

- مفتاح Gemini غير موجود في الأرشيف، وهذا مقصود. اضبطه محليًا باستخدام `SETUP_GEMINI_WINDOWS.bat` داخل `backend/.env`، ولا ترسله في المحادثة أو ترفعه إلى GitHub.
- شغّل `TEST_GEMINI_CONVERSATION_WINDOWS.bat`؛ فهو يجرب ترشيح فندق، متابعة الميزانية، سؤال تاريخي بمصدر، وخطة 20 يومًا مع تعديل الوجهة. يستخدم اتصالًا حقيقيًا بالمزوّد؛ قد يستهلك الرصيد ويكتب تقريرًا مختصرًا في `qa_reports/gemini_live_dialogue_results.json`.
- اجعل `GEMINI_MODEL` صريحًا في `backend/.env` إذا كنت تريد تثبيت إصدار محدد؛ تحقّق من توافق النموذج وحصتك من توثيق Google الرسمي قبل الاستخدام. الوضع `offline-preview` ليس Gemini.

## تجربة قبول من طرف المستخدم

- افتح الصفحة الرئيسية، اكتشف المدن والمعالم، وجرّب عرض الموبايل والعربية RTL.
- من AI Guide اكتب: `رشح لي فندق في القاهرة قريب من الأهرامات` ثم `ميزانيتي 100 دولار في الليلة` ثم `هل مينا هاوس متاح الليلة؟`. يجب أن يعطي مصادر فندقية ولا يخترع السعر أو الحجز.
- جرّب: `خطط رحلة 20 يوم، 13 يوم القاهرة و7 أيام الغردقة` ثم `بدل الغردقة بشرم الشيخ`. يجب الحفاظ على 20 يومًا، 13/7، وعرض الأيام المحدّثة.
- جرّب إنشاء حساب وحفظ رحلة واسترجاعها وتسجيل الخروج، دون الاعتماد على تخزين المتصفح وحده.
- لا ترفع المشروع GitHub Public أو سيرفر إنتاج قبل نجاح اختبارات React وGemini وتثبيت البيانات الدائمة والمراجعة الأمنية والنشر.

## الاختبارات المشغّلة في بيئة التسليم

- Backend: 261/261 PASS.
- سياق التخطيط: 18,000/18,000 assertions PASS.
- Chat offline evaluation: 52/52 PASS.
- Frontend dependency-free data and mode contracts: 11/11 PASS.
- Windows launcher static/functional checks: 11/11 PASS.
- Live FastAPI smoke: 7/7 HTTP responses PASS (أربع مسارات GET وثلاث رسائل).
- Secret scanner: PASS.
- React production build / Vitest / ESLint: **BLOCKED** (تثبيت npm غير مكتمل في بيئة الاختبار).
- Browser Chromium: **BLOCKED** (`ERR_BLOCKED_BY_ADMINISTRATOR`).
- Real Gemini API: **NOT EXECUTED/BLOCKED** (لا يوجد GEMINI_API_KEY متاح هنا).
- Production deployment/backup recovery: **NOT EXECUTED** في الجولة الحالية.

توجد سجلات التشغيل ضمن `qa_reports/local_release_2026_10_28/`. اجتياز الاختبارات التنفيذية لا يعني أن جميع وظائف المنتج التجارية مكتملة، ولا يوجد نظام مباشر لأسعار الفنادق أو الحجز.
