# Masr Guide AI — Part 2 | Actual Source Engineering Audit

**التاريخ:** 16 أكتوبر 2026  
**الحالة النهائية:** BACKEND PATCH VERIFIED / FRONTEND RELEASE BLOCKED / PRODUCTION NOT APPROVED.  
**المنطلق:** الأرشيف المرفق `Masr_Guide_AI_Source_and_Master_Prompt_2026-10-16(1).zip` (v7.8.1). لم يُعاد بناء المشروع من الصفر ولم تتم إعادة تسمية نسخته.

## ما تم إثباته وإصلاحه

### P1 — صيانة قيود الرحلة عبر إنشاء الخطة وحفظها واستعادتها

تم إعادة إنتاج خلل تخزين خطة بصيغة صحيحة لكن بتوزيع مدن يخالف قيود المستخدم: 13 يوم القاهرة +7 الغردقة تتحول في الـpayload إلى 14+6 مع بقاء `trip_state` الأصلي. قبل التصحيح، كان API حفظ المحادثة يرد HTTP 201 لهذا المستند غير المتوافق.

الإصلاح:
- Backend: `accounts.py` يتحقق من `TripState` ومن سلامة `travel` و`stops`، ويقارن الأيام الفعلية بكل Phase وعددها ومدنها قبل حفظ المحادثة؛ المستند غير المتوافق يعود 422 بدل 201.
- Frontend: `tripValidation.js` يقدم `isCompatibleTripPlan()`، ويمنع `Guide` تطبيق استجابة AI/استعادة ذاكرة المتصفح أو نسخة السحابة عند اختلاف التخطيط الفعلي عن القيود المعلنة.
- واجهة الحساب والمخطط لا تعرض مستندات محفوظة غير صالحة؛ تحقق إضافي من استجابة المخطط.
- تم تحديث **بيانات fixture غير صالحة** في اختبار عزل الحسابات القديم لتكون رحلة 20 يوم فعلية؛ لم يتم إضعاف اختبار التفويض أو تعديل اختبار Q49/Q52 الأصلي.

### P1 — حفظ توزيع الأيام المحدد لكل مدينة بدل التوزيع التقريبي

تم إعادة إنتاج طلب: 20 يومًا = 10 القاهرة +3 الأقصر +7 الغردقة؛ كان التنفيذ يعيد 9+4+7، ويعرض `day_allocation` مخادعًا `Cairo=13` رغم أن القاهرة ليست 13 يومًا. وطلب `10 Cairo, 3 Luxor, 7 Hurghada` بدون إجمالي كان يُفهم 10 أيام فقط.

الإصلاح:
- `travel_agent.py` يقرأ التوزيع المذكور صراحة للمدن المدعومة بالأرقام الإنجليزية والعربية ويُنشئ Phases منفصلة عند اكتمال تحديد كل مدينة.
- عند تعارض إجمالي الرحلة الصريح مع مجموع أيام المدن، يُرفض الإنشاء وتظهر حاجة لتوضيح بدل تغيير القيد بصمت.
- `day_allocation` يُحسب من الأيام الفعلية، حتى لو كان Phase واحد يشمل مدينتين.
- التفسير يظل heuristic محدودًا؛ العبارات الملتبسة وغير المدعومة تتطلب توسيعًا واختبارات إضافية. ليست هذه موافقة على جودة جميع صياغات اللغات أو على إمكانية الرحلة لوجستيًا.

### اختبارات انحدار مضافة

- ثلاثة Backend tests لمنع التخزين غير المتوافق، ورفض `trip_state` الفاسد، ورفض حقول الانتقال الفاسدة.
- Backend HTTP integration واحد: إنشاء الرحلة → تعديل Hurghada إلى Sharm El Sheikh → حفظ تحديث متزامن مشروط → استعادة → رفض تحديث `If-Match` قديم.
- خمسة Backend tests لتوزيع أيام المدن (EN/AR)، والتعارض، ودقة ملخص التوزيع.
- اختبارا Node بدون npm للتحقق من توافق الأيام مع مراحل الرحلة ومدنها وأنواعها.

## اختبارات نُفذت بالفعل **بعد التصحيح**

