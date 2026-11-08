import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { isValidItinerary } from '../tripValidation'
import { useI18n } from '../i18n'

async function request(path, method = 'GET', payload, token, ifMatch) {
  // Browsers reject a request body on GET/HEAD; omitted body must stay undefined.
  const hasBody = method !== 'GET' && method !== 'HEAD' && payload != null
  return api(path, { method, ...(hasBody ? { body: payload } : {}), token, ifMatch })
}

const SESSION = 'masr-account-session-v4'

// Do not expose a previous visitor's plans and AI context to the next person
// who uses the same browser profile. Account data stored on the server is
// governed separately by auth and account deletion.
export function clearBrowserTravelerData() {
  for (const key of ['masr-guide-chat-session-v7', 'masr-guide-consult-state-v2', 'masr-guide-consult-plan-v2', 'masr-guide-draft-v1']) {
    try { sessionStorage.removeItem(key) } catch { /* private browsing */ }
  }
  for (const key of ['masr-guide-plan-v1', 'masr-guide-saved-places-v3', 'masr-budget-estimate-v5']) {
    try { localStorage.removeItem(key) } catch { /* private browsing */ }
  }
}

export function getSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION) || 'null') } catch { return null }
}

export default function Account({ onSignOut = () => {}, onSignIn = () => {}, onOpenPlanner = () => {}, registrationEnabled = true }) {
  const { lang } = useI18n()
  const ar = lang === 'ar'
  const [session, setSession] = useState(getSession)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [signup, setSignup] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [trips, setTrips] = useState([])
  const [selected, setSelected] = useState(null)
  const [title, setTitle] = useState('My Egypt Journey')
  const [currentPlan, setCurrentPlan] = useState(null)
  const [deletionPassword, setDeletionPassword] = useState('')
  const [deletionOpen, setDeletionOpen] = useState(false)

  useEffect(() => {
    try {
      // Prefer the latest draft over an older saved local plan. The AI consultant
      // deliberately opens an itinerary as a draft before the traveler approves it.
      const draft = JSON.parse(sessionStorage.getItem('masr-guide-draft-v1') || 'null')
      const savedPlan = JSON.parse(localStorage.getItem('masr-guide-plan-v1') || 'null')
      if (isValidItinerary(draft)) setCurrentPlan(draft)
      else if (isValidItinerary(savedPlan)) setCurrentPlan(savedPlan)
    } catch { /* local storage unavailable */ }
  }, [])

  useEffect(() => {
    if (!session?.token) return
    let active = true
    request('/my/trips', 'GET', null, session.token)
      .then(data => { if (active) setTrips(data.trips) })
      .catch(err => { if (active) setError(err.message) })
    return () => { active = false }
  }, [session])

  async function signIn(e) {
    e.preventDefault(); setError(''); setBusy(true)
    try {
      const data = await request(signup ? '/auth/register' : '/auth/login', 'POST', { email, password })
      const next = { token: data.token, user: data.user }
      sessionStorage.setItem(SESSION, JSON.stringify(next))
      setSession(next); onSignIn(next); setPassword('')
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }

  async function saveCloud() {
    if (!currentPlan || !session) return
    setError(''); setBusy(true)
    try {
      await request('/my/trips', 'POST', { title, itinerary: currentPlan }, session.token)
      const data = await request('/my/trips', 'GET', null, session.token)
      setTrips(data.trips)
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }

  async function openTrip(id) {
    setError('')
    try {
      const data = await request(`/my/trips/${id}`, 'GET', null, session.token)
      if (!isValidItinerary(data.itinerary)) throw new Error('This saved trip is outdated or malformed; it cannot be displayed safely.')
      setSelected(data); setTitle(data.title)
    } catch (err) { setError(err.message) }
  }

  function openTripInPlanner() {
    if (!selected || !isValidItinerary(selected.itinerary)) return
    // Planner needs numeric daily activity totals in addition to the persisted
    // read-contract. Do not silently generate a replacement for an old plan.
    if (!selected.itinerary.days.every(day => typeof day.estimated_activity_minutes === 'number' && Number.isFinite(day.estimated_activity_minutes))) {
      setError('This saved itinerary uses an older format and cannot be edited in the planner. You can still view or export it.')
      return
    }
    try {
      sessionStorage.setItem('masr-guide-draft-v1', JSON.stringify(selected.itinerary))
      onOpenPlanner()
    } catch {
      setError('Could not open this itinerary in the planner because browser storage is unavailable.')
    }
  }

  async function replaceSavedTrip() {
    if (!selected || !currentPlan || !session?.token || busy) return
    // The target is explicit. Never write the currently open local draft into a
    // random account record or overwrite a concurrent edit without a version.
    if (!window.confirm(`Replace the saved itinerary "${selected.title}" with the current planner itinerary?`)) return
    setError(''); setBusy(true)
    try {
      await request(`/my/trips/${selected.id}`, 'PUT', {
        title: selected.title, itinerary: currentPlan
      }, session.token, selected.updated_at)
      const updated = await request(`/my/trips/${selected.id}`, 'GET', null, session.token)
      setSelected(updated)
      const list = await request('/my/trips', 'GET', null, session.token)
      setTrips(list.trips)
    } catch (err) {
      setError(err.status === 409 ? 'This saved trip changed on another device. Reload it before updating.' : err.message)
    } finally { setBusy(false) }
  }

  async function removeTrip(id) {
    if (!window.confirm('Delete this saved itinerary?')) return
    setError('')
    try {
      await request(`/my/trips/${id}`, 'DELETE', null, session.token)
      setTrips(old => old.filter(t => t.id !== id)); setSelected(null)
    } catch (err) { setError(err.message) }
  }

  async function exportMyData() {
    if (!session?.token || busy) return
    setError(''); setBusy(true)
    try {
      const data = await request('/my/export', 'GET', null, session.token)
      const file = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(file)
      const link = document.createElement('a')
      link.href = url; link.download = 'masr-guide-my-data.json'
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }

  async function signOut() {
    try { await request('/auth/logout', 'POST', null, session?.token) } catch { /* clear local session regardless */ }
    try { sessionStorage.removeItem(SESSION) } catch { /* private browsing */ }
    clearBrowserTravelerData()
    onSignOut()
    setSession(null); setTrips([]); setSelected(null); setCurrentPlan(null); setError('')
  }

  async function deleteMyAccount(e) {
    e.preventDefault()
    if (!session?.token || busy || !deletionPassword) return
    if (!window.confirm('Permanently delete your account, saved trips and conversations? This cannot be undone.')) return
    setError(''); setBusy(true)
    try {
      await request('/my/account', 'DELETE', { password: deletionPassword, confirmation: 'DELETE MY ACCOUNT' }, session.token)
      try { sessionStorage.removeItem(SESSION) } catch { /* private browsing */ }
      clearBrowserTravelerData()
      onSignOut()
      setSession(null); setTrips([]); setSelected(null); setCurrentPlan(null)
      setDeletionPassword(''); setDeletionOpen(false)
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }

  return (
    <main className="page-wrap container account-page">
      <div className="page-intro"><span className="eyebrow">TRAVELER ACCOUNT</span><h1>{ar ? 'حسابي' : 'My Travel Account'}</h1><p>{ar ? 'احفظ خطط رحلتك وشارك بتقييماتك من حسابك.' : 'Save Egypt itineraries and share reviews from your account.'}{!registrationEnabled && ` ${ar ? 'التخزين مؤقت في هذه النسخة، وقد تختفي البيانات بعد إعادة تشغيل الموقع.' : 'Storage is temporary in this preview, and data may disappear after a restart.'}`}</p></div>
      {error && <p role="alert" className="account-error">{error}</p>}
      {!session ? (
        <form className="account-panel" onSubmit={signIn}>
          <h2>{signup ? (ar ? 'إنشاء حساب' : 'Create an account') : (ar ? 'تسجيل الدخول' : 'Sign in')}</h2>
          <label>{ar ? 'البريد الإلكتروني' : 'Email'}<input required autoComplete="email" type="email" value={email} onChange={e => setEmail(e.target.value)} /></label>
          <label>{ar ? 'كلمة المرور' : 'Password'}<input required minLength={12} autoComplete={signup ? 'new-password' : 'current-password'} type="password" value={password} onChange={e => setPassword(e.target.value)} /></label>
          <small>{ar ? 'استخدم 12 حرفًا على الأقل، ولا تكرر كلمة مرور خدمة أخرى. يمكنك استخدام عنوان Gmail كبريد إلكتروني؛ تسجيل Google بضغطة واحدة غير مفعّل حاليًا.' : 'Use at least 12 characters and do not reuse another password. A Gmail address works as an email address; one-click Google sign-in is not enabled yet.'}</small>
          <button className="btn primary" disabled={busy} type="submit">{busy ? (ar ? 'انتظر...' : 'Please wait…') : signup ? (ar ? 'إنشاء الحساب' : 'Register') : (ar ? 'تسجيل الدخول' : 'Sign in')}</button>
          {registrationEnabled ? <button className="btn secondary" type="button" onClick={() => { setSignup(v => !v); setError('') }}>{signup ? (ar ? 'لديك حساب بالفعل؟' : 'Already have an account?') : (ar ? 'إنشاء حساب' : 'Create an account')}</button> : <p role="status">{ar ? 'إنشاء حساب جديد متوقف في هذه النسخة لأن التخزين مؤقت. سيعود عند توفير قاعدة بيانات دائمة.' : 'Registration is disabled on this temporary-storage public preview. It will return when durable storage is available.'}</p>}
        </form>
      ) : (
        <section className="account-panel">
          <div className="account-bar"><p>{ar ? 'تم تسجيل الدخول بالبريد' : 'Signed in as'} <strong>{session.user.email}</strong></p><button className="btn secondary" onClick={signOut}>{ar ? 'تسجيل الخروج' : 'Sign out'}</button></div>
          <h2>Save the itinerary from My Trip Planner</h2>
          <p>{currentPlan ? `${currentPlan.days.length}-day itinerary available to save.` : 'Create and save an itinerary in the Planner first, then return here.'}</p>
          <label>Trip title<input maxLength={120} minLength={2} value={title} onChange={e => setTitle(e.target.value)} /></label>
          <button className="btn primary" disabled={!currentPlan || busy || title.length < 2} onClick={saveCloud}>Save to my account</button>
          <h2>My saved trips</h2>
          {trips.length ? <div className="account-trip-list">{trips.map(trip => <div className="account-trip" key={trip.id}><strong>{trip.title}</strong><small>{new Date(trip.updated_at).toLocaleDateString()}</small><button className="btn secondary" onClick={() => openTrip(trip.id)}>View</button><button className="btn secondary" onClick={() => removeTrip(trip.id)}>Delete</button></div>)}</div> : <p>No saved trips yet.</p>}
          {selected && <div className="account-trip-preview"><h3>{selected.title}</h3>{selected.itinerary.days.map(day => <p key={day.day}><strong>Day {day.day} — {day.city}:</strong> {(day.stops || []).map(s => s.place?.name).filter(Boolean).join(', ') || day.note || 'Flexible day'}</p>)}
            <p>To edit, open this saved itinerary in the planner. After generating or revising a new draft, return here, select the saved trip, and explicitly update it. Another device's newer changes are protected.</p>
            <button className="btn secondary" disabled={busy} onClick={openTripInPlanner}>Open in planner to edit</button>
            <button className="btn primary" disabled={busy || !currentPlan} onClick={replaceSavedTrip}>Replace with my current planner itinerary</button>
            <button className="btn secondary" onClick={() => setSelected(null)}>Close</button></div>}
          <section className="account-delete-section" aria-label="Delete account">
            <h2>Account privacy</h2>
            <p>Download a JSON copy of your saved trips, favorites, AI conversations, ratings, and comments. This export does not contain passwords or session tokens.</p>
            <button type="button" className="btn secondary" disabled={busy} onClick={exportMyData}>Download my account data</button>
            <p>Deleting your account permanently removes your saved trips, conversations, sessions, ratings, and comments. Partner inquiries submitted separately are not linked to this account.</p>
            {!deletionOpen ? <button type="button" className="btn secondary" onClick={() => setDeletionOpen(true)}>Delete my account</button> : (
              <form onSubmit={deleteMyAccount}>
                <label>Confirm with your current password<input required type="password" autoComplete="current-password" minLength={12} maxLength={128} value={deletionPassword} onChange={e => setDeletionPassword(e.target.value)} /></label>
                <button className="btn secondary" type="submit" disabled={busy || !deletionPassword}>{busy ? 'Deleting…' : 'Permanently delete account'}</button>
                <button className="btn secondary" type="button" disabled={busy} onClick={() => { setDeletionOpen(false); setDeletionPassword('') }}>Cancel</button>
              </form>
            )}
          </section>
        </section>
      )}
    </main>
  )
}
