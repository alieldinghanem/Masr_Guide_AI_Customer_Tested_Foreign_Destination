# Masr Guide AI — دليل التسليم الواحد والتشغيل المحلي

> **نوع التسليم:** الكود الكامل لنسخة الاختبار المحلي الحالية. ليس نسخة إنتاجية معتمدة حتى اكتمال اختبارات الواجهة الحقيقية وGemini والنشر.

## ما الذي ستحصل عليه؟

- `frontend/`: واجهة React/Vite للموقع السياحي (الاكتشاف، الأماكن، الرحلات، المرشد، الحسابات، المفضلة، المقالات، الشركاء).
- `backend/`: FastAPI وكتالوج السياحة ومحرك الرحلات وGemini وSQLite للاختبار المحلي.
- `qa_chatbot/`، `scripts/`، `backend/tests/`، `frontend/src/__tests__/`: اختبارات وفحوص الجودة.
- `Dockerfile` و`docker-compose.yml` و`.github/workflows/ci.yml`: إعدادات البناء والتشغيل وCI.

## تشغيل الموقع الأساسي على Windows — دون فتح localhost مسبقًا

1. ثبّت Python 3.12 وNode.js 22 LTS (مع npm). تأكد من اتصال الإنترنت لأول تشغيل، وتوفر مساحة تخزين كافية.
2. فك ملف ZIP بالكامل في مسار محلي قصير مثل `C:\Projects\Masr_Guide_AI`، بعيدًا عن الأرشيف نفسه.
3. انقر مرتين على `OPEN_WEBSITE_WINDOWS.bat`، واترك نافذة الأوامر مفتوحة.
4. انتظر ظهور **`[READY] React AND FastAPI`**. عندئذ يُفتح المتصفح تلقائيًا، أو افتح **http://127.0.0.1:5173/** من Chrome/Edge/Brave على **نفس الجهاز**.
5. إذا ظهرت `[FAILED]`، **لا تفتح الرابط**؛ اقرأ الخطأ أو أرسل ملفات `.local-logs/npm-install.log` و`.local-logs/frontend-build.log` و`.local-logs/backend.log` و`.local-logs/frontend.log` (الموجودة بالفعل فقط).

إذا ظهر `ERR_CONNECTION_REFUSED` فالسيرفر المحلي لم يبدأ أو توقف أو لم يبدأ على نفس جهاز المتصفح. الرابط ليس موقعًا عامًا يمكن فتحه من أي جهاز أو متصفح سحابي.

**ملاحظات:** لا تغلق نافذة التشغيل؛ وإذا استُخدم المنفذ 5173 أو 8000 بواسطة نسخة قديمة، أغلقها قبل بدء هذه النسخة. لا ترفع مفاتيح API أو ملفات SQLite إلى GitHub.

## تجربة المرشد الخفيفة — ليست الموقع الكامل

إذا لم تستطع تنزيل حزم npm، شغّل `RUN_FREE_DEMO_WINDOWS.bat`؛ هذا يشغل واجهة `/demo` المرتبطة بخادم FastAPI بعد أن تصبح جاهزة، ثم يفتح http://127.0.0.1:8000/demo من المتصفح المحلي. **هذه صفحة استشارية محدودة ولا تعني نجاح React أو اكتمال الموقع.**

## تم التحقق هنا بالفعل

- `python -m pytest -q tests` داخل `backend/`: 233/233 PASS.
- `node --test scripts/validate_trip_contract.test.mjs` داخل `frontend/`: 6/6 PASS.
- فحوص Python syntax وHTTP على `/api/ready` و`/demo` والاعتمادات البرمجية للمشغّل: تفاصيلها في `docs/LOCAL_RELEASE_VERIFICATION_2026-10-17_AR.md`.

## ما لم يتحقق بعد

- `npm ci`, `npm run build`, `npm test`, `npm run lint`: **BLOCKED** في بيئة التسليم الحالية بسبب تعذّر DNS لـ`registry.npmjs.org` وعدم توافر `node_modules`.
- Browser E2E: **BLOCKED** بسياسة Chromium في البيئة التي يجري فيها الفحص (`ERR_BLOCKED_BY_ADMINISTRATOR`).
- Gemini Live: **NOT EXECUTED** بدون مفتاح حقيقي. لا ترسل المفتاح داخل الشات ولا ترفعه على GitHub؛ يمكنك إعداده محليًا في `backend/.env`.
- نشر GitHub/استضافة وإثبات تخزين دائم ونسخ احتياطي: **NOT EXECUTED**.

قبل اعتماد النسخة، نفّذ على جهاز Windows: `cd frontend && npm ci && npm run lint && npm test && npm run build` ثم اختبار وظائف الواجهة محليًا، وبعدها سيناريو Gemini حقيقي بتصريحك.
