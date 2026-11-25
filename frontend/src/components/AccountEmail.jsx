import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { useI18n } from '../i18n'

export default function AccountEmail({ session, onPasswordReset }) {
  const { lang } = useI18n()
  const ar = lang === 'ar'
  const [capabilities, setCapabilities] = useState(null)
  const [verified, setVerified] = useState(false)
  const [link] = useState(() => {
    const query = new URLSearchParams(window.location.hash.split('?')[1] || '')
    return { action: query.get('action'), token: query.get('token') }
  })
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [finished, setFinished] = useState(false)
  useEffect(() => {
    if (link.token) window.history.replaceState(null, '', '#/account')
    let active = true
    api('/auth/email-capabilities').then(data => { if (active) setCapabilities(data) }).catch(() => {})
    if (session?.token) api('/auth/email-status', { token: session.token }).then(data => { if (active) setVerified(data.verified) }).catch(() => {})
    return () => { active = false }
  }, [session?.token, link.token])
  const perform = async (path, body) => {
    if (busy) return
    setBusy(true); setMessage('')
    try {
      await api(`/auth/${path}`, { method: 'POST', body, token: session?.token })
      if (path === 'password-reset/confirm') {
        setPassword(''); setConfirmation(''); setFinished(true); onPasswordReset?.()
        setMessage(ar ? 'تم تغيير كلمة المرور وإنهاء جلسات الدخول القديمة. سجّل الدخول مجددًا.' : 'Password changed. Old sessions ended. Sign in again.')
      } else if (path === 'email-verification/confirm') {
        setVerified(true); setFinished(true)
        setMessage(ar ? 'تم تأكيد البريد الإلكتروني.' : 'Email verified.')
      } else setMessage(ar ? 'إذا كان الحساب مؤهلًا، راجع صندوق البريد والبريد غير المرغوب فيه. لا تشارك الرابط.' : 'If the account is eligible, check its inbox and spam folder. Do not share the link.')
    } catch (error) {
      setMessage(error.status === 503 ? (ar ? 'إرسال البريد لم يُفعّل بعد.' : 'Account email is not configured yet.')
        : error.status === 429 ? (ar ? 'انتظر قليلًا قبل المحاولة مجددًا.' : 'Wait before trying again.')
          : (ar ? 'تعذّر إتمام الطلب. قد يكون الرابط منتهيًا أو مستخدمًا؛ اطلب رابطًا جديدًا.' : 'Could not complete the request. The link may be expired or used; request a new one.'))
    } finally { setBusy(false) }
  }
  return <section className="account-panel" aria-label={ar ? 'أمان البريد والحساب' : 'Email and account security'}>
    <h2>{ar ? 'أمان حسابك' : 'Account security'}</h2>
    {link.token && !finished && link.action === 'reset' && <form onSubmit={event => {
      event.preventDefault()
      if (password !== confirmation) {
        setMessage(ar ? 'كلمتا المرور غير متطابقتين.' : 'Passwords do not match.')
        return
      }
      perform('password-reset/confirm', { token: link.token, password })
    }}>
      <label>{ar ? 'كلمة المرور الجديدة' : 'New password'}<input type="password" required minLength={12} maxLength={128} autoComplete="new-password" value={password} onChange={event => setPassword(event.target.value)} /></label>
      <label>{ar ? 'تأكيد كلمة المرور الجديدة' : 'Confirm new password'}<input type="password" required minLength={12} maxLength={128} autoComplete="new-password" value={confirmation} onChange={event => setConfirmation(event.target.value)} /></label>
      <button type="submit" disabled={busy}>{ar ? 'حفظ كلمة المرور الجديدة' : 'Set new password'}</button>
    </form>}
    {link.token && !finished && link.action === 'verify' && <button type="button" disabled={busy} onClick={() => perform('email-verification/confirm', { token: link.token })}>{ar ? 'تأكيد البريد' : 'Confirm email'}</button>}
    {session?.token ? <><p>{verified ? (ar ? 'البريد مؤكّد' : 'Email verified') : (ar ? 'البريد غير مؤكّد بعد' : 'Email not yet verified')}</p>
      {!verified && capabilities?.email_verification && <button type="button" disabled={busy} onClick={() => perform('email-verification/request')}>{ar ? 'إرسال رابط التأكيد' : 'Send verification link'}</button>}</>
      : capabilities?.password_recovery ? <details><summary>{ar ? 'نسيت كلمة المرور؟' : 'Forgot password?'}</summary><form onSubmit={event => { event.preventDefault(); perform('password-reset/request', { email }) }}>
        <label>{ar ? 'بريد حسابك' : 'Your account email'}<input type="email" required maxLength={254} autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} /></label>
        <button type="submit" disabled={busy}>{ar ? 'طلب رابط الاستعادة' : 'Request reset link'}</button>
      </form></details> : <p>{ar ? 'استعادة كلمة المرور بالبريد لم تُفعّل بعد.' : 'Email password recovery is not available yet.'}</p>}
    {message && <p role="status">{message}</p>}
  </section>
}
