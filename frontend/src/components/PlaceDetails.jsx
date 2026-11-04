import React from 'react'
import { ArrowLeft, Bookmark, BookmarkCheck, ExternalLink, MapPin, MessageCircle } from 'lucide-react'
import { useI18n } from '../i18n'
import { getMapUrl } from './Common'
import { EditorialImage, LANDMARK_MEDIA, PhotoCredit, getLandmarkFraming } from './EditorialMedia'
import RatingWidget from './RatingWidget'
import VisitorComments from './VisitorComments'

export default function PlaceDetails({ place, onBack, backLabel, askQuestion, saved, toggleSaved, ratings = {}, myRatings = {}, onRate, temporaryStorage = false, session, onSignIn, registrationEnabled = true }) {
  const { t, lang, placeName, placeSummary, cityName, category } = useI18n()
  const ar = lang === 'ar'
  if (!place) return <main className="container place-full-page"><h1>{ar ? 'المكان غير موجود في الدليل' : 'Place not found in the guide'}</h1><button type="button" onClick={onBack}>{ar ? 'ارجع لاستكشاف مصر' : 'Back to Explore Egypt'}</button></main>
  const title = placeName(place)
  const media = LANDMARK_MEDIA[place.id]
  return <main className="container place-full-page">
    <button type="button" className="place-back" onClick={onBack}><ArrowLeft size={17} aria-hidden="true" />{backLabel || (ar ? 'استكشف مصر' : 'Explore Egypt')}</button>
    <div className="place-full-hero">
      <div className="place-full-photo" style={getLandmarkFraming(place.id)}>{media ? <EditorialImage src={media} alt={title} className="mg-place-img" /> : <div className="place-no-photo">{ar ? 'لا توجد صورة موثقة لهذا المكان' : 'No verified photo available'}</div>}</div>
      <div className="place-full-intro"><span><MapPin size={16} aria-hidden="true" />{cityName(place.city)} · {category(place.category)}</span><h1>{title}</h1><p>{placeSummary(place)}</p>
        <PhotoCredit id={place.id} ar={ar} />
        <div className="place-full-actions"><button type="button" aria-pressed={saved} onClick={() => toggleSaved(place.id)}>{saved ? <BookmarkCheck size={17} /> : <Bookmark size={17} />}{ar ? (saved ? 'إزالة من المحفوظات' : 'احفظ المكان') : (saved ? 'Remove saved place' : 'Save place')}</button><button type="button" onClick={() => askQuestion(ar ? `احكيلي عن ${title} وإزاي أضيفه لرحلتي؟` : `Tell me about ${title} and how to add it to my itinerary.`)}><MessageCircle size={17} />{ar ? 'اسأل المرشد' : 'Ask AI'}</button></div>
      </div>
    </div>
    <section className="place-rating-top"><h2>{ar ? 'قيّم المكان بالنجوم' : 'Rate this place'}</h2><p>{ar ? 'اختر من نجمة إلى 5 نجوم. يلزم حساب، لكن الزيارات غير موثّقة.' : 'Choose 1 to 5 stars. An account is required, but visits are not verified.'}</p><RatingWidget targetId={place.id} name={title} summary={ratings[place.id]} yourRating={myRatings[place.id]} onRate={onRate} session={session} onSignIn={onSignIn} registrationEnabled={registrationEnabled} />{temporaryStorage && <p className="reviews-storage-note">{t('reviews.storage')}</p>}</section>
    <div className="place-full-grid"><section><h2>{ar ? 'عن المكان' : 'About this place'}</h2><p>{placeSummary(place)}</p>{!ar && place.details && <p>{place.details}</p>}{(ar ? place.tip_ar : place.tip) && <div className="place-advice"><strong>{ar ? 'نصيحة للزيارة' : 'Visiting advice'}</strong><p>{ar ? place.tip_ar : place.tip}</p></div>}<p className="place-unverified">{ar ? 'تحقق من المواعيد والأسعار وإمكانية الوصول من الجهة الرسمية قبل الزيارة.' : 'Check hours, prices and accessibility with the official venue before visiting.'}</p><a href={place.source_url} target="_blank" rel="noopener noreferrer">{ar ? 'مرجع المكان' : 'Place reference'} <ExternalLink size={15} aria-hidden="true" /></a></section>
      <section><h2>{ar ? 'الموقع على الخريطة' : 'Location on map'}</h2><iframe title={ar ? `خريطة ${title}` : `Map of ${title}`} src={getMapUrl(place)} loading="lazy" referrerPolicy="no-referrer" /></section></div>
    <VisitorComments targetId={place.id} session={session} onSignIn={onSignIn} registrationEnabled={registrationEnabled} />
  </main>
}
