> **آخر دمج وتحقق بعد استلام v7.8.1 الأصلية:** راجع [docs/LOCAL_ENGINEERING_VALIDATION_2026-10-16_AR.md](docs/LOCAL_ENGINEERING_VALIDATION_2026-10-16_AR.md) و[START_LOCAL_FIRST_AR.md](START_LOCAL_FIRST_AR.md). النتيجة الحالية 233/233 Backend و6/6 Node contracts. الأرقام التاريخية أدناه موثقة لمرحلتها وليست أحدث النتائج.

# Masr Guide AI — تسليم سورس المشروع كاملًا واستكمال المحادثة السابقة

**تاريخ العمل:** 16 أكتوبر 2026

هذه حزمة السورس الكاملة للمشروع الذي بدأ في المحادثة السابقة، وليست مشروعًا جديدًا أو نسخة محادثة بديلة. راجع `docs/MASTER_PROMPT_MASR_GUIDE_AI.md` لاتفاق نطاق المشروع. لا يدل اسم الملف أو نجاح اختبارات جزئية على جاهزية تجارية مثبتة.

## محتويات الأرشيف

- `frontend/`: React 18 وVite، منصة استكشاف الوجهات والمعالم والتجارب، بحث، دعم العربية RTL، محتوى ومجلة، مخطط رحلات، مساعد AI، حاسبة ميزانية، حسابات، مفضلة، بوابة شركاء ولوحة CMS.
- `backend/`: FastAPI، بيانات المعالم مع الاستشهادات، Planner محدد السلوك وتوزيع الأيام، Router للمحادثات والتعديلات، تكامل Gemini اختياري، RAG مبني على كتالوج محلي، حسابات وحفظ ومزامنة الرحلات والمحادثات والمفضلة، CMS وإحالات.
- `scripts/`: فحوص HTTP والضغط والتحقق من المتصفح وGemini والأسرار وعمليات النسخ الاحتياطي.
- `.github/workflows/ci.yml`, `Dockerfile`, `docker-compose*.yml`, `render.yaml`: إعدادات البناء والاختبارات والنشر.
- `docs/`: متطلبات المنتج، المعمارية، التقييمات السابقة، وقرار الإطلاق الصريح.

## التحسينات المضافة في متابعة هذه المحادثة

1. **مفضلة الحساب:** جدول `account_favorites`، إضافة/قراءة/حذف عبر API بتفويض مالك الحساب، حد 500 مكان، التأكد من وجود المكان في الكتالوج، ومنع التكرارات. المفضلة المحلية للزوار تعمل دون حساب؛ عند تسجيل الدخول تُعرض بيانات حساب المسافر فقط ولا تُرفع المفضلة المجهولة تلقائيًا. الواجهة تعيد الحالة السابقة عند فشل طلب التحديث.
2. **تصدير بيانات المسافر:** `GET /api/my/export` وواجهة لتنزيل JSON للرحلات والمحادثات والمفضلة الخاصة بالحساب. لا يتضمن كلمة السر أو الهاش أو جلسات الدخول أو بيانات حساب آخر، وتستخدم الاستجابة `Cache-Control: no-store`.
3. **حماية المعاينات المجانية:** إذا كانت `APP_ENV=portfolio` والتخزين المستمر غير مؤكد، تُوقف عمليات تسجيل حسابات جديدة ويظهر التوضيح بالواجهة. لا ينبغي تقديم تخزين مؤقت للمستخدم على أنه حساب دائم.
4. **اختبارات جديدة:** أربعة Backend tests للأمان وعزل الحسابات وسقف المفضلة والتصدير ومعاينة التخزين المؤقت، وستة HTTP checks فعلية (ضمن 27 فحصًا). أضيف سيناريو مفضلة للمتصفح في CI، لكن **لم يتم تنفيذه** بسبب حجب Chromium وعدم تثبيت حزم الواجهة.
5. **حفظ الإصلاحات السابقة:** توزيع أيام المدن، منع خطط لا تطابق قيود السائح، حفظ الحوارات، التحقق من طلبات AI قبل تعديل البيانات، وثوابت Planner.

## نتيجة التنفيذ في البيئة الحالية

