"""Masr Guide's conversational itinerary orchestrator.

Turns natural language into a *validated* planning request; never asks the LLM to
invent stops or route timings. An optional Gemini extraction enhances phrasing;
local deterministic rules always work without internet or paid services.

MVP scope: illustrative attractions, capped at 30 days and curated cities. Travel
between phase boundaries is approximate and is displayed separately, NOT used
as a guarantee of feasibility or realtime logistics.
"""
import json
import re
from copy import deepcopy
from typing import Any
from fastapi import HTTPException

from .conversation_router import detect_language
from .catalog_extra import CITY_AR
from .database import all_places
from .gemini_client import gemini_key, generate
from .openai_client import openai_key, generate as generate_openai
import os
from .guide import answer_chat
from .planner import build_plan, city_centres, estimate_transfer
from .schemas import PlanRequest, TripState

_CITY_ALIASES = {
    'cairo': 'Cairo', 'القاهره': 'Cairo', 'القاهرة': 'Cairo', 'للقاهرة': 'Cairo',
    'giza': 'Giza', 'الجيزة': 'Giza', 'الجيزه': 'Giza',
    'luxor': 'Luxor', 'louxor': 'Luxor', 'الأقصر': 'Luxor', 'الاقصر': 'Luxor',
    'le caire': 'Cairo', 'caire': 'Cairo', 'assouan': 'Aswan', 'alexandrie': 'Alexandria',
    'aswan': 'Aswan', 'اسوان': 'Aswan', 'أسوان': 'Aswan',
    'alexandria': 'Alexandria', 'الاسكندرية': 'Alexandria', 'الإسكندرية': 'Alexandria', 'اسكندريه': 'Alexandria',
    'hurghada': 'Hurghada', 'الغردقة': 'Hurghada', 'الغردقه': 'Hurghada', 'للغردقة': 'Hurghada', 'للغردقه': 'Hurghada',
    'sharm el sheikh': 'Sharm El Sheikh', 'sharm': 'Sharm El Sheikh', 'شرم الشيخ': 'Sharm El Sheikh',
    'dahab': 'Dahab', 'دهب': 'Dahab', 'دهب ': 'Dahab',
    'siwa': 'Siwa', 'سيوة': 'Siwa', 'سيوه': 'Siwa',
    'fayoum': 'Fayoum', 'الفيوم': 'Fayoum',
    'abu simbel': 'Abu Simbel', 'أبو سمبل': 'Abu Simbel',
    'saint catherine': 'Saint Catherine', 'سانت كاترين': 'Saint Catherine',
    'marsa matrouh': 'Marsa Matrouh', 'مرسى مطروح': 'Marsa Matrouh',
}
# Explicit destinations outside our Egypt-only catalogue. These are checked
# BEFORE the generic Cairo fallback. Never silently replace a customer's
# requested non-Egyptian location with a different city.
_NON_EGYPT_DESTINATIONS = {
    'rome': 'Rome', 'roma': 'Rome', 'روما': 'Rome',
    'paris': 'Paris', 'باريس': 'Paris',
    'london': 'London', 'لندن': 'London',
    'dubai': 'Dubai', 'دبي': 'Dubai',
    'istanbul': 'Istanbul', 'اسطنبول': 'Istanbul', 'إسطنبول': 'Istanbul',
    'tokyo': 'Tokyo', 'طوكيو': 'Tokyo',
    'barcelona': 'Barcelona', 'برشلونة': 'Barcelona',
    'madrid': 'Madrid', 'مدريد': 'Madrid',
    'berlin': 'Berlin', 'برلين': 'Berlin',
    'riyadh': 'Riyadh', 'الرياض': 'Riyadh',
    'jeddah': 'Jeddah', 'جدة': 'Jeddah',
    'mecca': 'Mecca', 'مكة': 'Mecca',
    'saudi arabia': 'Saudi Arabia', 'السعودية': 'Saudi Arabia',
    'turkey': 'Turkey', 'تركيا': 'Turkey',
    'italy': 'Italy', 'إيطاليا': 'Italy', 'ايطاليا': 'Italy',
    'france': 'France', 'فرنسا': 'France',
}


def _explicit_non_egypt_destination(message: str) -> list[str]:
    text = message.lower()
    return sorted({name for alias, name in _NON_EGYPT_DESTINATIONS.items()
                   if re.search(r'(?<!\w)(?:و)?(?:ل)?' + re.escape(alias) + r'(?!\w)', text)})


_BEACH = ('beach', 'sea', 'red sea', 'coast', 'snorkel', 'diving', 'بحر', 'شاطئ', 'شواطئ', 'غوص', 'سباحة', 'mer', 'plage', 'hurghada', 'الغردقة', 'الغردقه', 'للغردقة', 'للغردقه', 'sharm', 'شرم الشيخ', 'dahab', 'دهب')
_HISTORY = ('history', 'historic', 'ancient', 'museum', 'pyramid', 'temple', 'ruins', 'heritage', 'آثار', 'اثار', 'تاريخ', 'معابد', 'متحف', 'اهرام', 'histoire', 'antique')
_PLAN = ('plan', 'itinerary', 'trip', 'holiday', 'travel', 'visit egypt', 'week', 'days', 'route', 'برنامج', 'رحلة', 'اسبوع', 'أسبوع', 'يوم', 'زيارة', 'visiter', 'voyage', 'jours', 'semaine')
_EDIT = ('move ', 'transfer ', 'shift ', 'انقل', 'نقل ', 'حوّل', 'حول ', 'change', 'replace', 'instead', 'remove', 'swap', 'modify', 'add one', 'extra day', 'more day', 'switch', 'غير', 'غيّر', 'بدل', 'بدّل', 'استبدل', 'خلي', 'خلّي', 'خلينا', 'احذف', 'شيل', 'زود', 'زيادة', 'ضيف', 'plus de', 'remplace', 'add ', 'include ', 'أضف', 'اضف', 'more days', 'fewer days', 'less days', 'مدة الرحلة', 'المدة', 'ميزانيتي', 'budget', 'معايا')


def mentioned_cities(text: str, available: set[str]) -> list[str]:
    t = text.lower()
    hits = []
    for alias, canonical in sorted(_CITY_ALIASES.items(), key=lambda a: -len(a[0])):
        if canonical in available and alias in t and canonical not in hits:
            hits.append(canonical)
    return hits



def _explicit_city_allocations(message: str, available: set[str]) -> list[tuple[str, int]]:
    """Parse clearly expressed per-city durations, including Arabic 'يومين'.

    Do not infer allocations when any named destination lacks a duration.
    A structured state rather than an LLM decides the authoritative day count.
    """
    t = _digits(message)
    unit = r'(?:days?|jours?|أيام|ايام|يوم|ليالي|ليلة|nights?)'
    amount = r'(?:\d{1,2}|يومين|يومان|one|two|three|four|five|six|seven|eight|nine|ten|un|deux|trois|quatre|cinq|six|sept|huit|neuf|dix)'
    prep = r'(?:in|at|for|on|في|على|علي|ل|لل|ب|الى|إلى)'
    results = {}
    for alias, city in sorted(_CITY_ALIASES.items(), key=lambda item: -len(item[0])):
        if city not in available:
            continue
        name = re.escape(alias.strip())
        patterns = (
            rf'(?<![\w])(?:و\s*)?({amount})\s*(?:{unit}\s*)?(?:{prep}\s*){{0,2}}{name}(?!\w)',
            rf'(?<!\w){name}\s*(?:{prep}\s*){{0,2}}({amount})\s*(?:{unit})?',
        )
        for pattern in patterns:
            found = re.search(pattern, t)
            if not found:
                continue
            value = found.group(1)
            count = {'يومين': 2, 'يومان': 2, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'un': 1, 'deux': 2, 'trois': 3, 'quatre': 4, 'cinq': 5, 'six': 6, 'sept': 7, 'huit': 8, 'neuf': 9, 'dix': 10}.get(value)
            if count is None:
                count = int(value)
            if 1 <= count <= 30 and (city not in results or found.start() < results[city][0]):
                results[city] = (found.start(), count)
    named = mentioned_cities(message, available)
    if len(named) < 2 or any(city not in results for city in named):
        return []
    return [(city, count) for city, (_, count) in sorted(results.items(), key=lambda item: item[1][0])]


def _full_reallocation(state: dict, message: str, available: set[str]) -> dict | None:
    """Treat a COMPLETE, explicitly requested city/day split as a new version of
    the plan. The requested destinations replace the prior split, never a
    guessed mutation of unrelated phases. Preserve user preferences.
    """
    phrase = _digits(message)
    if not re.search(
        r'(?:غير(?:ها|ه|لي|الرحلة| البرنامج)?|غيّر|خلي(?:ها|ه| الرحلة)?|'
        r'اعد(?:ها| تخطيط)|أعد(?:ها| تخطيط)|وزع|وزّع|'
        r'change (?:it|the trip|my trip|the itinerary)|replan|'
        r'make (?:it|the trip|my trip)|set (?:it|the trip)|répartis|modifie)', phrase
    ):
        return None
    allocation = _explicit_city_allocations(message, available)
    if not allocation or len(allocation) > 5:
        return None
    days = sum(count for _, count in allocation)
    declared = _declared_overall_duration(message)
    if days > 30 or (declared is not None and declared != days):
        return None
    rebuilt = _standard_state(
        days, any(p['kind'] == 'history' for p in state['phases']),
        any(city in {'Hurghada', 'Sharm El Sheikh', 'Dahab', 'Alexandria'} for city, _ in allocation),
        [city for city, _ in allocation], message,
        state.get('budget_egp'), allocation
    )
    rebuilt['budget_usd'] = _budget_usd(message) or state.get('budget_usd')
    rebuilt['family'] = state['family']
    rebuilt['pace'] = state['pace']
    rebuilt['accessibility_needs'] = state.get('accessibility_needs', False)
    return rebuilt


