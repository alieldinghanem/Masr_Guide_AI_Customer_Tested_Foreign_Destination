# شغّل منصة Masr Guide AI الجديدة — v3

**ابدأ من هنا، وليس من `/demo`.**

### المتطلبات
Windows، Python 3.10 أو أحدث، Node.js 20 أو أحدث، وإنترنت لتثبيت المكتبات أول مرة.

### خطوة واحدة
من داخل مجلد المشروع شغّل:

```powershell
.\RUN_STARTUP_WINDOWS.bat
```

هيفتح نافذتين (Backend وFrontend). أول تشغيل قد يأخذ وقتًا لتثبيت المكتبات. بعد ما الخدمات تبدأ، افتح:

**http://localhost:5173**

- الصفحة الرئيسية: ترويج مصر ووجهات ومعالم وتجارب.
- Destinations: مدن ومناطق مصر.
- Discover: المعالم والخريطة وحفظ المفضلة.
- Experiences: الأنشطة حسب اهتماماتك.
- Travel tips: روابط رسمية للاستعداد للسفر.
- Trip planner: بناء برنامج رحلة وحفظه محليًا.
- AI guide: مرشد سياحي (Gemini اختياري).
- Saved places: أماكنك المحفوظة على جهازك.

### تشغيل Gemini
بعد إلغاء أي API Key سبق نشره، أنشئ مفتاحًا جديدًا من Google AI Studio، ثم شغّل:

```powershell
.\SETUP_GEMINI_WINDOWS.bat
```

احفظ المفتاح في الجهاز فقط. ملف `backend/.env` لا يجب رفعه إلى GitHub.

### مهم
- العنوان `http://localhost:8000/demo` هو **الـDemo القديم المصغر** فقط.
- المنصة الجديدة تتطلب React على `http://localhost:5173`.
- ده أول Sprint فعلي؛ مش مكتمل نظام Accounts أو Paid Booking.
- إن ظهر خطأ Install من npm، تأكد أن Node.js متثبت وأن الإنترنت متاح ثم أعد تشغيل أمر Startup.

للتفاصيل التقنية والـRoadmap: `docs/STARTUP_V3_IMPLEMENTATION_AR.md`.
لتصميم الإيرادات: `docs/BUSINESS_MODEL_AND_REVENUE_AR.md`.
