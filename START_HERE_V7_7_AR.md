# Masr Guide AI — v7.7 Release-Candidate Verification

## ماذا تغير عن v7.6.1؟
- توحيد استدعاءات حساب السائح ولوحة الشركاء على HTTP client واحد له مهلة زمنية، حتى لا تظل الواجهة معلقة عند انقطاع الشبكة.
- تحديث اختبار Chromium ليطابق React الحالية بدل الاعتماد على أسماء مكونات قديمة.
- إضافة مهمة GitHub Actions مستقلة تبني React وتشغّل الـBackend وChromium لإجراء E2E فعلي على سطح المكتب والموبايل.
- إضافة اختبار اتصال Gemini حقيقي **اختياري**؛ لا يعمل دون موافقة صريحة ومفتاح خاص على جهازك.
- إبقاء نتائج Backend وChatbot QA كما هي دون العبث بالمعايير للوصول إلى أرقام جميلة.

## قبل النشر على GitHub / Render
1. تأكد أن كل API Keys قديمة أو نُشرت في المحادثات **ملغاة**. لا ترفع `backend/.env`.
2. `cd frontend` ثم `npm ci && npm test && npm run lint && npm run build`.
3. ارجع للمجلد الأساسي وشغّل `RUN_STARTUP_WINDOWS.bat` واختبر الصفحات.
4. ثبت Playwright للـPython: `pip install playwright` ثم `python -m playwright install chromium`.
5. بعد تشغيل React + Backend في رابط واحد، نفّذ `python scripts/qa_browser_e2e.py` مع `FRONTEND_URL` المناسب. **لا تعتبره ناجحًا إلا لو ظهر PASS**.
6. افحص GitHub Actions: الوظيفة `Compiled React + backend browser E2E` لازم تكون خضراء.
7. اختبار Live Gemini (اختياري ويستهلك رصيدًا): احتفظ بمفتاح جديد في `backend/.env` فقط، ثم في PowerShell:
   ```powershell
   $env:MASR_LIVE_AI_QA='1'
   python .\scripts\qa_gemini_live.py
   Remove-Item Env:\MASR_LIVE_AI_QA
   ```
8. انشر رابط HR تجريبيًا فقط، ولا تستخدم حسابات حقيقية مهمة أو مدفوعات فعلية على تخزين Render المجاني المؤقت.

## ما الذي لم يثبت بعد؟
- لا يمكن تأكيد React Build أو E2E في بيئة إعداد الحزمة الحالية بسبب انقطاع الوصول لـnpm؛ وفُتح Chromium لكن سياسات البيئة تمنع تحميل أي URL (`ERR_BLOCKED_BY_ADMINISTRATOR`).
- لم تُنفّذ مكالمات Gemini حقيقية دون مفتاح خاص جديد.
- لم يحدث Live deployment إلى حساب المستخدم.
- لا توجد تحويلات حجوزات أو عمولات حقيقية أو PostgreSQL وإجراءات Backup/Restore Production.

**التصنيف: Portfolio / HR Release Candidate — NOT production-approved.**
