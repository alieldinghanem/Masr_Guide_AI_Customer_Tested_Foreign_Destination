# ابدأ من هنا — Masr Guide AI Commercial Pilot Candidate (30 Oct 2026)

هذا هو **السورس الموحد الذي يواصل تطوير المشروع السابق**. لا تتعامل معه كنسخة تشغيل تجاري معتمدة قبل اجتياز شروط `COMPANY_RELEASE_GATE_AR.md`.

## التجربة المحلية

- Windows: شغّل `OPEN_WEBSITE_WINDOWS.bat` بعد تثبيت Python 3.11+ وNode.js 22 ومع اتصال إنترنت لتثبيت حزم npm.
- لا تفتح `http://127.0.0.1:5173/` إلا بعد `[READY]`. الرابط محلي على نفس الجهاز فقط.
- لو فشل المشغّل، اقرأ `.local-logs/frontend-build.log` و`.local-logs/npm-install.log`؛ فشل بناء React لا يعني أن الـAPI معطّل.
- لتشغيل Gemini ضع مفتاحك في `backend/.env` (غير مرفق وغير قابل للنشر)، ثم شغّل `TEST_GEMINI_CONVERSATION_WINDOWS.bat` واختبر المحادثة من الواجهة أيضًا.

## قبل النشر

شغّل `python scripts/check_company_release.py` من جذر السورس. يُخرج حالات `PASS` و`BLOCKED` و`NOT EXECUTED` و`NOT VERIFIED` في `qa_reports/company_release_gate.json`. كود الخروج غير الصفري طبيعي طالما الاختبارات الحاسمة ناقصة.

- GitHub لحفظ الكود وCI، وليس سيرفر API.
- استضافة الإنتاج تحتاج TLS ونطاقًا خاصًا وتخزينًا دائمًا وسجلات مراقبة، وإعداد مفاتيح في Secret Manager، واختبار استعادة بيانات، والتحقق القانوني والتجاري.
- لا تفعل `APP_ENV=production` إلا بعد ملء شروط `COMPANY_RELEASE_GATE_AR.md` وإثباتها خارج الكود. مجرد متغير بيئة `BACKUP_RECOVERY_VERIFIED=yes` ليس دليلًا على نجاح الاسترجاع.

## النتيجة المثبتة وقت التسليم

- Backend: 301/301 اختبار ناجح، بما فيها اختبارات جديدة لضوابط تشغيل الإنتاج.
- رحلة عميل حقيقية عبر HTTP: 11/11 فحصًا ناجحًا في الوضع Offline.
- Planner: 18,000/18,000 تحقق في مجموعة السيناريوهات المنفذة.
- Frontend contracts: 12/12 ناجحة.
- React Build وChromium E2E وGemini الحقيقي **غير متحقق منها في هذه البيئة**؛ لا يتم إعلانها ناجحة.
- الحجوزات والمدفوعات المباشرة وPostgreSQL المُدار ليست منفذة.
