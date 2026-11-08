"""Beach suggestions from the same editorial data shown in the React UI."""

import json
import re
from pathlib import Path


_DATA_FILE = Path(__file__).resolve().parents[2] / 'frontend' / 'src' / 'coastalDestinations.json'
DESTINATIONS = json.loads(_DATA_FILE.read_text(encoding='utf-8'))

_EXTRA_ALIASES = {
    'sharm-el-sheikh': ('خليج نعمة', 'خليج القرش', 'naama bay', "shark's bay"),
    'north-coast-alamein': ('الساحل الشمالي', 'الساحل', 'العلمين', 'north coast', 'alamein'),
    'marsa-matruh': ('marsa matrouh', 'matrouh'),
    'marsa-alam': ('marsa alam', 'شرم اللولي', 'sharm el luli'),
    'ain-sokhna': ('السخنه', 'sokhna'),
}
_BEACH_INTENT = re.compile(
    r'شاطي|شواطي|بحر|سباح|اسبح|اعوم|عوم|نزول الميه|نزول المياه|'
    r'\b(?:beach(?:es)?|sea|swim(?:ming)?)\b|\b(?:plage|plages|mer)\b'
)
_CURRENT_INFO = re.compile(
    r'النهارده|النهاردة|اليوم|بكره|بكرة|دلوقتي|مفتوح|مواعيد|سعر|بكام|'
    r'حاله البحر|حالة البحر|امن|امان|\b(?:today|tomorrow|now|open|hours|price|safe|weather)\b'
)
_BROAD_RECOMMEND = re.compile(
    r'تنصحني|ترشح|رشح|اقترح|افضل|احسن|فين اروح|عايز|اريد|حابب|'
    r'\b(?:recommend|suggest|best|want|looking for|where should i go)\b|conseille|recommande'
)


def _mentions(query: str, phrase: str, fold) -> bool:
    phrase = fold(phrase)
    if re.search(r'[a-z]', phrase):
        return bool(re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', query))
    return phrase in query


def _place(destination: dict) -> dict:
    """Use the established RAG place shape so citations and fallback stay intact."""
    return {
        'id': 'coast:' + destination['id'],
        'name': destination['spotEn'],
        'name_ar': destination['spotAr'],
        'city': destination['en'],
        'category': 'Beach',
        'tags': ['beaches'],
        'description': f"A swimming-area suggestion for {destination['en']}. {destination['noteEn']}",
        'summary_ar': f"مثال لمنطقة سباحة في {destination['ar']}. {destination['noteAr']}",
        'details': f"Area: {destination['regionEn']}. Access and sea conditions are not live verified.",
        'tip': destination['noteEn'],
        'source_url': destination['url'],
    }


def recommendations(message: str, fold) -> list[dict]:
    """Return beach examples, never a dive site or a live access guarantee."""
    query = fold(message)
    if not _BEACH_INTENT.search(query) or _CURRENT_INFO.search(query):
        return []
    for destination in DESTINATIONS:
        aliases = (destination['en'], destination['ar'], destination['spotEn'],
                   destination['spotAr'], *_EXTRA_ALIASES.get(destination['id'], ()))
        if any(_mentions(query, alias, fold) for alias in aliases):
            return [_place(destination)]
    if not _BROAD_RECOMMEND.search(query):
        return []
    preferred = ('nuweiba', 'dahab', 'marsa-alam') if re.search(r'هادي|هادئ|هدوء|quiet|calm', query) else (
        'sharm-el-sheikh', 'marsa-alam', 'alexandria')
    by_id = {destination['id']: destination for destination in DESTINATIONS}
    return [_place(by_id[slug]) for slug in preferred]
