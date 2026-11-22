"""Conservative, explicit profile extraction; never infer ages from trip days."""
import re
from .schemas import TravelerProfile


def update_profile(profile, message):
    profile = TravelerProfile.model_validate(profile or {}).model_dump()
    text = message.lower().translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))
    words = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'اثنين': 2, 'اتنين': 2, 'ثلاثة': 3}
    adults = re.search(r'(?<!\w)(\d{1,2}|one|two|three|four|اثنين|اتنين|ثلاثة)\s*(?:adults?|adultes?|بالغين|بالغ|كبار)(?!\w)', text)
    if adults:
        count = int(adults[1]) if adults[1].isdigit() else words[adults[1]]
        if 1 <= count <= 20:
            profile['adults'] = count
    # A bounded list after an explicit age label. It stops at prose, preventing
    # numbers in "aged 4 and 7, budget 2000" from becoming extra children.
    ages = re.search(r'(?:children(?:\s+are)?\s+aged?|kids(?:\s+are)?\s+aged?|ages|أعمار(?:هم| الأطفال)?|اعمار(?:هم| الاطفال)?|عمرهم|سنهم)\s*[:=]?\s*'
                     r'(\d{1,2}(?:(?:\s*(?:,|،|and|و|et)\s*|\s+)\d{1,2}){0,11})(?!\d)', text)
    if ages:
        values = [int(value) for value in re.findall(r'\d+', ages[1])]
        if values and all(0 <= age <= 17 for age in values):
            profile['children_ages'] = values
    for pattern, preference in [(r'\bvegetarian\b|نباتي', 'vegetarian'), (r'\bvegan\b|نباتي صرف', 'vegan'),
                                (r'\bhalal\b|حلال', 'halal')]:
        if re.search(pattern, text) and preference not in profile['food_preferences']:
            # Avoid recording a clearly negated preference.
            if not re.search(r'(?:not|no|مش|غير|بدون)\s+(?:a\s+)?(?:' + pattern + ')', text):
                profile['food_preferences'].append(preference)
    return TravelerProfile.model_validate(profile).model_dump()
