# نشر Masr Guide AI على GitHub وRender — خطوات بالعربي

**GitHub مش سيرفر لتشغيل FastAPI.** هو مكان الكود وCI والتاريخ البرمجي. GitHub Pages يستضيف مواقع Static فقط؛ لكن المشروع عندنا React + FastAPI + قواعد بيانات، فهننشره على استضافة مثل **Render** بخدمة Docker واحدة.

## 1) اختبر محليًا قبل الرفع

من فولدر المشروع `Masr_Guide_AI`:

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

لو فشل أي أمر، **متعتبرش المشروع جاهز للنشر**. ممكن ترجع لروت المشروع وتجرب `RUN_STARTUP_WINDOWS.bat` للتطوير العادي. لو عندك Docker Desktop استخدم `RUN_DOCKER_PORTFOLIO_WINDOWS.bat` لاختبار النسخة المدمجة محليًا.

## 2) حضّر GitHub Repository

1. افتح GitHub → New repository → اسم مقترح `masr-guide-ai`.
2. اختار **Private** لو عايز تحافظ على الكود، أو **Public** لو عايز HR تشوفه بدون دعوتها كمتعاونة. ممكن الـRepo يبقى Private والموقع نفسه Public على Render.
3. اختار **بدون README أو .gitignore إضافي** لأنهم موجودين.
4. من VS Code Terminal داخل جذر المشروع:

```powershell
git init -b main
git add .
git status
git commit -m "Portfolio release: Masr Guide AI TravelTech MVP"
git remote add origin https://github.com/YOUR_USERNAME/masr-guide-ai.git
git push -u origin main
```

بدّل `YOUR_USERNAME` باسم حسابك. **افحص `git status` قبل الالتزام** وتأكد إن `backend/.env` أو أي مفتاح Gemini مش مضاف. لا ترفع مفتاح API قديم سبق نشره في محادثة؛ ألغيه واستخدم مفتاحًا جديدًا خاصًا.

## 3) النشر على Render

1. افتح https://dashboard.render.com/، سجل دخولك واعمل ربط بحساب GitHub بإذنك.
2. أنشئ **Blueprint** واختر مستودع `masr-guide-ai` اللي رفعته. الملف `render.yaml` يعرّف Docker Web Service.
3. لو Render طلب منك `GEMINI_API_KEY` أدخل **مفتاحًا جديدًا خاصًا** في إعدادات Environment، ولا تخزنه في Git.
4. `ADMIN_API_TOKEN` اختياري للوصول للـCMS؛ توليده بأمان على جهازك:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

خزّنه كمتغير سري في Render، ومتبعتوش في الشات. لو متحطش، لوحة الإدارة تظل معطلة بشكل آمن.
5. اترك `PARTNER_INQUIRIES_ENABLED=false` في العرض العام الأول، إلا لو مجهز سياسة خصوصية وتشغيل لدعم الشركات.
6. انتظر Build/Deploy. عند النجاح افتح رابط Render (`https://...onrender.com/`)، وبعدها افتح `/api/health` و`/#/project`.

> **تحذير مهم:** خدمة Render المجانية تعيد إنشاء مساحة التخزين المحلية؛ بيانات الحسابات والرحلات والمقالات المعدلة وطلبات الشراكة لا تعتبر دائمة على Free. للعرض أمام HR: اعرض تجربة الموقع والـAI، واستخدم بيانات وهمية فقط. لتسجيل مستخدمين حقيقيين استخدم **Persistent Disk مدفوع** أو قاعدة بيانات PostgreSQL مُدارة بعد تطوير الدعم اللازم. احتفظ بنسخ احتياطية وراجع امتثال الخصوصية قبل التعامل مع بيانات العملاء.

## 4) إزاي تتأكد إن الموقع شغال فعلًا؟

1. Home تعرض معالم مصر، وتقدر تتنقل إلى Destinations وExplore وExperiences وJournal.
2. `/api/health` يرجع `status: ok`.
3. Planner يعمل 14 يومًا ويعرض أيام وأنشطة؛ خطة 20 يومًا تحتوي أيامًا حرة بأفكار واضحة (مش حجوزات وهمية).
4. Budget Calculator يقبل الأرقام اللي السائح يدخلها.
5. AI Assistant: اسأله عن الكرنك. لو Gemini غير مفعّل، يشتغل وضع المساعدة المحلي بقدرات أقل.
6. حساب اختباري يقدر يحفظ رحلة. لا تختبر بيانات شخصية حقيقية على Free.
7. تأكد من GitHub Actions → CI → **Backend + Frontend ✅** قبل إرسال الرابط للـHR.

## 5) رابط المشروع في CV / LinkedIn

Project: **Masr Guide AI | Full-Stack AI TravelTech Platform**

Tech: React, Vite, FastAPI, Python, Gemini API, RAG, SQL/SQLite, Docker, GitHub Actions.

GitHub: `https://github.com/YOUR_USERNAME/masr-guide-ai`

Live Demo: `https://YOUR_RENDER_SERVICE.onrender.com`

**ما تكتبش روابط افتراضية في الـCV**؛ بدلها بالروابط الفعلية بعد النشر والاختبار. لو المشروع Private، الـHR هتقدر تشوف الـLive Demo لكن مش ملفات المستودع إلا لو منحتها صلاحية.
