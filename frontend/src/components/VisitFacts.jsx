import React from 'react'

// Official links reviewed on 2026-11-26; not live prices or schedules.
const TICKETS = { 'grand-egyptian-museum': 'https://tickets.gem.eg/', nmec: 'https://egymonuments.com/nmec' }

export default function VisitFacts({ place, ar = false }) {
  return <section className="visit-facts" aria-label={ar ? 'خطط زيارتك' : 'Plan your visit'}>
    <h2>{ar ? 'خطط زيارتك' : 'Plan your visit'}</h2>
    <dl>
      <div><dt>{ar ? 'مدة الزيارة المقترحة' : 'Suggested visit duration'}</dt><dd>{place.visit_minutes ? `${place.visit_minutes} ${ar ? 'دقيقة تقريبًا' : 'minutes, approximately'}` : (ar ? 'تُحدد مع المكان' : 'Confirm with the venue')}</dd></div>
      <div><dt>{ar ? 'مع الأطفال' : 'With children'}</dt><dd>{place.family_friendly ? (ar ? 'مُصنّف للعائلات في دليلنا؛ أكّد قيود الأعمار والمرافق مع المكان.' : 'Family-tagged in our guide; confirm age restrictions and facilities with the venue.') : (ar ? 'اسأل المكان عن ملاءمة الزيارة لأعمار أطفالك.' : 'Ask the venue whether this visit suits your children’s ages.')}</dd></div>
      <div><dt>{ar ? 'المواعيد والتذاكر' : 'Hours and admission'}</dt><dd>{ar ? 'راجع تاريخ زيارتك والجنسية والفئة العمرية في المصدر؛ لا نعرض أسعارًا حية.' : 'Check your visit date, nationality and age category with the source; live prices are not provided.'}</dd></div>
      <div><dt>{ar ? 'الوصول والمدخل' : 'Getting there and entry'}</dt><dd>{ar ? 'الخريطة تحدد موقع المكان؛ أكّد مدخل الزوار ونقطة النزول مع المشغّل.' : 'The map locates the place; confirm the visitor entrance and drop-off point with its operator.'}</dd></div>
    </dl>
    {TICKETS[place.id] && <><a className="btn secondary" href={TICKETS[place.id]} target="_blank" rel="noopener noreferrer">{ar ? 'التذاكر عبر الموقع الرسمي' : 'Official ticketing website'}</a><small>{ar ? 'مراجعة رابط التذاكر: 26 نوفمبر 2026' : 'Ticket link reviewed: 26 November 2026'}</small></>}
  </section>
}
