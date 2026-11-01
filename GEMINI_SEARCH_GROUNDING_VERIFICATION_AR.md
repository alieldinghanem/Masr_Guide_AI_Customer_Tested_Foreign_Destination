# Masr Guide AI — سجل التنفيذ والتحقق (30 أكتوبر 2026)

## التغيير المنفذ

1. دعم `GEMINI_MODEL=gemini-2.5-flash` مع أداة Google Search داخل طلبات Gemini على API `generateContent`.
2. إظهار metadata الفعلية للبحث `grounding.requested` و`grounding.search_performed` و`grounding.grounded` مع مصادر `google_search` مميزة عن مراجع الكتالوج.
3. دعم أسئلة المطاعم عبر Google Search عند التفعيل؛ إذا لم تُرجع الخدمة مصادر صالحة لا يؤكد النظام أي مطعم من رد غير موثق.
4. رفض تقديم الأسعار/المواعيد المتغيرة كمعلومات موثقة إذا لم تظهر استشهادات حية.
5. الحفاظ على تنفيذ الرحلات وحفظها ضمن FastAPI وليس ضمن Google Search.
6. Windows setup يستخدم Gemini 2.5 Flash ويفعّل Search؛ أضيف `TEST_GEMINI_SEARCH_GROUNDING_WINDOWS.bat` للاتصال الحقيقي.
7. إعداد `AI_PROVIDER` يمكنه اختيار Gemini أو OpenAI؛ تكامل GPT اختياري ومغلق عند عدم توفر مفتاح خاص به.
8. عرض المحادثة يوضح هل هناك استشهادات بحث ويحاول عرض Search Suggestions في iframe معزول.

## اختبارات أُجريت فعليًا في بيئة التسليم

- **PASS:** `python -m pytest -q` داخل `backend`: **323/323**.
- **PASS:** 10 اختبارات جديدة لمحتوى طلب Gemini، والفصل بين الحالات المثبتة وغير المثبتة، والروابط الخبيثة، وعدم تسريب المفاتيح، واحتفاظ OpenAI بالأولوية إذا اختاره المشغّل.
- **PASS:** `node --test scripts/validate_trip_contract.test.mjs scripts/chat_ui_modes.test.mjs`: **12/12**.
- **PASS:** `python scripts/qa_planner_stress.py`: **18,000** تحقق.
- **PASS:** `python scripts/check_no_secrets_v75.py` وفحص CSP لصور/خرائط الواجهة.
- **PASS:** تشغيل FastAPI عبر `uvicorn` فعليًا في بيئة محلية مع قواعد بيانات مؤقتة: `GET /api/ready` و`GET /api/health` و`POST /api/chat` أعادت HTTP 200.
- **BLOCKED:** اتصال **Gemini Live + Google Search** لأن `GEMINI_API_KEY` غير موجود في متغيرات التشغيل أو ملفات `.env` المتاحة داخل هذه البيئة. أداة الاختبار تعيد status=BLOCKED، لا PASS.
- **NOT EXECUTED:** React Production Build، Chromium E2E، استضافة عامة، فحص استرجاع النسخ الاحتياطية على السيرفر المستهدف.

## أمثلة الاستجابة

عندما يختار Gemini استخدام Google Search ويرجع مراجع:

```json
{
  "mode": "gemini-search-grounded",
  "sources": [{"number": 1, "title": "Source title", "url": "https://...", "type": "google_search"}],
  "grounding": {
    "requested": true,
    "search_performed": true,
    "grounded": true,
    "queries": ["Egypt attraction official opening hours"],
    "search_suggestions_html": "...provider supplied markup..."
  }
}
```

**تنبيه:** المثال توضيحي لشكل JSON، وليس بيانات فعلية مسترجعة من Google في هذه الجولة. إذا لم ترد مراجع ويب لا يجوز استخدام `gemini-search-grounded`.

## قيود يجب معالجتها قبل إطلاق شركة

- بحث Google لا يؤكد وجود غرف فنادق أو حجوزات أو توافر مطاعم، ولا يجوز وصفه كمزود حجوزات.
- التأكد من شروط عرض Search Suggestions وروابط المصادر والسياسات الخاصة باستخدام Google Grounding في الواجهة العامة.
- الفئة المجانية لها حدود؛ تفعيل حساب مدفوع يمكن أن يؤدي إلى رسوم بحسب الاستهلاك.
- لا تستخدم مفاتيح قد تسربت في محادثات؛ أنشئ مفتاحًا جديدًا وضعه داخل متغيرات بيئة السيرفر فقط.
- بيئة الإنتاج لا تزال تحتاج تخزينًا دائمًا موثقًا، اختبار Restore فعليًا، TLS، مراقبة، ونشرًا عامًا.

للتشغيل راجع `GEMINI_SEARCH_GROUNDING_START_HERE_AR.md`.
