# ابدأ من هنا — Masr Guide AI v5.0

ده **Portfolio Release قابل للتطوير** لمشروع TravelTech، وليس منصة حجوزات تجارية مكتملة أو شركة مرخصة.

## أقصر طريق لتشغيله على Windows

1. فك ضغط المشروع وافتح فولدر `Masr_Guide_AI` نفسه في VS Code.
2. شغّل `RUN_STARTUP_WINDOWS.bat` (لازم Python وNode.js يكونوا متثبتين وعندك Internet لتثبيت مكتبات الواجهة أول مرة).
3. افتح `http://localhost:5173`، وابدأ من Home (مش `/demo`).
4. لو عايز Gemini حي، افتح `backend/.env.example` واعمل نسخة منه في `backend/.env` وأضف **مفتاح جديد لم يتم نشره**. لا تشاركه ولا ترفعه مع المشروع.

**Docker (اختياري):** لو Docker Desktop موجود، شغّل `RUN_DOCKER_PORTFOLIO_WINDOWS.bat` وبعدها افتح `http://localhost:8000`.

## أقسام الموقع الموجودة فعليًا

- الرئيسية / Explore / Destinations / Experiences / Travel Tips
- Journal مقالات يمكن تحديثها من Staff Console
- AI Guide (Gemini لو اتضبط) + Smart Planner حتى 30 يومًا + Budget Calculator
- Favorites + حسابات وحفظ الرحلات
- Partner Offers + Partner Enquiry + Dashboard الإدارة
- Project Case Study عبر `/#/project` لإظهار التقنية للـHR

## إعداد لوحة الإدارة

من PowerShell داخل فولدر المشروع شغّل:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

انسخ القيمة **لنفسك فقط** في `backend/.env` كالتالي `ADMIN_API_TOKEN=...`، ثم أعد تشغيل الـBackend وافتح `http://localhost:5173/#/staff`.

**ما فيش حساب Admin افتراضي أو مفتاح مُضمن**، ودي نقطة أمان مقصودة.

## قبل GitHub

من المشروع:

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
cd ..\frontend
npm ci
npm test
npm run lint
npm run build
```

الفحص الكامل لـReact لازم ينجح **عندك**؛ اختبارات الـBackend اجتازت 88/88 في بيئة تجهيز النسخة، لكن `npm ci` ما اكتملش هناك. خطوات GitHub/Render كلها موثقة في `docs/DEPLOY_GITHUB_RENDER_AR.md`.

## تنبيه مهم

- **GitHub لحفظ الكود وليس سيرفر لتشغيل FastAPI**. Render يشغّل الموقع والـAPI في Docker واحد.
- Render Free Storage مش ثابت؛ لحسابات وبيانات حقيقية، استخدم استضافة ببيانات دائمة ونسخ احتياطي.
- لا تدّعي حجوزات مباشرة أو عمولات أو شركاء متعاقدين؛ قسم العروض الخارجية لا ينشر شيئًا حتى تراجعه وتفعّله.
