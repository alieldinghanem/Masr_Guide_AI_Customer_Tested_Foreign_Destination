"""Editorial discovery content for the first TravelTech product slice.

Deliberately no real-time prices, affiliate claims or bookable inventory here.
Destination counts and highlights are derived from the existing curated catalog.
"""
from .database import all_places

DESTINATION_EDITORIAL = (
    {'city':'Cairo','slug':'cairo','name_ar':'القاهرة','tag':'The living capital','tag_ar':'مدينة الحكايات', 'lead':'Historic neighbourhoods, remarkable museums and unforgettable city life.', 'lead_ar':'أحياء تاريخية ومتاحف مميزة وحياة مدينة لا تتوقف.','mood':'heritage'},
    {'city':'Giza','slug':'giza','name_ar':'الجيزة','tag':'Ancient wonders','tag_ar':'عجائب الحضارة','lead':'Explore the great monuments of Egypt’s ancient world.','lead_ar':'اكتشف آثار مصر القديمة ومعالمها الاستثنائية.','mood':'heritage'},
    {'city':'Luxor','slug':'luxor','name_ar':'الأقصر','tag':'Open-air history','tag_ar':'التاريخ في كل مكان','lead':'Temples, tombs and layers of ancient stories along the Nile.','lead_ar':'معابد ومقابر وقصص الحضارة على ضفاف النيل.','mood':'heritage'},
    {'city':'Aswan','slug':'aswan','name_ar':'أسوان','tag':'Nile & Nubian culture','tag_ar':'النيل والثقافة النوبية','lead':'A slower pace, island scenery and beautiful Nubian heritage.','lead_ar':'هدوء النيل وجمال الجزر وتفاصيل الثقافة النوبية.','mood':'nature'},
    {'city':'Alexandria','slug':'alexandria','name_ar':'الإسكندرية','tag':'Mediterranean soul','tag_ar':'روح البحر المتوسط','lead':'Coastal promenades, historical layers and distinctive local culture.','lead_ar':'كورنيش البحر وتاريخ متنوع وثقافة سكندرية مميزة.','mood':'coast'},
    {'city':'Hurghada','slug':'hurghada','name_ar':'الغردقة','tag':'The Red Sea','tag_ar':'البحر الأحمر','lead':'A base for beach days and Red Sea activities.','lead_ar':'وجهة للاستمتاع بالشواطئ وأنشطة البحر الأحمر.','mood':'coast'},
    {'city':'Sharm El Sheikh','slug':'sharm-el-sheikh','name_ar':'شرم الشيخ','tag':'Sea & escape','tag_ar':'بحر واسترخاء','lead':'Explore the Sinai coast and its varied marine experiences.','lead_ar':'استكشف ساحل سيناء وتجارب البحر المتنوعة.','mood':'coast'},
    {'city':'Dahab','slug':'dahab','name_ar':'دهب','tag':'Slow travel','tag_ar':'رحلة على مهلك','lead':'Coastal calm, outdoor pursuits and a distinctive Sinai atmosphere.','lead_ar':'هدوء البحر والأنشطة الخارجية وأجواء سيناء الخاصة.','mood':'coast'},
    {'city':'Siwa','slug':'siwa','name_ar':'سيوة','tag':'Oasis & adventure','tag_ar':'الواحات والمغامرة','lead':'An oasis escape with unique landscapes and cultural heritage.','lead_ar':'تجربة الواحات والمناظر الطبيعية والتراث المحلي.','mood':'desert'},
    {'city':'Fayoum','slug':'fayoum','name_ar':'الفيوم','tag':'Nature nearby','tag_ar':'طبيعة ومغامرة','lead':'Lakes, desert landscapes and nature-focused getaways.','lead_ar':'بحيرات وصحراء ورحلات وسط الطبيعة.','mood':'desert'},
    {'city':'Abu Simbel','slug':'abu-simbel','name_ar':'أبو سمبل','tag':'Monumental heritage','tag_ar':'عظمة الحضارة','lead':'Extraordinary temples in southern Egypt.','lead_ar':'معابد استثنائية في جنوب مصر.','mood':'heritage'},
    {'city':'Saint Catherine','slug':'saint-catherine','name_ar':'سانت كاترين','tag':'Mountains & history','tag_ar':'الجبال والتاريخ','lead':'Mountain landscapes and sites of cultural and spiritual significance.','lead_ar':'طبيعة جبلية ومعالم ثقافية وروحية مميزة.','mood':'desert'},
)

