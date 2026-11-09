# Masr Guide AI — AI / Chatbot / Backend Technical Review
**تاريخ المراجعة:** 31 أكتوبر 2026  
**أساس العمل:** `Masr_Guide_AI_Reviewed_AI_Backend_Full_2026-10-30.zip`  
**النطاق:** Chat / AI providers / RAG / trip orchestration / HTTP API / authentication / authorization / data integrity.

## 1. القرار
النسخة **صالحة لمراجعة الفريق واختبارات الـMVP المحلية**؛ وليست جاهزة بعد لاستقبال سائحين على خادم إنتاجي. لا يمكن ضمان خلو أي تطبيق من جميع الأخطاء.

## 2. عيوب تم اكتشافها وإصلاحها

### A. OpenAI partial response accepted as complete
المسار `backend/app/openai_client.py` كان يقرأ `output_text` دون التحقق من `response.status` و`incomplete_details`؛ وبالتالي يمكن قبول جواب مبتور عند `max_output_tokens`. تمت كتابة أربعة اختبارات جديدة، أثبت اثنان منها الخلل قبل الإصلاح. الإصلاح يرفض كل `status` غير `completed` ويفرض نفس سياسة فشل المزوّد عند وجود `incomplete_details`، من دون كشف مفاتيح أو بيانات حساسة للعميل.

### B. Explicit day transfer between two existing cities ignored
طلب السائح «انقل يومين من القاهرة للغردقة» في رحلة مدتها 30 يومًا بأربع مدن كان لا يغيّر تخصيص الأيام، وكذلك `Move 2 days from Cairo to Hurghada`. أضفت تفسيرًا حتميًا محدودًا للعبارتين عندما يكون المصدر والوجهة موجودَين في مراحل مستقلة، ونرفض خصم أيام يترك المدينة بلا يوم. بعد الإصلاح اختُبر انتقال 10/5/7/8 إلى 8/5/7/10 ثم انتقال آخر إلى 6/5/7/12، مع إبقاء إجمالي الرحلة 30 يومًا.

## 3. نتائج اختبارات منفذة
| الفحص | النتيجة |
| --- | --- |
| `python -m pytest -q` | **372/372 PASS** |
| اختبارات الإضافة الجديدة | **7/7 PASS** |
| FastAPI حقيقي عبر Uvicorn على 127.0.0.1 | **20/20 HTTP acceptance PASS** |
| `python -m compileall -q app` | PASS |
| Gemini Live API | **BLOCKED**: لا يوجد `GEMINI_API_KEY` في بيئة الاختبار |
| OpenAI Live API | **BLOCKED**: لا يوجد `OPENAI_API_KEY` في بيئة الاختبار |
| Google Search Grounding الحقيقي | **NOT VERIFIED** |
| اختبار دقة المصادر على مستوى كل جملة | **NOT EXECUTED** |
| تحمل نشر إنتاجي متعدد النسخ، Restore Drill | **NOT EXECUTED** |

HTTP acceptance موجود في `backend/scripts/ai_backend_customer_http_20261031.py` ونتيجته في `qa_reports/AI_Backend_HTTP_Acceptance_2026-10-31.json`. يستخدم قواعد بيانات مؤقتة ويتجنب أي مفتاح حقيقي.

### السيناريوهات التي اجتازتها التجربة
أسبوع عائلي؛ شهر 30 يومًا بـ4 مدن وتوزيع صريح؛ نقل يومين داخل الرحلة بالعربية والإنجليزية؛ رفض التعديل غير الصالح؛ سؤال فندق دون تغيير الرحلة؛ رفض بيانات البطاقة؛ رفض الحفظ للمجهول؛ تسجيل حساب؛ الحفظ الفعلي؛ إعادة قراءة خطة 30 يومًا من قاعدة البيانات؛ منع حساب آخر من قراءة الرحلة؛ إبطال التوكن عند الخروج؛ رفض الرسائل الطويلة؛ عدم اختراع مطاعم مفتوحة الآن دون مصدر حي.

## 4. الحدود الحرجة المتبقية
1. **مصادر الحقيقة:** Grounding يرجع روابط بحث وقد تكون مفيدة، لكن مجرد قائمة روابط لا يثبت صحة كل ادعاء. يلزم ربط جمل الجواب بمقاطع الإسناد ومراجعة بشرية للادعاءات عالية المخاطر والمعلومات المتغيرة.
2. **RAG:** الاسترجاع الحالي BM25 مع مرادفات عربية/فرنسية، وليس semantic retrieval متينًا. قاعدة معالم مصر محدودة؛ لا يوجد تغطية موثقة كافية للفنادق والمطاعم وتوافر الغرف والمواعيد اللحظية.
3. **المزوّد الحقيقي:** اختبارات محاكاة عقد الـAPI لا تثبت جودة اللغة أو استخدام Google Search مع اتصال فعلي. شغّل اختبارات حية بمفاتيح مخزنة في البيئة وليس الشات أو GitHub.
4. **التخزين:** MVP يستخدم SQLite؛ إنتاج متعدد النسخ يحتاج تصميم تخزين دائم ونسخ احتياطي/استرجاع تم اختباره فعليًا، مع سياسة خصوصية وحذف بيانات.
5. **الأمان/التشغيل:** rate limiting الحالي محلي لكل عملية، ولا يغني عن Edge/Reverse Proxy limiting, alerts, quotas, logging مع إخفاء بيانات المستخدم، وعمليات disaster recovery.
6. **التشغيل الشامل:** لم يُثبت React Build أو متصفح Chromium أو نشر عام ضمن هذه الجولة؛ ليست أهداف مراجعة AI/Backend لكنها مطلوبة للاعتماد النهائي.

## 5. طريقة إعادة التشغيل
من داخل مجلد `backend`:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/ai_backend_customer_http_20261031.py
```

لتفعيل Gemini الفعلي على جهاز المطوّر:

```dotenv
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
GEMINI_SEARCH_GROUNDING=true
GEMINI_API_KEY=SET_LOCALLY_NOT_IN_GIT
```

**مهم:** لا تضع `.env` في ZIP ولا تشارك مفاتيح API في GitHub أو المحادثات. اختبر الاستخدام التجاري، الحصص، الخصوصية والمراجع قبل استقبال مستخدمين حقيقيين.
