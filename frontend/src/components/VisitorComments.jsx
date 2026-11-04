import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { ratingVisitorId } from '../ratingIdentity'
import { useI18n } from '../i18n'

export default function VisitorComments({ targetId }) {
  const { lang } = useI18n()
  const ar = lang === 'ar'
  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const [name, setName] = useState('')
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)

  useEffect(() => {
    let active = true
    setItems([]); setCount(0); setComment(''); setError(''); setSent(false)
    api(`/ratings/${encodeURIComponent(targetId)}/comments`)
      .then(data => { if (active) { setItems(data.comments || []); setCount(data.count || 0) } })
      .catch(() => { if (active) setError(ar ? 'تعذّر تحميل التعليقات.' : 'Could not load comments.') })
    return () => { active = false }
  }, [targetId, ar])

  const submit = async event => {
    event.preventDefault()
    setBusy(true); setError(''); setSent(false)
    try {
      const data = await api(`/ratings/${encodeURIComponent(targetId)}/comments`, {
        method: 'POST', body: { visitor_id: ratingVisitorId(), name: name.trim(), comment: comment.trim() },
      })
      setItems(data.comments || []); setCount(data.count || 0); setComment(''); setSent(true)
    } catch (err) {
      setError(err.status === 429 ? (ar ? 'طلبات كثيرة. حاول بعد دقيقة.' : 'Too many requests. Try again in a minute.')
        : (ar ? 'تعذّر إرسال التعليق. اكتب اسمًا وتعليقًا بدون روابط وحاول تاني.' : 'Could not post your comment. Use a name and comment without links, then retry.'))
    } finally { setBusy(false) }
  }

  return <section className="mg-visitor-comments" aria-labelledby={`comments-${targetId}`}>
    <h2 id={`comments-${targetId}`}>{ar ? 'تعليقات الزوار' : 'Visitor comments'} <small>{count}</small></h2>
    <p>{ar ? 'تعليقات الزوار غير موثّقة. يمكنك تعديل تعليقك بإرساله مرة ثانية من نفس المتصفح.' : 'Visitor comments are not verified. You can edit yours by posting again from this browser.'}</p>
    <form onSubmit={submit}>
      <label>{ar ? 'اسمك المعروض' : 'Display name'}<input value={name} onChange={event => setName(event.target.value)} required minLength={2} maxLength={40} autoComplete="nickname" /></label>
      <label>{ar ? 'تعليقك عن المكان' : 'Your comment about this place'}<textarea value={comment} onChange={event => setComment(event.target.value)} required minLength={5} maxLength={500} rows={4} /></label>
      <button type="submit" disabled={busy}>{busy ? (ar ? 'جارٍ الإرسال...' : 'Posting...') : (ar ? 'انشر تعليقك' : 'Post comment')}</button>
    </form>
    {error && <p role="alert" className="mg-comment-error">{error}</p>}
    {sent && <p role="status" className="mg-comment-success">{ar ? 'تم نشر تعليقك.' : 'Your comment is published.'}</p>}
    <div className="mg-comment-list">{items.length ? items.map((item, index) => <article key={`${item.name}-${item.updated_at}-${index}`}><strong>{item.name}</strong><p>{item.comment}</p></article>)
      : <p>{ar ? 'لا توجد تعليقات بعد. كن أول من يكتب تعليقًا.' : 'No comments yet. Be the first to comment.'}</p>}</div>
  </section>
}
