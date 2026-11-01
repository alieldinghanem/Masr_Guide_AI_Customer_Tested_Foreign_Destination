# Masr Guide AI — TravelTech Startup | Sprint 1 Delivery

**الحالة:** إصدار أولي للتطوير v3.0 (ليس خدمة حجوزات تجارية جاهزة للإطلاق).
**تاريخ النسخة:** 15 أكتوبر 2026.

## تعريف المنتج
منصة تسويق واكتشاف مصر للمسافر الأجنبي والعربي، تجمع المحتوى السياحي، قاعدة بيانات المعالم، اكتشاف التجارب، مرشد ذكاء اصطناعي، تخطيط الرحلات، ودليل السفر. لا تضع الـChatbot كواجهة المنتج الوحيدة.

## ما تم تنفيذه فعلًا

- صفحة Home أصبحت تعرض معالم ووجهات وتجارب، ثم تعرّف بالمساعد الذكي لاحقًا.
- صفحة `Destinations` بها 12 وجهة وتصنيفات حسب التاريخ والبحر والواحات والطبيعة، وعدد المعالم مرتبط فعليًا بالكتالوج الأصلي.
- صفحة `Experiences` بها 8 فئات تفاعلية، ويمكن منها فتح المعالم ذات العلاقة أو سؤال المرشد.
- صفحة `Travel tips` تحتوي روابط رسمية للتأشيرات والمعالم والتذاكر ومعلومات وزارة السياحة؛ دون ادعاء امتلاك أسعار لحظية.
- صفحة `Saved places` تحفظ المعالم في LocalStorage، وتسمح بإزالتها والرجوع إلى مكانها. هذا ليس نظام حسابات أو مزامنة بين الأجهزة.
- مكوّن Explore يسمح بحفظ أي معلم مباشرة.
- إضافة APIs: `GET /api/discover/destinations` و`GET /api/discover/experiences` و`GET /api/discover/essentials`.
- الحفاظ على Backend Planner وGemini AI وRAG والخرائط الموجودة سابقًا. لا يتطلب نشر المفتاح في الواجهة.
- سكربت Windows لتشغيل واجهة React الأساسية والـBackend بسهولة `RUN_STARTUP_WINDOWS.bat`، وإصلاح قبول صيغتي مفاتيح Gemini `AQ.` و`AIza` ضمن سكربت الإعداد.
- إصلاح التوجيه في تعليمات الإعداد إلى الموقع الحقيقي localhost:5173، وليس Demo localhost:8000/demo.

## كيفية التشغيل على Windows
1. فك الضغط وافتح مجلد `Masr_Guide_AI` من VS Code.
2. تأكد من Python 3.10+ وNode.js 20+ واتصال إنترنت لتنزيل dependencies أول مرة.
3. اضغط مرتين على `RUN_STARTUP_WINDOWS.bat` أو شغّل `./RUN_STARTUP_WINDOWS.bat` من PowerShell.
4. انتظر حتى نافذتي Backend وFrontend تبدأان. افتح **http://localhost:5173**.
5. للمرشد Gemini: أنشئ مفتاحًا خاصًا جديدًا من Google AI Studio، وشغّل `SETUP_GEMINI_WINDOWS.bat`. لا ترفع `backend/.env` أو المفتاح إلى GitHub.
6. الميزة البديلة بدون Node تعمل على `/demo` لكنها **الشاشة القديمة المصغرة**، ولا تعرض منصة TravelTech الجديدة.

## ما لم يتم تنفيذه — متطلبات قبل إطلاق Startup للجمهور

| النظام | الحالة | معيار التسليم المستقبلي |
|---|---|---|
| Accounts & Cloud Trips | غير منفذ | Auth آمن، PostgreSQL، حفظ متزامن مع خصوصية البيانات |
| CMS / Admin | غير منفذ | صلاحيات إدارة، رفع وتوثيق الصور، دورة نشر ومراجعة |
| True destination editorial | جزئي | محتوى متنوع مرخص وموثق لكل مدينة، صور فعلية عالية الجودة |
| SEO | جزئي | Next.js/SSR أو Static Generation، sitemap, structured data, metadata، multilingual routes |
| Budget Engine | غير منفذ | أسعار مؤكدة ومؤرخة، حدود ميزانية، إدارة عملات ومجموعة المسافرين |
| Booking affiliate | غير منفذ | اتفاقات شركاء فعلية، deep links معتمدة، conversion reconciliation |
| Partner Portal | غير منفذ | تسجيل الشركات والتحقق والتعاقد وإدارة التجارب والعروض |
| Payments | غير منفذ | عدم تحصيل أموال من السائح دون قانون وعقود وPCI/payment provider |
| Analytics | غير منفذ | Event taxonomy، attribution، funnel وconsent |
| Public production | غير منفذ | CI, monitoring, rate limiting, backups, security reviews, legal policies |

## مكونات النظام القادمة

```text
[Next.js / Frontend]
  Home + Destinations + Attractions + Experiences + Essentials
  Traveler accounts + Saved + Trip Workspace + AI Companion
                 |
            [FastAPI]
  Auth | Content | Search | Planner | AI Tools | Partners | Analytics
         |                         |
  [PostgreSQL + pgvector]    [Gemini + retrieval + tool validation]
         |
  [Object storage / CMS / publisher workflow]
         |
  [Maps] [Licensed tour suppliers] [Affiliate tracking] [Payments (later)]
```

### Design rules
- لا تعرض رابط حجز ما لم تكن هناك شركة مرخصة وعرض رسمي يمكن التحقق منه.
- لا تعتبر ذكر اسم شركة خدمات إقرارًا بوجود شراكة.
- لا تجمع بيانات خاصة عن السائح دون سياسة خصوصية واتفاق واضح.
- المعلومات الثابتة تُحرر في CMS مع المصدر وآخر مراجعة؛ الأسعار والمواعيد تكون من موفر البيانات أو تميّز كغير مؤكدة.
- احتفظ بخطة الرحلة ككيانات structured data، وليس نص LLM فقط. أي AI Tool يكتب تعديلات بعد تحقق الـBackend.

## Sprint 2 المقترح
1. بناء PostgreSQL migrations + traveler auth + REST API للرحلات المحفوظة.
2. CMS قائم على أدوار admin/editor + محتوى للوجهات + إدارة تراخيص الصور.
3. صفحات وجهات قابلة للفهرسة بـSEO (Next.js أو بديل SSR) وعناوين لغات مختلفة.
4. قياس التحويل funnels دون تتبع بيانات حساسة دون موافقة.

## Sprint 3 المقترح
1. شراكات حقيقية مع مزودي أنشطة مرخصين، ثم Trackable offers & redirect مع reconciliation.
2. محرك تكلفة للرحلات مدعوم بأسعار يتم تحديثها من الشركاء.
3. تحسين Planner وتجربة الـAI متعددة الأدوات، عبر اختبارات محادثة فعلية بالعربية والإنجليزية.
4. اختبارات E2E للرحلة من Discover إلى Save/Plan إلى Booking handoff.

## حدود الاختبار الحالية
تمت اختبارات الـBackend وقراءة syntax لمكونات JS/JSX باستخدام TypeScript parser. عدم توفر npm dependencies في بيئة التسليم منع تنفيذ `npm test`, `npm run build` والفحص البصري المباشر للواجهة؛ يجب تنفيذها محليًا أو في GitHub Actions قبل اعتبارها Production-ready. لم يتم استخدام مفتاح Gemini فعلي في بيئة التسليم.
