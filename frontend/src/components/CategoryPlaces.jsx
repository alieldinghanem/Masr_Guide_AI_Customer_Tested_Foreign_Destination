import React, { useMemo, useState } from 'react'
import { ArrowUpRight, Search, Landmark, Waves, MapPin, MessageCircle } from 'lucide-react'
import { useI18n } from '../i18n'
import { LANDMARK_MEDIA, getLandmarkFraming, EditorialImage, PhotoCredit } from './EditorialMedia'
import { COASTAL_DESTINATIONS } from '../coastalDestinations'
import { COASTAL_MEDIA } from '../coastalMedia'
import { getReligiousGroup, isSwimmingBeach, matchesPlaceCategory, orderCategoryPlaces, RELIGIOUS_GROUP_ORDER } from '../categoryFilters'
import DiscoveryNav from './DiscoveryNav'
import RatingWidget from './RatingWidget'


/** Separate, data-driven collections. Results are sourced from /api/places,
 * never represented as live tickets, prices or bookable inventory.
 */
export default function CategoryPlaces({ type, places = [], openDetails, openPlace, openCoastalDetails, askQuestion, ratings = {}, myRatings = {}, onRate, session, onSignIn, registrationEnabled = true }) {
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
  const secularPlaces = coast ? [] : visible.filter(place => !getReligiousGroup(place))
  const religiousGroups = coast ? [] : RELIGIOUS_GROUP_ORDER.map(group => [group, visible.filter(place => getReligiousGroup(place) === group)]).filter(([, items]) => items.length)
  const coastalGuides = coast ? COASTAL_DESTINATIONS.filter(item =>
    [item.en, item.ar, item.regionEn, item.regionAr, item.spotEn, item.spotAr, item.noteEn, item.noteAr]
      .join(' ').toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())) : []
  const coastalEntries = coast ? [
    ...coastalGuides.map(item => ({ kind: 'guide', value: item, targetId: `coast:${item.id}` })),
    ...visible.map(item => ({ kind: 'place', value: item, targetId: item.id })),
  ] : []
  if (sort === 'rated') coastalEntries.sort((a, b) => {
    const first = ratings[a.targetId]
    const second = ratings[b.targetId]
    return (second?.count ? 1 : 0) - (first?.count ? 1 : 0)
      || (second?.average || 0) - (first?.average || 0)
      || (second?.count || 0) - (first?.count || 0)
  })
  const placeCards = (items, wrap = true) => {
    const cards = items.map(place => <article className="mg-place-card" key={place.id}>
      <button type="button" className="mg-place-photo" style={getLandmarkFraming(place.id)} aria-label={`${ar ? 'تفاصيل أكثر عن' : 'More details about'} ${placeName(place)}`} onClick={() => (openDetails || openPlace)?.(place)}><EditorialImage src={LANDMARK_MEDIA[place.id]} alt="" className="mg-place-img" /><span className="mg-place-symbol" aria-hidden="true">{coast && isSwimmingBeach(place) ? <Waves size={20} /> : <Landmark size={20} />}</span><span className="mg-image-more" aria-hidden="true">{ar ? 'تفاصيل أكثر' : 'More details'} <ArrowUpRight size={15} /></span></button>
      <div className="mg-place-content">
        <div className="mg-place-location"><MapPin size={13}/>{cityName(place.city)}</div>
        <h2>{placeName(place)}</h2>
        <p>{ar ? (place.summary_ar || place.description) : place.description}</p>
        <RatingWidget targetId={place.id} name={placeName(place)} summary={ratings[place.id]} yourRating={myRatings[place.id]} onRate={onRate} session={session} onSignIn={onSignIn} registrationEnabled={registrationEnabled} />
        <div className="mg-place-actions"><button type="button" onClick={() => (openDetails || openPlace)?.(place)}>{ar ? 'تفاصيل المكان' : 'View details'} <ArrowUpRight size={15}/></button><button type="button" title={ar ? 'اسأل المساعد' : 'Ask AI'} aria-label={`${ar ? 'اسأل المساعد عن' : 'Ask AI about'} ${placeName(place)}`} onClick={() => askQuestion(ar ? `احكيلي عن ${placeName(place)} وإزاي أضيفه لرحلتي؟` : `Tell me about ${place.name} and how to add it to my itinerary.`)}><MessageCircle size={17}/></button></div>
        <PhotoCredit id={place.id} ar={ar} />
      </div>
    </article>)
    return wrap ? <div className="mg-category-grid">{cards}</div> : cards
  }

  return <main className="mg-category-page">
    <section className="mg-category-hero container">
      <div className="mg-category-kicker">{coast ? (ar ? 'مصر على البحر' : 'EGYPT BY THE SEA') : (ar ? 'مصر عبر العصور' : 'EGYPT THROUGH THE AGES')}</div>
      <h1>{coast ? (ar ? 'الشواطئ والأماكن البحرية' : 'Beaches & coastal escapes') : (ar ? 'الأماكن الأثرية والتاريخية' : 'Historical places')}</h1>
      <p>{coast ? (ar ? 'استكشف الوجهات والشواطئ والأنشطة البحرية في مكان واحد. راجع تعليمات السباحة والدخول وحالة البحر قبل الزيارة.' : 'Explore beach destinations and coastal activities in one place. Check swimming rules, access and sea conditions before visiting.') : (ar ? 'اكتشف الأهرامات والمعابد والمتاحف وأشهر معالم الحضارة المصرية.' : 'Discover pyramids, temples, museums and the remarkable heritage of Egypt.')}</p>
      <label className="mg-category-search"><Search size={18} aria-hidden="true"/><span className="sr-only">{ar ? 'ابحث عن مكان' : 'Search places'}</span><input value={query} onChange={event => setQuery(event.target.value)} placeholder={ar ? 'ابحث عن مكان أو مدينة...' : 'Search places or cities...'} aria-label={ar ? 'ابحث عن مكان' : 'Search places'} /></label>
    </section>
    <div className="container mg-category-body">
      <DiscoveryNav current={type} />
      <div className="mg-category-count" role="status">{coast ? (ar ? `${coastalGuides.length + visible.length} مكان على البحر` : `${coastalGuides.length + visible.length} coastal places`) : (ar ? `${visible.length} مكان في الدليل` : `${visible.length} curated places`)}</div>
      {coast && (coastalGuides.length > 0 || visible.length > 0) && <section className="mg-coastal-guides" aria-labelledby="coastal-guides-title">
        <div className="mg-coastal-guides-head"><h2 id="coastal-guides-title">{ar ? 'الشواطئ والأماكن البحرية' : 'Beaches & coastal places'}</h2><label className="mg-coast-sort">{ar ? 'الترتيب' : 'Sort by'} <select value={sort} onChange={event => setSort(event.target.value)}><option value="editorial">{ar ? 'الترتيب المقترح' : 'Recommended order'}</option><option value="rated">{ar ? 'الأعلى تقييمًا' : 'Highest visitor rating'}</option></select></label></div>
        <div className="mg-coastal-guides-grid">{coastalEntries.map(({ kind, value: item, targetId }) => kind === 'guide' ? <article className="mg-coastal-guide" key={targetId}>
          <button type="button" className="mg-coastal-guide-image-button" aria-label={`${ar ? 'تفاصيل أكثر عن' : 'More details about'} ${ar ? item.ar : item.en}`} onClick={() => openCoastalDetails?.(item)}><img className="mg-coastal-guide-photo" src={COASTAL_MEDIA[item.id].photo} alt={ar ? COASTAL_MEDIA[item.id].ar : COASTAL_MEDIA[item.id].en} loading="lazy" decoding="async" /><span className="mg-image-more" aria-hidden="true">{ar ? 'تفاصيل أكثر' : 'More details'} <ArrowUpRight size={15} /></span></button>
          <span>{ar ? item.regionAr : item.regionEn}</span><h3>{ar ? item.ar : item.en}</h3><p className="mg-coastal-example"><strong>{ar ? 'مثال لشاطئ: ' : 'Beach example: '}</strong>{ar ? item.spotAr : item.spotEn}</p><p className="mg-coastal-note">{ar ? item.noteAr : item.noteEn}</p><RatingWidget targetId={`coast:${item.id}`} name={ar ? item.ar : item.en} summary={ratings[`coast:${item.id}`]} yourRating={myRatings[`coast:${item.id}`]} onRate={onRate} session={session} onSignIn={onSignIn} registrationEnabled={registrationEnabled} /><button type="button" className="mg-coastal-details-button" onClick={() => openCoastalDetails?.(item)}>{ar ? 'تفاصيل المكان' : 'View details'} <ArrowUpRight size={16} aria-hidden="true" /></button>
          <div className="mg-coastal-photo-credit">{ar ? 'الصورة: ' : 'Photo: '}<a href={COASTAL_MEDIA[item.id].source} target="_blank" rel="noopener noreferrer">{COASTAL_MEDIA[item.id].author}</a> · <a href={COASTAL_MEDIA[item.id].licenseUrl} target="_blank" rel="noopener noreferrer">{COASTAL_MEDIA[item.id].license}</a></div>
        </article> : placeCards([item], false)[0])}</div>
      </section>}
      {!coast && secularPlaces.length > 0 && placeCards(secularPlaces)}
      {!coast && religiousGroups.length > 0 && <section className="mg-religious-places" aria-labelledby="religious-places-title">
        <h2 id="religious-places-title">{ar ? 'دور العبادة التاريخية' : 'Historic places of worship'}</h2>
        {religiousGroups.map(([group, items]) => <section className="mg-religious-group" key={group} aria-labelledby={`religious-${group}`}>
          <h3 id={`religious-${group}`}>{ar ? ({ mosques: 'المساجد', churches: 'الكنائس والأديرة', synagogues: 'المعابد اليهودية' }[group]) : ({ mosques: 'Mosques', churches: 'Churches & monasteries', synagogues: 'Synagogues' }[group])}</h3>
          {placeCards(items)}
        </section>)}
      </section>}
      {!selection.length && !coastalGuides.length && !query.trim() && <p className="mg-category-empty">{ar ? 'بيانات الأماكن قيد التحميل. جرّب إعادة الاتصال بالخادم.' : 'The place catalogue is not available yet. Check your connection to the backend.'}</p>}
      {!visible.length && !coastalGuides.length && query.trim() && <p className="mg-category-empty">{ar ? 'مفيش أماكن مطابقة. جرّب بحث مختلف.' : 'No places match that search. Try another term.'}</p>}
    </div>
  </main>
}
