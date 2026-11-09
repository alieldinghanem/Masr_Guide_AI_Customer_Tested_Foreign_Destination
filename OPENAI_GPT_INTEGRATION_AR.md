# ربط Masr Guide AI مع OpenAI GPT API

الـBackend هو الوحيد الذي يحتفظ بمفتاح OpenAI. لا تضع المفتاح في React أو GitHub.

## الإعداد المحلي

1. افتح `backend/.env` (يمكنك نسخه من `backend/.env.example`).
2. اضبط:

```dotenv
AI_PROVIDER=openai
OPENAI_API_KEY=ضع_مفتاح_OpenAI_الحقيقي_هنا
OPENAI_MODEL=gpt-4o-mini
```

3. ثبّت الحزم من داخل مجلد `backend`:

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

4. افحص `GET http://127.0.0.1:8000/api/health` للتأكد من `openai-configured` (المفتاح مضبوط، وليس بالضرورة الاتصال ناجحًا).
5. أرسل `POST http://127.0.0.1:8000/api/chat` بالجسم `{"message":"احكي لي عن معبد الكرنك","language":"Arabic"}`.
6. جرّب `/api/consult` لطلب رحلة وتعديلها؛ التنفيذ والحفظ يجريان في FastAPI وليس في GPT.

## التصميم والحدود

- `AI_PROVIDER=openai`: يختار GPT صراحةً حتى لو مفتاح Gemini موجود.
- `AI_PROVIDER=gemini`: يختار Gemini فقط.
- `AI_PROVIDER=auto`: السلوك القديم؛ Gemini أولًا، ثم OpenAI عند غياب مفتاح Gemini.
- `AI_PROVIDER=offline`: عرض المحتوى المحلي دون طلب خارجي؛ غير مناسب للإطلاق التجاري.
- يعمل التكامل عبر **Responses API** مع `store=False`، وسجل أدوار محادثة محدود، و`JSON object` للاستخراج المنظم.
- يستمر RAG في إرجاع مراجع الكتالوج، وتبقى سلامة توزيع الأيام وحفظ الرحلات مسؤولية الخادم.
- لا توجد أسعار فنادق أو حجوزات مباشرة ما لم تُضف أدوات بمصادر حية.
- لا تتطلب النسخة تكاملًا جديدًا في React، لكنها تضيف حالات عرض جديدة للمزوّد.
- لا تتضمن الحزمة مفتاح API، ولم يتم تنفيذ اتصال مدفوع فعلي دون مفتاح في البيئة.
- عند فشل OpenAI تظهر رسالة خدمة غير متاحة أو fallback موسوم بوضوح؛ لا يُبلغ العميل بنجاح وهمي.

**ملاحظة:** اشتراك ChatGPT لا يوفر تلقائيًا رصيدًا لواجهة OpenAI API. راجع حساب الـAPI والفوترة وحدود الإنفاق.