EXPERIENCES = (
    {'id':'history','title':'Walk through history','title_ar':'رحلة عبر التاريخ','intro':'Temples, ancient sites and stories spanning millennia.','intro_ar':'معابد وآثار وحكايات من آلاف السنين.','mood':'heritage','question':'What historical places should I visit in Egypt?'},
    {'id':'beaches','title':'Find your Red Sea escape','title_ar':'استمتع بالبحر الأحمر','intro':'Coastal towns, sea views and time to unwind.','intro_ar':'مدن ساحلية وإطلالات بحرية ووقت للراحة.','mood':'coast','question':'Compare Hurghada, Dahab and Sharm El Sheikh.'},
    {'id':'culture','title':'Meet local culture','title_ar':'اكتشف الثقافة المحلية','intro':'Discover neighbourhoods, traditions and everyday Egypt.','intro_ar':'اكتشف الأحياء والعادات وتفاصيل الحياة في مصر.','mood':'city','question':'What should I know about Egyptian culture?'},
    {'id':'food','title':'Taste the real Egypt','title_ar':'تذوق الأكل المصري','intro':'Explore local food traditions and familiar favourites.','intro_ar':'تعرف على الأكلات المصرية وتجارب الطعام المحلية.','mood':'city','question':'Which Egyptian foods should I try?'},
    {'id':'nature','title':'Go beyond the city','title_ar':'اخرج للطبيعة','intro':'Oases, gardens and remarkable natural landscapes.','intro_ar':'واحات وحدائق ومناظر طبيعية تستحق الزيارة.','mood':'desert','question':'Where can I explore nature in Egypt?'},
    {'id':'adventure','title':'Take the scenic route','title_ar':'عيش روح المغامرة','intro':'Discover active days and destinations off the usual route.','intro_ar':'أنشطة ومغامرات ووجهات خارج المسار المعتاد.','mood':'desert','question':'What adventure activities can I do in Egypt?'},
    {'id':'museums','title':'Inside Egypt’s museums','title_ar':'جولة في المتاحف','intro':'Collections that bring Egypt’s history to life.','intro_ar':'مجموعات أثرية تحكي تاريخ مصر عبر العصور.','mood':'heritage','question':'Which museums in Egypt should I visit?'},
    {'id':'family','title':'Travel together','title_ar':'رحلة لكل العائلة','intro':'Places and activities to consider when travelling with family.','intro_ar':'أماكن وأنشطة مناسبة للتخطيط لرحلة عائلية.','mood':'nature','question':'What are good family activities in Egypt?'},
)

# Links to actual institutions, not paid/affiliate inventory; eligibility depends on nationality.
ESSENTIALS = (
    {'id':'entry','title':'Visas & entry','title_ar':'التأشيرات والدخول','detail':'Entry requirements depend on your passport and circumstances. Check the official Egyptian e-Visa portal before travelling.', 'detail_ar':'شروط الدخول تختلف بحسب الجنسية والحالة. راجع البوابة المصرية الرسمية للتأشيرة قبل السفر.', 'source_name':'Egypt e-Visa portal','url':'https://www.visa2egypt.gov.eg/'},
    {'id':'monuments','title':'Museums & monuments','title_ar':'المتاحف والمعالم','detail':'Check official venue information for opening hours, tickets and visitor notices. These may change.', 'detail_ar':'راجع المصادر الرسمية لمواعيد الزيارة والتذاكر والتنبيهات لأن المعلومات قد تتغير.', 'source_name':'Ministry of Tourism and Antiquities','url':'https://egymonuments.gov.eg/'},
    {'id':'tickets','title':'Official attraction tickets','title_ar':'التذاكر الرسمية للمعالم','detail':'Find official ticketing information for participating archaeological and cultural attractions.', 'detail_ar':'اطلع على معلومات الحجز الرسمي للمواقع الأثرية والثقافية المتاحة.', 'source_name':'EgyMonuments e-Ticketing','url':'https://egymonuments.com/'},
    {'id':'transport','title':'Getting around','title_ar':'المواصلات والتنقل','detail':'Plan transfers between cities ahead of time; compare transport options and recheck schedules directly with operators.', 'detail_ar':'خطط للانتقالات بين المدن مسبقًا، وقارن الخيارات وأكد المواعيد من مقدم الخدمة.', 'source_name':'Egypt tourism ministry','url':'https://mota.gov.eg/'},
)

def get_destinations():
    places = all_places()
    output=[]
    for item in DESTINATION_EDITORIAL:
        selected=[p for p in places if p['city']==item['city']]
        output.append({**item,'attraction_count':len(selected),'highlights':[
            {'id':p['id'],'name':p['name'],'name_ar':p.get('name_ar') or p['name']}
            for p in selected[:3]]})
    return output

def get_experiences():
    places=all_places()
    return [{**item,'place_count':sum(item['id'] in p['tags'] for p in places),
             'sample_places':[{'id':p['id'],'name':p['name'],'city':p['city']}
                               for p in places if item['id'] in p['tags']][:3]}
            for item in EXPERIENCES]
