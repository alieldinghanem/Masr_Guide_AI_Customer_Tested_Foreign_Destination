# Masr Guide AI — Source comparison, fixes and local release gates

**تاريخ:** 16 أكتوبر 2026 — **الحالة:** نسخة سورس متكاملة للاختبار المحلي؛ ليست Production-Ready معتمدة.

## مرجع الدمج

- المرجع الأصلي من الشات السابق: `Masr_Guide_AI_Final_Portfolio_Source_v7_8_1(1).zip` (181 ملفًا).
- المرجع المستكمل في المحادثة الحالية: `Masr_Guide_AI_Full_Source_Continuation_2026-10-16.zip` (200 ملف).
- مقارنة SHA-256 على جميع المسارات: **لا توجد ملفات من الأصل مفقودة في النسخة المستكملة**. أضيف 19 ملفًا مع الحفاظ على قاعدة السورس، وتعدّلت 18 ملفات قائمة مقارنة بالأصل. بعد هذه المراجعة أُضيفت اختبارات وتقارير وملفات تشغيل أخرى. لم تُعَد كتابة المشروع من الصفر.

## إصلاحات منفذة هنا بعد مقارنة النسختين

1. **حفظ تحديث نفس رحلة المستخدم:** أزرار حساب المسافر تسمح بفتح رحلة محفوظة في Planner، ثم استعمال الرحلة المحلية الجديدة لتحديث **السجل المحدد** عبر `PUT /api/my/trips/{id}` مع `If-Match` لحماية تعديلات الأجهزة المتزامنة. في حالة `409` تُعرض رسالة واضحة بدل الكتابة فوق تعديل أحدث. تُقرأ المسودة الأحدث من `sessionStorage` قبل خطة محلية أقدم. يحتاج هذا المسار لتأكيد Chromium UI؛ API نفسه اختُبر.
2. **اختبار رحلات متكامل مستقل:** اختبار HTTP لرحلة 20 يومًا (13 القاهرة + 7 الغردقة)، واستبدال الغردقة بشرم الشيخ، ثم تحديث السجل واسترجاعه والتحقق من حماية حساب ثان ومنع التعديل بإصدار قديم.
3. **تدقيق حدود بيانات React:** اتضح أن الحارس كان يمرر بيانات انتقال سالبة أو حقولًا محرفة كانت ستُرفض على السيرفر. جرى تشديد `isValidItinerary` وإضافة `isValidPlannerPlan` لمنع عرض بيانات route/warnings/stops غير المتوافقة، وتحصين قراءات وسائل النقل الناقصة. اختبارات Node بلا npm تبرهن سلوك الحراس، لا سلوك واجهة React.
4. **إصلاح إعداد اختبار المتصفح:** أداة التحقق السابقة كانت تبدأ E2E في وضع `portfolio` الذي يعطّل عمدًا تسجيل الحسابات على قواعد مؤقتة، رغم أن اختبار المتصفح نفسه يتطلب التسجيل. E2E المعزول أصبح يستخدم `development` مع قاعدة مؤقتة تنتهي بانتهاء الاختبار. أضيف مسار فتح الرحلة المحفوظة وتحديثها لسيناريو Chromium، لكنه **لم يُنفذ** في هذه البيئة.
5. **تشغيل مبدئي أوضح على Windows:** `SETUP_AND_TEST_LOCAL_WINDOWS.bat` يثبت Python/npm اعتمادًا على lockfile ويشغّل الفحوص، و`START_LOCAL_FIRST_AR.md` يشرح التجربة الفعلية وGate التحقق قبل GitHub.

## نتائج نفذتها في البيئة الحالية بعد التغييرات