def _declared_overall_duration(message: str) -> int | None:
    """Separate a stated total from the individual city-day amounts."""
    t = _digits(message)
    match = re.search(
        r'(?:\b(?:plan|trip|journey|holiday)\b|رحلة|برنامج|مدة الرحلة)'
        r'[^\d]{0,24}(\d{1,2})\s*(?:days?|jours?|يوم|أيام|ايام)', t)
    if not match:
        return None
    # 'Plan 10 days in Cairo' declares a *city stay*, not a 10-day total.
    suffix = t[match.end():]
    # 'Change the trip: 3 days Cairo and 3 days Aswan' is a complete
    # city-by-city allocation, NOT a declaration that the whole trip lasts
    # three days. A destination may immediately follow the unit, with or
    # without 'in'. Only a clearly separate total may override the sum.
    near = re.match(r'\s*(?:(?:in|at|for|في|على|علي)\s+)?(.+)', suffix)
    if near:
        for alias in _CITY_ALIASES:
            if re.match(re.escape(alias.strip()) + r'(?!\w)', near.group(1)):
                return None
    return int(match.group(1))


def _digits(text: str) -> str:
    """Normalize Arabic and Eastern-Arabic numerals before intent extraction."""
    return text.lower().translate(str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789'))


def _explicit_phase_days(message: str, segment: str) -> int | None:
    """Recognize explicit regional splits without guessing from unrelated numbers.

    Examples: '7 أيام على البحر', '7 البحر', '13 يوم في القاهرة',
    '7 days by the sea', 'Hurghada 7 days'. The number must be adjacent to
    the location, allowing only a unit and common prepositions in between.
    """
    t = _digits(message)
    beach_terms = r'(?:البحر|بحر|الشاطئ|شاطئ|شواطئ|beach|sea|seaside|للغردقة|للغردقه|الغردقة|الغردقه|hurghada|شرم الشيخ|sharm(?: el sheikh)?)'
    culture_terms = r'(?:القاهرة|القاهره|cairo|الأقصر|الاقصر|luxor|أسوان|اسوان|aswan|الجيزة|الجيزه|giza)'
    place = beach_terms if segment == 'beach' else culture_terms
    unit = r'(?:يوم|أيام|ايام|days?|jours?)'
    preposition = r'(?:في|على|علي|ع|ل|لل|ب|at|in|on|by|for|the|of|to|around)'
    forward = rf'(?<!\d)(\d{{1,2}})\s*(?:{unit}\s*)?(?:{preposition}\s*){{0,3}}{place}'
    reverse = rf'{place}\s*(?:{preposition}\s*){{0,2}}(\d{{1,2}})\s*(?:{unit})?'
    for regex in (forward, reverse):
        found = re.search(regex, t)
        if found:
            value = int(found.group(1))
            return value if 1 <= value <= 30 else None
    return None


def total_days(message: str) -> int | None:
    t = _digits(message)
    # Explicit total-trip duration wins over earlier per-city allocations, e.g.
    # "7 days on the beach, but change the whole trip to 20 days".
    overall = re.search(
        r'(?:whole\s+trip|entire\s+trip|total\s+(?:trip\s+)?duration|'
        r'الرحلة\s*(?:كلها|كاملة|بكاملها)?|مدة\s+الرحلة)'
        r'[^\d]{0,28}(\d{1,3})\s*(?:days?|jours?|يوم|أيام|ايام)', t)
    if overall:
        return int(overall.group(1))
    # Accept adjectival English durations such as "a 14-day family trip" as
    # well as the conventional "14 days" form.
    dates = [int(m.group(1)) for m in re.finditer(
        r'(?<!\d)(\d{1,3})\s*(?:-\s*)?(?:days?|jours?|يوم|أيام|ايام)', t)]
    if not dates:
        word_numbers = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
                        'un': 1, 'deux': 2, 'trois': 3, 'quatre': 4, 'cinq': 5,
                        'sept': 7, 'huit': 8, 'neuf': 9, 'dix': 10,
                        'onze': 11, 'douze': 12, 'quinze': 15, 'vingt': 20, 'trente': 30}
        word_durations = list(re.finditer(
            r'\b(' + '|'.join(word_numbers) + r')\s+(?:days?|jours?)\b', t))
        # If several city durations were named, never mistake the first for
        # the full holiday. A single duration can safely initialize a draft.
        if len(word_durations) == 1:
            return word_numbers[word_durations[0].group(1)]
    # '20 days: 13 days Cairo, 7 days beach' is a 20-day trip, not 13.
    if dates:
        if len(dates) > 2 and max(dates) == sum(dates) - max(dates):
            return max(dates)
        if len(dates) == 2:
            sea = _explicit_phase_days(t, 'beach')
            city = _explicit_phase_days(t, 'culture')
            if sea is not None and city is not None and sea + city <= 30:
                return sea + city
        return dates[0]
    for pattern, factor in [
        (r'\b(\d{1,2})\s*weeks?\b', 7),
        (r'(\d{1,2})\s*(?:اسابيع|أسابيع|اسبوع|أسبوع)', 7),
    ]:
        found = re.search(pattern, t)
        if found:
            return int(found.group(1)) * factor
    if any(word in t for word in ('one day', 'a day', 'يوم واحد', 'يوما واحدا', 'يومًا واحدًا', 'un jour')):
        return 1
    if any(word in t for word in ('two weeks', 'fortnight', 'اسبوعين', 'أسبوعين', 'deux semaines')):
        return 14
    if any(word in t for word in ('one week', 'a week', 'اسبوع واحد', 'أسبوع واحد', 'une semaine')):
        return 7
    if re.search(r'(?<![\w])(?:اسبوع|أسبوع)(?![\w])', t) and re.search(
            r'(?:مصر|رحلة|سفر|مدة|جاي|هنقعد|زيارة|برنامج|خطة|خطه)', t):
        return 7
    # Month-length intent for an *undated* trip: use an explicitly provisional
    # 30-day planning window. Never interpret 'next month' or a named calendar
    # month as 30 dates, because actual calendar lengths vary (28–31 days).
    month_count = re.search(
        r'(?<!\w)(\d{1,2})\s*(?:months?|أشهر|اشهر|شهور)(?!\w)', t)
    if month_count:
        return int(month_count.group(1)) * 30
    if re.search(r'(?<!\w)(?:one|a)\s+month(?!\w)|'
                 r'(?<!\w)(?:un|une)\s+mois(?!\w)|'
                 r'(?<!\w)شهر(?:\s+واحد|\s+كامل)?(?!\w)', t):
        return 30
    beach = _explicit_phase_days(t, 'beach')
    culture = _explicit_phase_days(t, 'culture')
    if beach is not None and culture is not None and beach + culture <= 30:
        return beach + culture
    return None


def _relative_trip_extension(message: str) -> int | None:
    """Return an explicitly requested increase to the total trip duration."""
    t = _digits(message)
    total_phrase = r'(?:إجمالي\s+(?:مدة\s+)?الرحلة|اجمالي\s+(?:مدة\s+)?الرحلة|مدة\s+الرحلة|الرحلة\s+كلها|whole\s+trip|entire\s+trip|total\s+(?:trip\s+)?duration)'
    additive = r'(?:زود|زيد|مدد|اضف|زيادة|extend|increase|add)'
    if not (re.search(total_phrase, t, flags=re.I) and re.search(additive, t, flags=re.I)):
        return None
    amount = re.search(
        r'(?:ب(?:مقدار)?\s*)?(\d{1,2})\s*(?:days?|يوم|أيام|ايام)', t, flags=re.I)
    if amount:
        return int(amount.group(1))
    if re.search(r'(?:يوم\s+واحد|one\s+(?:more\s+)?day|an?\s+extra\s+day)', t, flags=re.I):
        return 1
    if re.search(r'(?:يومين|يومان|two\s+(?:more\s+)?days)', t, flags=re.I):
        return 2
    return None


def _extension_city_from_context(request, message: str, state: dict, available: set[str]) -> str | None:
    """Resolve the city for a clarified extension from literal chat context."""
    present = {city for phase in state['phases'] for city in phase['cities']}
    # Cities named after "without/من غير" are protected from the edit, not
    # candidates to receive the extra days. Never count them as targets.
    target_clause = re.split(r'\bwithout\b|\band\s+keep\b|من\s+غير|بدون|وخلي\s+(?:أيام\s+|ايام\s+)?(?=ال)',
                             message, maxsplit=1, flags=re.I)[0]
    current = [city for city in mentioned_cities(target_clause, available) if city in present]
    if len(current) == 1:
        return current[0]
    if len(current) > 1:
        return None
    for turn in reversed(request.history):
        if turn.role != 'user':
            continue
        prior = [city for city in mentioned_cities(turn.content, available) if city in present]
        if len(prior) == 1 and re.search(
                r'(?:\b(?:add|increase|extend)\b|زود|زيد|ضيف|اضف)',
                _digits(turn.content), flags=re.I):
            return prior[0]
    return None


def _apply_relative_extension(state: dict, amount: int, city: str | None) -> dict | None:
    """Extend without taking or redistributing any existing city days."""
    if amount < 1 or state['days'] + amount > 30 or city is None:
        return None
    matches = [i for i, phase in enumerate(state['phases']) if city in phase['cities']]
    if len(matches) != 1:
        return None
    index = matches[0]
    updated = deepcopy(state)
    phase = updated['phases'][index]
    if len(phase['cities']) > 1:
        # Freeze the planner's current per-city allocation before extending a
        # shared phase. Increasing its total directly could move another city's
        # days when the planner distributes the new total.
        if len(updated['phases']) - 1 + len(phase['cities']) > 5:
            return None
        current = build_plan(PlanRequest(
            cities=phase['cities'], days=phase['days'], interests=phase['interests'],
            pace=state['pace'], family=state['family'], optimize_route=False,
            language='en',
        ))['day_allocation']
        separate = []
        for name in phase['cities']:
            segment = deepcopy(phase)
            segment['cities'] = [name]
            segment['days'] = current[name]
            separate.append(segment)
        updated['phases'][index:index + 1] = separate
        index += phase['cities'].index(city)
    updated['days'] += amount
    updated['phases'][index]['days'] += amount
    return updated


