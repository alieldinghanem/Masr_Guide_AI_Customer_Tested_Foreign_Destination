# تشغيل Masr Guide AI v7.6

1. فك ضغط المشروع، وافتح مجلد `Masr_Guide_AI` في VS Code.
2. شغّل `RUN_STARTUP_WINDOWS.bat` للـBackend والواجهة، أو ادخل `frontend` وشغّل `npm ci && npm run build && npm test && npm run lint` للتحقق قبل العرض على HR.
3. انسخ `backend/.env.example` إلى `backend/.env` محليًا، وضع مفتاح Gemini **جديدًا غير منشور** داخل ملف `.env` فقط، ولا ترسله في المحادثة ولا تضفه لـGitHub.
4. ادخل `/api/ready` لتتأكد إن قواعد البيانات جاهزة. `/api/health` يعرض حياة العملية فقط.
5. للاستخدام الإنتاجي: لابد من قاعدة بيانات دائمة ونسخ احتياطية مجربة، ثم `APP_ENV=production` و`MASR_DURABLE_STORAGE_CONFIRMED=yes`. تدوين القيمة وحده لا يضمن سلامة التخزين.
6. ملف `render.yaml` معدّ لعرض Portfolio مؤقت؛ **لا تعتمد على حفظ رحلات حقيقية على الخطة المجانية ذات التخزين غير الدائم**.
7. اقرأ `docs/RELIABILITY_AUDIT_V7_6_AR.md` قبل النشر؛ النسخة غير معتمدة تجاريًا حتى تنجح اختبارات الواجهة والمتصفح وGemini الحي والنشر.

GitHub مستودع للكود وليس سيرفر FastAPI بذاته. Render أو استضافة مماثلة تشغّل التطبيق بعد نجاح الـBuild وإضافة المتغيرات السرية.