| الاختبار | النتيجة | الإثبات |
|---|---|---|
| Backend `python -m pytest -q` | **233/233 PASS** | `qa_reports/backend_pytest_after_merge_2026-10-16.txt` |
| Node trip data contracts | **6/6 PASS** | `qa_reports/frontend_node_contract_after_merge_2026-10-16.txt` |
| Corrected offline tourism QA | **52/52 PASS** | `qa_reports/chatbot_offline_after_merge_2026-10-16.txt` |
| Planner invariants | **18,000 assertions PASS** | `qa_reports/planner_stress_after_merge_2026-10-16.txt` |
| Retrieval evaluation | 49 answerable cases؛ hit@3 = 1.00؛ 4 no-answer cases | `qa_reports/retrieval_eval_after_merge_2026-10-16.txt` |
| Real HTTP + mocked provider | **27/27 PASS** | `qa_reports/http_integration_after_merge_2026-10-16.txt` |
| Local Nginx syntax/routing/proxy/rate | **4/4 PASS** | `qa_reports/nginx_integration_after_merge_2026-10-16.txt` |
| Python compileall | **PASS** | تم التنفيذ مباشرة |
| JS/JSX static syntax parser | **30 files parsed without errors** | `qa_reports/jsx_static_parse_after_merge_2026-10-16.txt` |
| Best-effort source credentials scan | **PASS** | `qa_reports/source_secret_scan_after_merge_2026-10-16.txt` |

## لم ينجح في بوابة الاعتماد أو لم يُنفذ

| الاختبار/الميزة | الحالة | التفسير |
|---|---|---|
| `npm ci` + Vitest + ESLint + Vite production build | **BLOCKED** | `npm ci --offline` يطلب `yocto-queue` غير موجود بالكاش، ومحاولة npm المتصلة فشلت بخطأ في npm CLI. لا توجد حزم frontend مثبتة للتأكد من البناء في هذه البيئة |
| React desktop/mobile Chromium E2E | **BLOCKED** | لا يوجد React `dist` مبني؛ محاولة Chromium السابقة اصطدمت كذلك بقيد سياسة البيئة. وجود سيناريو E2E في الكود لا يعني نجاحه |
| Real Gemini API request and response evaluation | **NOT EXECUTED** | لا يوجد مفتاح سري جديد مصرح باستخدامه هنا؛ الـoffline tests ليست Gemini حيًا |
| Docker image build/public cloud smoke | **NOT EXECUTED** | لا توجد بيئة Docker/استضافة منشورة تم فحصها |
| PostgreSQL مع migration + managed backup/restore | **NOT IMPLEMENTED** | محليًا يستخدم SQLite؛ لا يُعرض كمخزن Production durable مضمون |
| Real travel bookings, payments and commissions | **NOT IMPLEMENTED** | لا توجد عقود أو معاملات شركاء حقيقية؛ فقط بنية محتوى وإحالات ومؤشرات أولية |
| Next.js/SSR dynamic editorial SEO | **NOT IMPLEMENTED** | الواجهة الأساسية ما زالت React/Vite Client-Side؛ لا ندّعي SEO مكافئًا لموقع SSR |
| Penetration test/performance load on production host | **NOT EXECUTED** | لا توجد بيئة إنتاجية لتجريبها |

## الحكم

هذه **أحدث حزمة مصدر متكاملة جاهزة لمرحلة تشغيل المستخدم Local واختبارها**، وليست إثباتًا بأن كل شيء يعمل في المتصفح ولا نسخة تجارية Production-Ready. عند تشغيل جهاز متصل بـnpm، نفّذ `SETUP_AND_TEST_LOCAL_WINDOWS.bat` ثم `RUN_STARTUP_WINDOWS.bat` واتبع `START_LOCAL_FIRST_AR.md`.

بمجرد نجاح QA الأساسي محليًا يمكن رفع المستودع إلى GitHub مع توثيق الشاشات الحقيقية، ثم الانتقال إلى اختبارات النشر والتخزين الدائم والمراقبة قبل فتح حسابات عامة. لا تنشر مفاتيح API أو بيانات الاختبار.
