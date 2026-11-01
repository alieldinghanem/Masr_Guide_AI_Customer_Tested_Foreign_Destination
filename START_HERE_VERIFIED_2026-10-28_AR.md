# Masr Guide AI — ملف التسليم الموحّد للتجربة المحلية

**تاريخ إعادة المراجعة: 28 أكتوبر 2026.** هذا هو سورس التطبيق الكامل (React/Vite + FastAPI + تخطيط رحلات + حسابات ومفضلة + CMS وشركاء + تقييمات واختبارات)، مبني على آخر أرشيف Advanced QA من المحادثة السابقة، وليس رابطًا منشورًا على الإنترنت. **لم تثبت جاهزية الإنتاج بعد.**

## التشغيل الحقيقي على Windows

1. فك ضغط الأرشيف تمامًا في مسار بسيط مثل `C:\MasrGuideAI`.
2. ثبت Node.js 22 وPython 3.12، واتصل بالإنترنت **لأول تشغيل** لتحميل مكتبات npm وpip.
3. شغّل `OPEN_WEBSITE_WINDOWS.bat` من داخل مجلد `Masr_Guide_AI`، واترك النافذة مفتوحة.
4. لا تفتح رابط الموقع إلا بعد ظهور `[READY]`. افتح في Chrome/Edge **على نفس الكمبيوتر**: `http://127.0.0.1:5173/`.
5. إذا ظهر `ERR_CONNECTION_REFUSED` فهذا يعني أن Vite أو FastAPI ليس شغالاً على نفس الكمبيوتر؛ ابحث عن السبب في `.local-logs/npm-install.log` و`.local-logs/frontend-build.log` و`.local-logs/frontend.log` و`.local-logs/backend.log`. لا يفيد إعادة فتح الرابط قبل إصلاح بدء السيرفر.
6. لتشغيل فحوص QA مستقلّة: `VERIFY_LOCAL_WINDOWS.bat`، وملف النتائج: `qa_reports/local_release_snapshot.json`.

**مهم:** لا تفتح عنوان `127.0.0.1` في متصفح سحابي أو جهاز مختلف. Github مكان لحفظ السورس؛ ليس السيرفر الذي سيشغّل Backend.

## تجربة Gemini الحقيقي

- ملف `.env` أو مفتاح خاص **غير موجودين في أرشيف التسليم لأسباب أمنية**.
- إذا كان لديك مفتاح بالفعل على جهازك، شغّل `SETUP_GEMINI_WINDOWS.bat` وضعه محليًا فقط في `backend/.env`، أو انسخ الإعداد الموجود لديك إلى ذلك الملف. **لا ترسل المفتاح داخل محادثة، ولا ترفعه على GitHub**.
- شغّل `TEST_GEMINI_LIVE_WINDOWS.bat` لإجراء اختبار Provider حقيقي، متى توافرت شبكة Google API وحصّة API. راقب النتيجة دون مشاركة أسرار.
- يعمل تخطيط الرحلات والكتيّب المحلي في وضع Offline من دون مفتاح؛ لكن هذا ليس إثباتًا لنجاح إجابات Gemini.

## نتائج التنفيذ داخل بيئة المراجعة الحالية

| المجموعة | نتيجة قابلة للإثبات |
|---|---|
| Backend pytest | **233/233 PASS** |
| HTTP live integration | **27/27 PASS** |
| Advanced security/concurrency/load/recovery | **36/36 PASS** |
| Offline chatbot acceptance | **52/52 PASS** |
| Planner invariant checks | **18,000/18,000 PASS** |
| Frontend data contract (Node) | **6/6 PASS** |
| Nginx local | **4/4 PASS** |
| Local launch self-tests | **11/11 PASS** |
| React npm dependencies / actual production build, Vitest and ESLint | **BLOCKED** — registry.npmjs.org returned `EAI_AGAIN`, no React node_modules |
| Chromium full React E2E | **BLOCKED** — React build not available. Even opening `/demo` in Chromium returned `ERR_BLOCKED_BY_ADMINISTRATOR` despite HTTP 200 |
| Real Gemini API | **NOT EXECUTED** — no usable GEMINI_API_KEY was found in this working environment |
| Production deployment, persistent managed DB, real bookings | **NOT EXECUTED / NOT IMPLEMENTED** as applicable |

نتائج PASS تخص هذه البيئة وهذه الحالات فقط. احتفظ بالـQA logs، ولا تضع علامة PASS أمام اختبار لم يُنفذ.

## الحدود الفعلية للمنتج

هذا مشروع Portfolio / TravelTech MVP متقدم، **وليس** منصة حجز مدفوعة أو خدمة ببيانات تخزين إنتاجية مُدارة. `SQLite` يصلح للتجارب المحلية، أما تشغيل حسابات حقيقية للجمهور فيحتاج تخزينًا دائمًا مناسبًا، نسخًا احتياطيًا مستعادًا ومختبرًا، مراقبة تشغيل، تقييم أمان/تراخيص وسرية بيانات، وفحصًا بشريًا للمحتوى والأسعار والمواعيد. لا تدّع وجود شراكات أو حجوزات حقيقية غير مفعلة.

## خطة الاعتماد قبل الرفع

1. فتح React محليًا بعد `npm ci` ونجاح `npm run build`, `npm test`, `npm run lint`.
2. تجربة رحلة 20 يومًا (13 القاهرة، 7 الغردقة)، ثم استبدال الغردقة بشرم الشيخ، وتسجيل الحساب وحفظ الرحلة وإعادة تحميلها.
3. اختبار Gemini Live باستخدام مفتاح خاص من جهازك دون نشره.
4. تشغيل Chromium E2E محليًا أو عبر GitHub Actions ومراجعة تصميم الموبايل وRTL.
5. بعد ذلك إنشاء GitHub Repository نظيف ونشر Frontend + Backend على استضافة مناسبة مع تخزين دائم قبل أي حسابات حقيقية.