| الفحص | النتيجة | الدليل/الحدود |
|---|---|---|
| Python `pytest -q` | **PASS 228/228** | تنفيذ محلي على Python 3.13 |
| Corrected offline conversation acceptance | **PASS 52/52** | محاكاة offline، ليست Gemini حقيقي |
| Original legacy conversation acceptance | **50/52** | Q49 وQ52 احتُفظ بهما كما هما؛ معايير متعارضة/ناقصة التوصيف |
| Planner invariant stress | **PASS 18,000/18,000** | فحوص ثوابت، لا ضمان حجز أو جودة نصائح السفر |
| Node `--test` frontend data contract | **PASS 4/4** | دون React أو DOM |
| HTTP integration + mock provider | **PASS 21/21** | خادم FastAPI فعلي ومزود AI محاكى؛ ليس Gemini حيًا |
| Local Nginx proxy and throttling | **PASS 4/4** | nginx محلي دون Docker |
| Curated retrieval eval | hit@1 0.98; hit@3 1.00 | 49 سؤالًا قابلاً للإجابة + 4 no-answer في benchmark داخلي |
| Python syntax compileall | **PASS** | صحة التركيب فقط |
| Source secret check | **PASS** | مسح best-effort وليس اختبار اختراق |
| React production `npm run build` | **BLOCKED** | `npm ci --offline`: missing `yocto-queue@0.1.0`؛ `registry.npmjs.org` DNS غير متاح |
| Vitest / React unit/accessibility | **BLOCKED** | حزم npm لم تُثبت كاملة |
| ESLint / JS dependency audit | **BLOCKED** | غياب تثبيت frontend صالح. كذلك `ruff` غير مثبت في هذه البيئة |
| Chromium E2E | **BLOCKED** | محاولة فعلية لـ `/demo` فشلت `net::ERR_BLOCKED_BY_ADMINISTRATOR`؛ React dist غير مُنشأ |
| Real Gemini and conversation live E2E | **NOT EXECUTED** | لا مفتاح Gemini جديد مصرح به داخل البيئة؛ mock ليس بديلًا |
| Docker image build | **NOT EXECUTED** | Docker غير متاح في البيئة |
| Cloud production smoke, backups restore, external security review | **NOT EXECUTED** | تحتاج بنية نشر ومفاتيح وقاعدة دائمة |

## Release status حسب الأنظمة

| النظام | التنفيذ | التحقق الحالي / المتبقي |
|---|---|---|
| FastAPI discovery/catalog/itinerary | IMPLEMENTED | Backend tests + HTTP verified؛ زيارات وتغطية البيانات السياحية تحتاج توسعًا |
| Multilingual AI tourism companion | IMPLEMENTED (offline+Gemini adapter) | 52/52 offline؛ Gemini real **NOT EXECUTED** |
| Explicit day planning and follow-up changes | IMPLEMENTED | حالات EN/AR و20=10+3+7 و13+7 والتحرير والحفظ **VERIFIED**؛ الصياغات الحرة ليست مغطاة بالكامل |
| Accounts and saved conversations/trips | IMPLEMENTED | الاختبارات والتفويض والنزاهة محليًا VERIFIED؛ الإنتاج الدائم يتطلب تخزينًا مدققًا |
| Editorial CMS, partner offers | IMPLEMENTED AS MVP | Tests محلية؛ نشر وتشغيل تجاري/تعاقدات حقيقية **NOT IMPLEMENTED** |
| React travel UX/RTL/accessibility | IMPLEMENTED IN SOURCE | Build/Vitest/Chromium **BLOCKED**؛ لا تعتمد screenshots حالية كدليل |
| Next.js SEO migration | NOT IMPLEMENTED | مسار تطوير محتمل فقط؛ لا تهاجر دون متطلبات SEO دقيقة وقرار معماري |
| PostgreSQL production storage / managed backup drills | NOT IMPLEMENTED | SQLite حاليًا؛ لا تفعّل تسجيل مستخدمين عموميين على تخزين مؤقت |
| Structured AI tool-call orchestration | PARTIALLY IMPLEMENTED | Deterministic routing and Gemini intent extraction؛ strict provider tool-calling متعدد الأدوات غير مكتمل |
| Verified bookings, payouts, commissions and contracts | NOT IMPLEMENTED | لا تحتسب الإحالات إيرادات |
| Public live demo, monitoring, audit logs, incident recovery | NOT VERIFIED/NOT IMPLEMENTED | بوابات إطلاق إلزامية |

## الإجراءات اللازمة قبل استخدام المشروع كعرض حي في CV

1. على جهاز يسمح بالتثبيت: `cd frontend && npm ci && npm test && npm run lint && npm run build`، واحفظ سجلات تنفيذ حقيقية.
2. شغل FastAPI والـReact المترجم ثم اختبارات Chromium على Desktop/Mobile بالأمر `python scripts/qa_browser_e2e.py`، وأضف اختبارات UI لانحدارات هذا التصحيح.
3. فعّل مفتاح Gemini خاصًا وآمنًا، واختبر ربط Gemini الحقيقي واستهلاك الحصة ومخرجاته، من دون وضع المفتاح في GitHub.
4. نفّذ مراجعة أمنية وتبعية وصلاحيات وخصوصية، واختر قاعدة إنتاجية دائمة (يفضل PostgreSQL) مع استعادة نسخة احتياطية ناجحة عمليًا.
5. اختبر Docker/CI/CD على GitHub والنشر والـHTTPS والتحليل والمراقبة، وراجع حقوق الصور والمحتوى قبل استخدامه تجاريًا.

**قرار الإطلاق:** مصدر Backend محسّن ومتحقق محليًا + عدد من حواجز واجهة JS المتحقق منها بالاختبارات المباشرة. **غير جاهز للمصادقة على كامل React أو إطلاق تجاري حقيقي.**
