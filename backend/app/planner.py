"""Deterministic content-based itinerary builder (not a trained ML model).

* One city per day; each destination gets a contiguous block of days.
* Stops are picked by explicit scoring (interest tags, heritage bonus, family fit) with a
  distance-aware tie-break inside the day.
* Travel between cities is an ESTIMATE derived from straight-line distance between city
  centres (road = distance x 1.3 at 65 km/h; a 4 h door-to-door flight is assumed only
  between cities with major airports when the road trip would exceed 6 h). It is deducted from
  the first day in a new city. Live traffic, schedules, opening hours, prices and availability
  are NOT modelled.
"""
from itertools import permutations
from math import atan2, cos, radians, sin, sqrt

from .catalog_extra import CITY_AR
from .database import all_places

PACE_LIMITS = {"relaxed": 240, "balanced": 360, "packed": 450}

ROAD_FACTOR = 1.3
ROAD_SPEED_KMH = 65
MIN_TRANSFER_MIN = 45
FLIGHT_MIN = 240
FLIGHT_ROAD_THRESHOLD_MIN = 360
LONG_TRANSFER_WARN_MIN = 300
AIRPORT_CITIES = {"Cairo", "Giza", "Luxor", "Aswan", "Hurghada", "Sharm El Sheikh"}


def distance_km(a, b):
    dlat = radians(b["lat"] - a["lat"])
    dlon = radians(b["lng"] - a["lng"])
    lat1, lat2 = radians(a["lat"]), radians(b["lat"])
    n = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    return 6371 * 2 * atan2(sqrt(n), sqrt(max(0, 1-n)))


def score(place, interests, family=False):
    matched = len(set(place["tags"]) & set(interests))
    base = matched * 7 + (2 if place["category"] == "Heritage" else 0)
    if family and place["family_friendly"]: base += 5
    if family and not place["family_friendly"]: base -= 14
    return base


def city_centres(places):
    groups = {}
    for p in places:
        groups.setdefault(p["city"], []).append(p)
    return {c: {"lat": sum(p["lat"] for p in ps) / len(ps), "lng": sum(p["lng"] for p in ps) / len(ps)}
            for c, ps in groups.items()}


def estimate_transfer(a, b, centres):
    """Rough minutes to move from city `a` to city `b`: returns {minutes, mode, road_km}."""
    road_km = distance_km(centres[a], centres[b]) * ROAD_FACTOR
    road_min = road_km / ROAD_SPEED_KMH * 60
    if road_min > FLIGHT_ROAD_THRESHOLD_MIN and a in AIRPORT_CITIES and b in AIRPORT_CITIES:
        return {"minutes": FLIGHT_MIN, "mode": "flight (assumed)", "road_km": round(road_km)}
    minutes = max(MIN_TRANSFER_MIN, int(round(road_min / 5.0)) * 5)
    return {"minutes": minutes, "mode": "road", "road_km": round(road_km)}


def optimise_order(cities, centres):
    """Keep the first city as the start and pick the order with the least total transfer time."""
    if len(cities) <= 2:
        return list(cities)
    first, rest = cities[0], cities[1:]
    best, best_cost = None, None
    for perm in permutations(rest):
        order = [first, *perm]
        cost = sum(estimate_transfer(x, y, centres)["minutes"] for x, y in zip(order, order[1:], strict=False))
        if best_cost is None or cost < best_cost:
            best, best_cost = order, cost
    return best


