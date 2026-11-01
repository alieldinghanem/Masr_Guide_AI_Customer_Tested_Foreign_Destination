# Masr Guide AI — Startup Foundation v4 (Development Release)

## البدء على Windows
1. فك الضغط وافتح فولدر `Masr_Guide_AI` في VS Code.
2. ثبّت Python 3.11+ وNode.js 20+.
3. من مجلد المشروع شغّل `RUN_STARTUP_WINDOWS.bat`.
4. افتح `http://localhost:5173` وليس `/demo`.
5. من قائمة My Account / حسابي يمكنك تسجيل مستخدم (كلمة مرور 12 حرفًا على الأقل)، الدخول، حفظ الرحلة الموجودة على الجهاز للحساب، عرضها وحذفها.
6. مزايا Gemini تتطلب مفتاحك الجديد في `backend/.env` وليس في React أو GitHub. استخدم `SETUP_GEMINI_WINDOWS.bat` لإعداد المفتاح؛ لا تشارك المفاتيح مع أحد.

## ما تم تنفيذه برمجيًا
- صفحات اكتشاف مصر والوجهات والمعالم والتجارب والمرشد السياحي والمخطط ودليل السفر من v3.
- API لتسجيل حساب ودخول وخروج + جلسات تنتهي بعد سبعة أيام، وكلمات مرور مجزأة PBKDF2 مع Salt.
- API لحفظ وعرض وتعديل وحذف الرحلات بملكية فردية في SQLite داخل `backend/data/traveler.sqlite3`.
- صفحة حساب داخل الموقع تتيح تسجيل الدخول وحفظ البرنامج الذي حفظته محليًا في Planner وعرض الرحلات المحفوظة.
- استقبال اهتمام شريك سياحي اختياري: غير مفعّل افتراضيًا لحين ترتيب الحماية التجارية.
- اختبار لعزل البيانات بين مستخدمين مختلفين + اختبارات الانحدار القديمة.

## ملاحظات صريحة عن الجاهزية
هذه **نسخة تطوير v4** وليست إطلاقًا تجاريًا مكتملًا: لا توجد حجوزات فعلية ولا دفعات أو عمولات أو شركاء معتمدون، ولا لوحة إدارة CMS متكاملة، ولا محرك أسعار موثوقة، ومحرك تخطيط 20 يومًا ما زال يحتاج إثراء البيانات منعًا للأيام الفارغة. لم يتم تأكيد بناء React في بيئة التسليم بسبب تعذر تحميل npm dependencies. تخزين SQLite مناسب لتطوير محدود، وليس بديلاً عن PostgreSQL المُدار في الإنتاج. الحسابات لا تتضمن إثبات ملكية البريد، إعادة تعيين كلمة المرور، الحماية المتقدمة من brute-force، أو نظام رقابة/مراقبة كامل.

## قبل نشر الموقع للعامة
- استبدال SQLite بنظام PostgreSQL مُدار مع ترحيلات ونسخ احتياطية وسياسة حذف بيانات.
- تأكيد البريد وإعادة تعيين كلمة المرور وMFA للإدارة، وحماية Login من brute-force، واختبارات أمن واختبارات E2E.
- استخدام HTTPS، وSecret rotation، وCSP/CSRF حسب تصميم الجلسات، ونظام محدودية API tokens، وإشعارات إساءة الاستخدام.
- CMS، ولوحة شركاء، ومخزون خدمات مثبت، واتفاقات شراكة، والتزام قانوني وخصوصية.
- تحسين محتوى الوجهات ومواعيد عمل المعالم، وتطوير إنشاء خطط أطول دون أيام فارغة.

## تشغيل الاختبارات
`cd backend`
`python -m pip install -r requirements.txt pytest httpx`
`python -m pytest -q`

`cd ../frontend`
`npm ci`
`npm run build`
`npm test -- --run`

## نقاط النهاية الجديدة
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout` (Bearer token)
- `GET /api/auth/me` (Bearer token)
- `GET/POST /api/my/trips` (Bearer token)
- `GET/PUT/DELETE /api/my/trips/{id}` (Bearer token)
- `POST /api/partners/apply` (disabled by default, set `PARTNER_INQUIRIES_ENABLED=true` only once anti-spam/privacy practices are implemented)