def wants_beach(message: str) -> bool:
    return any(w in message.lower() for w in _BEACH)


def wants_history(message: str) -> bool:
    return any(w in message.lower() for w in _HISTORY)


def needs_accessibility(message: str) -> bool:
    return bool(re.search(
        r'(?:wheelchair|step.free|reduced mobility|fauteuil roulant|mobilité réduite|'
        r'كرسي متحرك|الكراسي المتحركة|صعوبة الحركة|إعاقة حركية)',
        message.lower()))


def _reply_language(message: str, requested: str) -> str:
    return detect_language(message, requested)


def _budget_egp(message: str) -> tuple[int | None, bool]:
    """Read an explicit EGP number but flag confusing '15000 ألف' expressions."""
    t = message.lower().replace(',', '').replace('،', '')
    t = t.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))
    if not any(w in t for w in ('جنيه', 'egp', 'pound')):
        return None, False
    match = re.search(r'(?<!\d)(\d{1,9})\s*(?:الف|ألف|آلاف)?\s*(?:جنيه|egp|pounds?)', t)
    if not match:
        return None, False
    value = int(match.group(1))
    fragment = t[match.start():match.end()]
    thousands = bool(re.search(r'(?:الف|ألف|آلاف)', fragment))
    if thousands and value >= 1000:
        return None, True
    return value * (1000 if thousands else 1), False



def _budget_usd(message: str) -> int | None:
    """Extract a *stated* USD travel budget; never convert FX or infer prices."""
    t = _digits(message).replace(',', '').replace('،', '')
    patterns = (
        r'(?:\busd\s*|\$\s*)(\d{1,7})(?!\d)',
        r'(?<!\d)(\d{1,7})\s*(?:\busd\b|dollars?\b|دولار(?:ات)?)(?!\w)',
    )
    for pattern in patterns:
        m = re.search(pattern, t)
        if m:
            val = int(m.group(1))
            return val if 1 <= val <= 1000000 else None
    return None


def _beach_duration(message: str, days: int) -> int | None:
    t = _digits(message)
    if not wants_beach(t) and not any(c in t for c in ('hurghada','الغردقة','الغردقه','sharm','شرم الشيخ','dahab','دهب')):
        return None
    explicit = _explicit_phase_days(t, 'beach')
    if explicit and explicit < days:
        return explicit
    cultural = _explicit_phase_days(t, 'culture')
    if cultural and cultural < days:
        return days - cultural
    if re.search(r'(?:first week|week one|اول اسبوع|أول أسبوع|الأسبوع الأول).{0,55}(?:beach|sea|بحر|شاطئ)', t):
        return 7 if days > 7 else None
    # Informal "a week at the beach" without a numeric expression.
    one_week = r'(?:اسبوع|أسبوع|7\s*(?:days?|ايام|أيام)|one week|a week|seven days)'
    beach = r'(?:بحر|شاطئ|شواطئ|beach|red sea|seaside|coast)'
    if re.search(one_week + r'.{0,80}' + beach, t) or re.search(beach + r'.{0,80}' + one_week, t):
        return 7 if days > 7 else None
    return None


def _standard_state(days: int, history: bool, beach: bool, cities: list[str], message: str = '', budget_egp: int | None = None, city_allocations: list[tuple[str, int]] | None = None):
    beach_cities = [x for x in cities if x in ('Hurghada', 'Sharm El Sheikh', 'Dahab', 'Alexandria')]
    historic_cities = [x for x in cities if x not in beach_cities]
    mixed_with_city = beach and bool(historic_cities)
    if city_allocations:
        coastal = {'Hurghada', 'Sharm El Sheikh', 'Dahab', 'Alexandria'}
        phases = []
        for city, count in city_allocations:
            coast = city in coastal
            kind = 'beach' if coast else ('history' if history else 'mixed')
            interests = ['beaches', 'nature'] if coast else (['history', 'culture', 'museums'] if history else ['culture', 'food', 'history'])
            phases.append({'kind': kind, 'days': count, 'cities': [city], 'interests': interests})
    elif (history or mixed_with_city) and beach and days >= 2:
        bdays = _beach_duration(message, days) or days // 2
        bdays = min(days - 1, max(1, bdays))
        hdays = days - bdays
        first_beach = bool(re.search(r'(?:first week|week one|اول اسبوع|أول أسبوع).{0,35}(?:beach|sea|بحر|شاطئ)', message.lower()))
        cultural = {'kind': 'history' if history else 'mixed', 'days': hdays,
                    'cities': historic_cities or ['Cairo', 'Luxor'],
                    'interests': ['history', 'culture', 'museums'] if history else ['culture', 'food', 'history']}
        coastal = {'kind': 'beach', 'days': bdays, 'cities': beach_cities or ['Hurghada'],
                   'interests': ['beaches', 'nature']}
        phases = [coastal, cultural] if first_beach else [cultural, coastal]
    elif beach:
        phases = [{'kind': 'beach', 'days': days, 'cities': beach_cities or ['Hurghada'], 'interests': ['beaches', 'nature']}]
    else:
        phases = [{'kind': 'history' if history else 'mixed', 'days': days,
                   'cities': historic_cities or cities or ['Cairo'], 'interests': ['history', 'culture'] if history else ['culture', 'nature']}]
    family = bool(re.search(r'(?:طفل(?:ين|ان|ة|ين)?|أطفال|اطفال|عائلي|عائلية|عيلة|عايلة|family|kids?|children|toddler|bébé|enfants?)', message.lower()))
    return {'days': days, 'phases': phases, 'pace': 'balanced', 'family': family, 'budget_egp': budget_egp,
            'accessibility_needs': needs_accessibility(message)}


def _extract_gemini(message: str, state: dict | None, available: set[str], *, provider: str = 'gemini'):
    """Optional bounded JSON patch. Server performs all authoritative validation."""
    instructions = ("Extract user travel intent; return JSON object only. Never invent destination names. "
                    "Known cities: " + ', '.join(sorted(available)) + '. '
                    'Schema keys: action (plan/edit/question), days (integer or null), history (boolean), '
                    'beach (boolean), city_preferences (array of exact city names), '
                    'replace_from (city name or empty string), replace_to (city name or empty string), '
                    'extra_day_city (city name or empty string). '
                    'Use empty or null for things user did not say. Changes refer to existing state.')
    generator = generate_openai if provider == 'openai' else generate
    response = generator(json.dumps({'message': message, 'current_trip': state}, ensure_ascii=False),
                         instructions, json_mode=True, max_tokens=450)
    data = json.loads(response)
    return data if isinstance(data, dict) else {}


def _valid_city(value, available):
    if not isinstance(value, str):
        return None
    if value in available:
        return value
    return _CITY_ALIASES.get(value.lower()) if _CITY_ALIASES.get(value.lower()) in available else None


def _explicit_replacement(message: str, state: dict, available: set[str]) -> tuple[str | None, str | None]:
    """Only replace cities when the traveler explicitly says WHICH city to swap.

    A model-proposed patch is not evidence of user authorization. The old city
    must be present in the trip and both names must be in the user's own text.
    """
    text = _digits(message)
    hits = []
    for alias, canonical in sorted(_CITY_ALIASES.items(), key=lambda pair: -len(pair[0])):
        if canonical not in available:
            continue
        for match in re.finditer(re.escape(alias), text):
            # Avoid an English alias matching inside an unrelated English word.
            if alias[0].isascii() and alias[0].isalpha():
                left = text[match.start()-1:match.start()]
                right = text[match.end():match.end()+1]
                if (left and left.isascii() and left.isalpha()) or (right and right.isascii() and right.isalpha()):
                    continue
            hits.append((match.start(), match.end(), canonical))
    hits.sort(key=lambda x: (x[0], -(x[1]-x[0])))
    ordered = []
    for hit in hits:
        if not any(hit[0] >= h[0] and hit[1] <= h[1] for h in ordered):
            ordered.append(hit)
    present = {city for phase in state['phases'] for city in phase['cities']}
    for index, old in enumerate(ordered):
        if old[2] not in present:
            continue
        prefix = text[max(0, old[0]-45):old[0]]
        if not re.search(r'(?:\b(?:replace|swap|switch|change|substitute)\b|بدل|استبدل|غير|غيّر|حول|حوّل)\s*$', prefix):
            continue
        for new in ordered[index+1:]:
            if new[0] - old[1] > 30 or new[2] == old[2]:
                continue
            between = text[old[1]:new[0]]
            if re.fullmatch(r'\s*(?:with|to|for|instead of|ب|ل|إلى|الى|بـ|ب\s*|ل\s*)\s*', between):
                return old[2], new[2]
    return None, None