MESSAGES = {
    "en": {
        "empty_note": "No additional unique stops fit this day; use it as a flexible/free day or add destinations.",
        "travel_note": "Mostly a travel day: about {d} to reach {city}, leaving little time for sightseeing.",
        "long_transfer": "Day {day}: about {d} to get from {a} to {b} ({mode}). Consider an earlier start, a flight or overnight transport.",
        "empty_days": "{n} of {total} days have no unique stops left in the catalogue (day {days}). Reduce the trip length or add more destinations.",
        "disclaimer": ("Illustrative itinerary only. Visit durations and 30-minute between-stop buffers are "
                       "planning allowances, not travel-time predictions. Travel between cities is a rough estimate "
                       "from straight-line distance (it ignores traffic, schedules and border/security checks) and "
                       "arrival on day 1 is not modelled. Verify official opening hours, ticket fees, transport, "
                       "reservations and closures separately. Budget is recorded but NOT used for cost estimates."),
        "popular": "popular heritage / local highlight", "matches": "Matches: {list}",
        "road": "road", "flight": "flight (assumed)", "h": "h", "m": "m",
    },
    "ar": {
        "empty_note": "لا توجد محطات فريدة إضافية تناسب هذا اليوم؛ استخدمه كيوم حر أو أضف وجهات.",
        "travel_note": "يوم سفر في الغالب: حوالي {d} للوصول إلى {city}، ولا يتبقى وقت كبير للزيارات.",
        "long_transfer": "اليوم {day}: حوالي {d} للانتقال من {a} إلى {b} ({mode}). فكّر في البدء مبكراً أو الطيران أو السفر الليلي.",
        "empty_days": "{n} من {total} أيام بلا محطات فريدة متبقية في الكتالوج (اليوم {days}). قلّل مدة الرحلة أو أضف وجهات.",
        "disclaimer": ("جدول استرشادي فقط. مدد الزيارة وفواصل الـ 30 دقيقة بين المحطات مخصصات تخطيط وليست توقعات "
                       "لزمن التنقل. السفر بين المدن تقدير تقريبي مبني على المسافة المباشرة (يتجاهل الزحام والمواعيد "
                       "والتفتيش) ولا يشمل يوم الوصول الأول. تحقق بشكل مستقل من مواعيد الفتح والتذاكر والمواصلات "
                       "والحجوزات وحالات الإغلاق. الميزانية تُسجَّل فقط ولا تُستخدم في أي تقدير للتكلفة."),
        "popular": "من أبرز المعالم التراثية والمحلية", "matches": "يطابق: {list}",
        "road": "بالطريق", "flight": "بالطيران (افتراضي)", "h": "س", "m": "د",
    },
}


def _human(minutes, lang="en"):
    u = MESSAGES[lang]
    h, m = divmod(int(minutes), 60)
    return f"{h}{u['h']} {m:02d}{u['m']}" if h and m else (f"{h}{u['h']}" if h else f"{m}{u['m']}")


# Editorial inspiration for days that exceed the finite attractions catalogue. These
# are NOT booked stops, live availability, guaranteed events or priced experiences.
# A 20-day trip must not show 16 visually empty days just because catalogued
# unique monuments were exhausted. The distinction stays explicit to travellers.
LOCAL_DAY_IDEAS = {
    'Cairo': [('Walk through a local neighbourhood at your own pace', 'جولة مشي هادئة في أحد أحياء القاهرة'),
              ('Try Egyptian breakfast and explore local food culture', 'تجربة إفطار مصري والتعرف على ثقافة الأكل'),
              ('Browse independent crafts, markets and small shops', 'جولة في الأسواق والحرف والمحلات المحلية'),
              ('Visit a local art space after checking opening times', 'استكشاف مساحة فنية محلية بعد التحقق من مواعيدها'),
              ('Spend time along the Nile at a suitable public viewpoint', 'قضاء وقت قرب النيل في مكان عام مناسب'),
              ('Take a slower café and photography day', 'يوم هادئ للمقاهي والتصوير'),
              ('Explore a different food district and favourite local dishes', 'زيارة منطقة جديدة لتجربة الأطباق المحلية'),
              ('Have a flexible day for extra museum time or rest', 'يوم مرن لاستكمال زيارة متحف أو الاستراحة')],
    'Giza': [('Enjoy a relaxed day exploring the broader Giza area', 'يوم هادئ لاستكشاف الجيزة'),
             ('Explore traditional local dining options', 'تجربة أكلات محلية تقليدية'),
             ('Take a flexible photography day with breaks', 'يوم مرن للتصوير والاستراحة')],
    'Hurghada': [('Relax on an accessible beach or hotel facility', 'استرخاء على شاطئ متاح أو مرافق الإقامة'),
                ('Compare licensed snorkelling operators for an optional outing', 'الاستفسار عن رحلات السنوركلينج لدى جهات مرخصة'),
                ('Enjoy a low-key waterfront walk and local food', 'جولة هادئة على الواجهة البحرية وتجربة الطعام المحلي'),
                ('Make a flexible pool, beach or rest day', 'يوم مرن للمسبح أو البحر أو الاستراحة'),
                ('Explore responsible Red Sea marine-life experiences', 'التعرف على التجارب البحرية المسؤولة في البحر الأحمر'),
                ('Browse markets and cafes around your accommodation', 'استكشاف الأسواق والمقاهي بالقرب من الإقامة'),
                ('Reserve time for a weather-dependent optional excursion', 'تخصيص وقت اختياري لنشاط يعتمد على حالة الطقس')],
    'Sharm El Sheikh': [('Enjoy a relaxed beach day', 'يوم استرخاء على الشاطئ'),
                       ('Research licensed snorkelling activities', 'البحث عن أنشطة سنوركلينج لدى جهات مرخصة'),
                       ('Explore waterfront dining at your own pace', 'استكشاف مطاعم الواجهة البحرية'),
                       ('Take a rest and photography day', 'يوم استراحة وتصوير')],
    'Luxor': [('Take a slow Nile-side walk at a suitable public area', 'نزهة هادئة بالقرب من النيل في مكان مناسب'),
              ('Try local Upper Egyptian cuisine', 'تجربة الأكل الصعيدي المحلي'),
              ('Reserve a flexible day for historical sites or rest', 'يوم مرن للآثار أو الاستراحة')],
    'Aswan': [('Enjoy the Nile scenery from a suitable public viewpoint', 'استمتع بمشهد النيل من نقطة مناسبة'),
              ('Explore Nubian-inspired crafts with respect for local communities', 'استكشاف الحرف النوبية باحترام المجتمع المحلي'),
              ('Plan a low-key food and rest day', 'يوم هادئ للأكل والاستراحة')],
    'Alexandria': [('Enjoy a promenade walk when weather permits', 'جولة على الكورنيش حسب حالة الطقس'),
                  ('Sample local seafood cuisine', 'تجربة المأكولات البحرية المحلية'),
                  ('Spend a flexible café and sea-view day', 'يوم مرن للمقاهي ومشاهدة البحر')],
}

