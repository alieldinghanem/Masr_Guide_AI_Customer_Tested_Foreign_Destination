# رفع Masr Guide AI v2.0 إلى GitHub

هذه حزمة الكود المصدري الكامل لنسخة **MVP**؛ ننصح بإبقائها **Private** حتى اكتمال فحص الواجهة الحي وحقوق الصور، وباقي اختبارات التشغيل.

## تجهيز الملفات

1. فك ضغط الملف ZIP؛ ستجد المجلد `Masr_Guide_AI`.
2. افتحه في VS Code وثبّت Python 3.10+ وNode.js 20+ وGit (وللرفع الآلي GitHub CLI).
3. لتهيئة Gemini شغّل `SETUP_GEMINI_WINDOWS.bat` بعد استخراج مفتاحك من Google AI Studio. يُحفظ المفتاح **محليًا** في `backend/.env`، وهو مستبعد من Git؛ لا تضعه داخل `frontend/` أو README.
4. لتجربة محرك الرحلات فورًا دون npm شغّل `RUN_FREE_DEMO_WINDOWS.bat` ثم افتح `http://localhost:8000/demo`.
5. لتجربة واجهة React شغّل `RUN_BACKEND_WINDOWS.bat` ثم `RUN_FRONTEND_WINDOWS.bat` وافتح `http://localhost:5173`.
6. شغّل `VERIFY_PROJECT_WINDOWS.bat`، وراجع أي أخطاء (خصوصًا تحميل مكتبات npm).

## طريقة الرفع المفضلة (Private)

بعد تسجيل الدخول مرة واحدة إلى GitHub CLI باستخدام `gh auth login`، افتح PowerShell في المجلد وشغّل:

```powershell
.\PUBLISH_PRIVATE_GITHUB.ps1
```

سيحاول السكربت تشغيل اختبارات Backend وFrontend وبناء React ثم يطلب منك موافقة واضحة قبل إنشاء المستودع الخاص ورفع الملفات. **لا ترفع ZIP كما هو إلى مستودع فارغ**؛ المطلوب محتويات المجلد بعد فك الضغط.

بديل يدوي بعد إنشاء مستودع Private فارغ:

```bash
git init
git add .
git status
git commit -m "Initial Masr Guide AI v2 travel consultant MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/masr-guide-ai.git
git push -u origin main
```

استبدل `YOUR_USERNAME` باسم الحساب. تأكد قبل الدفع أن `backend/.env` وملفات المفاتيح غير موجودة في `git status`.

## ماذا بعد الرفع؟

راجع تبويب **Actions**: نجاح اختبارات `backend` و`frontend` و`browser-e2e` ضروري قبل اعتبار واجهة React مختبرة. تسجيل نجاح tests في الماضي لا يعني أن الإنتاج جاهز الآن.

- تشغيل Gemini الحقيقي يحتاج API Key وحصة متاحة؛ لا تختبر بالمفتاح في GitHub Actions العام.
- المستودع ليس نشرًا لموقع حي؛ تحتاج استضافة منفصلة للـReact والـFastAPI.
- لا تحول المستودع إلى Public قبل مراجعة حقوق الصور، والمصادر، ومساهمات أعضاء الفريق الأصلي إن وُجدت.
- لا توجد حجوزات، أسعار حية أو تنقلات لحظية في هذا الإصدار.

انظر `docs/QA_V2_AR.md` و`docs/RELEASE_STATUS_V2.md` للحدود والاختبارات.