def _transition_error(previous: dict, updated: dict, message: str, available: set[str]) -> str | None:
    """The backend, not the LLM, decides whether a state mutation is valid.

    Fail closed on unintended city replacements, invalid phase types and any
    unrelated field changes; failed edits keep the previous trip untouched.
    """
    # Prevent a future patch/refactor from modifying duration or phase allocations
    # while processing an unrelated request (e.g. updating only a budget).
    mentioned_total = total_days(message)
    beach_days = _explicit_phase_days(message, 'beach')
    land_days = _explicit_phase_days(message, 'culture')
    explicit_total = bool(re.search(
        r'(?:whole\s+trip|entire\s+trip|total\s+(?:trip\s+)?duration|'
        r'الرحلة\s*(?:كلها|كاملة|بكاملها)?|مدة\s+الرحلة)', message.lower()))
    duration_verb = bool(re.search(
        r'(?:\b(?:change|make|set|extend|shorten|increase|reduce)\b|خلي|خليه|زود|قلل)',
        message.lower()))
    if updated['days'] != previous['days']:
        authorized_total = (
            mentioned_total == updated['days'] and
            ((explicit_total or duration_verb) or
             (beach_days is not None and land_days is not None and
              beach_days + land_days == updated['days']))
        )
        if not authorized_total:
            return 'trip duration was changed without an explicit request'
    if [p['days'] for p in updated['phases']] != [p['days'] for p in previous['phases']]:
        adding_day = bool(re.search(
            r'(?:one more day|another day|extra day|يوم زيادة|يوم كمان|زود يوم|ضيف يوم)',
            message.lower()))
        if not (updated['days'] != previous['days'] or
                beach_days is not None or land_days is not None or adding_day):
            return 'phase allocation changed without an explicit request'
    phases = updated.get('phases', [])
    if not phases or sum(p['days'] for p in phases) != updated['days']:
        return 'phase durations do not match trip duration'
    if not 1 <= updated['days'] <= 30:
        return 'trip duration out of supported range'
    if len(phases) != len(previous['phases']):
        return 'unrequested phase structure change'
    coastal = {'Hurghada', 'Sharm El Sheikh', 'Dahab', 'Alexandria'}
    old_cities = [p['cities'] for p in previous['phases']]
    new_cities = [p['cities'] for p in phases]
    for old, new in zip(previous['phases'], phases):
        if new['kind'] != old['kind'] or new['interests'] != old['interests']:
            return 'unrequested phase type or interests change'
        if new['days'] < len(new['cities']) or not new['cities'] or len(new['cities']) != len(set(new['cities'])):
            return 'invalid number of days or duplicate cities'
        if any(city not in available for city in new['cities']):
            return 'unavailable city'
        if new['kind'] == 'beach' and any(city not in coastal for city in new['cities']):
            return 'destination is incompatible with the beach phase'
    if old_cities != new_cities:
        old, new = _explicit_replacement(message, previous, available)
        removed = {c for phase in old_cities for c in phase} - {c for phase in new_cities for c in phase}
        added = {c for phase in new_cities for c in phase} - {c for phase in old_cities for c in phase}
        add_command = bool(re.search(r'(?:\b(?:add|include)\b|ضيف|اضف|أضف)\s*', message.lower()))
        if removed:
            if not old or not new or removed != {old} or added != {new}:
                return 'destination replacement was not explicitly authorized'
        elif added:
            if not add_command or not added.issubset(set(mentioned_cities(message, available))):
                return 'destination addition was not explicitly authorized'
        else:
            return 'unexpected destination reorder'
    if previous['budget_egp'] != updated['budget_egp']:
        budget, ambiguous = _budget_egp(message)
        if ambiguous or budget != updated['budget_egp']:
            return 'unrequested budget update'
    if previous.get('budget_usd') != updated.get('budget_usd'):
        if _budget_usd(message) != updated.get('budget_usd'):
            return 'unrequested USD budget update'
    if previous['family'] != updated['family'] and not re.search(r'(?:kids?|children|family|طفلين|طفلان|عيلة|عائلة)', message.lower()):
        return 'unrequested family preference update'
    if previous['pace'] != updated['pace']:
        return 'unrequested pace update'
    if previous.get('accessibility_needs', False) != updated.get('accessibility_needs', False):
        return 'unrequested accessibility requirement change'
    return None


def _explicit_day_transfer(state: dict, message: str, available: set[str]) -> dict | None:
    """Move a stated number of days from an existing city to a new city.

    This intentionally covers a narrow, independently verifiable utterance,
    rather than accepting a speculative LLM modification of a trip. Duration,
    budget and all previously specified preferences remain unchanged.
    """
    t = _digits(message.strip()).lower()
    # Unambiguous redistribution between two EXISTING single-city phases.
    # This is not a new itinerary: retain all other preferences and the total.
    number = r'(?:يومين|\d{1,2}\s*(?:يوم|أيام|ايام)|\d{1,2}\s*days?)'
    arabic_move = re.fullmatch(
        rf'(?:انقل|حوّل|حول)\s+({number})\s+من\s+(.+?)\s+(?:إلى\s*|الى\s*|ل\s*)(.+?)\s*[.؟!]*',
        t, flags=re.I)
    # Common Egyptian Arabic phrasing: "شيل يومين من الأقصر وحطهم في الغردقة".
    colloquial_move = re.fullmatch(
        rf'(?:شيل|احذف)\s+({number})\s+من\s+(.+?)\s+'
        rf'(?:وحط(?:هم|ها)?|وضع(?:هم|ها)?|وضيف(?:هم|ها)?|واضف(?:هم|ها)?)\s+'
        rf'(?:في|على|ل|لل|الى|إلى)\s*(.+?)\s*[.؟!]*', t, flags=re.I)
    english_move = re.fullmatch(
        rf'(?:move|transfer|shift)\s+({number})\s+from\s+(.+?)\s+to\s+(.+?)\s*[.!?]*',
        t, flags=re.I)
    move = arabic_move or colloquial_move or english_move
    if move:
        count_raw, source_raw, target_raw = (s.strip().lower() for s in move.groups())
        amount = 2 if count_raw == 'يومين' else int(re.match(r'\d{1,2}', count_raw).group())
        source = _CITY_ALIASES.get(source_raw)
        target = _CITY_ALIASES.get(target_raw)
        if target is None:
            # The Arabic destination prefix may be attached: للغردقة.
            target = _CITY_ALIASES.get('ل' + target_raw)
        if target is None and target_raw.startswith('ل'):
            target = _CITY_ALIASES.get('ال' + target_raw[1:])
        if (not source or not target or source == target or amount < 1
                or source not in available or target not in available):
            return None
        donor = next((i for i, p in enumerate(state['phases']) if p['cities'] == [source]), None)
        receiver = next((i for i, p in enumerate(state['phases']) if p['cities'] == [target]), None)
        if donor is None or receiver is None or state['phases'][donor]['days'] - amount < 1:
            return None
        updated = deepcopy(state)
        updated['phases'][donor]['days'] -= amount
        updated['phases'][receiver]['days'] += amount
        return updated
    qty = r'(يومين|\d{1,2}\s*(?:يوم|أيام|ايام))'
    pattern = (rf'\s*(?:ضيف|اضف|أضف)\s+{qty}\s+(?:في|ل|لل)\s+'
               rf'(.+?)\s+بدل\s+{qty}\s+من\s+(.+?)\s*[.؟!]*')
    found = re.fullmatch(pattern, t, flags=re.I)
    if not found:
        return None
    def quantity(raw):
        if raw == 'يومين':
            return 2
        m = re.match(r'\d{1,2}', raw)
        return int(m.group()) if m else 0
    count, requested_city, donor_count, from_city = found.groups()
    amount = quantity(count)
    if amount < 1 or amount != quantity(donor_count):
        return None
    source = _CITY_ALIASES.get(from_city.strip().lower())
    target = _CITY_ALIASES.get(requested_city.strip().lower())
    if not source or not target or source == target or source not in available or target not in available:
        return None
    if any(target in p['cities'] for p in state['phases']):
        return None  # More complex multi-phase reallocations need clarification.
    index = next((i for i,p in enumerate(state['phases']) if p['cities']==[source]), None)
    if index is None or state['phases'][index]['days']-amount < 1 or len(state['phases'])>=5:
        return None
    updated = deepcopy(state)
    updated['phases'][index]['days'] -= amount
    coastal = {'Hurghada', 'Sharm El Sheikh', 'Dahab', 'Alexandria'}
    if target in coastal:
        kind, interests = 'beach', ['beaches', 'nature']
    else:
        kind, interests = 'mixed', ['culture', 'history']
    updated['phases'].insert(index+1, {'kind':kind,'days':amount,'cities':[target],'interests':interests})
    return updated


