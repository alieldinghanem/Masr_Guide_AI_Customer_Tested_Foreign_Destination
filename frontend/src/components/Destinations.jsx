import React, { useEffect, useMemo, useState } from 'react'
import { ArrowRight, ArrowUpRight, Landmark, MapPin, Search } from 'lucide-react'
import { useI18n } from '../i18n'
import { DESTINATIONS } from './TravelData'
import { DESTINATION_MEDIA, EditorialImage } from './EditorialMedia'

export default function Destinations({ destinations, places, openPlace, askQuestion, go, initialQuery = '' }) {
  const { lang } = useI18n()
  const ar = lang === 'ar'
  const [q, setQ] = useState(initialQuery)
  useEffect(() => setQ(initialQuery), [initialQuery])
  const [active, setActive] = useState('all')
  const catalog = useMemo(() => destinations.length ? destinations : DESTINATIONS.map(d => ({ ...d,
    attraction_count: places.filter(p => p.city === d.city).length,
    highlights: places.filter(p => p.city === d.city).slice(0, 3).map(p => ({id:p.id,name:p.name,name_ar:p.name_ar}))
  })), [destinations, places])
  const kind = ['heritage', 'coast', 'desert', 'nature'].includes(q.toLowerCase()) ? q.toLowerCase() : null
  const matches = catalog.filter(d => (active === 'all' || d.mood === active) &&
    (kind ? d.mood === kind : `${d.city} ${d.name_ar} ${d.tag} ${d.tag_ar} ${d.lead} ${d.lead_ar}`.toLowerCase().includes(q.toLowerCase())))
  return <main className="v3-page">
    <section className="v3-page-head v3-head-destinations"><div className="container">
      <span className="v3-overline">{ar ? 'مصر في كل مكان' : 'THE COUNTRY OF A THOUSAND STORIES'}</span>
      <h1>{ar ? 'اختار وجهتك.' : 'Find your next'} <em>{ar ? 'واكتشف مصر.' : 'Egypt story.'}</em></h1>
      <p>{ar ? 'من المعابد القديمة إلى شواطئ البحر الأحمر، استكشف مدن مصر ومناطقها على راحتك.' : 'From ancient landmarks to the Red Sea, discover the places and perspectives that make Egypt unforgettable.'}</p>
    </div></section>
    <div className="container v3-content">
      <div className="v3-filters">
        <label className="v3-search"><Search size={17}/><input value={q} onChange={e=>setQ(e.target.value)} placeholder={ar?'ابحث عن مدينة أو وجهة...':'Search for a destination...'} aria-label={ar?'ابحث عن وجهة':'Search destinations'}/></label>
        <div className="v3-filter-pills" role="group" aria-label={ar?'نوع الوجهة':'Destination type'}>
          {['all','heritage','coast','desert','nature'].map(x=><button type="button" key={x} className={active===x?'chosen':''} aria-pressed={active===x} onClick={()=>setActive(x)}>{({all:ar?'الكل':'All',heritage:ar?'تاريخ':'History',coast:ar?'بحر':'Coast',desert:ar?'صحرا وواحات':'Desert',nature:ar?'طبيعة':'Nature'})[x]}</button>)}
        </div>
      </div>
      <div className="v3-destination-grid">
        {matches.map((d,i)=>{
          const matched = places.filter(p=>p.city===d.city)
          return <article className={`v3-destination-card mood-${d.mood}`} key={d.city}>
            <div className="v3-destination-visual"><EditorialImage src={DESTINATION_MEDIA[d.city]} alt="" className="v6-cover-image"/><span className="v3-destination-index">{String(i+1).padStart(2,'0')} / EGYPT</span><span className="v3-destination-location"><MapPin size={13}/>{ar ? d.name_ar : d.city}</span></div>
            <div className="v3-destination-text"><span className="v3-kicker">{ar?d.tag_ar:d.tag}</span><h2>{ar?d.name_ar:d.city}</h2><p>{ar?d.lead_ar:d.lead}</p>
              <div className="v3-destination-meta"><Landmark size={15}/>{ar ? `${d.attraction_count ?? matched.length} معلم في الدليل` : `${d.attraction_count ?? matched.length} catalogued attractions`}</div>
              {matched.length > 0 ? <button className="v3-link" onClick={()=>openPlace(matched[0])}>{ar?'استكشف المعالم':'Explore places'} <ArrowUpRight size={17}/></button> : <button className="v3-link" onClick={()=>askQuestion(ar?`ما أفضل الأنشطة في ${d.name_ar}؟`:`What can I do in ${d.city}?`)}>{ar?'اسأل عن الوجهة':'Ask about this destination'} <ArrowRight size={17}/></button>}
            </div>
          </article>
        })}
      </div>
      {matches.length===0 && <p className="v3-empty">{ar?'مفيش نتائج، جرّب كلمة تانية.':'No destinations matched your search.'}</p>}
      <div className="v3-soft-cta"><div><span className="v3-kicker">{ar?'خطوتك الجاية':'NEXT STEP'}</span><h2>{ar?'لقيت مكان نفسك تزوره؟':'Found a place you love?'}</h2><p>{ar?'ابدأ تخطيط الرحلة أو اسأل المرشد عن التفاصيل.':'Build a route around your favourite places.'}</p></div><button className="btn primary dark" onClick={()=>go('planner')}>{ar?'خطط رحلتك':'Plan a journey'} <ArrowRight size={18}/></button></div>
    </div>
  </main>
}
