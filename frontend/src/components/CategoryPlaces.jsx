import React, { useMemo, useState } from 'react'
import { ArrowUpRight, Search, Landmark, Waves, MapPin, MessageCircle } from 'lucide-react'
import { useI18n } from '../i18n'
import { LANDMARK_MEDIA, getLandmarkFraming, EditorialImage } from './EditorialMedia'
import { matchesPlaceCategory } from '../categoryFilters'


/** Separate, data-driven collections. Results are sourced from /api/places,
 * never represented as live tickets, prices or bookable inventory.
 */
export default function CategoryPlaces({ type, places = [], openPlace, askQuestion }) {
  const { lang, placeName } = useI18n()
  const ar = lang === 'ar'
  const coast = type === 'coast'
  const [query, setQuery] = useState('')
  const selection = useMemo(() => places.filter(place => matchesPlaceCategory(place, type)), [places, type])
  const visible = useMemo(() => selection.filter(place => {
    const text = [place.name, place.name_ar, place.city, place.category, place.description, place.summary_ar].join(' ').toLocaleLowerCase()
    return text.includes(query.trim().toLocaleLowerCase())
  }), [query, selection])

  return <main className="mg-category-page">
    <section className="mg-category-hero container">
      <div className="mg-category-kicker">{coast ? 'EGYPT BY THE SEA' : 'EGYPT THROUGH THE AGES'}</div>
      <h1>{coast ? (ar ? 'الشواطئ والأماكن البحرية' : 'Beaches & coastal escapes') : (ar ? 'الأماكن الأثرية والتاريخية' : 'Historical places')}</h1>
      <p>{coast ? (ar ? 'اكتشف شواطئ مصر وتجارب البحر الأحمر والمدن الساحلية، واختار الأماكن اللي تناسب رحلتك.' : 'Explore Red Sea beaches and coastal experiences, then choose what fits your journey.') : (ar ? 'اكتشف الأهرامات والمعابد والمتاحف وأشهر معالم الحضارة المصرية.' : 'Discover pyramids, temples, museums and the remarkable heritage of Egypt.')}</p>
      <label className="mg-category-search"><Search size={18} aria-hidden="true"/><span className="sr-only">{ar ? 'ابحث عن مكان' : 'Search places'}</span><input value={query} onChange={event => setQuery(event.target.value)} placeholder={ar ? 'ابحث عن مكان أو مدينة...' : 'Search places or cities...'} aria-label={ar ? 'ابحث عن مكان' : 'Search places'} /></label>
    </section>
    <div className="container mg-category-body">
      <div className="mg-category-count" role="status">{ar ? `${visible.length} مكان في الدليل` : `${visible.length} curated places`}</div>
      <div className="mg-category-grid">
        {visible.map(place => <article className="mg-place-card" key={place.id}>
          <div className="mg-place-photo" aria-hidden="true" style={getLandmarkFraming(place.id)}><EditorialImage src={LANDMARK_MEDIA[place.id]} alt="" className="mg-place-img" /><span className="mg-place-symbol">{coast ? <Waves size={20} /> : <Landmark size={20} />}</span></div>
          <div className="mg-place-content">
            <div className="mg-place-location"><MapPin size={13}/>{place.city}</div>
            <h2>{placeName(place)}</h2>
            <p>{ar ? (place.summary_ar || place.description) : place.description}</p>
            <div className="mg-place-actions"><button type="button" onClick={() => openPlace(place)}>{ar ? 'تفاصيل المكان' : 'View details'} <ArrowUpRight size={15}/></button><button type="button" title={ar ? 'اسأل المساعد' : 'Ask AI'} aria-label={`${ar ? 'اسأل المساعد عن' : 'Ask AI about'} ${placeName(place)}`} onClick={() => askQuestion(ar ? `احكيلي عن ${placeName(place)} وإزاي أضيفه لرحلتي؟` : `Tell me about ${place.name} and how to add it to my itinerary.`)}><MessageCircle size={17}/></button></div>
          </div>
        </article>)}
      </div>
      {!selection.length && <p className="mg-category-empty">{ar ? 'بيانات الأماكن قيد التحميل. جرّب إعادة الاتصال بالخادم.' : 'The place catalogue is not available yet. Check your connection to the backend.'}</p>}
      {selection.length > 0 && !visible.length && <p className="mg-category-empty">{ar ? 'مفيش أماكن مطابقة. جرّب بحث مختلف.' : 'No places match that search. Try another term.'}</p>}
    </div>
  </main>
}
