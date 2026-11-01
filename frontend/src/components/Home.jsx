import React, { useState } from 'react'
import { ArrowRight, ArrowUpRight, BookOpen, Compass, MapPin, MessageCircle, Search, Sparkles, Waves, Landmark, Route, ShieldCheck } from 'lucide-react'
import { useI18n } from '../i18n'
import { DESTINATIONS, EXPERIENCE_FALLBACK } from './TravelData'
import { DESTINATION_MEDIA, EXPERIENCE_MEDIA, EditorialImage } from './EditorialMedia'

const FEATURED = ['Giza', 'Luxor', 'Aswan', 'Hurghada', 'Alexandria', 'Siwa']
const MOODS = [{id:'heritage', en:'History & heritage', ar:'تاريخ وحضارة', icon:Landmark},{id:'coast', en:'Sea & beaches', ar:'بحر وشواطئ',icon:Waves},{id:'desert',en:'Desert adventures',ar:'مغامرات صحراوية',icon:Compass}]

export default function Home({ go, places, cities, openPlace, askQuestion, destinations = [], experiences = [], searchDestinations }) {
  const { t, lang, placeName, cityName, category } = useI18n()
  const ar = lang === 'ar'
  const [search, setSearch] = useState('')
  const catalog = destinations.length ? destinations : DESTINATIONS
  const experiencesList = experiences.length ? experiences : EXPERIENCE_FALLBACK
  const discover = city => {
    const related = places.find(p => p.city === city)
    if (related) openPlace(related)
    else searchDestinations(city)
  }
  return <main className="v6-home">
    <section className="v6-hero" aria-label={ar?'اكتشف جمال مصر':'Discover the beauty of Egypt'}>
      <div className="v6-hero-photo" aria-hidden="true"><EditorialImage src={DESTINATION_MEDIA.Giza.replace('w=1100','w=2000')} fallback="/assets/gem.jpeg" alt="" eager /></div>
      <div className="v6-hero-overlay" />
      <div className="container v6-hero-layout">
        <div className="v6-hero-main">
          <span className="v6-overline v6-light"><span className="v6-sun" /> {ar?'بوابتك لاكتشاف مصر':'THE WORLD IS WAITING. START WITH EGYPT.'}</span>
          <h1>{t('home.h1a')}<br/><em>{t('home.h1b')}</em></h1>
          <p>{t('home.sub')}</p>
          <div className="v6-hero-ctas"><button type="button" className="v6-button v6-button-sand" onClick={()=>go('destinations')}>{ar?'اكتشف الوجهات':'Explore destinations'} <ArrowUpRight size={19}/></button><button type="button" className="v6-button v6-button-outline" onClick={()=>go('planner')}>{t('home.start')} <ArrowRight size={19}/></button></div>
          <span className="v6-travel-note"><MapPin size={14}/>{ar?'الجيزة، مصر':'Giza, Egypt'} <span className="v6-vertical-rule"/>{ar?'رحلتك تبدأ هنا':'Your Egyptian story begins here'}</span>
        </div>
        <div className="v6-hero-sidecard" aria-hidden="true"><span>01 / 03</span><strong>{ar?'اكتشف عالماً من الحكايات':'A world of wonder'}</strong><span>{ar?'حضارة · طبيعة · بحر':'CULTURE · NATURE · THE RED SEA'}</span></div>
      </div>
      <div className="container v6-search-shell">
        <form className="v6-discovery-search" onSubmit={e=>{e.preventDefault(); searchDestinations(search)}} role="search">
          <span className="v6-search-icon"><Search size={22}/></span>
          <div className="v6-search-copy"><label htmlFor="v6-destination-search">{ar?'فين نفسك تروح؟':'Where to next?'}</label><input id="v6-destination-search" value={search} onChange={e=>setSearch(e.target.value)} placeholder={ar?'ابحث عن القاهرة، الأقصر، الغردقة...':'Search Cairo, Luxor, Hurghada...'} autoComplete="off" /></div>
          <button type="submit" className="v6-search-submit">{ar?'استكشف':'Explore'}<ArrowRight size={18}/></button>
        </form>
        <div className="v6-trust-summary"><span><Compass size={16}/>{cities.length ? t('home.proofCount', {n:cities.length}) : (ar?'وجهات مصرية':'Egypt destinations')}</span><span><BookOpen size={16}/>{ar?'معالم ومعلومات موثقة':'Curated travel knowledge'}</span><span><Sparkles size={16}/>{ar?'تخطيط مدعوم بالذكاء الاصطناعي':'AI-assisted travel planning'}</span></div>
      </div>
    </section>

    <section className="v6-intro container" id="destinations">
      <div className="v6-section-title"><div><span className="v6-overline">{ar?'اكتشف الوجهات':'01 / EXPLORE EGYPT'}</span><h2>{ar?'مصر مش مكان واحد.':'One country.'}<br/><em>{ar?'دي عوالم كتير.':'Endless discoveries.'}</em></h2><p>{ar?'من حكايات الفراعنة لنسمات البحر الأحمر، كل وجهة لها سحرها.':'Ancient cities, magical coastlines, and quiet desert escapes. Find the Egypt that moves you.'}</p></div><button className="v6-text-button" onClick={()=>go('destinations')}>{ar?'كل الوجهات':'View all destinations'}<ArrowUpRight size={18}/></button></div>
      <div className="v6-destination-grid">
        {FEATURED.map((city,i)=>{
          const d = catalog.find(x=>x.city===city) || DESTINATIONS.find(x=>x.city===city)
          if (!d) return null
          return <button type="button" key={city} className={`v6-destination-card v6-destination-${i} mood-${d.mood}`} onClick={()=>discover(city)} aria-label={ar?`استكشف ${d.name_ar}`:`Explore ${city}`}>
            <EditorialImage src={DESTINATION_MEDIA[city]} alt="" className="v6-cover-image" />
            <span className="v6-card-top"><span>0{i+1}</span><ArrowUpRight size={19}/></span>
            <span className="v6-card-content"><small>{ar?d.tag_ar:d.tag}</small><strong>{ar?d.name_ar:city}</strong><span>{ar?'استكشف المدينة':'Discover destination'} <ArrowRight size={15}/></span></span>
          </button>
        })}
      </div>
      <div className="v6-mood-strip"><span>{ar?'مش عارف تبدأ منين؟':'FIND YOUR KIND OF EGYPT'}</span><div>{MOODS.map(m=>{const Icon=m.icon;return <button key={m.id} onClick={()=>searchDestinations(m.id)}><Icon size={18}/>{ar?m.ar:m.en}<ArrowUpRight size={14}/></button>})}</div></div>
    </section>

    <section className="v6-experiences"><div className="container">
      <div className="v6-section-title"><div><span className="v6-overline">{ar?'عِش التجربة':'02 / EXPERIENCES'}</span><h2>{ar?'مش بس تتفرج.':'Don’t just visit.'}<br/><em>{ar?'عيش الحكاية.':'Feel everything.'}</em></h2><p>{ar?'اختر اللي بتحبه: حضارة، طبيعة، بحر، أو تجارب من قلب الحياة المصرية.':'From legendary temples to the wild Red Sea, experience a country that stays with you.'}</p></div><button className="v6-text-button" onClick={()=>go('experiences')}>{ar?'استكشف التجارب':'Browse experiences'}<ArrowUpRight size={18}/></button></div>
      <div className="v6-experience-grid">{['history','beaches','culture','adventure'].map((id,i)=>{
        const e=experiencesList.find(x=>x.id===id)||EXPERIENCE_FALLBACK.find(x=>x.id===id)
        return <button className={`v6-experience-card v6-experience-${i}`} key={id} onClick={()=>go('experiences')}>
          <EditorialImage src={EXPERIENCE_MEDIA[id]} alt="" className="v6-cover-image" />
          <span className="v6-experience-content"><span>{`0${i+1} / ${ar?'تجارب':'EXPERIENCES'}`}</span><strong>{ar?e?.title_ar:e?.title}</strong><span>{ar?'استكشف الآن':'Explore stories'} <ArrowUpRight size={15}/></span></span>
        </button>
      })}</div>
      <p className="v6-disclosure">{ar?'تجارب للإلهام والاستكشاف، وليست حجوزات أو أسعارًا مباشرة.':'Discover experiences and inspiration. These are not live bookable offers or prices.'}</p>
    </div></section>

    <section className="v6-editorial container"><div className="v6-editorial-visual"><EditorialImage src={DESTINATION_MEDIA.Aswan} alt={ar?'مركب شراعي في النيل بأسوان':'Felucca sailing on the Nile in Aswan'} className="v6-cover-image"/><span>{ar?'اكتشف ما وراء الأماكن':'BEYOND THE GUIDEBOOK'}</span></div><div className="v6-editorial-copy"><span className="v6-overline">{ar?'خطط بذكاء':'03 / YOUR TRIP, YOUR WAY'}</span><h2>{ar?'بلد مليانة قصص.':'Your journey,'}<br/><em>{ar?'وخطة على مزاجك.':'beautifully yours.'}</em></h2><p>{ar?'اختار اهتماماتك، نظّم أيامك، احفظ الأماكن اللي عجبتك، واسأل مرشدنا السياحي عن أي حاجة تخص رحلتك.':'Collect the places you love, build your itinerary, and explore with an AI companion that knows the destination — not just the prompt.'}</p><div className="v6-editorial-features"><span><Route size={20}/>{ar?'خطط لرحلتك':'Personalized itineraries'}</span><span><ShieldCheck size={20}/>{ar?'معلومات بمصادر':'Source-aware travel knowledge'}</span><span><MessageCircle size={20}/>{ar?'اسأل باللغة اللي تحبها':'Arabic and English AI guide'}</span></div><div className="v6-editorial-ctas"><button className="v6-button v6-button-dark" onClick={()=>go('planner')}>{t('home.start')} <ArrowRight size={18}/></button><button className="v6-text-button" onClick={()=>askQuestion(ar?'عايز أعرف أفضل الأماكن اللي أزورها في مصر':'What are the best places to visit in Egypt?')}>{ar?'اسأل المرشد الذكي':'Ask our AI guide'}<ArrowUpRight size={18}/></button></div></div></section>

    <section className="v6-featured container"><div className="v6-section-title"><div><span className="v6-overline">{ar?'مختارات من مصر':'04 / MUST-SEE PLACES'}</span><h2>{ar?'أماكن هتفضل':'Places worth'} <em>{ar?'فاكرها.':'remembering.'}</em></h2></div><button className="v6-text-button" onClick={()=>go('explore')}>{ar?'كل المعالم':'View all attractions'}<ArrowUpRight size={18}/></button></div><div className="v6-landmark-row">{['grand-egyptian-museum','karnak','philae','qaitbay'].map((id,i)=>{const p=places.find(x=>x.id===id); if(!p) return null; return <button className="v6-landmark-card" key={p.id} onClick={()=>openPlace(p)}><span className="v6-landmark-photo"><EditorialImage src={i===0?'/assets/gem.jpeg':DESTINATION_MEDIA[p.city]} alt="" className="v6-cover-image"/><span>{cityName(p.city)}</span></span><span className="v6-landmark-desc"><small>{category(p.category)}</small><strong>{placeName(p)}</strong><span>{ar?'تعرف على المكان':'Explore the story'} <ArrowUpRight size={16}/></span></span></button>})}</div></section>

    <section className="v6-bottom-banner"><div className="container v6-bottom-inner"><div><span className="v6-overline v6-light">{ar?'جاهز تبدأ؟':'THE ADVENTURE STARTS HERE'}</span><h2>{ar?'كل رحلة عظيمة':'Every great trip'}<br/><em>{ar?'بتبدأ بفضول.':'starts with curiosity.'}</em></h2><p>{ar?'اكتشف مصر بطريقتك وخلي مرشدك الذكي يساعدك في كل خطوة.':'A world of history, coastlines and culture. Egypt is ready when you are.'}</p></div><div><button className="v6-button v6-button-sand" onClick={()=>go('planner')}>{ar?'ابدأ تخطيط رحلتك':'Build my Egypt trip'} <ArrowRight size={19}/></button><button className="v6-button v6-button-outline" onClick={()=>go('guide')}>{ar?'اتكلم مع المرشد':'Meet your AI guide'}<MessageCircle size={18}/></button></div></div></section>
  </main>
}
