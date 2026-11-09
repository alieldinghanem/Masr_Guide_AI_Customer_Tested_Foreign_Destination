import React, { useMemo, useState } from 'react'
import { ArrowUpRight, Sparkles } from 'lucide-react'
import { useI18n } from '../i18n'
import { EXPERIENCE_FALLBACK } from './TravelData'
import { EXPERIENCE_MEDIA, EditorialImage } from './EditorialMedia'

export default function Experiences({ experiences, places, onExplore, askQuestion }) {
  const { lang } = useI18n()
  const ar=lang==='ar'
  const [selected, setSelected] = useState('all')
  const catalog = useMemo(() => experiences.length ? experiences : EXPERIENCE_FALLBACK.map(e=>({...e,place_count:places.filter(p=>p.tags.includes(e.id)).length})),[experiences,places])
  const themes=selected==='all'?catalog:catalog.filter(e=>e.id===selected)
  return <main className="v3-page">
    <section className="v3-page-head v3-head-experiences"><div className="container">
      <span className="v3-overline">{ar?'أكتر من مجرد أماكن':'MORE THAN PLACES'}</span>
      <h1>{ar?'عايز تعيش':'What will you'} <em>{ar?'تجربة إيه؟':'experience?'}</em></h1>
      <p>{ar?'تاريخ، بحر، أكل، ثقافة ومغامرات. اختار اللي بتحبه واكتشف تجارب مصر.' : 'Egypt is not one trip. Discover experiences shaped by your interests, from ancient stories to easy coastal days.'}</p>
    </div></section>
    <div className="container v3-content">
      <div className="v3-filter-pills v3-experience-pills" role="group" aria-label={ar?'فلاتر التجارب':'Experience categories'}>
        <button className={selected==='all'?'chosen':''} onClick={()=>setSelected('all')}>{ar?'كل التجارب':'All experiences'}</button>
        {catalog.map(e=><button key={e.id} onClick={()=>setSelected(e.id)} className={selected===e.id?'chosen':''}>{ar?e.title_ar:e.title}</button>)}
      </div>
      <div className="v3-experience-grid">
        {themes.map((e,i)=><article className={`v3-experience-card mood-${e.mood}`} key={e.id}>
          <div className="v3-experience-art"><EditorialImage src={EXPERIENCE_MEDIA[e.id]} alt="" className="v6-cover-image"/><span>{String(i+1).padStart(2,'0')}</span></div>
          <div className="v3-experience-copy"><span className="v3-kicker">{ar?'تجارب في مصر':'EXPERIENCE EGYPT'}</span><h2>{ar?e.title_ar:e.title}</h2><p>{ar?e.intro_ar:e.intro}</p>
            <span className="v3-destination-meta">{ar?`${e.place_count??0} مكان مرتبط في الدليل`:`${e.place_count??0} related catalogued places`}</span>
            <div className="v3-card-actions"><button onClick={()=>onExplore(e.id)}>{ar?'شوف الأماكن':'Explore places'} <ArrowUpRight size={16}/></button><button onClick={()=>askQuestion(ar?`اقترح لي تجارب ${e.title_ar} في مصر`:(e.question||`Tell me about ${e.title} in Egypt`))}><Sparkles size={16}/>{ar?'اسأل المرشد':'Ask AI'}</button></div>
          </div>
        </article>)}
      </div>
      <p className="v3-data-note">{ar?'دي أفكار ومعلومات للاستكشاف، مش عروض حجز مؤكدة أو أسعار مباشرة.':'These are discovery themes, not live bookable offers or verified prices.'}</p>
    </div>
  </main>
}
