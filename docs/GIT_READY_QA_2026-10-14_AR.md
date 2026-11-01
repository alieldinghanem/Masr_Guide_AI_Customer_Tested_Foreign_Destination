# تقرير اعتماد Git-Ready — Masr Guide AI

**التاريخ:** 14 أكتوبر 2026. **الأساس:** نسخة Git-ready v1.9 من المحادثة، مع إصلاحات إضافية.

## نجح محليًا (من إعادة تشغيل فعلية)

| الاختبار | النتيجة |
|---|---|
| Backend `pytest` | PASS — 60/60 |
| HTTP + mock provider | PASS — 21/21 |
| Planner stress | PASS — 1,500 رحلة / 18,000 تحقق |
| Nginx proxy local checks | PASS — 4/4 |
| Retrieval evaluation | Hit@3 = 100% على بيانات التقييم الداخلية فقط؛ ليست دليلاً على كل أسئلة السياح |
| React JS/JSX syntax | PASS — 18 ملفًا بفحص TypeScript syntax |
| `api.js` native Node smoke | PASS — نجاح الاتصال وتحديد signal وفشل الشبكة |

## غير مُتحقق منه — لا يُحتسب نجاحًا

- `npm ci` غير مكتمل بسبب عدم توافر اتصال npm Registry في بيئة الاختبار. لذلك React build وVitest وESLint وPlaywright **NOT VERIFIED** محليًا.
- سيناريو اختبار API timeout أُضيف إلى Vitest لكنه لم يُنفذ بعد.
- GitHub Actions الجديد لم يُنفّذ لأن المستودع لم يُنشأ/يُرفع في هذه الجلسة.
- اتصال OpenAI الحقيقي غير مُختبر لعدم توافر مفتاح للاختبار.
- Docker غير مُختبر لعدم وجود Docker في البيئة.
- تراخيص الصور الواردة من النموذج الأصلي ومحتوى المصادر السياحية تحتاج تحققًا قبل جعل المستودع عامًا.

## التعديلات

1. ضبط مهلة زمنية آمنة لطلبات الـAPI (20 ثانية للطلبات العادية و65 ثانية للمحادثة) وإظهار خطأ واضح عند انتهاء المدة.
2. إضافة اختبار وحدة لسيناريو مهلة HTTP.
3. تصحيح اختيار عنوان Home في اختبار Playwright E2E.
4. إضافة GitHub Actions Browser E2E job يتحقق من Desktop وMobile بعد اختبار Backend وFrontend.
5. إضافة سكربت PowerShell لنشر خاص مشروط بنجاح الاختبارات، وعدم رفع أي أسرار.
6. تحسين `release_preflight.py` ليتحقق من وجود `vite` فعليًا وليس مجرد مجلد node_modules فارغ.

## قرار التسليم

**READY FOR PRIVATE REPOSITORY PREPARATION — NOT VERIFIED FOR PUBLIC RELEASE.** لا تضع وصف "Live LLM fully tested" أو "production-ready" إلى أن تُنفذ اختبارات المزود الحقيقي والبناء والمتصفح.
