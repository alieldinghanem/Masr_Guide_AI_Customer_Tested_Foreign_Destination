import React, { useEffect, useState } from 'react'
import { Star } from 'lucide-react'
import { useI18n } from '../i18n'

const storedRating = targetId => {
  try { return Number(localStorage.getItem(`masr-guide-rating:${targetId}`)) || 0 }
  catch { return 0 }
}

export default function RatingWidget({ targetId, name, summary, onRate }) {
  const { lang } = useI18n()
  const ar = lang === 'ar'
  const [selected, setSelected] = useState(() => storedRating(targetId))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { setSelected(storedRating(targetId)); setError('') }, [targetId])

  const submit = async stars => {
    setBusy(true); setError('')
    try { await onRate(targetId, stars); setSelected(stars) }
    catch { setError(ar ? 'تعذّر حفظ تقييمك. جرّب مرة تانية.' : 'Could not save your rating. Please try again.') }
    finally { setBusy(false) }
  }

  return <div className="mg-rating-widget">
    <div className="mg-rating-summary" aria-live="polite">{summary?.count
      ? (ar ? `${summary.average} من 5 · ${summary.count} تقييم` : `${summary.average} / 5 · ${summary.count} rating${summary.count === 1 ? '' : 's'}`)
      : (ar ? 'لسه مفيش تقييمات' : 'No ratings yet')}</div>
    <div className="mg-rating-stars" role="group" aria-label={ar ? `قيّم ${name}` : `Rate ${name}`}>
      {[1, 2, 3, 4, 5].map(stars => <button type="button" key={stars} disabled={busy || !onRate} aria-label={ar ? `قيّم ${name} ${stars} من 5` : `Rate ${name} ${stars} out of 5`} aria-pressed={selected === stars} title={ar ? `${stars} من 5` : `${stars} out of 5`} onClick={() => submit(stars)}>
        <Star size={19} fill={stars <= selected ? 'currentColor' : 'none'} aria-hidden="true" />
      </button>)}
    </div>
    {selected > 0 && <span className="mg-rating-yours">{ar ? `تقييمك: ${selected} من 5` : `Your rating: ${selected} / 5`}</span>}
    {error && <p role="alert" className="mg-rating-error">{error}</p>}
  </div>
}