def _apply_edit(state, message, cities, hint, available):
    updated = deepcopy(state)
    new_days = total_days(message)
    explicit_beach = _explicit_phase_days(message, 'beach')
    explicit_culture = _explicit_phase_days(message, 'culture')
    # A phase-specific request is NOT necessarily a request to shorten the whole
    # holiday: "make the beach 7 days" must preserve the existing 14-day total.
    total_specified = bool(re.search(
        r'(?:whole\s+trip|entire\s+trip|total\s+(?:trip\s+)?duration|'
        r'الرحلة\s*(?:كلها|كاملة|بكاملها)?|مدة\s+الرحلة)'
        r'[^\d]{0,28}\d{1,3}\s*(?:days?|jours?|يوم|أيام|ايام)', _digits(message)))
    if explicit_beach is not None and explicit_culture is not None:
        # Both phases were explicitly requested: their sum determines the trip.
        # If the user also gave an incompatible overall total, do not silently
        # override either of their stated constraints.
        if total_specified and new_days != explicit_beach + explicit_culture:
            return state
        new_days = explicit_beach + explicit_culture
    elif (explicit_beach is not None or explicit_culture is not None) and not total_specified:
        new_days = state['days']
    # A duration edit is a state operation, not a fresh plan. Proportionally scale
    # phase lengths and preserve the exact sum and a minimum day per listed city.
    if new_days is not None and new_days != state['days']:
        minimums = [len(p['cities']) for p in updated['phases']]
        if not 1 <= new_days <= 30 or new_days < sum(minimums):
            return state
        weights = [p['days'] / state['days'] for p in updated['phases']]
        allocations = minimums[:]
        remaining = new_days - sum(allocations)
        quotas = [max(0, weights[i] * new_days - minimums[i]) for i in range(len(weights))]
        total_quota = sum(quotas)
        if total_quota:
            exact = [remaining * q / total_quota for q in quotas]
        else:
            exact = [remaining / len(weights)] * len(weights)
        whole = [int(q) for q in exact]
        allocations = [a + b for a, b in zip(allocations, whole)]
        extras = remaining - sum(whole)
        order = sorted(range(len(weights)), key=lambda i: -(exact[i] - whole[i]))
        for index in order[:extras]:
            allocations[index] += 1
        updated['days'] = new_days
        for phase, allocation in zip(updated['phases'], allocations):
            phase['days'] = allocation
    # Apply the requested phase split *after* any total-duration change. A valid
    # 13 Cairo + 7 Red Sea edit must never degrade into an automatic 10 + 10.
    beach_index = next((i for i, phase in enumerate(updated['phases']) if phase['kind'] == 'beach'), None)
    land_indices = [i for i, phase in enumerate(updated['phases']) if phase['kind'] != 'beach']
    if beach_index is not None and len(land_indices) == 1:
        land_index = land_indices[0]
        total = updated['days']
        if explicit_beach is not None or explicit_culture is not None:
            beach_alloc = explicit_beach if explicit_beach is not None else total - explicit_culture
            land_alloc = total - beach_alloc
            if (beach_alloc < len(updated['phases'][beach_index]['cities']) or
                    land_alloc < len(updated['phases'][land_index]['cities'])):
                return state
            updated['phases'][beach_index]['days'] = beach_alloc
            updated['phases'][land_index]['days'] = land_alloc
    budget_egp, ambiguous_budget = _budget_egp(message)
    if budget_egp is not None:
        updated['budget_egp'] = budget_egp
    budget_usd = _budget_usd(message)
    if budget_usd is not None:
        updated['budget_usd'] = budget_usd
    if re.search(r'(?:with (?:two|2) (?:kids|children)|(?:مع |عندي |معايا )?(?:طفلين|طفلان)|عيلة|عائلة|family)', message.lower()):
        updated['family'] = True
    # Never trust an LLM-suggested replacement unless the user's literal message
    # independently authorizes the old and new destination names.
    old, new = _explicit_replacement(message, state, available)
    if old and new and old != new:
        for phase in updated['phases']:
            if old in phase['cities']:
                phase['cities'] = list(dict.fromkeys(new if c == old else c for c in phase['cities']))
    requested_day_city = _valid_city(hint.get('extra_day_city'), available)
    if not requested_day_city and re.search(r'(one more day|another day|extra day|يوم زيادة|يوم كمان|زود يوم|ضيف يوم)', message.lower()):
        requested_day_city = next((c for c in cities if any(c in p['cities'] for p in updated['phases'])), None)
    if re.search(r'(?:\b(?:add|include)\b|ضيف|اضف|أضف)\s+', message.lower()) and not re.search(r'(?:one more day|another day|extra day|يوم زيادة|يوم كمان|زود يوم|ضيف يوم)', message.lower()):
        extra = [city for city in cities if not any(city in phase['cities'] for phase in updated['phases'])]
        for city in extra:
            phase = next((p for p in updated['phases'] if p['kind'] != 'beach'), updated['phases'][0])
            if len(phase['cities']) < 5 and phase['days'] > len(phase['cities']):
                phase['cities'].append(city)
    if requested_day_city and len(updated['phases']) > 1:
        receiver = next((i for i, p in enumerate(updated['phases']) if requested_day_city in p['cities']), None)
        donor = next((i for i, p in enumerate(updated['phases']) if i != receiver and p['days'] > len(p['cities'])), None)
        if receiver is not None and donor is not None:
            updated['phases'][receiver]['days'] += 1
            updated['phases'][donor]['days'] -= 1
    return updated


def _make_plan(state: dict, lang: str):
    days = []
    warnings = []
    route = []
    travel_minutes = 0
    total_places = 0
    sources = []
    centres = city_centres(all_places())
    for segment in state['phases']:
        req = PlanRequest(cities=segment['cities'], days=segment['days'], interests=segment['interests'],
                          pace=state['pace'], family=state['family'], optimize_route=False, language=lang)
        part = build_plan(req)
        if route and part['route']:
            prev_city, city = route[-1], part['route'][0]
            if prev_city != city and prev_city in centres and city in centres:
                transfer = estimate_transfer(prev_city, city, centres)
                travel_minutes += transfer['minutes']
                warnings.append((f'Cross-phase transfer {prev_city} → {city}: about {transfer["minutes"]} minutes, estimated; verify transport schedules.'
                                 if lang == 'en' else f'الانتقال بين {CITY_AR.get(prev_city, prev_city)} و{CITY_AR.get(city, city)} حوالي {transfer["minutes"]} دقيقة تقريبية؛ تأكد من وسائل النقل.'))
                if part['days']:
                    part['days'][0]['travel'] = {'from_city': prev_city, **transfer}
        offset = len(days)
        if route and part['days'] and part['days'][0].get('travel'):
            first = part['days'][0]
            first_day_allowance = {'relaxed': 240, 'balanced': 360, 'packed': 450}[state['pace']]
            # Travel to a phase consumes first-day capacity; drop stops rather than promising
            # physically impossible activity. Approximate, not live-routing.
            while first['stops'] and first['estimated_activity_minutes'] + first['travel']['minutes'] > first_day_allowance:
                first['stops'].pop()
                first['estimated_activity_minutes'] = sum(s['suggested_visit_minutes'] for s in first['stops']) + max(0, len(first['stops']) - 1) * 30
            if not first['stops']:
                first['note'] = ('Travel day; no reliably schedulable visit left.' if lang == 'en' else 'يوم انتقال؛ لم يتبق وقت مناسب لزيارة موثوقة.')
        for entry in part['days']:
            item = dict(entry)
            item['day'] += offset
            item['phase_kind'] = segment['kind']
            days.append(item)
        route.extend(part['route'])
        warnings.extend(part['warnings'])
        travel_minutes += part['total_travel_minutes']
        total_places += sum(len(day['stops']) for day in part['days'])
        for entry in part['days']:
            for stop in entry['stops']:
                p = stop['place']
                if p['id'] not in {x['id'] for x in sources}:
                    sources.append({'id': p['id'], 'title': p['name'], 'title_ar': p['name_ar'], 'url': p['source_url']})
    if state.get('accessibility_needs'):
        warnings.append(('Accessibility has NOT been verified at any attraction, entrance, transfer, or hotel. Confirm step-free routes and assistance with each operator before booking.' if lang == 'en' else
                         'إمكانية الوصول بالكراسي المتحركة غير متحقق منها للمعالم والمداخل والانتقالات والفنادق. يجب تأكيد الممرات والمساعدة مع كل جهة قبل الحجز.'))
    disclaimer = ('Illustrative plan. Many beach days are intentionally free time, not a fabricated activity. '
                  'No live prices, hotel/flight availability or schedules; cross-city travel is approximate. '
                  'Verify opening hours, routes and ticket prices independently.' if lang == 'en'
                  else 'خطة استرشادية؛ الأيام البحرية الحرة مقصودة وليست أنشطة مخترعة. لا تتوفر أسعار أو حجوزات أو مواعيد حية، والانتقالات تقريبية؛ تحقق منها قبل الحجز.')
    allocations = {}
    for day in days:
        allocations[day['city']] = allocations.get(day['city'], 0) + 1
    return {'days': days, 'warnings': warnings, 'route': route, 'route_optimized': False,
            'total_travel_minutes': travel_minutes, 'total_places': total_places, 'pace': state['pace'],
            'accessibility_needs': bool(state.get('accessibility_needs', False)),
            'disclaimer': disclaimer, 'sources': sources, 'day_allocation': allocations}


def _with_verified_dialogue(request, message: str, response: dict) -> dict:
    """Let an available LLM *discuss* a validated plan without editing it."""
    if not response.get('itinerary') or not response.get('trip_state'):
        return response
    from .travel_dialogue import narrate_verified_trip
    narrative, mode = narrate_verified_trip(
        message, request.language, response['trip_state'],
        response['itinerary'], request.history
    )
    if narrative:
        return {**response, 'answer': narrative + '\n\n' + response['answer'],
                'mode': mode}
    return response


