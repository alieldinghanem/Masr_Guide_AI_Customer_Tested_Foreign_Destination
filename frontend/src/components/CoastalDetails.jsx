import React from 'react'
import { ArrowLeft, Bookmark, MapPin, MessageCircle } from 'lucide-react'
import { useI18n } from '../i18n'
import { COASTAL_MEDIA } from '../coastalMedia'
import RatingWidget from './RatingWidget'
import VisitorComments from './VisitorComments'

export default function CoastalDetails({ destination, onBack, askQuestion, savedIds = [], toggleSaved = () => {}, ratings = {}, myRatings = {}, onRate, temporaryStorage = false, session, onSignIn, registrationEnabled = true }) {
  const { lang, t } = useI18n()
  const ar = lang === 'ar'
  if (!destination) return <main className="container place-full-page"><h1>{ar ? 'الوجهة غير موجودة في الدليل' : 'Destination not found in the guide'}</h1><button type="button" onClick={onBack}>{ar ? 'العودة إلى الشواطئ' : 'Back to beaches'}</button></main>
  const title = ar ? destination.ar : destination.en
  const targetId = `coast:${destination.id}`
  const media = COASTAL_MEDIA[destination.id]
  return <main className="container place-full-page">
    <button type="button" className="place-back" onClick={onBack}><ArrowLeft size={17} aria-hidden="true" />{ar ? 'الشواطئ والأماكن البحرية' : 'Beaches & coastal places'}</button>
    <div className="place-full-hero">
      <div className="place-full-photo"><img src={media.photo} alt={ar ? media.ar : media.en} className="mg-place-img" /></div>
      <div className="place-full-intro"><span><MapPin size={16} aria-hidden="true" />{ar ? destination.regionAr : destination.regionEn}</span><h1>{title}</h1><p><strong>{ar ? 'مثال لشاطئ: ' : 'Beach example: '}</strong>{ar ? destination.spotAr : destination.spotEn}</p><p>{ar ? destination.noteAr : destination.noteEn}</p>
        <div className="mg-coastal-photo-credit">{ar ? 'الصورة: ' : 'Photo: '}<a href={media.source} target="_blank" rel="noopener noreferrer">{media.author}</a> · <a href={media.licenseUrl} target="_blank" rel="noopener noreferrer">{media.license}</a></div>
        <div className="place-full-actions"><button type="button" onClick={() => askQuestion(ar ? `احكيلي عن ${title} وأفضل شواطئها وإزاي أضيفها لرحلتي؟` : `Tell me about ${title}, its beaches, and how to add it to my itinerary.`)}><MessageCircle size={17} />{ar ? 'اسأل المرشد' : 'Ask AI'}</button></div>
      </div>
    </div>
    <section className="place-rating-top"><h2>{ar ? 'قيّم المكان بالنجوم' : 'Rate this place'}</h2><p>{ar ? 'اختر من نجمة إلى 5 نجوم. يلزم حساب، لكن الزيارات غير موثّقة.' : 'Choose 1 to 5 stars. An account is required, but visits are not verified.'}</p><RatingWidget targetId={targetId} name={title} summary={ratings[targetId]} yourRating={myRatings[targetId]} onRate={onRate} session={session} onSignIn={onSignIn} registrationEnabled={registrationEnabled} />{temporaryStorage && <p className="reviews-storage-note">{t('reviews.storage')}</p>}</section>
    <div className="place-full-grid"><section><h2>{ar ? 'عن المكان' : 'About this place'}</h2><p>{ar ? (destination.aboutAr || destination.noteAr) : (destination.aboutEn || destination.noteEn)}</p>
      {destination.visitAr && <p>{ar ? destination.visitAr : destination.visitEn}</p>}
      <button type="button" aria-pressed={savedIds.includes(targetId)} onClick={() => toggleSaved(targetId)}><Bookmark size={16} />{savedIds.includes(targetId) ? (ar ? 'إزالة من المفضلة' : 'Remove from saved') : (ar ? 'حفظ المكان' : 'Save this place')}</button>
      <p className="place-unverified">{ar ? 'راجع إمكانية الدخول وتعليمات السباحة وحالة البحر محليًا قبل الزيارة.' : 'Check access, swimming rules and sea conditions locally before visiting.'}</p>
      <iframe title={ar ? `خريطة بحث عن ${title}` : `Map search for ${title}`} src={`https://maps.google.com/maps?q=${encodeURIComponent(`${destination.spotEn}, ${destination.en}, Egypt`)}&output=embed`} loading="lazy" referrerPolicy="no-referrer" style={{ width: '100%', minHeight: 260, border: 0 }} />
      <small>{ar ? 'الخريطة للبحث عن المنطقة؛ أكد مدخل الشاطئ مع الجهة المشغلة.' : 'Map searches the area; confirm the beach entrance with its operator.'}</small>
    </section></div>
    <VisitorComments targetId={targetId} session={session} onSignIn={onSignIn} registrationEnabled={registrationEnabled} />
  </main>
}