| الفحص | الدليل | الحالة |
|---|---|---|
| Backend `pytest -q` | 232 اختبارًا ناجحًا (السجلات في `qa_reports/`) | VERIFIED |
| Offline chatbot corrected acceptance | 52 من 52 | VERIFIED OFFLINE |
| Stress invariants | 18,000 من 18,000 | VERIFIED |
| HTTP+mock-provider localhost | 27 من 27 (تشمل مفضلة وحذف حساب وتصدير) | VERIFIED |
| Nginx localhost | 4 من 4 | VERIFIED |
| Node data-contract | 4 من 4 | VERIFIED |
| JS/JSX syntax parse | 30 ملفًا دون أخطاء تركيب باستخدام TypeScript محلي | VERIFIED (syntax ONLY) |
| React `npm ci`, production build, lint and Vitest | `yocto-queue` غير موجود بالكاش؛ `registry.npmjs.org` لا يتحول عبر DNS | BLOCKED |
| Chromium E2E للـReact والـdemo | `ERR_BLOCKED_BY_ADMINISTRATOR` حتى عند HTTP 200 للـdemo | BLOCKED |
| Gemini live | لا يوجد مفتاح مخول في البيئة | NOT EXECUTED |
| Docker image build/cloud deployment | Docker غير متاح ولم يتم نشر بيئة سحابية | NOT EXECUTED |
| PostgreSQL/نسخ احتياطي إنتاجي مُدار | غير منفذ في هذا السورس | NOT IMPLEMENTED |
| عقود شركاء/حجوزات/عائدات/دفع حقيقي | لا توجد تكاملات تجارية معتمدة | NOT IMPLEMENTED |

**مهم:** اختبارات API الداخلية لا تثبت تشغيل تجربة React، وتقارير `qa_chatbot` offline لا تساوي Gemini حيًا، واختبارات الضغط لا تثبت أسعارًا أو تذاكر قابلة للحجز.

## تشغيل السورس عندك — Windows / VS Code

المطلوب Python 3.11+ وNode.js 20+، ويفضل Node 22.

### الطرفية الأولى
```powershell
cd Masr_Guide_AI\backend
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload --port 8000
```
### الطرفية الثانية
```powershell
cd Masr_Guide_AI\frontend
npm ci
npm test
npm run lint
npm run build
npm run dev
```

- الموقع الأساسي: `http://localhost:5173` — لا تخلط بينه وبين `/demo` البسيط.
- Swagger API: `http://localhost:8000/docs`.
- شغل `VERIFY_FULL_RELEASE_WINDOWS.bat` قبل اعتبار المشروع جاهزًا، وراجع **نتائج الاختبارات الفعلية**؛ لا يكفي وجود ملف CI.
- أضف مفتاح Gemini جديدًا بنفسك إلى `backend/.env` اعتمادًا على `backend/.env.example`. لا ترفع المفاتيح إلى GitHub ولا تضعها في الواجهة.
- عند بدء نشر خارجي، تحقق من حقوق الصور، قواعد بيانات دائمة والنسخ الاحتياطي، HTTPS، فحوص أمان، اختبارات Gemini الحي، التشغيل الحقيقي للواجهة والمتصفح.

## تصنيف الأنظمة

| النظام | الحالة الحالية |
|---|---|
| اكتشاف مصر والمعالم والمحتوى وCMS | IMPLEMENTED / Backend VERIFIED / Browser BLOCKED |
| مساعد AI والردود متعددة اللغات | IMPLEMENTED / Offline VERIFIED / Gemini live NOT EXECUTED |
| Planner وحفظ توزيع أيام المدن وتعديل الرحلات | IMPLEMENTED / Backend VERIFIED / UI browser BLOCKED |
| الحسابات والرحلات والحوارات والمفضلة والتصدير | IMPLEMENTED / Backend VERIFIED / Cloud durability NOT VERIFIED |
| شركاء وإحالات وإحصاء نقرات | MVP IMPLEMENTED / Real partner contracts NOT IMPLEMENTED |
| React واجهة عربية/إنجليزية وتجربة متجاوبة | SOURCE IMPLEMENTED / React build & browser BLOCKED |
| أمان Backend وحدود أحجام الطلبات وصلاحيات | PARTIALLY VERIFIED / External audit NOT EXECUTED |
| PostgreSQL ونسخ احتياطي سحابي واختبار Disaster Recovery | NOT IMPLEMENTED |
| SEO ديناميكي بنمط SSR / Next.js | NOT IMPLEMENTED |
| حجوزات ودفع وعمولات مثبتة وعوائد | NOT IMPLEMENTED |
| نشر Production حقيقي وصور شاشة مثبتة | NOT EXECUTED |

**التصنيف النهائي:** Complete current source handoff + verified local Backend & integration improvements؛ **لا تصديق لـ production-ready** إلى أن تنجح بوابات الإطلاق المذكورة.
