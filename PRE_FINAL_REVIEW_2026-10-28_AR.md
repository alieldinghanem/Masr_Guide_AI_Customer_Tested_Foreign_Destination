# Masr Guide AI — مراجعة ما قبل التجربة المحلية النهائية

**تاريخ المراجعة:** 28 أكتوبر 2026  
**المصدر:** آخر حزمة `Masr_Guide_AI_Full_Project_Local_QA_2026-10-28.zip`؛ لم تُستبدل بمشروع جديد.  
**قرار الجودة:** السورس قابل للانتقال إلى تجربة التشغيل المحلي، لكن **غير معتمد كنسخة Production-Ready** حتى نجاح React build والاختبارات داخل المتصفح وGemini الحقيقي.

## إصلاحات هذه المراجعة

1. **صور الوجهات في النشر عبر Nginx:** كان `img-src` في Content Security Policy يمنع صور Unsplash التي يستخدمها `EditorialMedia.jsx` و`styles.css`. أُصلح بالسماح فقط لـ`https://images.unsplash.com`، مع الحفاظ على منع inline scripts و`unsafe-eval`، وإضافة فحص آلي في CI (`scripts/qa_frontend_security_contract.py`). أُعيد إنتاج فشل الفحص على الإعداد القديم ثم نجح بعد التصحيح.
2. **نظافة اختبارات SQLite:** إغلاق اتصالات قواعد البيانات المؤقتة بشكل صريح في اختبار النسخ الاحتياطي وفحص الحذف المتكامل. هذا إصلاح في أدوات التحقق، وليس تغييرًا في نموذج البيانات الإنتاجي.

## فحوص تم تنفيذها بالفعل

| المنطقة | النتيجة | حدود النتيجة |
|---|---|---|
| Python / FastAPI tests | **261/261 PASS** | اختبارات Backend؛ ليست بديلًا عن المتصفح |
| Python code coverage | **94% line coverage** | على ملفات `backend/app` التي قاسها الاختبار، وليس إجمالي المنتج |
| Real HTTP integration | **27/27 PASS** | يتضمن mock OpenAI adapter؛ لا يثبت اتصالًا خارجيًا حقيقيًا |
| Additional auth, concurrency, recovery and load tests | **36/36 PASS** | بيئة محلية مؤقتة؛ ليست اختبار ضغط إنترنت إنتاجي |
| Chat offline acceptance | **52/52 PASS** | إجابات Offline وقواعد اختبار محدودة |
| Planner property stress | **18,000/18,000 PASS** | invariants على 1500 حالة محددة |
| Node frontend source/data contracts | **11/11 PASS** | بدون React runtime |
| JS/JSX syntax | **30 files / 0 parse errors** | فحص syntax فقط وليس Vite compilation |
| Package manifest vs lockfile | **PASS** | فحص تطابق إصدارات root dependencies فقط |
| Local launcher checks | **11/11 PASS** | فحوص منطق المشغّل بدون Windows فعلًا |
| Nginx proxy checks | **4/4 PASS** | Nginx محلي لا Docker production |
| New Nginx CSP regression check | **PASS** | يشمل مصادر الصور والخرائط الموجودة حاليًا |
| Source-tree best-effort secret scan | **PASS** | لا يغني عن فحص Git history أو secret scanner احترافي |

## ما لم يثبت بعد

- **React production build / Vitest / ESLint: BLOCKED.** محاولة `npm ci` توقفت بسبب الوصول/التحميل من npm في بيئة العمل الحالية. وبالتالي لا يُوجد ادعاء بنجاح بناء React أو اختبار المكونات.
- **Chromium browser E2E: NOT EXECUTED في هذه المراجعة.** لا يوجد React build متاح لتشغيل سيناريو متصفح حقيقي. في المحاولات السابقة حُظر الوصول المحلي بسياسة المتصفح.
- **Gemini Live: BLOCKED.** لم يُعثر على `GEMINI_API_KEY` قابل للاستخدام في بيئة التشغيل الحالية، ولم تُرسل طلبات حقيقية إلى Google. محاكاة Gemini لا تكفي لاعتماد جودة الإجابات.
- **Production deployment / durable storage / security penetration / real partner bookings: NOT EXECUTED أو خارج النطاق الحالي.** غياب هذه الاختبارات يمنع اعتماد النسخة كمنتج تجاري منشور.

## طريقة قبول الاختبار المحلي على Windows

1. فك ضغط الملف كاملًا (لا تشغّل الملفات من داخل ZIP).
2. تأكد من Python 3.11+، وNode.js 20+، واتصال إنترنت لتثبيت مكتبات npm عند الحاجة.
3. شغّل `OPEN_WEBSITE_WINDOWS.bat` من مجلد `Masr_Guide_AI`؛ لا تفتح localhost قبل ظهور `[READY]`.
4. افتح **في Chrome أو Edge على نفس الجهاز**: `http://127.0.0.1:5173/`.
5. اختبر صفحات الوجهات والصور والخرائط، التحويل بين العربية والإنجليزية، الشات، إنشاء رحلة 20 يومًا (13 القاهرة و7 الغردقة)، ثم تبديل الغردقة بشرم الشيخ، التسجيل والحفظ والاسترجاع وتسجيل الخروج.
6. اختبر Gemini الحقيقي فقط بعد إضافة المفتاح **محليًا** إلى `backend/.env` وتشغيل `TEST_GEMINI_CONVERSATION_WINDOWS.bat`. لا تشارك المفتاح ولا تضعه في Git.
7. قبل اعتماد النسخة: شغّل `VERIFY_LOCAL_WINDOWS.bat` ومراجعة سجل `.local-logs` في حالة فشل أي خطوة.

**تعريف الاعتماد:** نتيجة PASS فعلية لـReact Build وVitest وChromium End-to-End وGemini Live، واختبار الرحلة الكاملة دون أخطاء حرجة. لا تنشر حسابات مستخدمين بقاعدة بيانات مؤقتة، ولا تدّع وجود أسعار/حجوزات/شراكات مباشرة دون تكاملات موثقة.
