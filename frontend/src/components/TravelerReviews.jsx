import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Compass, ShieldCheck } from 'lucide-react'
import { api } from '../api'
import { useI18n } from '../i18n'
import { COASTAL_DESTINATIONS } from '../coastalDestinations'
import RatingWidget from './RatingWidget'
import VisitorComments from './VisitorComments'

export default function TravelerReviews({ onExplore, places = [], ratings = {}, myRatings = {}, onRate, temporaryStorage = false, session, onSignIn, registrationEnabled = true }) {
  const { t, lang, placeName } = useI18n()
  const ar = lang === 'ar'
  const [chosen, setChosen] = useState('')
  const [recent, setRecent] = useState([])
  const [feedState, setFeedState] = useState('loading')
  const request = useRef(0)
  const invalidate = useCallback(() => { request.current++ }, [])
  const refreshRecent = useCallback(() => {
    const current = ++request.current
    setFeedState('loading')
    api('/ratings/recent-comments').then(data => { if (current === request.current) { setRecent(data.comments || []); setFeedState('ready') } })
      .catch(() => { if (current === request.current) setFeedState('error') })
  }, [])
  useEffect(() => { refreshRecent(); return invalidate }, [refreshRecent, invalidate])
  const catalog = places.map(place => ({ id: place.id, label: placeName(place) }))
  const coast = COASTAL_DESTINATIONS.map(item => ({ id: `coast:${item.id}`, label: ar ? item.ar : item.en }))
  const targets = [...coast, ...catalog]
  const selectedId = targets.some(item => item.id === chosen) ? chosen : (targets[0]?.id || '')
  const selected = targets.find(item => item.id === selectedId)
  const ranked = targets.filter(item => ratings[item.id]?.count).sort((a, b) =>
    ratings[b.id].average - ratings[a.id].average || ratings[b.id].count - ratings[a.id].count || a.label.localeCompare(b.label, lang))
  const recentKnown = recent.filter(item => targets.some(target => target.id === item.target_id))

  return <main className="page-wrap container traveler-reviews">
    <span className="eyebrow">{t('reviews.eyebrow')}</span>
    <h1>{t('reviews.title')}</h1>
    <p className="reviews-intro">{t('reviews.intro')}</p>
    <div className="reviews-disclosure"><ShieldCheck size={18} aria-hidden="true" />{t('reviews.disclosure')}</div>
    {temporaryStorage && <p className="reviews-storage-note">{t('reviews.storage')}</p>}
    <section className="community-feed" aria-labelledby="community-feed-title">
      <h2 id="community-feed-title">{t('reviews.feed.title')}</h2>
      {feedState === 'loading' && <p role="status">{ar ? 'جارٍ تحميل المشاركات…' : 'Loading traveler tips…'}</p>}
      {feedState === 'error' && <div role="alert"><p>{ar ? 'تعذر تحميل المشاركات.' : 'Could not load traveler tips.'}</p><button type="button" onClick={refreshRecent}>{ar ? 'حاول مرة أخرى' : 'Try again'}</button></div>}
      {recentKnown.length ? <div className="community-feed-grid">{recentKnown.map((item, index) => <article key={`${item.target_id}-${item.updated_at}-${index}`}>
        <span>{ar ? item.name.replace(/^Traveler #/, 'مسافر #') : item.name}</span>
        <h3>{targets.find(target => target.id === item.target_id)?.label}</h3>
        <p>{item.comment}</p>
        <button type="button" onClick={() => { setChosen(item.target_id); document.getElementById('reviews-rate-title')?.scrollIntoView?.({ behavior: 'smooth' }) }}>{t('reviews.feed.open')}</button>
      </article>)}</div> : feedState === 'ready' && <p className="community-feed-empty">{t('reviews.feed.empty')}</p>}
    </section>
    <section className="reviews-rate" aria-labelledby="reviews-rate-title">
      <h2 id="reviews-rate-title">{t('reviews.rate.title')}</h2>
      <label>{t('reviews.rate.choose')}
        <select value={selectedId} onChange={event => setChosen(event.target.value)}>
          <optgroup label={t('reviews.coast')}>{coast.map(item => <option value={item.id} key={item.id}>{item.label}</option>)}</optgroup>
          <optgroup label={t('reviews.places')}>{catalog.map(item => <option value={item.id} key={item.id}>{item.label}</option>)}</optgroup>
        </select>
      </label>
      {selected && <><RatingWidget targetId={selected.id} name={selected.label} summary={ratings[selected.id]} yourRating={myRatings[selected.id]} onRate={onRate} session={session} onSignIn={onSignIn} registrationEnabled={registrationEnabled} /><VisitorComments key={selected.id + ':' + (session?.token || 'guest')} targetId={selected.id} session={session} onSignIn={onSignIn} onPosted={refreshRecent} registrationEnabled={registrationEnabled} /></>}
    </section>
    <section className="reviews-rank" aria-labelledby="reviews-rank-title">
      <h2 id="reviews-rank-title">{t('reviews.rank.title')}</h2>
      {ranked.length ? <ol>{ranked.map(item => <li key={item.id}><span>{item.label}</span><strong>{ratings[item.id].average} / 5</strong><small>{t('reviews.count', { n: ratings[item.id].count })}</small></li>)}</ol>
        : <div className="reviews-empty"><h3>{t('reviews.empty.title')}</h3><p>{t('reviews.empty.body')}</p><button type="button" className="btn primary" onClick={onExplore}><Compass size={17} aria-hidden="true" />{t('reviews.explore')}</button></div>}
    </section>
  </main>
}
