# Masr Guide AI — البداية الصحيحة لتجربة المشروع محليًا

## مرجع السورس

هذا المجلد يحتوي **جميع ملفات v7.8.1 الأصلية** مع التعديلات المحافظة التي طُورت بعدها. هذه حزمة كاملة للـFrontend والـBackend؛ ليست مجرد diff أو chatbot منفصل. لا تغيّر اسم الإصدار لمجرد تسليم الأرشيف.

## الخطوة 1 — جهز الكمبيوتر

على Windows 10/11 ثبّت **Python 3.11 أو 3.12** و**Node.js 22 LTS** (أو 20+) وGit. يلزم اتصال إنترنت أول مرة لتثبيت حزم pip/npm. افتح المجلد `Masr_Guide_AI` نفسه، وليس مجلدًا أعلى منه.

## الخطوة 2 — تثبيت وتشغيل الاختبارات

انقر مرتين على `SETUP_AND_TEST_LOCAL_WINDOWS.bat` أو من PowerShell:

```powershell
.\SETUP_AND_TEST_LOCAL_WINDOWS.bat
```

الملف يثبت المتطلبات في Python venv ويستخدم `npm ci` من `package-lock.json`، ويشغل Backend tests وReact tests وlint وproduction build. **أي فشل في خطوة يعني أن Gate التشغيل لم ينجح**؛ لا تتجاوز رسالة الخطأ أو تستبدل `npm ci` بحذف الـlockfile.

إذا ظهر فشل DNS أو npm registry، عالج الاتصال على جهازك وأعد تشغيل setup. لا تضع Gemini key في frontend أو git. لا يشغّل ملف setup أي طلب مدفوع إلى Gemini.

## الخطوة 3 — شغل الموقع الحقيقي

بعد نجاح setup:

```powershell
.\RUN_STARTUP_WINDOWS.bat
```

- الموقع الأساسي React: <http://localhost:5173>
- الـFastAPI والدوال: <http://localhost:8000/docs>
- اختبار جاهزية الـAPI: <http://localhost:8000/api/ready>
- `/demo` مثال مصغّر اختياري **وليس الموقع النهائي**.

**سيناريو تجربة القبول اليدوي:** افتح الموقع، جرّب Discover وSearch، ثم Planner بمدينتين، Guide بسؤال تاريخي، ثم طلب 20 يوم (13 القاهرة / 7 الغردقة)، وبعدها اطلب تغيير الغردقة إلى شرم الشيخ. افتح حسابًا محليًا، احفظ رحلة، افتحها من My Account، عدّل خطتها بالمخطط، ثم استخدم زر **Replace with my current planner itinerary** لتحديث الرحلة نفسها. أعد تحميل الصفحة وتأكد من الاحتفاظ بالتعديل وعدد الرحلات. جرّب لغة الواجهة العربية واتجاه RTL والموبايل.

لا تستخدم كلمات مرور شخصية مهمة في نسخة الاختبار. كل حسابات SQLite المحلية هنا للتجربة؛ احتفظ بنسخة احتياطية قبل حذف `backend/data`.

## الخطوة 4 — بوابات الاعتماد قبل GitHub والنشر

لتجربة المتصفح الآلية على Windows، وبعد إنشاء البيئة:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install playwright
.\backend\.venv\Scripts\python.exe -m playwright install chromium
.\backend\.venv\Scripts\python.exe scripts\verify_release_v78.py --browser
```

لاحظ أن الـverifier الافتراضي يسجل **Gemini الحقيقي NOT EXECUTED** إذا لم تطلبه صراحةً، وبالتالي قد يخرج بكود غير صفري رغم نجاح الاختبارات المحلية. لتجربة Gemini الحي، أنشئ `backend/.env` بمفتاح جديد خاص بك (ملف مستبعد من Git)، وافحص أي تكلفة أو حصص استخدام ثم شغّل `--live-gemini` فقط بموافقتك على الاتصال الحقيقي.

**لا تدّعِ إطلاقًا Production-Ready دون:** React build + lint + Vitest + Chromium E2E + Gemini الحي حين يكون جزءًا من العرض + فحص أمن + تخزين دائم حقيقي ونسخ احتياطية مجربة. Docker/GitHub Actions ملفات إعداد، وليست دليل تشغيل سحابي. GitHub مستودع مصدر؛ استضافة الواجهة/الـAPI على خادم منفصل.

## ما بقي خارج نطاق التشغيل المحلي الأساسي

- SQLite مناسب للتطوير المحلي المحدود؛ PostgreSQL أو تخزين إنتاجي معتمد مطلوب قبل خدمات المستخدمين العامة.
- SEO بمحتوى server-rendered، ومراقبة إنتاجية متقدمة، وحجوزات حقيقية وعقود شركاء وإيرادات مثبتة: **ليست معتمدة أو منفذة كلها**.
- لا تعرض الأرقام التجريبية لنقرات العروض وكأنها حجوزات أو عمولات محصلة.

راجع `docs/MASTER_PROMPT_MASR_GUIDE_AI.md` لرؤية المنتج الأصلية و`docs/PRODUCTION_GAPS_AR.md` للفجوات المتبقية.
