"""Safe, lightweight intent routing for common tourist conversations.

This is a deterministic tool dispatcher for intents we can answer without calling
an LLM. It does NOT claim to provide live transport schedules or booking quotes.
For all other questions, the guide falls back to curated retrieval + an optional
AI provider. Keep it deliberately conservative to avoid hijacking other intents.
"""
import re

LANG_AR = 'Arabic'
LANG_EN = 'English'
LANG_FR = 'French'


_CITY_NAMES = {
    'القاهرة': 'Cairo', 'القاهره': 'Cairo', 'cairo': 'Cairo',
    'الجيزة': 'Giza', 'الجيزه': 'Giza', 'giza': 'Giza',
    'الغردقة': 'Hurghada', 'الغردقه': 'Hurghada', 'للغردقة': 'Hurghada', 'للغردقه': 'Hurghada', 'hurghada': 'Hurghada',
    'شرم الشيخ': 'Sharm El Sheikh', 'sharm el sheikh': 'Sharm El Sheikh',
    'الأقصر': 'Luxor', 'الاقصر': 'Luxor', 'للأقصر': 'Luxor', 'للاقصر': 'Luxor', 'luxor': 'Luxor',
    'أسوان': 'Aswan', 'اسوان': 'Aswan', 'aswan': 'Aswan',
    'الإسكندرية': 'Alexandria', 'الاسكندرية': 'Alexandria', 'alexandria': 'Alexandria',
    'دهب': 'Dahab', 'dahab': 'Dahab', 'caire': 'Cairo', 'louxor': 'Luxor', 'assouan': 'Aswan',
}


def detect_language(message: str, fallback: str = LANG_EN) -> str:
    """Respect explicit language choice, then actual user script."""
    t = message.lower()
    if re.search(r'\b(?:bonjour|bonsoir|salut|merci|parlez|français|francais|comment aller|louxor|assouan|je vais|je voudrais|pouvez-vous|peux-tu|avec mes enfants|pour cinq jours|dix jours|pendant \w+ jours)\b', t):
        return LANG_FR
    if re.search(r'(?:speak|reply|respond|answer) (?:to me )?in arabic|باللغة العربية|بالعربي|ب العربي|خليها عربي|اتكلم عربي|تكلم عربي', t):
        return LANG_AR
    if re.search(r'(?:speak|reply|respond|answer) (?:to me )?in english|بالإنجليزي|بالانجليزي', t):
        return LANG_EN
    if re.search(r'(?:speak|reply|respond|answer) (?:to me )?in french|بالفرنساوي|parlez en fran[çc]ais|en fran[çc]ais', t):
        return LANG_FR
    return LANG_AR if len(re.findall(r'[\u0600-\u06ff]', message)) >= 3 else fallback


def _known_cities(text: str) -> list[str]:
    # Respect mention order (origin before destination), not alias string length.
    candidates = []
    for alias, city in _CITY_NAMES.items():
        position = text.lower().find(alias)
        if position >= 0:
            candidates.append((position, -len(alias), city))
    cities = []
    for _, _, city in sorted(candidates):
        if city not in cities:
            cities.append(city)
    return cities


def payment_sensitive(message: str) -> bool:
    """Intercept card disclosures and payment requests; distinguish visa *payment* from entry visas.

    Do not return any sensitive input or accept payment details in chat.
    """
    t = message.casefold()
    # A probable PAN should not be persisted into a chat transcript by an AI provider.
    if re.search(r'(?<!\d)(?:\d[ -]?){13,19}(?!\d)', t):
        return True
    if re.search(r'(?:credit card|card number|cvv|bank card|pay with (?:my|a|the) card|payment card|card details|رقم (?:بطاق|الكارت)|[اأ]دفع\s+(?:بالكارت|بالبطاقة|ببطاقتي|ببطاقة|بكارت)|بطاقتي البنكية|فيزا (?:بنك|الدفع)|بيانات (?:البطاق|الكارت))', t):
        return True
    pay = re.search(r'(?:[اأ]دفع|ندفع|الدفع|تدفع|دفع\s|pay|payment|checkout)', t)
    instrument = re.search(r'(?:بالفيزا|الفيزا|فيزا\s+كارت|بالكارت|بطاق(?:ة|تي)|بالبطاقة|credit|debit|card)', t)
    return bool(pay and instrument)


