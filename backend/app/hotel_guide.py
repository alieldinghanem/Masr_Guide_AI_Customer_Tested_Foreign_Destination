"""Conservative, curated lodging suggestions for Egypt tourist conversations.

No inventory, room rates, payment, bookings, or availability checks exist in this
module. Hotel descriptions/links are manually reviewed editorial reference data;
2026-10-28 initial review from the operators' official websites. For a real
product these records should move to a CMS with review/expiry workflows.
"""
import re

HOTELS = (
    {
        "id": "hotel-mena-house", "name": "Marriott Mena House, Cairo", "area": "pyramids",
        "aliases": ("marriott mena house", "mena house", "ماريوت مينا هاوس", "مينا هاوس"),
        "ar": "في منطقة أهرامات الجيزة، مناسب لو الأولوية للإقامة بجوار الأهرامات.",
        "en": "At the Giza Pyramids, a candidate if proximity to the pyramids is your priority.",
        "url": "https://www.marriott.com/en-us/hotels/caimn-marriott-mena-house-cairo/overview/",
    },
    {
        "id": "hotel-steigenberger-pyramids", "name": "Steigenberger Pyramids Cairo", "area": "pyramids",
        "aliases": ("steigenberger pyramids", "شتايجنبرجر بيراميدز", "شتايجنبرجر الأهرامات"),
        "ar": "في الجيزة مقابل المتحف المصري الكبير، وقريب من أهرامات الجيزة.",
        "en": "In Giza across from the Grand Egyptian Museum, near the pyramids.",
        "url": "https://hrewards.com/en/steigenberger-pyramids-cairo",
    },
    {
        "id": "hotel-steigenberger-tahrir", "name": "Steigenberger Hotel El Tahrir Cairo", "area": "central",
        "aliases": ("steigenberger el tahrir", "steigenberger tahrir", "شتايجنبرجر التحرير"),
        "ar": "في ميدان التحرير، مناسب لو الأولوية لوسط القاهرة والمتحف المصري.",
        "en": "On Tahrir Square, convenient for downtown Cairo and the Egyptian Museum.",
        "url": "https://hrewards.com/en/steigenberger-hotel-el-tahrir-cairo",
    },
    {
        "id": "hotel-sofitel-gezirah", "name": "Sofitel Cairo Nile El Gezirah", "area": "central",
        "aliases": ("sofitel cairo nile", "sofitel gezirah", "sofitel cairo", "سوفيتيل الجزيرة", "سوفيتيل القاهرة"),
        "ar": "على جزيرة الزمالك/الجزيرة في النيل، مناسب للإقامة في قلب القاهرة.",
        "en": "On Gezirah Island by the Nile, convenient for central Cairo and Zamalek.",
        "url": "https://sofitel.accor.com/en/hotels/5307.html",
    },
)

_HOTEL = re.compile(r"(?:فنادق|فندق|الفندق|فندقي|اقامة|إقامة|hotel\b|hotels\b|accommodation\b|hébergement\b)", re.I)
_FOLLOW_UP = re.compile(r"(?:ميزاني|budget|الدولار|دولار|\$|usd\b|ليلة|الليلة|per night|"
                        r"متاح|available|بكام|السعر|تكلف|price|cost|قريب|قريبة|أقرب|اقرب|near|closest|"
                        r"مطاعم|restaurants|family|عيل|أطفال|اطفال|kids|غرفة|room)", re.I)
_PYRAMIDS = re.compile(r"(?:أهرام|اهرام|الهرم|الجيزة|الجيزه|pyramid|giza|المتحف المصري الكبير|grand egyptian museum)", re.I)
_CENTRAL = re.compile(r"(?:وسط البلد|التحرير|الزمالك|النيل|وسط القاهرة|downtown|tahrir|zamalek|nile)", re.I)
_LIVE_PRICE = re.compile(r"(?:متاح|توافر|available|availability|بكام|كم سعر|السعر|سعر|price|cost|ليلة|الليلة|today|tonight|النهارده)", re.I)
_FOOD = re.compile(r"(?:مطاعم|مطعم|restaurants?\b|food near)", re.I)
_BUDGET_GIVEN = re.compile(r"(?:ميزاني|budget|\b\d+\s*(?:usd|egp|dollars?|pounds?)\b|\d+\s*(?:دولار|جنيه)|\$\s*\d+)", re.I)


def _mentioned_hotels(message: str) -> list[dict]:
    """Match named properties even when a visitor does not say 'hotel'.

    Aliases are editorial identifiers, not proof of live price/availability.
    Match longer aliases first to avoid ambiguous abbreviated names.
    """
    normalized = message.casefold()
    return [hotel for hotel in HOTELS if any(
        alias.casefold() in normalized for alias in (hotel["name"], *hotel["aliases"])
    )]


