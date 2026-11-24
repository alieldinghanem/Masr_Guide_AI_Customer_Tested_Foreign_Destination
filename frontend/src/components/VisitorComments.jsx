import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { useI18n } from '../i18n'

export default function VisitorComments({ targetId, session, onSignIn, onPosted, registrationEnabled = true }) {
  const { lang } = useI18n()
  const ar = lang === 'ar'
  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)
  const [reportMessage, setReportMessage] = useState('')
  const [reportTarget, setReportTarget] = useState(null)
  const [reason, setReason] = useState('spam')
  const report = async event => {
    event.preventDefault(); setBusy(true); setReportMessage('')
    try {
      await api('/community/reports', { method: 'POST', token: session?.token, body: { target_id: targetId, comment_id: reportTarget, reason } })
      setReportTarget(null); setReportMessage(ar ? 'تم إرسال البلاغ للمراجعة.' : 'Report sent for review.')
    } catch { setReportMessage(ar ? 'تعذّر إرسال البلاغ. سجّل الدخول وحاول مجددًا.' : 'Could not report. Sign in and retry.') }
    finally { setBusy(false) }
  }

  useEffect(() => {
    let active = true
    setItems([]); setCount(0); setError(''); setLoading(true)
    api(`/ratings/${encodeURIComponent(targetId)}/comments`)
      .then(data => { if (active) { setItems(data.comments || []); setCount(data.count || 0) } })
      .catch(() => { if (active) setError('load') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [targetId, attempt])

  const submit = async event => {
    event.preventDefault()
    setBusy(true); setError(''); setSent(false)
    try {
      const data = await api(`/ratings/${encodeURIComponent(targetId)}/comments`, {
        method: 'POST', body: { comment: comment.trim() }, token: session?.token,
      })
      setItems(data.comments || []); setCount(data.count || 0); setComment(''); setSent(true)
      onPosted?.()
    } catch (err) {
      setError(err.status === 401 ? (ar ? 'انتهت جلسة الدخول. سجّل دخولك مرة ثانية.' : 'Your session expired. Please sign in again.') : err.status === 429 ? (ar ? 'طلبات كثيرة. حاول بعد دقيقة.' : 'Too many requests. Try again in a minute.')
        : (ar ? 'تعذّر إرسال التعليق. اكتب تعليقًا بدون روابط وحاول تاني.' : 'Could not post your comment. Write a comment without links, then retry.'))
    } finally { setBusy(false) }
  }

  return <section className="mg-visitor-comments" aria-labelledby={`comments-${targetId}`}>
    <h2 id={`comments-${targetId}`}>{ar ? 'تعليقات الزوار' : 'Visitor comments'} <small>{count}</small></h2>
    <p>{ar ? 'التعليقات من حسابات مسجّلة، لكن زيارات أصحابها غير موثّقة. يمكنك تعديل تعليقك من حسابك.' : 'Comments come from signed-in accounts, but visits are not verified. You can edit yours from your account.'}</p>
    {session?.token ? <form onSubmit={submit}>
      <label>{ar ? 'تعليقك عن المكان' : 'Your comment about this place'}<textarea value={comment} disabled={busy || loading} onChange={event => setComment(event.target.value)} required minLength={5} maxLength={500} rows={4} /></label>
      <button type="submit" disabled={busy || loading || comment.trim().length < 5}>{busy ? (ar ? 'جارٍ الإرسال...' : 'Posting...') : (ar ? 'انشر تعليقك' : 'Post comment')}</button>
    </form> : <p className="mg-review-signin">{ar ? 'سجّل دخولك بالبريد الإلكتروني لكتابة تعليق.' : 'Sign in with email to comment.'} <button type="button" onClick={onSignIn}>{ar ? 'تسجيل الدخول' : 'Sign in'}</button>{registrationEnabled === false && <small>{ar ? 'إنشاء حساب جديد متوقف مؤقتًا حتى يتوفر تخزين دائم.' : 'New registration is paused until durable storage is available.'}</small>}</p>}
    {error && <p role="alert" className="mg-comment-error">{error === 'load' ? (ar ? 'تعذّر تحميل التعليقات.' : 'Could not load comments.') : error}{error === 'load' && <button type="button" onClick={() => setAttempt(value => value + 1)}>{ar ? 'حاول مرة أخرى' : 'Try again'}</button>}</p>}
    {sent && <p role="status" className="mg-comment-success">{ar ? 'تم نشر تعليقك.' : 'Your comment is published.'}</p>}
    {reportMessage && <p role="status">{reportMessage}</p>}
    {reportTarget && <form onSubmit={report}><label>{ar ? 'سبب البلاغ' : 'Report reason'}<select value={reason} onChange={event => setReason(event.target.value)}>{['spam', 'abuse', 'unsafe', 'privacy', 'misinformation'].map((value, index) => <option key={value} value={value}>{ar ? ['رسائل مزعجة', 'إساءة', 'محتوى خطير', 'خصوصية', 'معلومات خاطئة'][index] : value}</option>)}</select></label><button type="submit" disabled={busy}>{ar ? 'إرسال البلاغ' : 'Send report'}</button><button type="button" onClick={() => setReportTarget(null)}>{ar ? 'إلغاء' : 'Cancel'}</button></form>}
    {loading && <p role="status">{ar ? 'جارٍ تحميل التعليقات…' : 'Loading comments…'}</p>}
    <div className="mg-comment-list">{items.length ? items.map((item, index) => <article key={`${item.name}-${item.updated_at}-${index}`}><strong>{ar ? item.name.replace(/^Traveler #/, 'مسافر #') : item.name}</strong><p>{item.comment}</p>{item.comment_id && <button type="button" onClick={() => session?.token ? setReportTarget(item.comment_id) : onSignIn?.()}>{ar ? 'إبلاغ' : 'Report'}</button>}</article>)
      : !loading && error !== 'load' && <p>{ar ? 'لا توجد تعليقات بعد. كن أول من يكتب تعليقًا.' : 'No comments yet. Be the first to comment.'}</p>}</div>
  </section>
}
