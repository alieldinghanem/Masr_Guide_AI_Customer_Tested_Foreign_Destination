// Editorial fallbacks for temporary API unavailability, not claimed as live inventory.
// The primary source for the counts and highlight lists is /api/discover/*.
export const DESTINATIONS = [
  ['Cairo','القاهرة','The living capital','مدينة الحكايات','Historic neighbourhoods, unforgettable museums and everyday city life.','أحياء تاريخية ومتاحف وحياة مدينة مميزة.','heritage'],
  ['Giza','الجيزة','Ancient wonders','عجائب الحضارة','Discover Egypt’s monumental ancient world.','اكتشف أعظم آثار مصر القديمة.','heritage'],
  ['Luxor','الأقصر','Open-air history','التاريخ في كل مكان','Temples, tombs and ancient stories along the Nile.','معابد ومقابر وحكايات الحضارة على ضفاف النيل.','heritage'],
  ['Aswan','أسوان','Nile & Nubian culture','النيل والثقافة النوبية','River islands, laid-back afternoons and Nubian heritage.','جزر النيل وأجواء هادئة وثقافة نوبية.','nature'],
  ['Alexandria','الإسكندرية','Mediterranean soul','روح البحر المتوسط','History and culture meet the Mediterranean.','تاريخ وثقافة على البحر المتوسط.','coast'],
  ['Hurghada','الغردقة','Red Sea escapes','البحر الأحمر','Sea views and coastal experiences.','شواطئ وتجارب البحر الأحمر.','coast'],
  ['Sharm El Sheikh','شرم الشيخ','Sinai coast','ساحل سيناء','A gateway to coastal experiences in Sinai.','بوابة لتجارب البحر في سيناء.','coast'],
  ['Dahab','دهب','Slow travel','رحلة على مهلك','Coastal calm and outdoor activities.','هدوء البحر والأنشطة الخارجية.','coast'],
  ['Siwa','سيوة','Oasis & adventure','الواحات والمغامرة','An oasis escape with remarkable landscapes.','رحلة للواحات والمناظر الطبيعية.','desert'],
  ['Fayoum','الفيوم','Nature nearby','طبيعة ومغامرة','Lakes, landscapes and nature getaways.','بحيرات وطبيعة ورحلات متنوعة.','desert'],
  ['Abu Simbel','أبو سمبل','Monumental heritage','عظمة الحضارة','Impressive ancient temples in the far south.','معابد أثرية استثنائية في الجنوب.','heritage'],
  ['Saint Catherine','سانت كاترين','Mountains & history','الجبال والتاريخ','Mountain landscapes and heritage.','جبال وطبيعة وتراث مميز.','desert']
].map(([city,name_ar,tag,tag_ar,lead,lead_ar,mood]) => ({city,name_ar,tag,tag_ar,lead,lead_ar,mood}))

export const EXPERIENCE_FALLBACK = [
  ['history','Walk through history','رحلة عبر التاريخ','Temples, ancient sites and stories spanning millennia.','معابد وآثار وحكايات من آلاف السنين.','heritage'],
  ['beaches','Find your Red Sea escape','استمتع بالبحر الأحمر','Coastal towns, sea views and time to unwind.','مدن ساحلية ووقت للراحة والاسترخاء.','coast'],
  ['culture','Meet local culture','اكتشف الثقافة المحلية','Discover neighbourhoods and everyday Egypt.','اكتشف الأحياء وتفاصيل الحياة في مصر.','city'],
  ['food','Taste the real Egypt','تذوق الأكل المصري','Explore Egyptian food traditions.','تعرف على الأكلات والتجارب المحلية.','city'],
  ['nature','Go beyond the city','اخرج للطبيعة','Oases, gardens and natural landscapes.','واحات وحدائق ومناظر طبيعية.','desert'],
  ['adventure','Take the scenic route','عيش روح المغامرة','Active days and unusual destinations.','مغامرات ووجهات خارج المسار المعتاد.','desert'],
  ['museums','Inside Egypt’s museums','جولة في المتاحف','Collections that tell the story of Egypt.','مجموعات أثرية تروي تاريخ مصر.','heritage'],
  ['family','Travel together','رحلة لكل العائلة','Activities to plan together.','أنشطة تناسب التخطيط لرحلة عائلية.','nature']
].map(([id,title,title_ar,intro,intro_ar,mood]) => ({id,title,title_ar,intro,intro_ar,mood}))

export const ESSENTIAL_FALLBACK = [
  {id:'entry',title:'Visas & entry',title_ar:'التأشيرات والدخول',detail:'Entry rules depend on your nationality. Check the official portal before travel.',detail_ar:'شروط الدخول تختلف حسب الجنسية؛ راجع البوابة الرسمية قبل السفر.',source_name:'Egypt e-Visa',url:'https://www.visa2egypt.gov.eg/'},
  {id:'monuments',title:'Museums & monuments',title_ar:'المتاحف والمعالم',detail:'Confirm visiting hours and updates directly with the ministry.',detail_ar:'تأكد من مواعيد الزيارة والتحديثات من الوزارة مباشرة.',source_name:'Egypt Ministry of Tourism and Antiquities',url:'https://egymonuments.gov.eg/'},
  {id:'tickets',title:'Attraction tickets',title_ar:'تذاكر الأماكن الأثرية',detail:'Check official e-ticketing options for supported sites.',detail_ar:'تعرف على خيارات التذاكر الإلكترونية الرسمية للأماكن المتاحة.',source_name:'EgyMonuments',url:'https://egymonuments.com/'},
  {id:'transport',title:'Getting around',title_ar:'المواصلات والتنقل',detail:'Compare transfer options and confirm timetables with providers.',detail_ar:'قارن وسائل التنقل وأكد المواعيد مع مقدمي الخدمة.',source_name:'Ministry of Tourism and Antiquities',url:'https://mota.gov.eg/'}
]