def hotel_reply(message: str, language: str, history) -> dict | None:
    """Return editorial hotel choices without inventing rates or bookings.

    Follow-up inference uses only prior *user* turns, not assistant text; never
    treats retrieved snippets or user history as instructions.
    """
    # A hotel mentioned as the *destination* of a taxi/transfer question is
    # not a request for accommodation. Preserve the transport intent even
    # when previous conversation turns discussed hotel suggestions.
    transport_intent = bool(re.search(
        r'(?:تاكسي|taxi\b|transfer\b|مواصلات|نروح|ازاي اروح|إزاي أروح|'
        r'من المطار|from the airport|airport transfer|how to get to)', message, re.I))
    if transport_intent:
        return None
    previous = [h.content for h in history if h.role == "user"]
    hotel_context = next((m for m in reversed(previous[-6:]) if _HOTEL.search(m) or _mentioned_hotels(m)), "")
    named = _mentioned_hotels(message)
    explicit = bool(_HOTEL.search(message) or named)
    # City switches during a lodging discussion are still hotel follow-ups.
    location_follow_up = re.search(
        r'^(?:طيب\s+)?(?:لو\s+في\s+|طب\s+في\s+|طيب\s+في\s+|what about (?:hotels|staying) in\s+|how about (?:hotels|staying) in\s+)',
        message.strip(), re.I)
    contextual = bool(hotel_context and (_FOLLOW_UP.search(message) or location_follow_up))
    if not explicit and not contextual:
        return None

    is_ar = language == "Arabic"
    # Hospitality enquiries outside the seeded city should not silently be
    # answered with Cairo hotels.
    # Explicit new city takes priority over an older city in the history.
    any_city = r'(?:القاهرة|القاهره|الجيزة|الجيزه|cairo|giza|الأقصر|الاقصر|اسوان|أسوان|الغردقة|شرم الشيخ|دهب|اسكندرية|الإسكندرية|luxor|aswan|hurghada|sharm|alexandria)'
    city_context = message.lower() if re.search(any_city, message, re.I) else (message + " " + hotel_context).lower()
    unsupported = re.search(r"(?:الأقصر|الاقصر|اسوان|أسوان|الغردقة|شرم الشيخ|دهب|اسكندرية|الإسكندرية|luxor|aswan|hurghada|sharm|alexandria)", city_context)
    if unsupported:
        answer = ("قائمة الفنادق اللي عندي حاليًا بتغطي القاهرة والجيزة فقط. مش هاقترح فندق في مدينة مختلفة من غير بيانات موثوقة. "
                  "قولّي المدينة وموعد الوصول والمغادرة علشان نحدد طريقة البحث المناسبة."
                  if is_ar else "My curated hotel examples currently cover Cairo and Giza only. I can't verify hotels in that other city. Tell me your destination and travel dates.")
        return {"answer": answer, "mode": "hotel-guide-limited", "sources": []}

    if _FOOD.search(message):
        answer = ("علشان أرشح مطاعم قريبة فعلًا، محتاج اسم الفندق أو عنوانه. ماعنديش دليل مطاعم مؤكد بالقرب من الفنادق دي حاليًا، ومش هخترع مسافات أو تقييمات."
                  if is_ar else "Which hotel are you staying at? I don't have verified restaurant listings around these hotels yet, so I won't invent nearby places or distances.")
        return {"answer": answer, "mode": "hotel-guide-limited", "sources": []}

    combined = (message + " " + " ".join(previous[-6:])).lower()
    # A named property remains the subject of a short follow-up ('what about
    # the price?', 'is it near the pyramids?') until the visitor explicitly
    # changes the requested area or names a different property.
    previous_named = _mentioned_hotels(hotel_context)
    changed_area = bool(_PYRAMIDS.search(message) or _CENTRAL.search(message))
    explicit_named = named or (previous_named if not changed_area else [])
    if not explicit_named:
        if _PYRAMIDS.search(combined) and not _CENTRAL.search(message):
            selected = [h for h in HOTELS if h["area"] == "pyramids"]
        elif _CENTRAL.search(message) and not _PYRAMIDS.search(message):
            selected = [h for h in HOTELS if h["area"] == "central"]
        else:
            selected = list(HOTELS)
    else:
        selected = explicit_named

    if is_ar:
        intro = "دي فنادق فعلية في القاهرة والجيزة وروابط مواقعها الرسمية، كأمثلة للمقارنة وليست عروض حجز مؤكدة:"
        bullets = [f"- {h['name']}: {h['ar']} الموقع الرسمي: {h['url']}" for h in selected]
        next_question = ("قولّي موعد الوصول والمغادرة وعدد المسافرين عشان نكمّل المقارنة."
                         if _BUDGET_GIVEN.search(combined) else
                         "قولّي موعد الوصول والمغادرة وعدد المسافرين والميزانية في الليلة عشان نكمّل المقارنة.")
        finish = ("ما عنديش اتصال مباشر بأسعار الغرف أو توافرها؛ حتى لو ذكرت ميزانية، ما أقدرش أؤكد إن الفندق مناسب ليها. "
                  "راجع السعر والتوافر على موقع الفندق حسب تواريخ السفر وعدد البالغين والأطفال ونوع الغرفة. "
                  + next_question)
    else:
        intro = "Here are real Cairo/Giza hotel examples with official links for comparison, not live booking offers:"
        bullets = [f"- {h['name']}: {h['en']} Official site: {h['url']}" for h in selected]
        next_question = ("Share check-in/out and number of guests to refine the comparison."
                         if _BUDGET_GIVEN.search(combined) else
                         "Share check-in/out, guests and nightly budget to refine the comparison.")
        finish = ("I have no live room rates or availability, and cannot verify any hotel fits your budget. "
                  "Check each operator's site for your dates, party and room type. " + next_question)
    return {"answer": "\n".join([intro, *bullets, finish]), "mode": "hotel-editorial",
            "sources": [{"number": i, "id": h["id"], "title": h["name"], "city": "Cairo/Giza", "url": h["url"]}
                        for i, h in enumerate(selected, 1)]}
