# Masr Guide AI — Full-stack verification report

**تاريخ المراجعة:** 31 أكتوبر 2026  
**المصدر:** آخر ملف `Masr_Guide_AI_FullStack_ChatFirst_Reviewed_2026-10-31.zip` المفكوك في بيئة مستقلة.  
**حالة التسليم:** نسخة سورس كاملة للاختبار المحلي والفريق، **وليست اعتمادًا للإطلاق العام**.

## اختبارات تم تنفيذها فعليًا في هذه المراجعة

| الاختبار | النتيجة | النطاق |
|---|---:|---|
| Backend pytest | **372/372 PASS** | من ملفات الحزمة الأصلية |
| Chatbot Offline acceptance | **52/52 PASS** | قواعد المحادثة والرد المحلي؛ لا يشمل Gemini |
| Node JS contracts | **21/21 PASS** | منطق تصنيفات الأماكن والشات وصحة الـTrip contract؛ ليس React Build |
| FastAPI HTTP customer smoke | **10/10 PASS** | Uvicorn محلي وقاعدة بيانات اختبارية |
| Customer journey HTTP | **11/11 PASS** | حسابات وحفظ وتسجيل خروج وتعديل رحلات |
| Deep chat HTTP | **15/15 PASS** | أسئلة سياح ودفع وتحذيرات وسياق؛ Offline |
| Planner stress | **18,000/18,000 PASS** | 1,500 مسودة × 12 خاصية |
| Independent adversarial QA | **36/36 PASS** | صلاحيات، تحميل محدود، تسريب، تزامن، إعادة التشغيل |
| Mock provider + FastAPI HTTP | **27/27 PASS** | خادم OpenAI محلي وهمي، لا يثبت الاتصال بالشركة |
| Local launcher contracts | **11/11 PASS** | فحص ملفات التشغيل؛ ليس تشغيل Windows فعلي |
| Nginx proxy static contracts | **4/4 PASS** | فحص صيغ الإعداد، ليس Docker deployment |
| Security source scan | **PASS** | فحص اعتمادات وأسرار ظاهرية، ليس تدقيقًا أمنيًا شاملاً |
| Retrieval benchmark | **hit@1 = 0.98, hit@3 = 1.00** | 49 سؤالًا قابلًا للإجابة؛ 4 خارج النطاق، مجموعة صغيرة داخل المشروع |

### تصحيح أداة الاختبار

فشل أول تشغيل لأداة `scripts/qa_live_http.py` في 3 حالات OpenAI mock بسبب عدم توافق الـshim التجريبي مع واجهة SDK الحالية (context manager والـinput كقائمة أدوار). تم إصلاح **أداة الاختبار** فقط، وليس تغيير منطق الـAI في المنتج. نجح التشغيل الثاني **27/27** محليًا. غياب مكتبة OpenAI الحقيقية يعني أن التوافق مع SDK ومزود الخدمة لم يُثبت بتلك المحاكاة.

## الاختبارات غير المكتملة — لا نعتبرها نجاحًا

1. **React Production Build: BLOCKED.** `npm ci` تعذّر لأن بيئة التشغيل لا تستطيع الوصول إلى registry.npmjs.org (`EAI_AGAIN`). لذلك لم نتحقق من Vite build أو ESLint أو Vitest React components.
2. **Chromium Mobile/Desktop E2E: BLOCKED.** لا توجد حزمة React مبنية، وبالتالي لم يُختبر الموقع الكامل بصريًا أو استخدام شاشة الهاتف ولوحة المفاتيح.
3. **Gemini + Google Search Live: NOT EXECUTED.** مفتاح API غير متاح في بيئة الاختبار؛ وضع Offline أو اختبارات mocking لا يكافئان الاتصال الحقيقي.
4. **Real OpenAI SDK/API: NOT VERIFIED.** اختبارات الموفر استخدمت shim وخادمًا محليًا، وليس SDK مثبتًا أو نموذجًا حيًا.
5. **Production Deployment / backup restore / real visitor load: NOT EXECUTED.** لا يوجد عنوان عام تم التحقق منه أو اختبار شامل لبيئة النشر.

## محتوى التسليم

- **Frontend:** React + Vite؛ الشات في الصفحة الرئيسية، صفحات آثار وشواطئ مستقلة، الترشيحات وإرشادات السفر، تصميم إنجليزي وعربي RTL، تصميم Mobile-First بألوان برتقالية.
- **Backend:** FastAPI، API للحسابات والرحلات والحفظ، قيود على مدخلات المستخدم وحماية الحسابات في الحالات المختبرة.
- **AI:** التكامل البرمجي مع Gemini 2.5 Flash / OpenAI اختياريًا، الاسترجاع السياحي المحلي، تخطيط رحلات آلي، اختبارات وسكربتات تحقق.
- **تشغيل محلي:** `SETUP_AND_TEST_LOCAL_WINDOWS.bat` ثم `RUN_STARTUP_WINDOWS.bat`. افتح `http://127.0.0.1:5173/` فقط عندما يظهر نجاح خادمي Backend وFrontend.
- **API Settings:** نسخة تعليمات `backend/.env.example`؛ أنشئ محليًا `backend/.env` وأدخل المفاتيح بشكل سري ولا تضعها في Git أو الحزمة.

**معيار الاعتماد للإطلاق:** يجب أولًا نجاح React Build واختبار Chrome/Safari على الهاتف، اتصال Gemini الحقيقي ودقة المراجع، ثم اختبار حفظ البيانات واستعادة النسخ الاحتياطية على استضافة الإنتاج. لا يوجد ضمان انعدام الأخطاء في جميع الحالات.
