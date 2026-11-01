# Masr Guide AI — تقرير تنفيذ وفحص 17 أكتوبر 2026

**التسليم:** السورس الكامل لنسخة واحدة مهيأة للتشغيل المحلي على Windows، مع إصلاح لملف العرض السريع الذي كان يفتح الرابط قبل تشغيل السيرفر. **ليس إصدارًا Production-Ready معتمدًا.**

## نتائج منفذة فعليًا في هذه الجلسة

| فحص | نتيجة مؤكدة | الإثبات داخل الأرشيف |
|---|---|---|
| Backend Pytest | PASS — 233/233 | `qa_reports/current_2026_10_17/backend_pytest.txt` |
| Chatbot QA offline | PASS — 52/52 | `qa_reports/current_2026_10_17/chat_52.txt` |
| Planner invariants | PASS — 18,000/18,000 | `qa_reports/current_2026_10_17/planner_stress.txt` |
| HTTP API and mocked model adapter | PASS — 27/27 | `qa_reports/current_2026_10_17/http_integration.txt` |
| Nginx local proxy | PASS — 4/4 | `qa_reports/current_2026_10_17/nginx_proxy.txt` |
| Frontend persisted-data contract | PASS — 6/6 | `qa_reports/current_2026_10_17/frontend_contract.txt` |
| Local launchers: response identity and fail-closed logic | PASS — 11/11 | `qa_reports/current_2026_10_17/launcher_contracts.txt` |
| Credential source-tree best-effort check | PASS | `qa_reports/current_2026_10_17/source_secret_check.txt` |
| Lightweight preview backend server on port 8000 | PASS — `/api/ready` و`/demo` returned expected HTTP content before showing READY; startup and shutdown exercised. This is **not** a browser or React test. | `scripts/open_quick_demo.py`, `RUN_FREE_DEMO_WINDOWS.bat` |
| Launcher Python syntax | PASS — `py_compile` | `scripts/open_local_website.py`, `scripts/open_quick_demo.py` |

## قيود مهمة لا نُخفيها

- **React npm install / build / lint / component tests: BLOCKED.** بيئة الفحص لا تستطيع حل DNS لاسم `registry.npmjs.org`، ولا توجد نسخة مكتملة من `node_modules`. لا يوجد دليل تنفيذ React build.
- **Chromium browser E2E: BLOCKED.** محاولة فتح `/demo` على سيرفر FastAPI استجاب فعليًا أعادت `ERR_BLOCKED_BY_ADMINISTRATOR` داخل Chromium بسبب سياسة بيئة الفحص؛ لم نر الموقع في متصفح حقيقي هنا.
- **Gemini Live E2E: NOT EXECUTED.** لا يوجد مفتاح حقيقي متاح داخل الاختبار، ولا نطلب مشاركة مفتاح سري عبر المحادثة.
- **Windows double-click: NOT EXECUTED.** بيئة فحص Linux؛ يجب اختبار `.bat` فعليًا على جهاز Windows.
- **Production deployment / durable storage / backups / full partner booking integration: NOT EXECUTED/NOT IMPLEMENTED حسب الميزة.** نشر GitHub لا يشغّل API بمجرده.

## ماذا أصلحنا في هذا التسليم؟

- غيّرنا تشغيل `RUN_FREE_DEMO_WINDOWS.bat` لبدء FastAPI ثم **انتظار الجاهزية عبر HTTP** قبل فتح الرابط، بدل فتحه قبل السيرفر.
- أضفنا `scripts/open_quick_demo.py` بفحص فعلي للمحتوى وللجاهزية، وإبقاء السيرفر حيًا مع رسائل خطأ وسجل `.local-logs/demo-backend.log`، بدون اشتراط Node.js لتجربة العرض المحدود.
- أضفنا فحوصًا تلقائية لتمييز خادم React وخادم API وصفحة العرض المحدود عن أي صفحة مختلفة أو استجابة خطأ؛ وأدرجنا الفحوص في CI.
- حافظنا على كود v7.8.1 والتحسينات التالية له، واحتفظنا بنتائج الاختبارات الجديدة بدلاً من حذف أو تغيير تاريخ النتائج القديم.

## معايير اعتماد إصدار نهائي عام لاحقًا

1. تشغيل `npm ci && npm run lint && npm test && npm run build` بنجاح مع حفظ الناتج.
2. اختبار React desktop/mobile بواسطة Chromium ضد خادم API وقاعدة بيانات اختبار، وتأكيد تخطيط الرحلات والمفضلة والحسابات.
3. اختبار Gemini الحقيقي بمفتاح آمن دون كشف بيانات الاعتماد، مع تقييم السلوك متعدد المحادثات والأخطاء.
4. اختبار النشر النهائي وتخزين دائم ونسخ احتياطي والاسترجاع والمراقبة والأمان.

**لا ترفع هذا الأرشيف باعتباره منصة إنتاجية جاهزة لمستخدمين حقيقيين قبل إغلاق هذه المعايير.**
