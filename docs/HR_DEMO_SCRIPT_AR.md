# عرض Masr Guide AI للـHR في 5 دقائق

## رسالة المشروع

Masr Guide AI is an Egypt-focused full-stack TravelTech portfolio application that helps visitors discover destinations, learn about attractions, plan itineraries and manage personalized journeys, with an AI companion grounded in tourism data.

## رحلة العرض

1. **20 ثانية:** افتح Home → أظهر إن المنتج يبدأ بتسويق الوجهات المصرية وليس Chatbot.
2. **45 ثانية:** افتح Destinations وExplore، واعرض مدينة، معالمها، روابط المصادر وخريطة المكان.
3. **45 ثانية:** افتح Journal واعرض مقالًا. اشرح إن الـCMS يسمح بتعديل المحتوى والنشر من Dashboard منفصلة.
4. **60 ثانية:** افتح Guide واسأل عن معبد الكرنك. اشرح RAG وربط المعلومات بكتالوج المعالم، وأن Gemini اختياري حسب حالة الاتصال.
5. **60 ثانية:** افتح Trip Planner وأنشئ رحلة 14 يومًا. اعرض الأيام والانتقالات ثم Budget Calculator بأرقام تدخلها بنفسك، دون ادعاء أسعار حية.
6. **45 ثانية:** افتح Account وسجل حسابًا **تجريبيًا** واحفظ رحلة، ثم اعرض الـAPI docs وCase Study للتصميم التقني.
7. **30 ثانية:** اشرح Admin/Partners: المقالات، العروض الخارجية بإفصاح، طلبات الشراكة، وعدّادات النقرات (ليست حجوزات).

## نقاط تقنية تقولها في الانترفيو

- Designed and implemented REST APIs in FastAPI for tourism discovery, accounts, saved trips, CMS and partner-offer tracking.
- Integrated Gemini with a curated retrieval-backed Egypt knowledge base and a deterministic itinerary planning layer to reduce fabricated travel data.
- Developed a responsive bilingual React frontend with traveler discovery pages and interactive travel workflows.
- Added authenticated traveler sessions with password hashing and isolated trip ownership.
- Containerized frontend and backend together for single-origin deployment; added CI checks for Python tests and React build.

## أسئلة متوقعة وإجابات دقيقة

**هل دا SaaS Production جاهز؟** لا؛ ده Portfolio MVP وظيفي فيه بعض أساسيات المنتج، ويحتاج قاعدة بيانات مُدارة، Email Verification، حماية واستضافة دائمة، وشركاء متعاقدين قبل التشغيل التجاري.

**ليه مخطط الرحلات مش LLM وحده؟** لاستخدام Validation وتوقيتات تقريبية وبيانات معالم منظمة، مع إمكان تحرير الخطة بالمحادثة؛ والـLLM لا يملك صلاحية اختراع أسعار أو حجوزات.

**هل فيه دخل مالي حقيقي؟** لا. يوجد نظام نشر عروض مُراجعة وتتبع نقرات خارجية فقط. عمولات الحجز تحتاج عقودًا وأنظمة Attribution فعلية.

**فين الكود؟** GitHub Repository. **فين الموقع؟** رابط Render (أو أي خدمة تشغيل Docker). GitHub بمفرده ليس استضافة Backend.