def redact_payment_data(message: str) -> str:
    """Keep accidental payment credentials out of downstream model context."""
    message = re.sub(r'(?<!\d)(?:\d[ -]?){13,19}(?!\d)', '[payment number redacted]', message)
    message = re.sub(r'(?i)\b(CVV|CVC)\b\s*[:=]?\s*\d{3,4}\b',
                     '[security code redacted]', message)
    return message


def special_reply(message: str, language: str, history=None) -> dict | None:
    """Return a grounded reply for concise conversational or transport intents."""
    t = re.sub(r'\s+', ' ', message.strip().lower())
    # Critical tourist safety intents are evaluated before generic retrieval or the LLM.
    # This is not a live emergency service and must never invent local phone numbers.
    def reply(ar, en, fr=None):
        return {'mode': 'local-assistant', 'sources': [],
                'answer': {LANG_AR: ar, LANG_EN: en, LANG_FR: fr or en}.get(language, en)}
    if payment_sensitive(message):
        return reply('ماتشاركش رقم بطاقتك البنكية أو CVV أو أي بيانات دفع في المحادثة. لا يمكنني إتمام حجز أو تحصيل أموال من هنا. استخدم صفحة دفع آمنة وموثوقة عند مزود خدمة معتمد فقط.',
                     'Do not share card numbers, CVV or payment credentials in this chat. I cannot process a booking or payment. Use only a trusted provider’s secure checkout.',
                     'Ne partagez jamais de numéro de carte ou CVV ici. Aucun paiement ou réservation ne peut être traité dans ce chat.')
    # Do not turn an accessibility question into an unqualified historical
    # description. Accessibility can change by entrance, route and season;
    # our static attractions catalogue does not certify step-free access.
    if re.search(r'(?:wheelchair|step.free|wheelchair accessible|mobility aid|reduced mobility|كرسي(?:ًا)? متحرك|الكراسي المتحركة|ذوي الإعاقة|إمكانية الوصول|accessibilité|fauteuil roulant)', t) and re.search(
            r'(?:can|is|are|accessible|access|suitable|هل|ينفع|متاح|مناسب|دخول|دخولها|acces|accessible|peut)', t):
        return reply(
            'ما عنديش تأكيد موثوق لمسار مناسب لكرسي متحرك في المكان ده. قبل الزيارة تواصل مع إدارة الموقع أو الجهة الرسمية واسأل عن مدخل بدون درجات، الممرات، دورات المياه المناسبة، وإمكانية وجود مساعدة. ما تعتمدش على توصية عامة في اتخاذ قرار الوصول.',
            'I cannot verify a step-free route at this attraction. Before travelling, ask the venue or official operator about accessible entrances, paths, toilets and assistance. Do not rely on this chat to guarantee wheelchair access.',
            "Je ne peux pas confirmer l'accessibilité en fauteuil roulant. Vérifiez auprès du site officiel les entrées sans marches, les parcours, les toilettes accessibles et l'aide disponible.")
    # An after-hours attraction question must not be answered from general
    # history snippets as if they establish opening hours or night access.
    if re.search(r'(?:بالليل|ليلا|ليلًا|after dark|at night|night visit|evening entry|la nuit|le soir)', t) and re.search(
            r'(?:الأهرامات|الاهرامات|pyramids?|معبد|temple|museum|متحف|site|الموقع|the sphinx|ابو الهول)', t):
        return reply(
            'زيارة المعلم بالليل تعتمد على مواعيد الدخول الفعلية، وقد تختلف الفعاليات المسائية عن الزيارة العادية. ماقدرش أؤكد وجود دخول ليلي؛ راجع الموقع الرسمي أو اتصل بإدارة المعلم قبل ما تتحرك.',
            'Night access depends on official opening hours and separate evening events. I cannot verify nighttime admission. Check the attraction’s official website or operator before travelling.',
            "L'accès de nuit dépend des horaires et d'éventuels événements distincts. Je ne peux pas le confirmer ; consultez le site officiel avant le déplacement.")
    if re.search(r'(?:chest pain|heart attack|can.t breathe|medical emergency|unconscious|severe bleeding|ألم (?:في )?الصدر|الم في الصدر|وجع (?:في )?صدري|مش قادر (?:اتنفس|أتنفس)|نزيف شديد|إغماء|اسعاف|إسعاف)', t):
        return reply('لو عندك ألم في الصدر أو أعراض خطيرة، اطلب إسعافًا أو مساعدة طبية طارئة فورًا. أوقف النشاط واجلس بمكان آمن، واطلب من شخص قريب أو موظف المكان يساعدك. لا تعتمد على المحادثة للتشخيص أو تأخير العلاج.',
                     'If you have chest pain or other severe symptoms, seek emergency medical help immediately. Stop your activity, get to a safe place, and ask a nearby person or venue staff to assist. Do not delay care for advice from this chat.',
                     'En cas de douleur thoracique ou de symptôme grave, demandez immédiatement une assistance médicale urgente. N’attendez pas un diagnostic dans ce chat.')
    if re.search(r'(?:تهددني|بيهددني|تهديد|يتحرش|تحرش|خطف|خطر علي|unsafe driver|driver threatens|threatening me|being followed|assault|harassed|robbed)', t):
        return reply('لو فيه تهديد أو خطر عليك دلوقتي، ابتعد لمكان عام وآمن إن أمكن، واطلب المساعدة من الشرطة أو أمن المكان أو موظفي فندق قريب فورًا. شارك موقعك مع شخص تثق فيه، وما تواجهش الشخص المهدِّد.',
                     'If someone is threatening you, move to a public safe place if possible and contact local police, venue security, or hotel staff immediately. Share your location with someone you trust. Do not confront the person.',
                     'Si vous êtes menacé, rejoignez un lieu public sûr et contactez immédiatement la police ou la sécurité locale. Prévenez une personne de confiance.')
    if re.search(r'(?:الغوص|غوص|الغطس|غطس|dive|diving|scuba|snorkeling|plongée|plongee)', t) and re.search(r'(?:النهارده|اليوم|دلوقتي|today|now|current|sûr|safe|مناسب|آمن|امن|weather|sea conditions|الجو|البحر)', t):
        return reply('ماقدرش أؤكد إن البحر آمن للغوص النهارده من غير بيانات طقس وموج وتيارات بحرية مباشرة. اسأل مركز غوص مرخّص في المنطقة واتبع تعليمات السلامة المحلية، وماتنزلش لو الظروف أو تعليمات المركز غير مناسبة.',
                     'I cannot confirm that diving or snorkeling is safe today without live weather, sea and current conditions. Check with a licensed local dive operator and follow official safety advice; do not go if conditions are unsafe.',
                     'Je ne peux pas confirmer la sécurité de la plongée aujourd’hui sans conditions maritimes en direct. Consultez un opérateur de plongée agréé.')
    if re.search(r'(?:book (?:a |the )?(?:hotel|tour|activity)|reserve (?:a |the )?(?:hotel|tour)|احجز|حجز (?:فندق|رحلة)|réserver|réservation)', t):
        return reply('ممكن أساعدك تختار وجهات وتجارب، لكن لم يتم أي حجز أو دفع من خلال المحادثة. الحجوزات الفعلية تحتاج مزود خدمة معتمد وتأكيدًا مستقلًا منه.',
                     'I can help you compare options, but no booking or payment has been made in this chat. Real reservations require a verified provider and their confirmation.',
                     'Je peux vous aider à comparer des options, mais aucune réservation ni aucun paiement n’a été effectué ici.')
    if re.search(r'(?:احذف (?:كل )?(?:بيانات )?محادثات|امسح محادثات|delete (?:all )?(?:my )?(?:chat|conversation) history|delete my conversations)', t):
        return reply('تقدر تحذف أي محادثة محفوظة من حسابك في قسم سجل المحادثات. المحادثة الحالية ما اتحذفتش بمجرد الرسالة دي، ومش هادّعي إن بياناتك اتمسحت؛ استخدم زر الحذف في الحساب.',
                     'You can delete saved conversations from your account history. This message has not deleted your data; please use the account deletion control.',
                     'Vous pouvez supprimer les conversations enregistrées depuis votre compte. Ce message ne supprime aucune donnée.')
    if (not re.search(r'(?:مطاعم|مطعم|restaurants?\b|dining\b|restauration\b)', t) and
            re.search(r'(?:open now|open tomorrow|opening hours|entrance fee|entry fee|ticket price|'
                      r'مفتوح دلوقتي|مفتوح بكرة|مفتوح بكره|شغال النهارده|'
                      r'سعر (?:ال)?تذكر[ةه]|مواعيد الزيارة|'
                      r'(?:سعر|بكام|تكلفة|price|cost|fee).{0,45}'
                      r'(?:تذكر[ةه]|دخول|ticket|entry|admission))', t)):
        return reply('ماقدرش أؤكد حالة فتح المعلم أو سعر التذكرة الآن من غير بيانات مباشرة. راجع الموقع الرسمي للمكان قبل الزيارة والحجز.',
                     'I cannot verify live opening hours, ticket prices or availability. Check the attraction’s official website before visiting or purchasing tickets.',
                     'Je ne peux pas confirmer les horaires ou prix des billets en temps réel. Vérifiez le site officiel.')
    if re.search(r'(?:visa (?:to|for|requirements?|on arrival)|egyptian visa|need a visa|e-?visa|تأشيرة|تاشيرة|فيزا (?:مصر|السفر|دخول)|visa pour)', t):
        return reply('شروط تأشيرة دخول مصر بتعتمد على الجنسية ونوع جواز السفر وتاريخ السفر. راجع البوابة الحكومية الرسمية https://visa2egypt.gov.eg/ أو السفارة المصرية المختصة قبل السفر. مش عندي تحقق مباشر من الأهلية أو الرسوم الحالية.',
                     'Egyptian entry-visa rules vary by nationality, passport and travel date. Check the official government portal https://visa2egypt.gov.eg/ or an Egyptian consulate before traveling. I cannot confirm live eligibility or fees.',
                     'Les règles de visa dépendent de votre nationalité et de votre passeport. Vérifiez le portail officiel https://visa2egypt.gov.eg/ ou le consulat égyptien.')
    if re.search(r'(?:koshary|koshari|كشري|كشرى|طعام مصري|أكل مصري|أكلة مصرية|اكلة مصرية|egyptian food|egyptian dish|cuisine égyptienne)', t):
        return reply('من الأكلات المصرية المعروفة الكشري (رز ومكرونة وعدس وصلصة)، والفول والطعمية والملوخية والمحشي. لو بتحب أكل نباتي أو عندك حساسية غذائية، قولّي عشان أرشح لك أنواع مناسبة؛ مفيش أسعار أو أماكن متحقق منها مباشرة.',
                     'Egyptian favorites include koshary (rice, pasta, lentils and sauce), ful medames, taameya, molokhia and mahshi. Tell me any allergies or dietary preferences; I cannot verify live menus or prices.',
                     'Parmi les plats égyptiens : koshari, foul, taameya, molokhia et mahshi. Indiquez vos allergies ou préférences alimentaires.')
    if re.search(r'(?:رمضان|ramadan)', t):
        return reply('رمضان شهر صيام عند المسلمين؛ قد تتغير ساعات بعض المطاعم والخدمات وتزيد أجواء الإفطار والسهر. كن محترمًا للعادات المحلية، وتحقق من المواعيد الفعلية قبل الزيارة.',
                     'During Ramadan, some opening hours and dining patterns change, and evenings can be especially lively. Respect local customs and verify current opening times.',
                     'Pendant le Ramadan, certains horaires changent. Respectez les coutumes et vérifiez les horaires actuels.')
    if re.search(r'(?:sim card|e-?sim|شريحة|خط موبايل|carte sim)', t):
        return reply('تقدر تسأل عن شريحة موبايل أو eSIM لدى مقدمي الاتصالات في مصر. تأكد من متطلبات الهوية والتغطية والأسعار الحالية من مقدم الخدمة؛ ماعنديش عروض حية.',
                     'You can compare local SIM or eSIM options in Egypt. Check ID requirements, coverage and current prices directly with an operator; I do not have live offers.',
                     'Comparez les cartes SIM ou eSIM locales et vérifiez prix et pièces requises auprès des opérateurs.')
    if re.search(r'(?:currency|exchange rate|عملة مصر|الجنيه المصري|بالجنيه|الدولار|دولار|تحويل عملة|monnaie|devise)', t) and not re.search(r'(?:ميزاني|budget|بميزانية)', t):
        return reply('عملة مصر هي الجنيه المصري (EGP). سعر الصرف بيتغير؛ راجع بنكًا أو جهة موثوقة قبل التبديل. ماقدرش أؤكد سعر صرف لحظي من غير مصدر مباشر.',
                     'Egypt uses the Egyptian pound (EGP). Exchange rates change; verify current rates with a bank or trusted provider. I have no live exchange feed.',
                     'La monnaie égyptienne est la livre égyptienne (EGP). Vérifiez le cours actuel auprès d’une source fiable.')
    if re.search(r'(?:ميزانيت[ي|ك]|budget|بميزانية)', t) and re.search(r'(?:تكفي|تكفيني|يكفي|enough|afford)', t):
        return reply('ماقدرش أؤكد إن الميزانية تكفي من غير تفاصيل الإقامة والمواصلات والأكل وعدد المسافرين وأسعار مباشرة. لو قلتلي مدة الرحلة وعدد الأشخاص وهل الإقامة مشمولة، أقدر أساعدك تقسّم البنود بشكل استرشادي، مش عرض سعر.',
                     'I cannot confirm that the budget is enough without accommodation, transport, meals, party size and current quotes. Share your trip details for an illustrative breakdown, not a verified price.',
                     'Je ne peux pas confirmer la faisabilité de ce budget sans les tarifs actuels, votre hébergement et le nombre de personnes.')
    if re.search(r'^(?:طيب )?(?:بكام|كام السعر|كم السعر|how much|what.*(?:price|cost)|combien)', t) and history:
        previous = next((h.content for h in reversed(history) if h.role == 'user'), '')
        if re.search(r'(?:مواصلات|ازاي اروح|إزاي أروح|how .*get|transport|travel from)', previous.lower()):
            return reply('ماقدرش أقول سعر الانتقال الحالي من غير عرض مباشر من شركة النقل. اطلب سعر اليوم من الشركة وحدد التاريخ وعدد الركاب عشان تقدر تقارن.',
                         'I do not have verified live transport fares. Request a current quote from the operator for your date and party size.',
                         'Je ne dispose pas de tarifs de transport en temps réel. Vérifiez auprès du transporteur.')
    if len(t) <= 100 and re.search(r'باللغة العربية|بالعربي|ب العربي|خليها عربي|اتكلم عربي|تكلم عربي|(?:speak|reply|respond) (?:to me )?in arabic', t):
        return {'mode': 'local-assistant', 'sources': [], 'answer': 'أكيد، هنتكلم بالعربي من دلوقتي. اسألني عن معالم مصر أو الثقافة أو المواصلات أو تخطيط رحلتك.'}
    if len(t) <= 100 and re.search(r'بالإنجليزي|بالانجليزي|(?:speak|reply|respond) (?:to me )?in english', t):
        return {'mode': 'local-assistant', 'sources': [], 'answer': 'Sure. I can continue in English. Ask about Egyptian history, destinations, transport or trip planning.'}
    if len(t) <= 100 and re.search(r'بالفرنساوي|(?:speak|reply|respond) (?:to me )?in french|parlez en fran[çc]ais|en fran[çc]ais', t):
        return {'mode': 'local-assistant', 'sources': [], 'answer': 'Bien sûr ! Je peux répondre en français sur les sites, la culture et les voyages en Égypte.'}

    greetings = ('السلام عليكم', 'سلام عليكم', 'اهلا', 'أهلا', 'اهلاً', 'هلا', 'هلا والله', 'يا هلا', 'مرحبا', 'مرحباً',
                 'صباح الخير', 'مساء الخير', 'hello', 'hi', 'hey', 'bonjour', 'bonsoir', 'salut')
    # Tourists use Arabic hamza/diacritics freely (أهلاً, اهلا, أهلًا).
    normalized = re.sub(r'[\u064b-\u065f\u0670]', '', t.strip('!؟?.,، '))
    normalized = re.sub(r'[أإآٱ]', 'ا', normalized)
    def fold_greeting(text: str) -> str:
        return re.sub(r'[أإآٱ]', 'ا', re.sub(r'[\u064b-\u065f\u0670]', '', text))
    if len(t) < 55 and any(normalized == fold_greeting(greeting) or
                           (normalized.startswith(fold_greeting(greeting) + ' ') and len(normalized.split()) <= 5)
                           for greeting in greetings):
        responses = {
            LANG_AR: 'وعليكم السلام وأهلًا بيك في Masr Guide AI! أقدر أساعدك تكتشف مصر، تعرف تاريخ المعالم والثقافة، تختار المواصلات، أو تخطط رحلة على مزاجك. تحب نبدأ بإيه؟',
            LANG_EN: 'Welcome to Masr Guide AI! I can help you discover Egypt, explore history and culture, compare travel options or plan your trip. What would you like to explore?',
            LANG_FR: 'Bienvenue chez Masr Guide AI ! Je peux vous aider à découvrir les sites, la culture et les options de voyage en Égypte. Par où souhaitez-vous commencer ?',
        }
        return {'mode': 'local-assistant', 'sources': [], 'answer': responses.get(language, responses[LANG_EN])}

    if re.search(r'(?:سعر|تكلفة|price|fare|cost|combien)', t) and re.search(r'(?:أتوبيس|اتوبيس|autobus|bus|coach|قطار|train)', t):
        return reply('ما عنديش سعر مباشر لتذاكر المواصلات. السعر بيعتمد على التاريخ، الشركة، ونوع الخدمة؛ تأكد من مشغل النقل قبل الدفع.',
                     'I cannot quote live transport fares. Prices depend on operator, date and service type. Check directly with the provider.',
                     'Je ne dispose pas de tarifs de transport en temps réel ; vérifiez auprès du transporteur.')
    # Practical neighborhood-level airport transfer: distinguish Cairo Airport
    # from Cairo city and Zamalek district. These are OPTIONS only, never a
    # claimed route, live fare, arrival time or booking confirmation.
    airport = re.search(r'(?:مطار القاهرة|مطار القاهره|cairo (?:international )?airport|cai airport|aéroport du caire)', t)
    zamalek = re.search(r'(?:للزمالك|الزمالك|زمالك|zamalek|zamalik)', t)
    if airport and zamalek and re.search(r'(?:ازاي|إزاي|مواصلات|اروح|أروح|اوصل|أوصل|انتقل|الانتقال|'
                                         r'how to|get (?:from|to)|how do i reach|reach|arriv(?:e|ing)|transport|transfer|taxi|comment aller|aller)', t):
        return reply(
            'من مطار القاهرة إلى الزمالك تقدر تقارن تاكسي المطار المرخّص، أو تطبيق نقل مرخّص متاح وقت وصولك، أو سيارة يستقبل بها الفندق ضيوفه بعد تأكيد الحجز. '
            'راجع نقطة الالتقاء والسعر النهائي مع مقدم الخدمة قبل الركوب. مش عندي أسعار أو زمن وصول مباشر، ومش هأكد مسار مواصلات عامة من غير تحقق.',
            'From Cairo International Airport to Zamalek, compare a licensed airport taxi, an authorized ride-hailing option available on arrival, or a prearranged hotel transfer. '
            'Confirm the pickup point and final quote with the operator before travelling. I cannot verify live prices, journey times, or public-transport routes.',
            'Pour rejoindre Zamalek depuis l’aéroport du Caire, comparez un taxi officiel, un service de voiture autorisé ou un transfert organisé par votre hôtel. '
            'Confirmez le tarif et le lieu de prise en charge ; je n’ai pas de tarifs ou durées en direct.')

    # If the traveler already mentioned a hotel, an airport-transfer question is
    # still a TRANSPORT request. Never treat it as a new hotel recommendation.
    if (re.search(r'(?:المطار|مطار|airport|aéroport)', t)
            and re.search(r'(?:الفندق|فندق|hotel|hôtel|تاكسي|taxi|transfer|توصيل)', t)
            and re.search(r'(?:تاكسي|taxi|transfer|توصيل|نروح|أروح|اروح|نصل|ازاي|إزاي|how|get to)', t)):
        return reply(
            'أيوه، تاكسي مرخّص من المطار أو خدمة نقل مرتبة مسبقًا مع الفندق ممكن يكونوا خيارين مناسبين. اسأل الفندق عن نقطة الاستقبال، وتأكد من هوية السائق والتكلفة النهائية قبل الركوب. ما عنديش سعر أو زمن انتقال مباشر أو تأكيد حجز.',
            'A licensed airport taxi or a transfer confirmed directly with your hotel are options. Confirm the pickup point, driver and final quote before travel. I cannot verify live fares, travel times or bookings.',
            'Un taxi officiel à l’aéroport ou un transfert confirmé avec votre hôtel sont des possibilités. Vérifiez le point de prise en charge et le tarif ; aucun prix ni réservation en direct.')
    if (re.search(r'(?:محطة رمسيس|محطة مصر|ramses station|ramses railway)', t)
            and re.search(r'(?:التحرير|ميدان التحرير|tahrir)', t)
            and re.search(r'(?:ازاي|إزاي|أروح|اروح|اوصل|أوصل|مواصلات|how|get to|transport)', t)):
        return reply(
            'من محطة رمسيس إلى ميدان التحرير ممكن تقارن بين المترو أو سيارة مرخّصة حسب حقائبك واحتياجاتك. راجع اتجاه الخط والمحطة المناسبة على خريطة المترو الرسمية، ولا تعتمد على موعد أو سعر غير متحقق منه.',
            'Between Ramses railway station and Tahrir Square, compare the Cairo Metro with a licensed car, depending on luggage and mobility needs. Verify the correct line and stations using the official Metro map; I cannot confirm live fares.',
            'Entre la gare Ramsès et la place Tahrir, comparez le métro du Caire et une voiture autorisée. Vérifiez les stations et le tarif auprès des opérateurs.')

    # First-time family question should give a useful, honest starting point
    # instead of answering with unrelated attraction facts or fake prices.
    first_visit = re.search(r'(?:اول مرة|أول مرة|first time|premi[eè]re fois)', t)
    kids = re.search(r'(?:زوجتي|زوجي|عيلتي|عائلة|عيلة|طفلين|طفل|أطفال|اطفال|family|children|kids?|enfants?)', t)
    if first_visit and kids:
        return reply(
            'لأول زيارة عائلية لمصر، ممكن تبدأوا بيوم مرن لزيارة الأهرامات في الجيزة مع فترات راحة، ويوم لمعالم القاهرة أو متحف مناسب لعمر الأطفال. '
            'لو عندكم أسبوع، اقترح يوم وصول خفيف وأيام نشاط بالتبادل مع أوقات راحة، مع ترك برنامج السفر النهائي حسب ميزانيتكم وأعمار الأطفال والمدينة اللي هتقيموا فيها. '
            'قلّي أعمار الأطفال والمدة والميزانية، وأجهز توزيع أيام قابل للتعديل. لازم تتحققوا من المواعيد وإمكانية الوصول قبل الزيارة.',
            'For a first family trip to Egypt, consider a relaxed Giza pyramids day and a separate Cairo museum or cultural day, with rest breaks and a light arrival day. '
            'Tell me the children’s ages, the length of your stay and your budget to build an editable plan. Verify opening hours and accessibility before visiting.',
            'Pour une première visite familiale, envisagez une journée tranquille aux pyramides de Gizeh et une autre journée culturelle au Caire, avec des pauses. '
            'Indiquez l’âge des enfants, la durée et le budget pour un itinéraire modifiable. Vérifiez horaires et accessibilité.')

    # Only take over clear transportation questions, not any mention of a city.
    transport = (r'ازاي (?:اقدر )?اروح|ازاي اوصل|إزاي (?:أقدر )?أروح|إزاي أوصل|'
                 r'مواصلات|انتقل من|الانتقال من|how (?:do|can) i get|how to get|'
                 r'get from .+ to |transport from|travel from|train from|train (?:to|between)|'
                 r'القطار|قطار|بالقطر|قطر من|\btrain\b|comment aller|comment se rendre')
    if not re.search(transport, t):
        return None
    cities = _known_cities(t)
    if len(cities) < 2:
        replies = {
            LANG_AR: 'أقدر أساعدك تقارن وسائل الانتقال، لكن محتاج أعرف نقطة البداية والوجهة (مثلًا: من القاهرة للغردقة). مش عندي مواعيد أو أسعار حية.',
            LANG_EN: 'Tell me your starting city and destination so I can outline transport options. I do not have live timetables or fares.',
            LANG_FR: 'Précisez la ville de départ et la destination pour comparer les transports. Je ne dispose pas des horaires ou tarifs en direct.',
        }
        return {'mode': 'local-assistant', 'sources': [], 'answer': replies.get(language, replies[LANG_EN])}

    origin, destination = cities[0], cities[1]
    ar_names = {'Cairo': 'القاهرة', 'Giza': 'الجيزة', 'Hurghada': 'الغردقة',
                'Sharm El Sheikh': 'شرم الشيخ', 'Luxor': 'الأقصر', 'Aswan': 'أسوان',
                'Alexandria': 'الإسكندرية', 'Dahab': 'دهب'}
    if language == LANG_AR:
        answer = (f'للانتقال من {ar_names.get(origin, origin)} إلى {ar_names.get(destination, destination)}، '
                  'ممكن تقارن بين الأتوبيسات بين المدن أو السيارة الخاصة، وتتحقق من وجود قطار أو رحلات طيران إن كانت متاحة على هذا المسار. '
                  'اختار حسب وقت السفر والراحة والميزانية. دي خيارات عامة وليست تأكيدًا لتشغيل أي خط؛ '
                  'لا أملك جداول رحلات أو أسعارًا حية، فراجع شركة النقل قبل الحجز. '
                  'لو قلتلي يوم السفر وعدد المسافرين وأولوياتك، أساعدك تقارن الخيارات.')
    elif language == LANG_FR:
        answer = (f'Pour aller de {origin} à {destination}, comparez les autocars interurbains et la voiture privée, '
                  'et vérifiez les vols si cette liaison est proposée. Je ne peux pas confirmer les horaires, '
                  'les tarifs ni la disponibilité en temps réel. Donnez-moi votre date et vos préférences pour affiner les options.')
    else:
        answer = (f'To get from {origin} to {destination}, compare intercity coaches and private car travel, '
                  'and check whether a suitable flight operates on your dates. These are general options, '
                  'not verified live routes. I cannot confirm real-time prices or timetables. '
                  'Tell me your date, party size and priorities to narrow the comparison.')
    return {'mode': 'local-assistant', 'sources': [], 'answer': answer}
