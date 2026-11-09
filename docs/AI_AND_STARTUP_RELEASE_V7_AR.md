# Masr Guide AI v7.0 — AI, Privacy and Startup Release

**الحالة:** إصدار تطويري متقدم وقابل للاختبار والرفع على GitHub، **ليس** إطلاقًا تجاريًا نهائيًا ولا منصة حجوزات عاملة. لا تدّعِ في مقابلات HR أن الأسعار حية أو أن الشركاء والحجوزات مؤكدة.

## ما تم تنفيذه واختباره

1. **Intent-based conversational routing:** التحيات وطلب تغيير اللغة والأسئلة الواضحة عن المواصلات لا تُرسل خطأً لمحرك استرجاع المعالم. الأسئلة الأخرى تمر عبر RAG للمعلومات السياحية وGemini اختياريًا؛ إنشاء وتعديل الرحلات يمر عبر مخطط برمجي يخضع للتحقق.
2. **Trip intent parsing:** دعم صيغ عربية وإنجليزية مثل «20 يوم: 13 القاهرة و7 البحر»، وأرقام عربية `٢٠`، ومدة 14/20 يومًا، مع توضيح الأيام الحرة عند نقص الأنشطة الموثقة.
3. **Provider failure:** عند تعطل نموذج AI في `/api/consult` تُعاد معلومات محلية محدودة ومصادرها بدل انهيار المحادثة. يتم تمييز هذا الوضع بوضوح. `/api/chat` يظل يعيد 502 للمشكلات التقنية وفق عقد الـAPI القديم.
4. **Conversation memory:** رسائل المتصفح تبقى طوال جلسة المتصفح فقط. يمكن للسائح المسجّل **اختياريًا** حفظ المحادثة على خادم التطبيق، استرجاعها وتحديثها أو حذفها، مع عزل بيانات المستخدمين بواسطة Authentication. لا يتم إرسال المحادثات للتخزين السحابي تلقائيًا.
5. **Bounded inputs:** رسالة 1200 حرف، تاريخ قصير عبر API، حفظ 100 رسالة كحد أقصى لكل محادثة، 1500 حرف للرسالة المخزنة، وحد لحجم التخزين لكل محادثة. Rate limiting موجود لكنه في الذاكرة وعلى مستوى عملية واحدة فقط.
6. **Tourism and business features kept from v6:** صفحات الوجهات والتجارب والمرشد والمخطط والمجلة السياحية، ولوحة Staff، والعروض وإحالات الشركاء ضمن نطاق تجريبي واضح.

## فحوص هذا الإصدار

- `python -m pytest -q` من `backend/`: **99/99** successful locally.
- Python compile: Passed.
- TypeScript compiler **syntax parser** for 29 JS/JSX files: No parse diagnostics. This is **not** a React production build or a browser test.
- `npm ci --offline`: **Blocked** by missing `yocto-queue` in local npm cache (environment limitation); React build, lint and frontend tests **not verified** in this environment.
- Gemini live call, real bookings, partner payout and Render deployment: **not tested and not claimed**.

## GitHub / HR Demo

1. Unzip and open the `Masr_Guide_AI` project root.
2. Configure `backend/.env` **locally** (`GEMINI_API_KEY`, `GEMINI_MODEL=gemini-3.1-flash-lite`) with a new, private key. Never commit the file.
3. Run `RUN_STARTUP_WINDOWS.bat`; open `http://localhost:5173`.
4. Demo discovery pages, tourism content, places, greeting, transport advice, Arabic 20-day travel planning, saved traveler accounts, chat save/restore and show the `/#/project` case study.
5. Verify frontend locally before the first push:
   ```powershell
   cd frontend
   npm ci
   npm test
   npm run lint
   npm run build
   ```
6. Use `.github/workflows/ci.yml` to enforce Python and frontend checks on GitHub; fix any failed checks before presenting the public URL.
7. GitHub **hosts source code, not a continuously running Python server**. Use Render or another web host for the runnable application. SQLite on Render free/ephemeral storage is not reliable for storing real user accounts. Provision a persistent database/volume before real users.

## Business and quality gates — before commercial launch

- **Tourism data:** upgrade beyond 40 curated attractions; verify sources, languages, images, licensing, accessibility and last-updated metadata. No made-up opening hours/prices.
- **AI reliability:** multilingual eval set for history, practical travel, transport, plan changes, out-of-scope questions, prompt injection, unsupported facts; log latency and refusal quality without exposing personal data. Add per-user usage budgets and cost dashboard, provider spend alerts and observability.
- **Trip quality:** day-level visit feasibility, opening hours, verified transfer schedules, route geometry, budget itemization from confirmed prices, family mobility/accessibility needs, cancellation policies and independent QA. Current free-day suggestions are expressly unbooked ideas, **not** a complete 20-day commercial itinerary.
- **Commerce:** actual supplier contracts, licensed operator verification, signed commission agreements, referral conversion reconciliation, fraud controls, cancellation adjustments and audited payout ledger; tracked clicks are NOT confirmed reservations or revenue.
- **Infrastructure:** PostgreSQL migration, managed backups, secure secrets, stronger rate limiting at edge, account deletion/data retention requests, monitoring/error alerts, deployment rollback, OWASP review, domain and email, cookie/privacy policies and relevant legal consultation.

## الإيرادات: متى تبدأ؟

أول مصدر قابل للتحقق هو **عمولة حجز مكتمل** أو **سعر ثابت لكل عميل مؤهل** مع شريك سياحي متعاقد معه. تتبع الضغطات حاليًا مجرد بداية لمسار التحويل؛ لا يثبت حجزًا ولا عمولة. الحساب النموذجي: 50 حجزًا مكتملًا × متوسط عمولة 200 جنيه = 10,000 جنيه **إيرادًا افتراضيًا قبل التكلفة**. يجب إثبات الشروط والأرقام من عقود وتقارير الموردين قبل إدخالها في أي توقع مالي. يمكن لاحقًا اختبار B2B subscription للشركات السياحية، وليس قبل إثبات وجود طلب ودفع فعلي.

**تقييم صريح:** v7 يحسن السلوك الحواري والحفظ والاختبارات بوضوح، لكنه لا يحقق بعد جميع معايير منتج TravelTech جاهز لتشغيل حجوزات عالمية أو أرباح متكررة.
