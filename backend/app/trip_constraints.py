"""Small, explicit visitor constraints; no inferred bookings or opening hours."""
import re


def normalize(text):
    return re.sub(r'[\u064b-\u065f\u0670]', '', text.lower()).translate(
        str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))


def required_places(message):
    text = normalize(message)
    result = []
    for pattern, slug in [(r'\bpyramids?\b|الأهرامات|الاهرامات|الاهرام|الأهرام', 'giza-pyramids'),
                          (r'grand egyptian museum|المتحف المصري الكبير', 'grand-egyptian-museum')]:
        for match in re.finditer(pattern, text):
            prefix = text[max(0, match.start() - 35):match.start()]
            if not re.search(r'(?:\bno\b|\bnot\b|\bwithout\b|\bskip\b|بدون|مش|بلاش)[\w\s]{0,22}$', prefix):
                result.append(slug)
                break
    return result


def swimming_days(message):
    text = normalize(message)
    if re.search(r'\bpools?\b|مسبح|حمام سباحة', text) and not re.search(r'\bbeach|\bsea\b|بحر|شاطئ', text):
        return 0
    if re.search(r'\b(?:no|not|without)\s+(?:any\s+)?swim|بدون\s+سباحة|مش\s+عايز\s+سباحة', text):
        return 0
    numbers = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7}
    count = r'(\d{1,2}|one|two|three|four|five|six|seven)'
    patterns = [count + r'\s+(?:(?:relaxed|quiet|full|actual)\s+){0,2}swimming\s+days?',
                count + r'\s+days?\s+(?:of\s+|for\s+)?swimming',
                r'(\d{1,2})\s*(?:أيام|ايام|يوم)\s*(?:لل)?سباحة']
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = int(match[1]) if match[1].isdigit() else numbers[match[1]]
            return value if 1 <= value <= 30 else 0
    return 2 if re.search(r'يومين\s*(?:لل)?سباحة', text) else 0


def late_arrival(message):
    text = normalize(message)
    arrival = re.search(r'\barriv(?:e|es|ing|al)\b|بوصل|هوصل|اوصل|أوصل|وصول', text)
    if not arrival:
        return False
    if re.search(r"(?:\bnot\b|\bdon't\b|\bwon't\b|مش|لن)[\w\s]{0,12}$", text[max(0, arrival.start()-20):arrival.start()]):
        return False
    fragment = text[arrival.end():arrival.end() + 65]
    match = next((m for m in re.finditer(r'(?<!\d)(\d{1,2})(?::(\d{2}))?\s*(p\.?m\.?|a\.?m\.?|مساء|بالليل|صباح)?', fragment)
                  if m[2] is not None or m[3] is not None), None)
    if not match:
        return bool(re.search(r'\b(?:late evening|at night)\b|مساء|بالليل', fragment))
    hour = int(match[1]); suffix = match[3] or ''
    if (match[2] and int(match[2]) > 59) or hour > 23 or (suffix and hour > 12):
        return False
    if suffix.startswith('p') or suffix in ('مساء', 'بالليل'):
        hour = hour % 12 + 12
    elif suffix.startswith('a') or suffix == 'صباح':
        hour %= 12
    elif not match[2]:
        return False  # "at 8" needs AM/PM; never guess.
    return 18 <= hour <= 23


def rest_only(message):
    text = normalize(message)
    return bool(re.search(r'\b(?:rest only|arrival and rest|no (?:visits|activities|sightseeing))\b|'
                          r'راحة\s*(?:فقط|بس)|وصول\s*و\s*راحة|بدون\s*(?:زيارات|أنشطة|انشطة)', text))