def consult_travel(request):
    # Egyptian colloquial requests often include shadda: خلّي / بدّل / زوّد.
    # Parse the normalized text but retain the original visitor turn and history
    # for any conversational answer or provider-native chat context.
    message = re.sub(r'[\u064b-\u065f\u0670]', '', request.message)
    effective_language = _reply_language(message, request.language)
    if effective_language != request.language:
        request = request.model_copy(update={'language': effective_language})
    lowered = message.lower()
    available = {p['city'] for p in all_places()}
    state = request.trip_state.model_dump() if request.trip_state else None
    cities = mentioned_cities(message, available)
    # Never silently substitute unsupported destinations with Cairo.
    unsupported = sorted(set(_explicit_non_egypt_destination(message)) |
                         {canonical for alias, canonical in _CITY_ALIASES.items()
                          if canonical not in available and re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', lowered)})
    # A plain tourism question such as 'أريد زيارة الأهرامات' is not a request for a multi-day itinerary.
    two_day_city_stay = bool(not state and len(cities) == 1 and
                             re.search(r'(?<!\w)(?:يومين|يومان)(?!\w)', lowered))
    plan_words = (total_days(message) is not None or two_day_city_stay or bool(_explicit_city_allocations(message, available))
                  or any(x in lowered for x in ('plan', 'itinerary', 'trip', 'holiday', 'برنامج', 'رحلة', 'خطط', 'خطة', 'خطه', 'تخطيط', 'voyage')))
    from .conversation_router import payment_sensitive
    if (payment_sensitive(message) or
        re.search(r'(?:chest pain|medical emergency|can.t breathe|ألم الصدر|الم الصدر|بيهددني|تهددني|unsafe driver|driver threatens)', lowered)):
        from .conversation_router import special_reply
        safety = special_reply(message, request.language, request.history)
        if safety:
            return {**safety, 'itinerary': None, 'trip_state': state}
    # A traveler can ask about a hotel or airport while an itinerary is open.
    # Such questions must NOT be treated as mutations simply because they
    # mention children, a budget, or possessive words like "معايا".
    service_question = bool(re.search(
        r'(?:فنادق|فندق|إقامة|اقامة|مطار|مواصلات|تاكسي|مطعم|مطاعم|'
        r'\bhotels?\b|\bairports?\b|\brestaurants?\b|'
        r'\btransport\b|\btaxi\b|\btransfer\b)', lowered))
    explicit_edit = (any(x in lowered for x in _EDIT if x not in ('معايا', 'budget', 'ميزانيتي'))
                     or bool(state and re.search(r'\b(?:increase|extend)\b[^\n.!?]{0,55}?\d{1,2}\s*days?\b', lowered)))
    edit_words = explicit_edit
    # References to a stay length in a hotel query do not imply a new trip.
    if service_question and not explicit_edit and not re.search(
        r'(?:خطط|برنامج|خطة|خطه|اعمل رحلة|itinerary|plan (?:my|the|a) trip)', lowered):
        plan_words = False
    mode = 'local-planner'
    hint: dict[str, Any] = {}
    provider = os.getenv('AI_PROVIDER', 'auto').strip().lower()
    use_openai = (provider == 'openai' or (provider == 'auto' and not gemini_key())) and bool(openai_key())
    use_gemini = provider in ('auto', 'gemini') and bool(gemini_key())
    if (use_openai or use_gemini) and (state or plan_words):
        try:
            if use_openai:
                hint = _extract_gemini(message, state, available, provider='openai')
                mode = 'openai-intent+local-planner'
            else:
                hint = _extract_gemini(message, state, available)
                mode = 'gemini-intent+local-planner' 
        except Exception:
            # Plan can still be created locally, without consuming further requests.
            mode = 'local-planner'
    action = hint.get('action', '')
    # A follow-up stating only a budget or the new duration is also an edit.
    budget_value, _ = _budget_egp(message)
    budget_usd_value = _budget_usd(message)
    declared_total = bool(re.search(
        r'(?:whole\s+trip|entire\s+trip|total\s+(?:trip\s+)?duration|'
        r'الرحلة\s*(?:كلها|كاملة|بكاملها)?|مدة\s+الرحلة)', lowered))
    family_update = bool(re.search(
        r'(?:with (?:two|2) (?:kids|children)|(?:مع |عندي |معايا )?(?:طفلين|طفلان)|'
        r'عيلة|عائلة|family|kids?|children)', lowered))
    is_edit = bool(state and (edit_words or
                           ((budget_value is not None or budget_usd_value is not None or family_update) and not service_question) or
                           (not service_question and total_days(message) is not None and
                            (declared_total or any(k in lowered for k in
                             ('to ', 'إلى', 'الى', 'خلي', 'خليه', 'make ', 'set '))))))
    do_plan = plan_words or action == 'plan' or is_edit
    # A colloquial mixed day/evening sightseeing edit may lack an explicit
    # total-day number. Discuss a useful example, but never silently change
    # an existing itinerary's total or take a day from another city.
    if state and is_edit:
        from .guide import local_cairo_day_reply
        local_idea = local_cairo_day_reply(message, request.language)
        if local_idea:
            question = (
                'ما عدّلتش رحلتك لسه: تحب نزود يوم على إجمالي الرحلة، '
                'ولا ننقل يوم من مدينة تانية للقاهرة؟'
                if request.language == 'Arabic' else
                'Je n\'ai pas modifié votre voyage. Souhaitez-vous ajouter '
                'un jour au total ou le déplacer depuis une autre ville ?'
                if request.language == 'French' else
                'I have not changed your trip. Should I add a day to the total '
                'or move one from another city?'
            )
            return {
                **local_idea,
                'answer': local_idea['answer'] + '\n\n' + question,
                'mode': 'needs-clarification',
                'trip_state': state,
                'itinerary': None,
            }
    # Nights and sightseeing days are different units. A hotel stay described
    # only in nights must not be silently converted into an equal day count;
    # ask the traveler for the actual itinerary duration first.
    night_only = (bool(re.search(r'\b(?:night|nights|nuit|nuits)\b|(?:ليالٍ|ليالي|ليلة|ليلتين)', lowered))
                  and not bool(re.search(r'\b(?:day|days|jour|jours)\b|(?:يوم|أيام|ايام)', lowered)))
    if do_plan and night_only:
        answer = (
            'ذكرت عدد الليالي فقط. عدد الليالي مش بالضرورة يساوي أيام الزيارة؛ '
            'قولّي إجمالي أيام الرحلة وتوزيع الأيام على المدن عشان ما أغيّرش حجوزاتك بالخطأ.'
            if request.language == 'Arabic' else
            'Vous avez indiqué des nuits, pas le nombre exact de jours de visite. '
            'Précisez les jours et leur répartition avant de planifier.'
            if request.language == 'French' else
            'You specified nights, which do not always equal sightseeing days. '
            'Please confirm your trip days and the city-day allocation before I create or edit the itinerary.'
        )
        return {'answer': answer, 'mode': 'needs-clarification', 'sources': [],
                'trip_state': state, 'itinerary': None}
    if unsupported and do_plan:
        name = ', '.join(unsupported)
        return {'answer': (f'الوجهة {name} مش متاحة حاليًا في مخطط الرحلات الموثق. مش هغيّرها للقاهرة بدون موافقتك. تحب نخطط لوجهة مدعومة أو ننتظر إضافة بياناتها؟'
                           if request.language == 'Arabic' else
                           f'{name} is not yet supported by our verified trip planner. I will not silently substitute Cairo or another city. Would you like to choose a supported destination?'),
                'mode': 'unsupported-destination', 'sources': [], 'trip_state': state, 'itinerary': None}
    # An edit command needs an existing itinerary. In a fresh conversation,
    # "add a day to Cairo" must not turn into a new one-day Cairo trip or a
    # generic catalogue answer about Cairo.
    no_trip_day_edit = bool(not state and re.search(
        r'(?:\b(?:add|increase|extend|move|transfer)\b|زود|زيد|مدد|ضيف|اضف|أضف|انقل)'
        r'[^\n.!؟]{0,75}?(?:\d{1,2}\s*(?:days?|يوم|أيام|ايام)|يوم(?:ين|ان)?(?:\s+واحد)?|one(?:\s+more)?\s+day|two(?:\s+more)?\s+days|an?\s+extra\s+day)',
        lowered, flags=re.I))
    no_trip_city_edit = bool(not state and cities and re.search(
        r'(?<!\w)(?:بدل|استبدل|غير|غيّر|احذف|شيل|replace|swap|switch|remove)\s+',
        lowered, flags=re.I))
    if no_trip_day_edit or no_trip_city_edit:
        return {'answer': (
            'لسه ما عنديش رحلة أعدّلها. قولّي إجمالي أيام الرحلة والمدن اللي عايز تزورها، '
            'وبعد ما أجهزها أقدر أزود أيام مدينة من غير ما أغيّر باقي المدن.'
            if request.language == 'Arabic' else
            'I do not have an itinerary to edit yet. Tell me the total trip length and cities first; '
            'then I can add days to one city without changing the others.'),
                'mode': 'needs-clarification', 'sources': [], 'trip_state': None, 'itinerary': None}
    if not do_plan:
        try:
            result = answer_chat(request)
        except HTTPException as exc:
            if exc.status_code != 502:
                raise
            # The tourist app can still show verified local catalogue snippets
            # when the AI provider is down. Explicitly label the downgrade.
            from .guide import retrieve, offline_answer
            places = retrieve(message)
            sources = [dict(number=i, title=p['name'], title_ar=p['name_ar'],
                            city=p['city'], id=p['id'], url=p['source_url'])
                       for i, p in enumerate(places, 1)]
            warning = ('تعذّر الاتصال بالذكاء الاصطناعي؛ دي معلومات محلية محدودة وليست إجابة مولدة: '
                       if request.language == 'Arabic' else
                       'The AI service is temporarily unavailable. Showing limited local references, not an AI reply: ')
            result = {'answer': warning + offline_answer(places, request.language),
                      'sources': sources, 'mode': 'offline-fallback'}
        if state and result.get('mode') == 'offline-preview' and not result.get('sources'):
            # The catalogue has no match, but the structured itinerary is
            # authoritative context. Acknowledge it rather than asking again
            # for a duration the visitor has already supplied.
            allocation = []
            for phase in state['phases']:
                if len(phase['cities']) == 1:
                    city = phase['cities'][0]
                    name = CITY_AR.get(city, city) if request.language == 'Arabic' else city
                    allocation.append(f"{phase['days']} {name}" if request.language == 'Arabic'
                                      else f"{phase['days']} days {name}")
            if request.language == 'Arabic':
                result['answer'] = (
                    f"رحلتك الحالية {state['days']} أيام"
                    + (f" ({'، '.join(allocation)})" if allocation else '')
                    + ". تحب أساعدك تختار نشاط، أو تعدّل مدينة أو يوم، أو نراجع وتيرة الرحلة؟ "
                      "لو تقصد سؤالًا مختلفًا، وضّحه لي."
                )
            else:
                result['answer'] = (
                    f"Your current trip is {state['days']} days"
                    + (f" ({', '.join(allocation)})" if allocation else '')
                    + ". Would you like to choose an activity, edit a city or day, or review the pace? "
                      "If you meant something else, tell me a little more."
                )
        return {**result, 'itinerary': None, 'trip_state': state}

    if is_edit:
        reallocated = _full_reallocation(state, message, available)
        if reallocated is not None:
            # A full city/day allocation is a new, validated plan; all user-specified
            # durations and city order are preserved rather than phase-edited.
            try:
                checked = TripState.model_validate(reallocated)
                itinerary = _make_plan(checked.model_dump(), 'ar' if request.language == 'Arabic' else 'en')
            except (ValueError, KeyError):
                return {'answer': 'التوزيع المطلوب غير قابل للتنفيذ بهذه القيود.' if request.language == 'Arabic' else 'Those trip constraints are not supported.',
                        'mode': 'needs-clarification', 'sources': [], 'trip_state': state, 'itinerary': None}
            parts = [f"{p.days} — {', '.join(CITY_AR.get(c, c) for c in p.cities)}" if request.language == 'Arabic' else
                     f"{p.days} days — {', '.join(p.cities)}" for p in checked.phases]
            answer = ('عدلت توزيع الرحلة بناءً على الأيام والمدن التي حددتها. التعديل في هذه الجلسة فقط؛ استخدم حفظ الرحلة لتسجيله في حسابك.\n' if request.language == 'Arabic' else
                      'I rebuilt the itinerary using your exact city-day allocation. This is only in your current session until you save it to your account.\n') + '\n'.join(parts)
            if _budget_usd(message) is not None:
                answer += (f'\nسجّلت ميزانيتك: {checked.budget_usd:,} دولار. الخطة استرشادية ولا تؤكد تكلفة الإقامة والنقل.' if request.language == 'Arabic' else
                           f'\nBudget noted: USD {checked.budget_usd:,}. This itinerary does not verify hotel or transfer costs.')
            return _with_verified_dialogue(request, message, {'answer': answer, 'mode': 'local-planner', 'sources': itinerary.get('sources', []),
                    'trip_state': checked.model_dump(), 'itinerary': itinerary})
        extension_amount = _relative_trip_extension(message)
        if extension_amount is not None:
            extension_city = _extension_city_from_context(request, message, state, available)
            extended = _apply_relative_extension(state, extension_amount, extension_city)
            if extended is None:
                answer = (
                    'فهمت إنك تريد زيادة إجمالي مدة الرحلة من غير تقليل أي مدينة. '
                    'حدّد المدينة التي تريد إضافة اليوم لها؛ لم أغيّر الرحلة بعد.'
                    if request.language == 'Arabic' else
                    'I understand that you want to extend the total trip without reducing any city. '
                    'Please name the city that should receive the extra day; the trip is unchanged.'
                )
                return {'answer': answer, 'mode': 'needs-clarification', 'sources': [],
                        'trip_state': state, 'itinerary': None}
            checked = TripState.model_validate(extended)
            itinerary = _make_plan(checked.model_dump(), 'ar' if request.language == 'Arabic' else 'en')
            city_name = CITY_AR.get(extension_city, extension_city) if request.language == 'Arabic' else extension_city
            answer = (
                f'زودت إجمالي مدة الرحلة {extension_amount} يوم إلى {checked.days} أيام، '
                f'وضفت الزيادة إلى {city_name} من غير ما أقلل أيام أي مدينة أخرى.'
                if request.language == 'Arabic' else
                f'I extended the total trip by {extension_amount} day(s) to {checked.days} days and added '
                f'them to {city_name}, without reducing any other city.'
            )
            return _with_verified_dialogue(request, message, {
                'answer': answer, 'mode': 'local-planner', 'sources': itinerary.get('sources', []),
                'trip_state': checked.model_dump(), 'itinerary': itinerary})
        transfer = _explicit_day_transfer(state, message, available)
        # A request to 'add 3 days in Cairo' is NOT a request to set Cairo to
        # 3 days. It also does not say whether to lengthen the whole holiday
        # or transfer 3 days from another city. Do not silently overwrite the
        # destination's existing allocation or move days in the wrong direction.
        # A fully specified city-to-city transfer is handled above.
        ambiguous_city_increase = re.search(
            r'(?:\b(?:add|increase|extend)\b|(?:ن)?زود|زيد|ضيف|أضف|اضف)'
            r'[^\n.!؟]{0,55}?(?:\d{1,2}\s*(?:days?|يوم|أيام|ايام)|'
            r'one\s+more\s+day|another\s+day|extra\s+day|يوم(?:\s+(?:واحد|زيادة|كمان))?)',
            _digits(message).lower(), flags=re.I)
        if transfer is None and ambiguous_city_increase and cities:
            return {
                'answer': (
                    'لم أغيّر توزيع أيام رحلتك. هل تريد زيادة إجمالي مدة الرحلة، '
                    'أم نقل الأيام من مدينة أخرى؟ اذكر المدينة التي سننقل منها الأيام.'
                    if request.language == 'Arabic' else
                    'Your trip is unchanged. Should I extend the whole trip, or transfer days '
                    'from another city? Please specify the source city.'),
                'mode': 'needs-clarification', 'sources': [],
                'trip_state': state, 'itinerary': None,
            }
        # If a visitor assigns a duration to a destination absent from the
        # current trip, do not silently apply that amount to another beach/land
        # phase. Require an explicit transfer or replacement instead.
        current_cities = {city for phase in state['phases'] for city in phase['cities']}
        new_cities = set(cities) - current_cities
        old_city, new_city = _explicit_replacement(message, state, available)
        has_city_duration = (_explicit_phase_days(message, 'beach') is not None or
                             _explicit_phase_days(message, 'culture') is not None)
        if (transfer is None and new_cities and has_city_duration and
                not (old_city and new_city)):
            return {'answer': ('المدينة المذكورة مش موجودة في رحلتك الحالية. مش هغيّر توزيع الأيام '
                               'على مدينة تانية من غير موافقتك. حدّد من أي مدينة ننقل الأيام '
                               'وإلى أي مدينة، أو اطلب إعادة تخطيط الرحلة.'
                               if request.language == 'Arabic' else
                               'The city with the requested days is not in your current itinerary. '
                               'No allocation was changed. Specify which city should lose days '
                               'and which should gain them, or request a new itinerary.'),
                    'mode': 'needs-clarification', 'sources': [],
                    'trip_state': state, 'itinerary': None}
        # Reject an entire mixed request rather than partially applying a budget
        # while silently ignoring an ambiguous destination change, or multiplying
        # an ambiguous "15000 thousand EGP" amount.
        _, ambiguous_budget_edit = _budget_egp(message)
        swap_requested = bool(re.search(
            r'(?:\b(?:replace|swap|switch|substitute)\b|بدل|استبدل|غيّر|غير)\s+', lowered))
        unimplemented_removal = bool(re.search(r'(?:\bremove\b|احذف|شيل)\s+', lowered))
        if ambiguous_budget_edit or (swap_requested and transfer is None and _explicit_replacement(message, state, available) == (None, None)) or (unimplemented_removal and transfer is None):
            clarification = ('الطلب فيه مبلغ غير واضح أو تغيير وجهة محتاج تحديد أدق. لم أعدل أي جزء من رحلتك. '
                             'اذكر المبلغ الصحيح أو قل: بدل الغردقة بشرم الشيخ.'
                             if request.language == 'Arabic' else
                             'Your budget or destination change is ambiguous or unsupported. No part of your trip was changed. '
                             'Specify the exact amount or say: Replace Hurghada with Sharm El Sheikh.')
            return {'answer': clarification, 'mode': 'needs-clarification', 'sources': [],
                    'trip_state': state, 'itinerary': None}
        # Exact city-to-city day transfers have their own deterministic guard.
        updated = transfer if transfer is not None else _apply_edit(state, message, cities, hint, available)
        # Transaction guard: never return a new itinerary if a model or rule
        # silently rewrites unrelated trip fields or crosses phase categories.
        transition_error = None if transfer is not None else _transition_error(state, updated, message, available)
        if transition_error:
            coastal_issue = transition_error == 'destination is incompatible with the beach phase'
            if request.language == 'Arabic':
                explanation = ('وجهة الجزء البحري لازم تكون مناسبة لنوع الرحلة. ' if coastal_issue
                               else 'التعديل هينتج خطة غير متسقة أو هيغيّر بيانات ما طلبتش تغييرها. ')
                answer = explanation + 'مغيرتش أي جزء من رحلتك. وضّح التعديل المطلوب، أو اطلب إعادة تخطيط الجزء ده.'
            else:
                explanation = ('The replacement does not fit the beach segment. ' if coastal_issue
                               else 'The requested edit would make the trip inconsistent or change unrequested fields. ')
                answer = explanation + 'Your original trip was preserved. Please clarify or ask to re-plan that segment.'
            return {'answer': answer, 'mode': 'needs-clarification', 'sources': [],
                    'trip_state': state, 'itinerary': None}
        if updated == state:
            return {'answer': 'لم أتمكن من فهم التعديل. قل مثلاً: بدل الغردقة بشرم الشيخ، أو زود يوم للأقصر.'
                    if request.language == 'Arabic' else
                    'I could not identify a supported change. Try: Replace Hurghada with Sharm El Sheikh, or add one day to Luxor.',
                    'mode': mode, 'sources': [], 'trip_state': state, 'itinerary': None}
    elif state and action != 'plan':
        updated = state
    else:
        days = total_days(message)
        if days is None and two_day_city_stay:
            days = 2
        explicit_city_days = _explicit_city_allocations(message, available)
        # If all cities have an explicit number of days, do not let generic
        # attraction-density scoring rewrite the visitor's allocations.
        if explicit_city_days:
            explicitly_allocated = sum(count for _, count in explicit_city_days)
            declared_total = _declared_overall_duration(message)
            if (len(explicit_city_days) > 5 or explicitly_allocated > 30 or
                    (declared_total is not None and explicitly_allocated != declared_total)):
                return {'answer': ('مجموع أيام المدن لا يساوي مدة الرحلة المذكورة، أو يتجاوز حدود المخطط. رجاءً وضّح توزيع الأيام.'
                          if request.language == 'Arabic' else
                          'The named city-day allocations conflict with the stated total or exceed this planner limit. Please clarify the days.'),
                        'mode': 'needs-clarification', 'sources': [], 'trip_state': state, 'itinerary': None}
            days = explicitly_allocated
        if days is None and isinstance(hint.get('days'), int) and not isinstance(hint.get('days'), bool):
            days = hint['days']
        if not days:
            return {'answer': 'كم يوم ستقضي في مصر؟' if request.language == 'Arabic' else 'How many days will you spend in Egypt?',
                    'mode': mode, 'sources': [], 'trip_state': state, 'itinerary': None}
        if not 1 <= days <= 30:
            return {'answer': 'النسخة الحالية تدعم رحلات من 1 إلى 30 يومًا.' if request.language == 'Arabic' else 'This version supports trips between 1 and 30 days.',
                    'mode': mode, 'sources': [], 'trip_state': state, 'itinerary': None}
        history = wants_history(message) or hint.get('history') is True
        beach = wants_beach(message) or hint.get('beach') is True or any(c in ('Hurghada', 'Sharm El Sheikh', 'Dahab') for c in cities)
        requested = [x for x in (hint.get('city_preferences') or []) if x in available] if isinstance(hint.get('city_preferences'), list) else []
        budget_egp, ambiguous_budget = _budget_egp(message)
        # An open-ended, long Egypt trip should showcase the country, not default
        # to 30 days in Cairo. User-named cities always take precedence; these
        # are clearly described as a provisional suggestion, not a constraint.
        inferred_cities = cities or requested
        suggested_cities = False
        if not inferred_cities and days >= 21 and not (history or beach):
            inferred_cities = [city for city in
                               ('Cairo', 'Giza', 'Alexandria', 'Luxor', 'Aswan', 'Hurghada')
                               if city in available]
            suggested_cities = True
        updated = _standard_state(days, history, beach, inferred_cities, message, budget_egp, explicit_city_days)
        updated['budget_usd'] = _budget_usd(message)

    try:
        validated = TripState.model_validate(updated)
        if sum(p.days for p in validated.phases) != validated.days:
            raise ValueError('Phase durations do not add up')
        for phase in validated.phases:
            if phase.days < len(phase.cities):
                raise ValueError('A city needs at least one day')
            if any(city not in available for city in phase.cities):
                raise ValueError('Unsupported city')
        itinerary = _make_plan(validated.model_dump(), 'ar' if request.language == 'Arabic' else 'en')
    except (ValueError, KeyError) as exc:
        return {'answer': ('تعذّر تحديث الخطة بهذه القيود. حاول ذكر المدن والأيام بوضوح.' if request.language == 'Arabic'
                           else 'I cannot build a feasible plan from these constraints. Please specify destinations and days.'),
                'mode': mode, 'sources': [], 'trip_state': state, 'itinerary': None}

    if request.language == 'Arabic':
        kind_ar = {'history': 'آثار وتاريخ', 'mixed': 'ثقافة واستكشاف', 'beach': 'بحر واسترخاء'}
        def day_count_ar(days):
            return 'يوم واحد' if days == 1 else 'يومين' if days == 2 else f'{days} أيام'
        summaries = [f"{day_count_ar(p['days'])} — {', '.join(CITY_AR.get(c, c) for c in p['cities'])} ({kind_ar.get(p['kind'], p['kind'])})" for p in validated.model_dump()['phases']]
        intro = 'تم تجهيز البرنامج السياحي لهذه الجلسة. لم يُحفظ في حسابك بعد؛ استخدم زر حفظ الرحلة أو اطلب حفظها بعد تسجيل الدخول.'
        disclaimer = '\nلا توجد حجوزات أو أسعار مؤكدة.'
    elif request.language == 'French':
        kind_fr = {'history': 'histoire', 'mixed': 'culture et découverte', 'beach': 'mer et détente'}
        summaries = [f"{p['days']} jours — {', '.join(p['cities'])} ({kind_fr.get(p['kind'], p['kind'])})" for p in validated.model_dump()['phases']]
        intro = ("Votre itinéraire modifiable est prêt pour cette session. "
                 "Il n'a pas été enregistré dans votre compte ; connectez-vous pour le sauvegarder. "
                 "Les noms et descriptions des étapes restent en anglais dans cette version.")
        disclaimer = '\nAucun tarif, horaire ou réservation en temps réel n’est confirmé.'
    else:
        summaries = [f"{p['days']} days: {', '.join(p['cities'])} ({p['kind']})" for p in validated.model_dump()['phases']]
        intro = 'Your editable itinerary is ready below. I used curated catalogue stops and approximate transfer allowances.'
        disclaimer = '\nNo live prices or bookings are included.'
    answer = intro + '\n' + '\n'.join(summaries) + disclaimer
    # Make the simplifying calendar assumption visible before a visitor books.
    # A month without precise travel dates is NOT a confirmed calendar duration.
    month_mentioned = bool(re.search(
        r'(?<!\w)(?:(?:one|a)\s+month|(?:un|une)\s+mois|'
        r'شهر(?:\s+واحد|\s+كامل)?|\d{1,2}\s*(?:months?|أشهر|اشهر|شهور))(?!\w)',
        _digits(message)))
    explicit_days = bool(re.search(r'\d{1,3}\s*(?:days?|jours?|يوم|أيام|ايام)', _digits(message)))
    if not state and month_mentioned and not explicit_days:
        answer += ('\nاعتبرت «شهر» 30 يومًا للتخطيط المبدئي فقط؛ عدد الأيام الفعلي يتحدد بتاريخ الوصول والمغادرة.'
                   if request.language == 'Arabic' else
                   '\nPour ce brouillon, « un mois » correspond à 30 jours ; confirmez les dates d’arrivée et de départ.'
                   if request.language == 'French' else
                   '\nFor this draft, I assumed a month means 30 days. Confirm arrival and departure dates for the exact calendar duration.')
    if validated.accessibility_needs:
        answer += ('\nتنبيه مهم: المعالم والانتقالات في الخطة ليست معتمدة كأماكن مناسبة للكراسي المتحركة. يجب تأكيد الوصول مع كل جهة قبل الحجز.' if request.language == 'Arabic' else
                   '\nImportant : accessibilité en fauteuil roulant non vérifiée pour les visites et transports ; confirmez avec chaque opérateur avant toute réservation.' if request.language == 'French' else
                   '\nImportant: wheelchair access is NOT verified for any stops or transport. Confirm with each operator before booking.')
    if 'suggested_cities' in locals() and suggested_cities:
        answer += ('\nلأنك لم تحدد مدنًا، اقترحت مسارًا متنوعًا لزيارة مصر؛ يمكنك تغيير المدن أو عدد الأيام.'
                   if request.language == 'Arabic' else
                   '\nYou did not specify destinations, so these cities are a provisional Egypt-wide suggestion that you can change.')
    flexible_days = sum(1 for day in itinerary['days'] if not day['stops'])
    if flexible_days:
        answer += (f'\nتنبيه: {flexible_days} يوم بدون زيارات محددة من كتالوجنا؛ أضفت أفكارًا اختيارية غير محجوزة. '
                   'دي مسودة قابلة للتطوير وليست برنامجًا يوميًا مكتمل التحقق.' if request.language == 'Arabic' else
                   f'\nAttention : {flexible_days} jours sans visite vérifiée dans notre catalogue. '
                   'Ce programme reste un brouillon, sans réservation.' if request.language == 'French' else
                   f'\nNote: {flexible_days} days have no curated attraction stops; optional, unbooked ideas are shown. '
                   'This is a draft, not a fully verified daily itinerary.')
    if validated.budget_usd:
        answer += (f'\nسجّلت الميزانية التي ذكرتها: {validated.budget_usd:,} دولار. لا يمكن تأكيد أن الخطة داخل ميزانيتك دون عروض إقامة وانتقالات وأسعار حديثة.'
                   if request.language == 'Arabic' else
                   f'\nNoted budget: USD {validated.budget_usd:,}. This is not a live cost estimate; confirm actual accommodation and transport prices before relying on it.')
    if validated.budget_egp:
        answer += (f'\nسجلت ميزانيتك: {validated.budget_egp:,} جنيه مصري، لكن لا يمكنني التأكد أن الرحلة تناسب الميزانية دون أسعار إقامة وتنقلات حقيقية وعدد المسافرين. هل الميزانية تشمل الإقامة؟' if request.language == 'Arabic'
                   else f'\nNoted EGP {validated.budget_egp:,} budget. This is NOT a cost-verified plan; does the budget include accommodation and transport?')
    if not state and 'ambiguous_budget' in locals() and ambiguous_budget:
        answer += ('\nتوضيح مهم: ذكرت مبلغًا متبوعًا بكلمة «ألف»؛ هل الرقم بالجنيه بالفعل، أم تريد ضربه في ألف؟' if request.language == 'Arabic'
                   else '\nPlease clarify whether the stated figure is in EGP or thousands of EGP.')
    references = [{**ref, 'number': i} for i, ref in enumerate(itinerary['sources'], 1)]
    return _with_verified_dialogue(request, message, {'answer': answer, 'mode': mode, 'sources': references, 'trip_state': validated.model_dump(), 'itinerary': itinerary})
