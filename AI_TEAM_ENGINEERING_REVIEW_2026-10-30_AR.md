# Masr Guide AI — مراجعة AI وChatbot | 30 أكتوبر 2026

## النطاق
مراجعة الكود الفعلي من آخر تسليم موحّد: Gemini REST Adapter، Google Search Grounding، OpenAI Adapter، RAG/BM25، مسارات الشات، Trip Planner، الحسابات والتكامل. لم تُعد كتابة المشروع من الصفر.

## نتائج نفّذت أثناء هذه المراجعة
- Backend الكامل بعد الإصلاح: **365/365 PASS** (`cd backend && PYTHONPATH=. pytest -q`).
- اختبار سيرفر Uvicorn مستقل عبر HTTP: **7/7 PASS** (جاهزية السيرفر، سؤال إنجليزي، سؤال عربي، رحلة أسبوع، 30 يومًا موزعة 10/7/5/8، رفض دفع البطاقة، حالة المطاعم المحلية).
- اختبارات جديدة: **11/11 PASS** (8 حالات رد مقطوع/محجوب، حالتا اكتمال، واختبار رد احتياطي آمن).
- إعادة إنتاج الخلل قبل إصلاحه: كان Gemini adapter يعرض نصوصًا جزئية حتى عند `finishReason=MAX_TOKENS`.
- الإصلاح: رفض الردود التي تعلن حالة إنهاء غير `STOP`، ومعالجة الحالة في الـAPI كعدم توفر المزوّد بدل عرض نص ناقص كسرد مكتمل.

## نتائج مراجعة الجودة — ليست إثبات جاهزية تجارية
1. **RAG الحالي Lexical BM25** مع معالجة عربية/إنجليزية وفرنسية، وليس Semantic RAG مع Embeddings / Vector DB. التغطية متوقفة على الكتالوج الحالي.
2. `GEMINI_SEARCH_GROUNDING` يطلب Google Search عند تفعيله؛ وجود `groundingChunks` وحده لا يثبت صحة *كل* ادعاء في نص النموذج. يجب فحص Grounding Supports وتقييم الدقة من مصادر أولية.
3. هناك مسارات حوار تعتمد على قواعد ثابتة قبل Gemini (التحيات، المواصلات، الفنادق، حماية الدفع). ليست كل رسالة تولّد استدعاءً للنموذج.
4. Trip Planner يتعامل مع الحالات المختبرة من 1 إلى 30 يومًا فقط، ولا يجوز تقديمه كتغطية غير محدودة.
5. لا توجد أسعار فنادق أو توافر حجوزات مباشرة معتمدة.
6. **Gemini Live + Google Search = BLOCKED** لعدم وجود مفتاح في بيئة التنفيذ؛ لم يتم الادعاء بنتيجة اتصال حقيقية.
7. تشغيل React عبر المتصفح والسيرفر الإنتاجي خارج نطاق هذه المراجعة ولم يُعتمدا.

## خريطة الملفات المهمة لفريق AI
- `backend/app/gemini_client.py`: استدعاءات Gemini وGrounding واستخراج مصادر Google.
- `backend/app/openai_client.py`: مزود GPT البديل.
- `backend/app/guide.py`: RAG والإجابة والتوجيه إلى المصدر.
- `backend/app/conversation_router.py`: قواعد التوجيه للأسئلة العامة.
- `backend/app/travel_agent.py`: تفسير التخطيط والتعديلات والتحقق الحتمي.
- `backend/app/planner.py`: بناء البرنامج والتحقق من مدة الرحلة.
- `backend/app/hotel_guide.py`, `backend/app/hotel_companion.py`: اقتراحات فنادق تحريرية وتحسين الصياغة.
- `backend/app/schemas.py`, `backend/app/main.py`: عقود الـAPI ومسار `/api/chat` و`/api/consult`.
- `backend/tests/test_ai_completion_safety_review_20261030.py`: اختبارات الانقطاع الجديدة.

## طريقة إعادة الاختبار
داخل `backend` ثبت الاعتماديات من `requirements.txt`، ثم:

```bash
python -m pytest -q tests/test_ai_completion_safety_review_20261030.py tests/test_gemini_google_search_grounding_20261030.py tests/test_openai_provider_integration_20261030.py
```

لتشغيل المشروع كاملًا، استخدم ZIP الكامل. لا تضع مفتاح Gemini أو OpenAI في ملفات المصدر أو GitHub، ولا تُفصح عنه في سجلات الاختبار.

## قرار المراجعة
**الكود صالح للاستمرار في QA ومراجعة التيم، وليس جاهزًا للاعتماد التجاري النهائي.** معايير الإطلاق المتبقية: Gemini Live Grounding مع مفاتيح آمنة، تقييم واقعي للدقة بالمصادر، اختبارات انقطاع وخطة تكلفة/حدود، تخزين دائم واختبار استرجاع، وتجربة المستخدم الفعلية.
