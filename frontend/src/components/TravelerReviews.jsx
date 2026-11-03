import React from 'react'
import { Compass, MessageSquare, ShieldCheck } from 'lucide-react'
import { useI18n } from '../i18n'

export default function TravelerReviews({ onExplore }) {
  const { t } = useI18n()
  return <main className="page-wrap container traveler-reviews">
    <span className="eyebrow">{t('reviews.eyebrow')}</span>
    <h1>{t('reviews.title')}</h1>
    <p className="reviews-intro">{t('reviews.intro')}</p>
    <section className="reviews-empty" aria-labelledby="reviews-empty-title">
      <MessageSquare size={30} aria-hidden="true" />
      <h2 id="reviews-empty-title">{t('reviews.empty.title')}</h2>
      <p>{t('reviews.empty.body')}</p>
      <div className="reviews-disclosure"><ShieldCheck size={18} aria-hidden="true" />{t('reviews.disclosure')}</div>
      <button type="button" className="btn primary" onClick={onExplore}><Compass size={17} aria-hidden="true" />{t('reviews.explore')}</button>
    </section>
  </main>
}