def day_ideas(city: str, day: int, language='en') -> list[str]:
    ideas = LOCAL_DAY_IDEAS.get(city, [
        ('Explore local neighbourhoods and cuisine at an easy pace', 'استكشاف الأحياء والطعام المحلي بهدوء'),
        ('Keep an open day for rest or independent discovery', 'يوم مفتوح للراحة أو الاستكشاف الذاتي'),
        ('Research a locally operated activity before arranging it', 'البحث عن نشاط محلي قبل الحجز')])
    # One idea per day, not repeated attraction entries; long visits still need
    # editorial expansion or independently arranged activities.
    item = ideas[(day - 1) % len(ideas)]
    return [item[1] if language == 'ar' else item[0]]


def build_plan(request):
    places = all_places()
    cities = {p["city"] for p in places}
    unknown = [name for name in request.cities if name not in cities]
    if unknown:
        raise ValueError("Unknown city: " + ", ".join(unknown))
    if request.days < len(request.cities):
        raise ValueError("Number of days must be at least the number of selected destinations")

    lang = getattr(request, "language", "en")
    msg = MESSAGES[lang]
    cname = (lambda c: CITY_AR.get(c, c)) if lang == "ar" else (lambda c: c)
    centres = city_centres(places)
    ordered = optimise_order(request.cities, centres) if getattr(request, "optimize_route", False) else list(request.cities)

    max_minutes = PACE_LIMITS[request.pace]
    # Give each named city at least two days on a long enough multi-city stay;
    # one day in a major city can be consumed by the transfer alone. Keep days
    # contiguous so the itinerary does not bounce back and forth between cities.
    # Extra days are assigned to destinations with the greatest remaining activity
    # capacity, using only local catalog estimates (not live transport data).
    minimum = 2 if len(ordered) > 1 and request.days >= 3 * len(ordered) else 1
    allocations = {city: minimum for city in ordered}
    places_by_city = {
        city: [p for p in places if p["city"] == city
               and (not request.family or p["family_friendly"])]
        for city in ordered
    }
    for _ in range(request.days - minimum * len(ordered)):
        def opportunity(city):
            planned_minutes = sum(p["visit_minutes"] + 30 for p in places_by_city[city])
            capacity_days = planned_minutes / max_minutes
            return (capacity_days - allocations[city], planned_minutes, -ordered.index(city))
        best_city = max(ordered, key=opportunity)
        allocations[best_city] += 1

    scheduled_cities = [city for city in ordered for _ in range(allocations[city])]
    # Spread curated visits across the available days instead of exhausting a city
    # on its first morning. Long stays favour a focused attraction per day;
    # shorter stays can fit several. This preserves uniqueness and honest free days.
    remaining_city_days = allocations.copy()
    used = set()
    itinerary = []
    warnings = []
    total_travel = 0
    prev_city = None
    for day, city in enumerate(scheduled_cities, 1):
        travel = None
        if prev_city is not None and prev_city != city:
            travel = {"from_city": prev_city, **estimate_transfer(prev_city, city, centres)}
            total_travel += travel["minutes"]
            if travel["minutes"] >= LONG_TRANSFER_WARN_MIN:
                mode_txt = msg["flight"] if travel["mode"].startswith("flight") else msg["road"]
                warnings.append(msg["long_transfer"].format(
                    day=day, d=_human(travel["minutes"], lang), a=cname(prev_city), b=cname(city), mode=mode_txt))
        prev_city = city
        # Family days need an explicit pause and transfer days should not
        # promise sightseeing after several hours in transit.
        rest_allowance = 45 if request.family else 0
        day_budget = max(0, max_minutes - (travel["minutes"] if travel else 0) - rest_allowance)
        if request.family and travel and travel['minutes'] >= 180:
            day_budget = 0
        pool = [p for p in places if p["city"] == city and p["id"] not in used
                and (not request.family or p["family_friendly"])]
        had_candidates = bool(pool)
        city_days_left = remaining_city_days[city]
        remaining_city_days[city] -= 1
        # At most 3 stops in a day; if a city has as many attractions as days,
        # use one anchor per day to avoid exhausting the catalog prematurely.
        daily_stop_limit = min(3, max(1, (len(pool) + city_days_left - 1) // city_days_left))
        if request.family:
            daily_stop_limit = min(daily_stop_limit, 2)
        # If all spots in a city were exhausted, keep the day empty, not fake repeated plans.
        stops = []
        elapsed = 0
        prev = None
        while pool and len(stops) < daily_stop_limit:
            choices = []
            for p in pool:
                buffer = 0 if not stops else 30  # scheduling allowance, NOT predicted transit time
                cost = p["visit_minutes"] + buffer
                if elapsed + cost > day_budget: continue
                distance_penalty = min(distance_km(prev,p)/12, 4) if prev else 0
                choices.append((score(p, request.interests, request.family)-distance_penalty,p))
            if not choices: break
            choices.sort(key=lambda pair: (-pair[0], pair[1]["name"]))
            chosen = choices[0][1]
            if stops: elapsed += 30
            elapsed += chosen["visit_minutes"]
            matched = sorted(set(chosen["tags"]) & set(request.interests))
            stops.append({"place": chosen, "suggested_visit_minutes": chosen["visit_minutes"], "matched": matched,
                          "why": msg["matches"].format(list=", ".join(matched) or msg["popular"])})
            used.add(chosen["id"])
            pool.remove(chosen)
            prev = chosen
        note = None
        if not stops:
            if travel and had_candidates:
                note = msg["travel_note"].format(d=_human(travel["minutes"], lang), city=cname(city))
            else:
                note = msg["empty_note"]
        itinerary.append({"day": day, "city": city, "stops": stops,
                          "activity_ideas": day_ideas(city, day, lang) if not stops else [],
                          "estimated_activity_minutes": elapsed,
                          "rest_minutes": rest_allowance if stops else 0,
                          "estimated_travel_minutes": travel["minutes"] if travel else 0,
                          "travel": travel, "note": note})

    empty_days = [d["day"] for d in itinerary if not d["stops"] and not d["travel"]]
    if empty_days:
        warnings.append(msg["empty_days"].format(n=len(empty_days), total=request.days,
                                                 days=", ".join(map(str, empty_days))))

    return {"days": itinerary, "warnings": warnings,
            "route": ordered, "route_optimized": ordered != list(request.cities),
            "total_travel_minutes": total_travel,
            "day_allocation": allocations,
            "total_places": sum(len(x["stops"]) for x in itinerary),
            "pace": request.pace, "budget_usd": request.budget_usd,
            "disclaimer": msg["disclaimer"],
            "note": "Activity ideas are optional, unbooked editorial suggestions, not verified reservations."}
