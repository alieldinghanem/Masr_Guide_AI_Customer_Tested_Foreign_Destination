# Masr Guide AI — حالة اختبار التشغيل المحلي (16 أكتوبر 2026)

هذا تقرير إعادة فحص **السورس الكامل** الذي جرى تجميعه من v7.8.1 والإصلاحات اللاحقة، وليس تقرير تشغيل على كمبيوتر المستخدم أو استضافة عامة.

## نتائج منفّذة على البيئة المتاحة

| الاختبار | الأمر/الطريقة | النتيجة |
|---|---|---|
| Backend unit/integration | `cd backend && python -m pytest -q` | **PASS 233/233** |
| Real HTTP and mocked-provider integration | `python scripts/qa_live_http.py` | **PASS 27/27** (الـAI الخارجي Mock، ليس Gemini الحقيقي) |
| AI offline acceptance | `python qa_chatbot/acceptance_evaluation.py` | **PASS 52/52** |
| Planner deterministic stress | `python scripts/qa_planner_stress.py` | **PASS 18000/18000 assertions** |
| React trip-data contract without npm | `cd frontend && node --test scripts/validate_trip_contract.test.mjs` | **PASS 6/6** |
| Retrieval evaluation | `cd backend && python -m evaluation.run_eval` | **hit@3 1.00** على مجموعة التقييم المحلية |
| Nginx config/proxy QA | `python scripts/qa_nginx_proxy.py` | **PASS 4/4**؛ ليس حاوية Docker حقيقية |
| Best-effort credential scan | `python scripts/check_no_secrets_v75.py` | **PASS**؛ ليس تدقيقًا أمنيًا شاملًا |
| Actual FastAPI local startup | منفذ محلي مع قواعد بيانات مؤقتة و`GET /api/ready` | **HTTP 200** |
| Mini demo HTML | `GET /demo` | **HTTP 200**؛ ليس واجهة React الأساسية |

## عوائق ومهام لم تُنفّذ

- **BLOCKED:** `npm ci`, Vitest, ESLint, React production build، بسبب عدم الوصول إلى `registry.npmjs.org` وغياب حزمة `yocto-queue` من الكاش. فشل اعتماديات npm في هذه البيئة ليس اختبارًا لتطبيق React.
- **BLOCKED:** Chromium UI browser navigation: `net::ERR_BLOCKED_BY_ADMINISTRATOR` حتى لصفحة mini-demo المحلية. لم ينجح اختبار React Desktop/Mobile E2E.
- **NOT EXECUTED:** اتصال Gemini حي؛ لم يُقدَّم مفتاح API ضمن هذه البيئة. لا ترفع أي مفاتيح إلى GitHub.
- **NOT EXECUTED:** نشر على سيرفر فعلي، اختبار PostgreSQL والتعافي، فحص أمني مستقل، اختبارات حقيقية للحجوزات أو الإيرادات (غير منفذة وظيفيًا).

## تغييرات ملفات تشغيل Windows في هذه الحزمة

- `RUN_BACKEND_WINDOWS.bat` لا يعيد تنزيل الاعتمادات مع كل تشغيل؛ يتحقق من Python venv الموجود ويشغّل FastAPI محليًا على `127.0.0.1`.
- `RUN_FRONTEND_WINDOWS.bat` يتحقق من وجود Vite الفعلي، لا يكتفي بمجلد `node_modules` قد يكون ناقصًا بعد فشل `npm ci`، ويعمل على `127.0.0.1`.
- ملاحظة دخول حديثة أعلى `README.md` تشير إلى تعليمات التشغيل الحالية بدل الاعتماد على تقارير نسخ قديمة.

## على جهاز Windows — الخطوة التالية

1. فك ضغط الملف وافتح **المجلد `Masr_Guide_AI`** نفسه في VS Code.
2. تأكد من وجود Python 3.11/3.12 وNode.js 22 LTS واتصال إنترنت لتثبيت المكتبات أول مرة.
3. شغّل `SETUP_AND_TEST_LOCAL_WINDOWS.bat` وانتظر رسالة `PASS`؛ أي فشل يعني أن اختبار البناء لم ينجح.
4. شغّل `RUN_STARTUP_WINDOWS.bat` (نافذتان: Backend وReact).
5. افتح **http://localhost:5173**، وليس `/demo`، ثم جرّب Discover → Planner → Guide → حساب المسافر وحفظ الرحلات → فتحها وتعديلها → المفضلة → التبديل للعربية وتجربة الموبايل.
6. لبدء اختبار المتصفح: `backend\.venv\Scripts\python.exe -m pip install playwright` ثم `backend\.venv\Scripts\python.exe -m playwright install chromium` ثم `backend\.venv\Scripts\python.exe scripts\verify_release_v78.py --browser`. يتطلب نجاح React build مسبقًا.
7. لو تعطل التشغيل، احتفظ **برسالة الخطأ بالكامل** من النافذة التي فشلت، دون مشاركة ملفات `.env` أو مفاتيح خاصة.

**لا نبدأ خطوة GitHub والنشر كسيرفر عام إلا بعد قبول الاختبار المحلي الفعلي.** GitHub يخزّن الكود، واستضافة التطبيق الحي تحتاج خدمة نشر منفصلة وبيانات دائمة محمية.
