# Masr Guide AI — مراجعة هندسية شاملة

**التاريخ:** 30 أكتوبر 2026  
**نطاق المراجعة:** آخر سورس موحّد، مع مراجعة مسارات Backend وAI والشات والتخطيط والحسابات والواجهة وأوامر التشغيل وملفات النشر.  
**قرار الاعتماد:** **LOCAL TECHNICAL REVIEW PASSED / COMMERCIAL LAUNCH NOT APPROVED**

## اختبارات منفذة على هذه النسخة

| التحقق | نتيجة فعلية | الحدود |
|---|---|---|
| Python Backend (pytest) | 354/354 PASS | ضمن سيناريوهات الاختبارات المكتوبة |
| Independent customer HTTP journey | 17/17 PASS | تشغيل Uvicorn فعليًا مع Gemini/OpenAI غير مفعّلين، قاعدة بيانات معزولة |
| Offline chatbot acceptance | 52/52 PASS | ليس ردود Gemini أو GPT الحقيقية |
| Planner invariants | 18,000/18,000 PASS | 1,500 رحلة × 12 شرطًا |
| Frontend data + chat modes | 12/12 PASS | اختبارات Node مستقلة عن React Build |
| Local Windows launch contracts | 11/11 PASS | ليست تشغيلًا فعليًا على Windows |
| Basic source secrets scan | PASS | فحص أفضل جهد، ليس فحصًا أمنيًا كاملًا |
| React/Nginx asset CSP contract | PASS | تطابق قواعد المصادر في الاختبار |
| Python syntax | PASS | compileall |
| docker-compose/render YAML parsing | PASS | ليس Docker build/run |
| Gemini Live + Google Search | BLOCKED | لا يوجد مفتاح API متاح في بيئة المراجعة |
| OpenAI Live | BLOCKED | لا يوجد مفتاح API متاح |
| React Production Build / Vitest / ESLint | BLOCKED | `npm ci --offline` فشل بسبب عدم وجود `yocto-queue` في cache |
| Chromium frontend E2E | NOT EXECUTED | React لم يُبنَ محليًا |
| Production database backups / restore | NOT EXECUTED | يتطلب بيئة استضافة وتخزين دائم |
| Public service deployment + network tests | NOT EXECUTED | لا يوجد استضافة عامة متصلة بهذه النسخة |

## الخلل المكتشف والمصحح في هذه الجولة

كانت مسارات النشر منفصلة عن إعدادات التطوير الخاصة بـGemini:

1. `docker-compose.prod.yml` كان يستخدم نموذج `gemini-flash-latest` بدل النموذج المحدد `gemini-2.5-flash`، ولا يمرر `GEMINI_SEARCH_GROUNDING` ولا `AI_PROVIDER` أو مفاتيح OpenAI الاختيارية.
2. `render.yaml` كذلك كان يستخدم الاسم القديم ولا يعرّف إعداد Google Search أو مزود AI.

**تم تصحيح الإعدادين** لإتاحة `gemini-2.5-flash` وإعدادات اختيار Gemini/OpenAI وتمرير Google Search عند تفعيله. أضيفت **4 اختبارات انحدار** إلى `backend/tests/test_production_ai_compose_config.py`.

**تنبيه مهم:** `GEMINI_SEARCH_GROUNDING=false` هو الإعداد الافتراضي في ملفات النشر لتجنّب تفعيل أداة قد تستهلك حصة أو رسومًا دون قرار المشغل. من يريد تشغيل البحث الحي يحتاج إلى ضبطه صراحة على `true` في بيئة الاستضافة، مع `AI_PROVIDER=gemini` و`GEMINI_API_KEY` صالح. هذا **لا يثبت** إجراء بحث حي حتى يعود `groundingMetadata` بمصادر فعلية.

## ما أُعيد اختباره كعميل

أُضيف `backend/scripts/independent_customer_audit.py` لتكرار اختبار HTTP؛ يغطي: صحة الـAPI، جاهزية قاعدة البيانات، إنشاء أسبوع عائلي، إنشاء 30 يومًا، تعديل توزيع المدن مع الحفاظ على الإجمالي، عدم تغيير الرحلة بسؤال الفندق، سؤال مواصلات بالإنجليزية، عدم استقبال بيانات دفع، رفض الحفظ بدون دخول، إنشاء حساب مؤقت، الحفظ والاسترجاع، فصل حسابين، وإبطال الجلسة بالخروج. 17/17 PASS؛ نتائج هذه الجولة في `qa_reports/customer_http_audit_2026-10-30.json`.

## أسباب عدم اعتماد إطلاق تجاري حاليًا

- **لا دليل اتصال Gemini Live ولا دقة بحث Google الحالية.** اختبارات الـMock وOffline لا تمثل الذكاء الاصطناعي الحقيقي.
- **واجهة React والمتصفح غير متحقق منهما على هذه البيئة.** مشكلة تنزيل npm تمنع التثبيت والبناء.
- **التخزين الإنتاجي** ما زال SQLite؛ لا يوجد إثبات لنسخ احتياطي مسترجع، تخزين دائم، اختبارات فقدان السيرفر، أو نظام ترحيل إدارة بيانات للإنتاج.
- **الأسعار والحجوزات والتوافر:** لا توجد تكاملات حجوزات حية معتمدة. يجب ألا ينسب النظام أسعارًا أو مواعيد غير موثقة إلى مزود فعلي.
- **التكلفة والحصص والخصوصية:** استخدام Google Search Grounding وGemini يحتاج مراجعة سياسة بيانات الاستخدام وحدود الفئة المجانية، ومراقبة الاستهلاك عند تحويل الخدمة إلى شركة.
- **`AI_PROVIDER=auto` ليس وعدًا بآلية failover احترافية متعددة المزودين**؛ يلزم اختبارها أو تنفيذها بشكل صريح مع مراقبة حالات العطل.
- **الاختبارات ليست برهانًا على عدم وجود أخطاء** أو على صحة كل معلومة تاريخية أو سياحية.

## إعداد تجريبي على الاستضافة (غير مُعتمد للإنتاج بعد)

ضبط متغيرات البيئة **خارج GitHub وملفات ZIP**:

```dotenv
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
GEMINI_SEARCH_GROUNDING=true
GEMINI_API_KEY=<set-as-private-server-secret>
```

لا تضبط `APP_ENV=production` ولا متغيرات تأكيد التخزين والنسخ الاحتياطي إلا بعد اختبار استرجاع فعلي والتحقق من استدامة البيانات.

**اختبار القبول القادم:** تنفيذ `backend/scripts/run_customer_live_acceptance.py` على سيرفر يستخدم مفتاحًا صالحًا في بيئة مؤمنة، ثم المراجعة البشرية لردود السائحين ومصادر البحث، واختبار بناء React والمتصفح والنشر والنسخ الاحتياطية.
