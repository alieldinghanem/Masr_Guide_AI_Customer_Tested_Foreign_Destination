import React, { useMemo, useState } from 'react'
import { ArrowUpRight, ExternalLink, Search, Landmark, Waves, MapPin, MessageCircle } from 'lucide-react'
import { useI18n } from '../i18n'
import { LANDMARK_MEDIA, PHOTO_CREDITS, getLandmarkFraming, EditorialImage } from './EditorialMedia'
import { COASTAL_DESTINATIONS } from '../coastalDestinations'
import { getReligiousGroup, isSwimmingBeach, matchesPlaceCategory, orderCategoryPlaces, RELIGIOUS_GROUP_ORDER } from '../categoryFilters'
import DiscoveryNav from './DiscoveryNav'
import RatingWidget from './RatingWidget'
import { sortCoastalGuides } from '../ratingOrder'


/** Separate, data-driven collections. Results are sourced from /api/places,
 * never represented as live tickets, prices or bookable inventory.
 */
export default function CategoryPlaces({ type, places = [], openDetails, openPlace, askQuestion, ratings = {}, onRate }) {
  const { lang, placeName, cityName } = useI18n()
  const ar = lang === 'ar'
  const coast = type === 'coast'
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('editorial')
  const selection = useMemo(() => orderCategoryPlaces(places.filter(place => matchesPlaceCategory(place, type)), type), [places, type])
  const visible = useMemo(() => selection.filter(place => {
    const text = [place.name, place.name_ar, place.city, place.category, place.description, place.summary_ar].join(' ').toLocaleLowerCase()
    return text.includes(query.trim().toLocaleLowerCase())
  }), [query, selection])
  const swimmingPlaces = coast ? visible.filter(isSwimmingBeach) : []
  const otherCoastalPlaces = coast ? visible.filter(place => !isSwimmingBeach(place)) : []
  const secularPlaces = coast ? [] : visible.filter(place => !getReligiousGroup(place))
  const religiousGroups = coast ? [] : RELIGIOUS_GROUP_ORDER.map(group => [group, visible.filter(place => getReligiousGroup(place) === group)]).filter(([, items]) => items.length)
  const coastalGuides = coast ? sortCoastalGuides(COASTAL_DESTINATIONS.filter(item =>
    [item.en, item.ar, item.regionEn, item.regionAr, item.spotEn, item.spotAr, item.noteEn, item.noteAr]
      .join(' ').toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())), ratings, sort) : []
  const placeCards = items => <div className="mg-category-grid">
    {items.map(place => <article className="mg-place-card" key={place.id}>
      <button type="button" className="mg-place-photo" style={getLandmarkFraming(place.id)} aria-label={`${ar ? 'تفاصيل أكثر عن' : 'More details about'} ${placeName(place)}`} onClick={() => (openDetails || openPlace)?.(place)}><EditorialImage src={LANDMARK_MEDIA[place.id]} alt="" className="mg-place-img" /><span className="mg-place-symbol" aria-hidden="true">{coast && isSwimmingBeach(place) ? <Waves size={20} /> : <Landmark size={20} />}</span><span className="mg-image-more" aria-hidden="true">{ar ? 'تفاصيل أكثر' : 'More details'} <ArrowUpRight size={15} /></span></button>
      <div className="mg-place-content">
        <div className="mg-place-location"><MapPin size={13}/>{cityName(place.city)}</div>
        <h2>{placeName(place)}</h2>
        <p>{ar ? (place.summary_ar || place.description) : place.description}</p>
        <RatingWidget targetId={place.id} name={placeName(place)} summary={ratings[place.id]} onRate={onRate} />
        <div className="mg-place-actions"><button type="button" onClick={() => (openDetails || openPlace)?.(place)}>{ar ? 'تفاصيل المكان' : 'View details'} <ArrowUpRight size={15}/></button><button type="button" title={ar ? 'اسأل المساعد' : 'Ask AI'} aria-label={`${ar ? 'اسأل المساعد عن' : 'Ask AI about'} ${placeName(place)}`} onClick={() => askQuestion(ar ? `احكيلي عن ${placeName(place)} وإزاي أضيفه لرحلتي؟` : `Tell me about ${place.name} and how to add it to my itinerary.`)}><MessageCircle size={17}/></button></div>
        {PHOTO_CREDITS[place.id] && <a className="mg-photo-credit" href={PHOTO_CREDITS[place.id].url} target="_blank" rel="noopener noreferrer">{ar ? 'الصورة' : 'Photo'}: {PHOTO_CREDITS[place.id].author} · {PHOTO_CREDITS[place.id].license}</a>}
      </div>
    </article>)}
  </div>

  return <main className="mg-category-page">
    <section className="mg-category-hero container">
      <div className="mg-category-kicker">{coast ? (ar ? 'مصر على البحر' : 'EGYPT BY THE SEA') : (ar ? 'مصر عبر العصور' : 'EGYPT THROUGH THE AGES')}</div>
      <h1>{coast ? (ar ? 'الشواطئ والأماكن البحرية' : 'Beaches & coastal escapes') : (ar ? 'الأماكن الأثرية والتاريخية' : 'Historical places')}</h1>
      <p>{coast ? (ar ? 'اختار شاطئًا للنزول للمياه، واستكشف المعالم والأنشطة البحرية في قسم منفصل.' : 'Find a beach destination for swimming, then explore other coastal sights and activities separately.') : (ar ? 'اكتشف الأهرامات والمعابد والمتاحف وأشهر معالم الحضارة المصرية.' : 'Discover pyramids, temples, museums and the remarkable heritage of Egypt.')}</p>
      <label className="mg-category-search"><Search size={18} aria-hidden="true"/><span className="sr-only">{ar ? 'ابحث عن مكان' : 'Search places'}</span><input value={query} onChange={event => setQuery(event.target.value)} placeholder={ar ? 'ابحث عن مكان أو مدينة...' : 'Search places or cities...'} aria-label={ar ? 'ابحث عن مكان' : 'Search places'} /></label>
    </section>
    <div className="container mg-category-body">
      <DiscoveryNav current={type} />
      <div className="mg-category-count" role="status">{coast ? (ar ? `${coastalGuides.length} وجهات شاطئية · ${swimmingPlaces.length} أماكن شاطئية في الدليل` : `${coastalGuides.length} beach destinations · ${swimmingPlaces.length} beach places in the catalog`) : (ar ? `${visible.length} مكان في الدليل` : `${visible.length} curated places`)}</div>
      {coast && coastalGuides.length > 0 && <section className="mg-coastal-guides" aria-labelledby="coastal-guides-title">
        <div className="mg-coastal-guides-head"><h2 id="coastal-guides-title">{ar ? 'وجهات شاطئية للنزول للمياه' : 'Beach destinations for swimming'}</h2><p>{ar ? 'اختار مدينة وشوف مثالًا لشاطئ فيها. تأكد من السماح بالسباحة والدخول وحالة البحر في يوم زيارتك.' : 'Choose a destination and see a beach example. Check swimming permission, access and sea conditions on the day you visit.'}</p><label className="mg-coast-sort">{ar ? 'الترتيب' : 'Sort by'} <select value={sort} onChange={event => setSort(event.target.value)}><option value="editorial">{ar ? 'الترتيب المقترح' : 'Recommended order'}</option><option value="rated">{ar ? 'الأعلى تقييمًا' : 'Highest visitor rating'}</option></select></label></div>
        <div className="mg-coastal-guides-grid">{coastalGuides.map(item => <article className="mg-coastal-guide" key={item.id}>
          <span>{ar ? item.regionAr : item.regionEn}</span><h3>{ar ? item.ar : item.en}</h3><p className="mg-coastal-example"><strong>{ar ? 'مثال لشاطئ: ' : 'Beach example: '}</strong>{ar ? item.spotAr : item.spotEn}</p><p className="mg-coastal-note">{ar ? item.noteAr : item.noteEn}</p><RatingWidget targetId={`coast:${item.id}`} name={ar ? item.ar : item.en} summary={ratings[`coast:${item.id}`]} onRate={onRate} /><a href={item.url} target="_blank" rel="noopener noreferrer">{ar ? 'مصدر معلومات الوجهة' : 'Destination source'} <ExternalLink size={16} aria-hidden="true" /></a>
        </article>)}</div>
      </section>}
      {coast && swimmingPlaces.length > 0 && <section className="mg-coast-group" aria-labelledby="swimming-beaches-title">
        <h2 id="swimming-beaches-title">{ar ? 'أماكن شاطئية في دليلنا' : 'Beach places in our catalog'}</h2>
        <p>{ar ? 'الموقع الشاطئي لا يعني إن السباحة متاحة في كل جزء منه. اتبع العلامات وتعليمات المكان.' : 'Beach access does not mean swimming is allowed everywhere. Follow local signs and guidance.'}</p>
        {placeCards(swimmingPlaces)}
      </section>}
      {coast && otherCoastalPlaces.length > 0 && <section className="mg-coast-group" aria-labelledby="coastal-other-title">
        <h2 id="coastal-other-title">{ar ? 'معالم وأنشطة بحرية أخرى' : 'Other coastal sights and activities'}</h2>
        <p>{ar ? 'مواقع غوص ومراسي ومعالم على البحر؛ لا نعرضها كشواطئ سباحة.' : 'Dive sites, marinas and waterfront landmarks; these are not listed as swimming beaches.'}</p>
        {placeCards(otherCoastalPlaces)}
      </section>}
      {!coast && secularPlaces.length > 0 && placeCards(secularPlaces)}
      {!coast && religiousGroups.length > 0 && <section className="mg-religious-places" aria-labelledby="religious-places-title">
        <h2 id="religious-places-title">{ar ? 'دور العبادة التاريخية' : 'Historic places of worship'}</h2>
        {religiousGroups.map(([group, items]) => <section className="mg-religious-group" key={group} aria-labelledby={`religious-${group}`}>
          <h3 id={`religious-${group}`}>{ar ? ({ mosques: 'المساجد', churches: 'الكنائس والأديرة', synagogues: 'المعابد اليهودية' }[group]) : ({ mosques: 'Mosques', churches: 'Churches & monasteries', synagogues: 'Synagogues' }[group])}</h3>
          {placeCards(items)}
        </section>)}
      </section>}
      {!selection.length && !query.trim() && <p className="mg-category-empty">{ar ? 'بيانات الأماكن قيد التحميل. جرّب إعادة الاتصال بالخادم.' : 'The place catalogue is not available yet. Check your connection to the backend.'}</p>}
      {!visible.length && !coastalGuides.length && query.trim() && <p className="mg-category-empty">{ar ? 'مفيش أماكن مطابقة. جرّب بحث مختلف.' : 'No places match that search. Try another term.'}</p>}
    </div>
  </main>
}
