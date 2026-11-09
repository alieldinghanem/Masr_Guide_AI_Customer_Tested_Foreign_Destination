# تقرير مراجعة Masr Guide AI v5.0 (15-10-2026)

## اختبارات تم تنفيذها بالفعل في بيئة تجهيز الحزمة

- Python: `python -m pytest -q` داخل backend: **88 passed**.
- Python syntax: `python -m compileall -q app`: **Passed**.
- JSX/JS parser عبر TypeScript Compiler `createSourceFile` لجميع ملفات `frontend/src`: **27 ملفًا، 0 parse diagnostics**.
- ملفات `render.yaml`, `docker-compose.prod.yml`, `.github/workflows/ci.yml`: **تم تحليل YAML دون خطأ**.
- اختبارات مضافة خاصة بالـCMS والصلاحيات وعرض الشركاء ومراجعتهم ورفض روابط غير آمنة، ووجود أفكار موثقة بوضوح للأيام الحرة.
- فحص ملفات الحزمة للـAPI Keys و`.env` بعد التجهيز.

## اختبارات لم يتم نجاحها بعد

- `npm ci` تعذّر إكماله في بيئة التجهيز؛ لذلك **لم ينجح/لم يُشغّل هنا** React production build أو Vitest أو ESLint.
- Docker image build لم يتم التحقق منه محليًا. يحتاج بيئة تسمح بتثبيت npm packages.
- تشغيل Full UI داخل Browser أو اختبار Gemini بمفتاح فعّال لم يحدث لهذه النسخة.
- لم يتم النشر فعليًا على Render أو GitHub ضمن هذا الإصدار؛ الملفات **مُعدّة للنشر** فقط.

## اختبارات قبول يُرجى تنفيذها قبل إرسال الـCV

1. `npm ci` + `npm test` + `npm run lint` + `npm run build`: كلها تنجح.
2. افتح الموقع على Laptop/Mobile وتأكد من التنقل والواجهة والصور واللغة.
3. استعرض Blog ثم عدّله من Staff CMS بمفتاح Staff خاص.
4. جرّب تسجيل 2 مستخدمين والتأكد من اختلاف الرحلات المحفوظة.
5. 20-day plan: ظهور عدد الأيام الصحيح وأفكار حرة صريحة عند نفاد المعالم، دون أسعار غير مثبتة.
6. Configure Gemini key محليًا، تأكد من الردود في اللغة الصحيحة وعدم كشف أسرار عبر الكود أو Network Response.
7. أضف عرضًا تجريبيًا خاصًا فقط بدون تفعيله، وتأكّد أنه لا يظهر علنًا. لا تنشر عروض شركاء من غير اتفاق.
8. على GitHub Actions: Backend وFrontend لازم يظهروا باللون الأخضر.
9. في Render: `/`, `/api/health`, `/#/project`, `/#/planner`, `/#/stories` لازم يشتغلوا على نفس الدومين.

## قرار المراجعة

**Portfolio source release: tests passed for backend and source syntax.** Frontend build and cloud deployment remain **verification gates**, not presumed passes. Production commercial travel operations **not ready** without licenses, partners, verified pricing, durable storage and security hardening.
