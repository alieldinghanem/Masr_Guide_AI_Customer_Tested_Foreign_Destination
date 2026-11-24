import React, { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useI18n } from '../i18n'

let sdkPromise
function loadSdk() {
  if (window.google?.accounts?.id) return Promise.resolve()
  if (sdkPromise) return sdkPromise
  sdkPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    const timeout = setTimeout(() => { script.remove(); reject(new Error('Google library timeout')) }, 12000)
    script.onload = () => { clearTimeout(timeout); window.google?.accounts?.id ? resolve() : reject(new Error('Google library unavailable')) }
    script.onerror = () => { clearTimeout(timeout); script.remove(); reject(new Error('Google library unavailable')) }
    document.head.append(script)
  }).catch(error => { sdkPromise = null; throw error })
  return sdkPromise
}

export default function GoogleSignIn({ onSuccess, purpose = 'login', token, disabled = false, onBusyChange }) {
  const { lang } = useI18n()
  const ar = lang === 'ar'
  const container = useRef(null)
  const success = useRef(onSuccess)
  const busyChange = useRef(onBusyChange)
  const disabledRef = useRef(disabled)
  success.current = onSuccess; busyChange.current = onBusyChange; disabledRef.current = disabled
  const [state, setState] = useState('loading')
  const [attempt, setAttempt] = useState(0)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(null)
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [attempted, setAttempted] = useState(false)
  const exchange = useRef(null)
  const sending = useRef(false)

  useEffect(() => {
    let active = true
    setState('loading'); setError(''); setPending(null); setPassword('')
    exchange.current = async (credential, nonce, existingPassword) => {
      if (!active || sending.current) return
      sending.current = true; setAttempted(true); setBusy(true); busyChange.current?.(true); setError('')
      try {
        const data = await api(purpose === 'delete' ? '/auth/google/reauth-delete' : '/auth/google', {
          method: 'POST', token, body: { credential, nonce, ...(existingPassword ? { existing_password: existingPassword } : {}) }
        })
        if (!active) return
        setPending(null); setPassword(''); setState('done'); success.current?.(data)
      } catch (failure) {
        if (!active) return
        if (failure.status === 428 && purpose === 'login') { setPending({ credential, nonce }); setState('link') }
        else if (failure.status === 403 && existingPassword) setError('password')
        else { setError(failure.status === 422 ? 'external' : failure.status === 429 ? 'rate' : 'failed'); setState('error') }
      } finally {
        sending.current = false
        if (active) setBusy(false)
        busyChange.current?.(false)
      }
    }
    const start = async () => {
      try {
        const config = await api('/auth/google/config')
        if (!active) return
        if (!config.enabled || !config.client_id) { setState('disabled'); return }
        await loadSdk()
        if (!active) return
        const challenge = await api('/auth/google/challenge', { method: 'POST', token, body: { purpose } })
        if (!active) return
        window.google.accounts.id.initialize({ client_id: config.client_id, nonce: challenge.nonce, auto_select: false,
          callback: response => { if (active && !disabledRef.current && response.credential) exchange.current?.(response.credential, challenge.nonce) } })
        setState('ready')
      } catch { if (active) { setState('error'); setError('failed') } }
    }
    start()
    return () => { active = false; exchange.current = null }
  }, [attempt, purpose, token])

  useEffect(() => {
    if (state !== 'ready' || !container.current || !window.google?.accounts?.id) return
    container.current.replaceChildren()
    window.google.accounts.id.renderButton(container.current, { type: 'standard', theme: 'outline', size: 'large',
      text: 'continue_with', shape: 'rectangular', locale: lang, width: 280 })
  }, [state, lang])

  const messages = {
    password: ar ? 'كلمة المرور الحالية غير صحيحة. حاول مرة أخرى.' : 'The current password is incorrect. Try again.',
    external: ar ? 'لو حساب Google يستخدم بريدًا خارجيًا، أنشئ حسابًا بالبريد أولًا ثم اربطه بكلمة مروره.' : 'For a Google account using an external email provider, register with email first, then link it with its password.',
    rate: ar ? 'طلبات كثيرة. انتظر دقيقة وحاول مرة أخرى.' : 'Too many attempts. Wait a minute and retry.',
    failed: ar ? 'تعذر إتمام الدخول عبر Google. حاول مرة أخرى.' : 'Could not complete Google sign-in. Please retry.',
  }
  return <section className="google-signin" aria-label={ar ? 'الدخول عبر Google' : 'Google sign-in'}>
    <div ref={container} className="google-sdk-button" hidden={state !== 'ready' || busy || disabled} />
    {(state === 'loading' || busy) && <p role="status">{ar ? 'جارٍ تجهيز الدخول عبر Google…' : 'Preparing Google sign-in…'}</p>}
    {state === 'disabled' && <><button type="button" disabled className="btn secondary">{ar ? 'المتابعة بحساب Google' : 'Continue with Google'}</button><small>{ar ? 'الدخول عبر Google لم يُفعّل على الموقع بعد. تقدر تستخدم نموذج البريد أدناه.' : 'Google sign-in is not enabled on this site yet. You can use the email form below.'}</small></>}
    {pending && state === 'link' && <form onSubmit={event => { event.preventDefault(); exchange.current?.(pending.credential, pending.nonce, password) }}>
      <p>{ar ? 'فيه حساب بنفس البريد بالفعل. اكتب كلمة مروره الحالية لربط Google بالحساب والاحتفاظ برحلاتك.' : 'An account already uses this email. Enter its current password to link Google and keep your saved trips.'}</p>
      <label>{ar ? 'كلمة مرور الحساب الحالي' : 'Existing account password'}<input type="password" required minLength={12} maxLength={128} autoComplete="current-password" disabled={busy} value={password} onChange={event => setPassword(event.target.value)} /></label>
      <button type="submit" className="btn primary" disabled={busy}>{ar ? 'ربط Google والدخول' : 'Link Google and sign in'}</button>
      <button type="button" className="btn secondary" disabled={busy} onClick={() => setAttempt(value => value + 1)}>{ar ? 'إلغاء الربط' : 'Cancel linking'}</button>
    </form>}
    {state === 'done' && purpose === 'delete' && <p role="status">{ar ? 'تم تأكيد هويتك. يمكنك تأكيد الحذف أدناه خلال خمس دقائق.' : 'Identity confirmed. You can confirm deletion below within five minutes.'}</p>}
    {error && <p role={attempted ? "alert" : "status"}>{messages[error]}</p>}
    {state === 'error' && <button type="button" className="btn secondary" onClick={() => setAttempt(value => value + 1)}>{ar ? 'إعادة محاولة Google' : 'Retry Google sign-in'}</button>}
    {state === 'ready' && purpose === 'login' && <small>{ar ? 'اختر حسابك داخل Google. الموقع لا يستقبل كلمة مرور Google الخاصة بك.' : 'Choose your account with Google. This site never receives your Google password.'}</small>}
  </section>
}
