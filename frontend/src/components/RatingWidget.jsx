import React, { useEffect, useState } from 'react'
import { Star } from 'lucide-react'
import { useI18n } from '../i18n'

export default function RatingWidget({ targetId, name, summary, yourRating = 0, onRate, session, onSignIn, registrationEnabled = true }) {
  const { lang } = useI18n()
  const ar = lang === 'ar'
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { setError('') }, [targetId, session?.user?.id])

  const submit = async stars => {
    setBusy(true); setError('')
    try { await onRate(targetId, stars) }
    catch { setError(ar ? 'تعذّر حفظ تقييمك. جرّب مرة تانية.' : 'Could not save your rating. Please try again.') }
    finally { setBusy(false) }
  }

  return <div className="mg-rating-widget">
    <div className="mg-rating-summary" aria-live="polite">{summary?.count
      ? (ar ? `${summary.average} من 5 · ${summary.count} تقييم` : `${summary.average} / 5 · ${summary.count} rating${summary.count === 1 ? '' : 's'}`)
      : (ar ? 'لسه مفيش تقييمات' : 'No ratings yet')}</div>
    <div className="mg-rating-stars" role="group" aria-label={ar ? `قيّم ${name}` : `Rate ${name}`}>
      {[1, 2, 3, 4, 5].map(stars => <button type="button" key={stars} disabled={busy || !onRate || !session?.token} aria-label={ar ? `قيّم ${name} ${stars} من 5` : `Rate ${name} ${stars} out of 5`} aria-pressed={yourRating === stars} title={ar ? `${stars} من 5` : `${stars} out of 5`} onClick={() => submit(stars)}>
        <Star size={19} fill={stars <= yourRating ? 'currentColor' : 'none'} aria-hidden="true" />
      </button>)}
    </div>
    {!session?.token && <p className="mg-review-signin">{ar ? 'سجّل دخولك بالبريد الإلكتروني للتقييم.' : 'Sign in with email to rate.'} <button type="button" onClick={onSignIn}>{ar ? 'تسجيل الدخول' : 'Sign in'}</button>{!registrationEnabled && <small>{ar ? 'إنشاء حساب جديد متوقف مؤقتًا حتى يتوفر تخزين دائم.' : 'New registration is paused until durable storage is available.'}</small>}</p>}
    {yourRating > 0 && <span className="mg-rating-yours">{ar ? `تقييمك: ${yourRating} من 5` : `Your rating: ${yourRating} / 5`}</span>}
    {error && <p role="alert" className="mg-rating-error">{error}</p>}
  </div>
}
