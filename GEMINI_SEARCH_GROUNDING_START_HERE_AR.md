# Masr Guide AI — Gemini 3.1 Flash Lite + Google Search Grounding

## ما الجديد؟

- استدعاء Gemini REST يرفق Google Search كأداة `google_search` للأسئلة السياحية عبر `/api/chat` و`/api/consult` عند استخدام مسار المعرفة العامة.
- استجابة API تفصل بين المصادر المحلية `type: catalog` والمصادر الخارجية `type: google_search`، وتُظهر `grounding.grounded` و`grounding.search_performed` من metadata الفعلية.
- إذا لم ترجع Google مصادر للطلب المتعلق بالمواعيد/الأسعار، لا يُقدَّم رد Gemini على أنه متحقق.
- أسئلة المطاعم تستخدم Google Search عند تفعيلها، لكن لا تؤكد الأسعار أو ساعات العمل أو الحجوزات.
- عمليات حفظ/تعديل الرحلات تبقى محكومة بـFastAPI ولا تسمح لنتائج البحث بتعديل الحسابات أو تنفيذ حجوزات.

## الإعداد (محليًا أو استضافة خاصة)

داخل `backend/.env` على السيرفر فقط (ليس في ملفات Git):

```dotenv
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=PUT_YOUR_KEY_LOCALLY
GEMINI_SEARCH_GROUNDING=true
```

نسخ `.env.example` ثم تحرير `.env`، ولا تضع مفتاحًا سريًا داخل الشات أو في GitHub.  
**النسخة المنشورة حاليًا لا تفعّل Google Search Grounding.** لا تفترض أن حصة النموذج هي حصة البحث؛ راجع حدود كل منهما في لوحة Google قبل تفعيل الأداة، وراجع التسعير قبل إضافة وسيلة دفع. قد تستخدم Google نصوص الفئة المجانية لتحسين منتجاتها، لذا لا تُرسل معلومات شخصية حساسة.

### تشغيل API محليًا

```powershell
cd backend
python -m venv .venv
.\\.venv\\Scripts\\python -m pip install -r requirements.txt
.\\.venv\\Scripts\\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

- التحقق: `http://127.0.0.1:8000/api/ready`
- الوثائق: `http://127.0.0.1:8000/docs`
- تأكد أن `GET /api/health` يعيد `gemini_search_configured: true`.

### تجربة محادثة سائح

```powershell
$body = @{language="Arabic";message="ما هي مواعيد زيارة معبد الكرنك اليوم؟"} | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/chat -Method Post -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

يجب ألا تعتبر المصدر حيًا إلا لو كان `grounding.grounded = true` وظهر مصدر من `google_search`.

### فحص اتصال حقيقي اختياري (يستهلك حصة API)

```powershell
cd backend
.\\.venv\\Scripts\\python scripts/smoke_gemini_grounding.py
```

نتيجة `PASS` تتطلب وصولًا فعليًا لمصدر بحث؛ نتيجة `BLOCKED` تعني نقص إعداد المفتاح، و`NOT VERIFIED` تعني عدم وصول استشهادات.

## حدود الإطلاق التجاري

- استجابة Google Search لا تمثل مخزون حجز أو أسعارًا تعاقدية. الربط مع نظم الحجز والمطاعم يتطلب APIs وشراكات مناسبة.
- يجب على واجهة العميل أن تعرض مصادر Google والـSearch Suggestions عند توفرها حسب شروط Google Grounding، ويجب التعامل مع HTML الإرشادات كمحتوى غير موثوق (عدم حقنه عشوائيًا في DOM).
- استخدم مراجعة مصادر وCaching مناسبًا، وحدود طلبات وسياسة خصوصية قبل استقبال عملاء حقيقيين.
- تفعيل البحث لا يعني أن Google قررت تنفيذ بحث لكل رسالة؛ `search_performed` و`grounded` يعكسان ما عاد فعليًا في metadata.
- لا تعلن Production Ready دون Gemini live QA وbrowser E2E وتجربة نسخ احتياطية وتحمل الطلبات على الاستضافة الحقيقية.
