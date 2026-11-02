import React, { useEffect, useRef, useState } from 'react'
import { ArrowUpRight, Bot, ChevronDown, ExternalLink, Globe2, LoaderCircle, MessageCircle, SendHorizontal, ShieldCheck, Sparkles, Trash2 } from 'lucide-react'
import { api } from '../api'
import { errorText, useI18n } from '../i18n'
import { ErrorNote } from './Common'
import { getSession } from './Account'
import { likelyPaymentNumber, scrubPaymentNumber } from '../paymentSafety'
import { isCompatibleTripPlan } from '../tripValidation'

function restoredConsultation() {
  // The pair must be validated together before the app shows restored days.
  try {
    const state = JSON.parse(sessionStorage.getItem('masr-guide-consult-state-v2') || 'null')
    const plan = JSON.parse(sessionStorage.getItem('masr-guide-consult-plan-v2') || 'null')
    return isCompatibleTripPlan(state, plan) ? { state, plan } : { state: null, plan: null }
  } catch { return { state: null, plan: null } }
}

const MODES = ['gemini-search-grounded', 'gemini-search-unverified', 'gemini-rag-no-live-citations', 'restaurant-search-unverified', 'llm-rag', 'openai-rag', 'gemini-rag', 'gemini-configured', 'openai-configured', 'local-planner', 'gemini-intent+local-planner', 'openai-intent+local-planner', 'llm-configured', 'provider-error', 'offline-preview', 'local-assistant', 'offline-fallback', 'needs-clarification', 'hotel-editorial', 'hotel-gemini-assisted', 'hotel-openai-assisted', 'hotel-guide-limited', 'restaurant-guide-limited', 'unsupported-destination', 'trip-saved', 'needs-authentication']

export default function Guide({ prompt, setPrompt, messages, setMessages, language, setLanguage, guideMode, setGuideMode, openTrip, home = false }) {
  const { t, lang, cityNameAr } = useI18n()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [savedConversations, setSavedConversations] = useState([])
  const [selectedConversation, setSelectedConversation] = useState('')
  const [currentConversation, setCurrentConversation] = useState(null)
  const [currentConversationVersion, setCurrentConversationVersion] = useState(null)
  const [cloudStatus, setCloudStatus] = useState('')
  const [restored] = useState(restoredConsultation)
  const [tripState, setTripState] = useState(restored.state)
  const [itinerary, setItinerary] = useState(restored.plan)
  const scrollRef = useRef(null)
  useEffect(() => { scrollRef.current?.scrollIntoView?.({ behavior: 'smooth' }) }, [messages, busy])
  const mode = MODES.includes(guideMode) ? guideMode : 'offline-preview'
  const answerArabic = language === 'Arabic'
  const answerCity = city => answerArabic ? cityNameAr(city) : city

  const submitQuestion = async question => {
    if (busy || question.length < 2) return
    if (likelyPaymentNumber(question)) {
      setPrompt('')
      setError(lang === 'ar'
        ? 'لحماية بياناتك، لا ترسل رقم بطاقة بنكية في الشات. لا توجد مدفوعات مباشرة هنا.'
        : 'For your safety, do not enter card numbers in chat. Payments are not processed here.')
      return
    }
    const responseLanguage = /[\u0600-\u06ff]{3,}/.test(question) ? 'Arabic' : language
    if (responseLanguage === 'Arabic' && language !== 'Arabic') setLanguage('Arabic')
    const history = messages.map(m => ({ role: m.role, content: scrubPaymentNumber(m.text.slice(0, 1500)) })).slice(-8)
    setMessages(m => [...m, { role: 'user', text: question }]); setPrompt(''); setBusy(true); setError('')
    try {
      const result = await api('/consult', { method: 'POST', token: getSession()?.token, body: { message: question, language: responseLanguage, history, trip_state: tripState } })
      if (result.trip_state && result.itinerary) {
        if (!isCompatibleTripPlan(result.trip_state, result.itinerary)) {
          throw new Error('The assistant returned an invalid trip. Your previous trip is unchanged.')
        }
        setTripState(result.trip_state); setItinerary(result.itinerary)
        try {
          sessionStorage.setItem('masr-guide-consult-state-v2', JSON.stringify(result.trip_state))
          sessionStorage.setItem('masr-guide-consult-plan-v2', JSON.stringify(result.itinerary))
        } catch { /* private browsing */ }
      }
      if (result.saved_trip_id) setCloudStatus(lang === 'ar' ? 'تم حفظ الرحلة في حسابك ويمكنك العثور عليها من صفحة حسابي.' : 'Your trip was saved and is available in My Account.')
      setMessages(m => [...m, { role: 'assistant', text: result.answer, sources: result.sources, mode: result.mode, grounding: result.grounding, responseLanguage }])
      setGuideMode(result.mode)
    } catch (err) {
      // A failed request must not leave an unanswered user turn in the LLM history.
      setMessages(m => m.at(-1)?.role === 'user' && m.at(-1).text === question ? m.slice(0, -1) : m)
      setPrompt(p => p.trim() ? p : question)
      setError(errorText(err, t))
      if (['llm-configured', 'llm-rag', 'openai-configured', 'openai-rag', 'gemini-configured', 'gemini-rag', 'gemini-search-grounded', 'gemini-search-unverified'].includes(guideMode)) setGuideMode('provider-error')
    } finally { setBusy(false) }
  }
  const cloudToken = () => {
    const session = getSession()
    if (!session?.token) {
      setCloudStatus(lang === 'ar' ? 'سجّل الدخول من صفحة حسابي لحفظ المحادثات على حسابك.' : 'Sign in from My Account to save conversations to your account.')
      return null
    }
    return session.token
  }
  const refreshConversations = async () => {
    const token = cloudToken()
    if (!token) return
    try {
      const data = await api('/my/conversations', { token })
      setSavedConversations(data.conversations || [])
      setSelectedConversation(previous => previous || data.conversations?.[0]?.id || '')
      setCloudStatus('')
    } catch (err) { setCloudStatus(errorText(err, t)) }
  }
  const saveConversation = async () => {
    const token = cloudToken()
    if (!token || !messages.length || busy) return
    const record = {
      title: (messages.find(m => m.role === 'user')?.text || 'My Egypt conversation').slice(0, 110),
      messages: messages.slice(-100).map(m => ({ role: m.role, text: scrubPaymentNumber(m.text.slice(0, 1500)) })),
      trip_state: tripState,
      itinerary
    }
    try {
      const result = await api(currentConversation ? `/my/conversations/${currentConversation}` : '/my/conversations',
        { token, method: currentConversation ? 'PUT' : 'POST', body: record, ifMatch: currentConversation ? currentConversationVersion : undefined })
      if (!currentConversation) setCurrentConversation(result.id)
      if (result.updated_at) setCurrentConversationVersion(result.updated_at)
      setCloudStatus(lang === 'ar' ? 'تم حفظ المحادثة في حسابك.' : 'Conversation saved to your account.')
      const list = await api('/my/conversations', { token })
      setSavedConversations(list.conversations || [])
      if (!currentConversation) setSelectedConversation(result.id)
    } catch (err) { setCloudStatus(errorText(err, t)) }
  }
  const restoreConversation = async () => {
    const token = cloudToken()
    if (!token || !selectedConversation || busy) return
    try {
      const data = await api(`/my/conversations/${selectedConversation}`, { token })
      setMessages((data.messages || []).map(m => ({ role: m.role, text: m.text })))
      const valid = isCompatibleTripPlan(data.trip_state, data.itinerary)
      const hasTrip = Boolean(data.trip_state || data.itinerary)
      setTripState(valid ? data.trip_state : null); setItinerary(valid ? data.itinerary : null)
      setCurrentConversation(data.id)
      setCurrentConversationVersion(data.updated_at)
      if (valid) sessionStorage.setItem('masr-guide-consult-state-v2', JSON.stringify(data.trip_state))
      else sessionStorage.removeItem('masr-guide-consult-state-v2')
      if (valid) sessionStorage.setItem('masr-guide-consult-plan-v2', JSON.stringify(data.itinerary))
      else sessionStorage.removeItem('masr-guide-consult-plan-v2')
      setCloudStatus(hasTrip && !valid
        ? (lang === 'ar' ? 'تم استرجاع النص، لكن بيانات الرحلة القديمة غير متوافقة ولم يتم تشغيلها.' : 'Messages restored. An outdated itinerary was not loaded for safety.')
        : (lang === 'ar' ? 'تم استرجاع المحادثة.' : 'Conversation restored.'))
    } catch (err) { setCloudStatus(errorText(err, t)) }
  }
  const deleteConversation = async () => {
    const token = cloudToken()
    if (!token || !selectedConversation || busy) return
    try {
      await api(`/my/conversations/${selectedConversation}`, { token, method: 'DELETE' })
      if (currentConversation === selectedConversation) { setCurrentConversation(null); setCurrentConversationVersion(null) }
      setSelectedConversation('')
      const list = await api('/my/conversations', { token })
      setSavedConversations(list.conversations || [])
      setSelectedConversation(list.conversations?.[0]?.id || '')
      setCloudStatus(lang === 'ar' ? 'تم حذف المحادثة المحفوظة.' : 'Saved conversation deleted.')
    } catch (err) { setCloudStatus(errorText(err, t)) }
  }
  const send = e => { e.preventDefault(); return submitQuestion(prompt.trim()) }
  const clearChat = () => {
    setMessages([]); setPrompt(''); setError(''); setTripState(null); setItinerary(null); setCurrentConversation(null); setCurrentConversationVersion(null); setCloudStatus('')
    try { sessionStorage.removeItem('masr-guide-consult-state-v2'); sessionStorage.removeItem('masr-guide-consult-plan-v2') } catch { /* private browsing */ }
  }
  const saveTrip = () => {
    if (!itinerary) return
    try {
      const payload = { ...itinerary, _request: null }
      sessionStorage.setItem('masr-guide-draft-v1', JSON.stringify(payload))
      openTrip?.()
    } catch { setError(lang === 'ar' ? 'تعذر حفظ الرحلة داخل المتصفح.' : 'Unable to save this itinerary locally.') }
  }
  // Explicit one-click cloud save. This uses the same ownership-enforcing API as
  // My Account and never pretends that browser storage is a server-side save.
  const saveTripToAccount = async () => {
    if (!itinerary || busy) return
    const token = cloudToken()
    if (!token) return
    try {
      const days = itinerary.days.length
      await api('/my/trips', {
        method: 'POST', token,
        body: {
          title: (lang === 'ar' ? `رحلتي في مصر - ${days} يوم` : `My Egypt trip - ${days} days`),
          itinerary
        }
      })
      setCloudStatus(lang === 'ar' ? 'تم حفظ الرحلة في حسابك. يمكنك عرضها من صفحة حسابي.' : 'Itinerary saved to your account. View it in My Account.')
    } catch (err) {
      setCloudStatus(errorText(err, t))
    }
  }
  const exportTrip = () => {
    if (!itinerary) return
    const lines = ['MASR GUIDE AI — SAMPLE ITINERARY', `${itinerary.days.length} days`, '']
    for (const d of itinerary.days) {
      lines.push(`Day ${d.day} — ${d.city}`)
      for (const s of d.stops) lines.push(` - ${s.place.name}`)
      if (!d.stops.length) lines.push(' - Free day / no matching curated activity')
      lines.push('')
    }
    lines.push(itinerary.disclaimer)
    const url = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' }))
    const a = document.createElement('a'); a.href = url; a.download = 'masr-guide-trip.txt'; a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return (
    <main className={`page-wrap container guide-page ${home ? 'mg-guide-home' : ''}`}>
      <div className="page-intro">
        <span className="eyebrow">{home ? (lang === 'ar' ? 'مساعدك السياحي الشخصي' : 'YOUR PERSONAL TRAVEL COMPANION') : t('guide.eyebrow')}</span>
        <h1>{home ? (lang === 'ar' ? 'اكتشف مصر بطريقتك.' : 'Discover Egypt, your way.') : <>{t('guide.h1a')} <em>{t('guide.h1b')}</em></>}</h1>
        <p>{home ? (lang === 'ar' ? 'اسأل عن أي مكان في مصر، وخطط رحلتك مع مساعدك الذكي بسهولة.' : 'Ask about Egypt, discover places and plan your trip with your personal AI guide.') : t('guide.p')}</p>
      </div>
      <div className="guide-grid">
        <section className="chat-panel">
          <header className="chat-header">
            <span className="bot-avatar"><Bot size={21} /></span>
            <div>
              <h2>{t('guide.name')}</h2>
              <span><span className={`status-dot ${['gemini-search-grounded', 'gemini-rag', 'llm-rag', 'openai-rag', 'hotel-gemini-assisted', 'hotel-openai-assisted', 'gemini-intent+local-planner', 'openai-intent+local-planner'].includes(mode) ? 'ready' : ''}`} />{t(`guide.status.${mode}`)}</span>
            </div>
            <button type="button" className="chat-clear" onClick={clearChat} disabled={busy || (!messages.length && !prompt && !itinerary)} aria-label={t('guide.clear')} title={t('guide.clear')}><Trash2 size={16} />{t('guide.clear')}</button>
            <label className="lang-picker"><Globe2 size={17} />
              <select aria-label={t('guide.langAria')} value={language} onChange={e => setLanguage(e.target.value)}>
                {['English', 'Arabic', 'French'].map(l => <option key={l} value={l}>{t(`guide.lang.${l}`)}</option>)}
              </select><ChevronDown size={14} />
            </label>
          </header>
          <div className="chat-messages">
            <div className="guide-welcome">
              <div className="welcome-icon"><Sparkles size={25} /></div>
              <h3>{t('guide.welcomeTitle')}</h3>
              <p>{t('guide.welcomeText')}</p>
              <span>{t(`guide.welcome.${mode}`)}</span>
            </div>
            {messages.map((m, i) => (
              <div className={`msg ${m.role}`} key={i}>
                <div className="msg-avatar">{m.role === 'assistant' ? <Bot size={17} /> : t('guide.you')}</div>
                <div className="msg-content">
                  <div className="msg-text" dir="auto">{m.text}</div>
                  {m.role === 'assistant' && !!m.sources?.length && (
                    <div className="message-sources"><strong>{t('guide.refs')}</strong>
                      <div>{m.sources.filter(s => typeof s.url === 'string' && /^https:\/\//i.test(s.url)).map((s, n) => (
                        <a href={s.url} key={s.id || s.url || n} target="_blank" rel="noopener noreferrer">
                          [{s.number ?? n + 1}] {(m.responseLanguage || language) === 'Arabic' && s.title_ar ? s.title_ar : s.title}<ExternalLink size={12} />
                        </a>))}
                      </div>
                    </div>
                  )}
                  {m.role === 'assistant' && !!m.grounding?.search_suggestions_html && (
                    <iframe title="Google Search suggestions" sandbox="allow-popups allow-popups-to-escape-sandbox"
                      srcDoc={m.grounding.search_suggestions_html} loading="lazy"
                      style={{ width: '100%', height: 95, border: 0 }} />
                  )}
                </div>
              </div>
            ))}
            {busy && <div className="thinking"><LoaderCircle size={19} className="spin" /> {t('guide.thinking')}</div>}
            <div ref={scrollRef} />
          </div>
          {itinerary && <section className="consult-trip" aria-label={answerArabic ? 'الرحلة المقترحة' : 'Suggested itinerary'}>
            <div className="consult-heading">
              <strong>{answerArabic ? 'برنامج رحلتك القابل للتعديل' : 'Your editable Egypt itinerary'}</strong>
              <span>{itinerary.days.length} {answerArabic ? 'يوم' : 'days'}</span>
            </div>
            <p className="consult-help">{answerArabic ? 'اكتب في المحادثة: غير الغردقة إلى شرم الشيخ، أو زود يوم للأقصر.' : 'Try: Replace Hurghada with Sharm El Sheikh, or add one more day to Luxor.'}</p>
            <div className="consult-days">
              {itinerary.days.map(day => <details key={day.day} className="consult-day">
                <summary>{answerArabic ? 'اليوم' : 'Day'} {day.day} — {answerCity(day.city)} · {day.stops.length} {answerArabic ? (day.stops.length === 1 ? 'زيارة' : 'زيارات') : (day.stops.length === 1 ? 'stop' : 'stops')}</summary>
                {day.travel && <p>{answerArabic ? 'انتقال تقريبي' : 'Approximate transfer'}: {answerCity(day.travel.from_city)} → {answerCity(day.city)} ({day.travel.minutes} min)</p>}
                {day.stops.length ? <ul>{day.stops.map(stop => <li key={stop.place.id}>{answerArabic ? stop.place.name_ar : stop.place.name}</li>)}</ul>
                  : <div><p>{answerArabic ? 'يوم حر / لا توجد زيارات موثقة أخرى في الكتالوج' : 'Free day / no additional curated visits'}</p>{(day.activity_ideas||[]).map((idea,i)=><p key={i} className="planner-idea">{answerArabic?'فكرة اختيارية غير محجوزة: ':'Optional unbooked idea: '}{idea}</p>)}</div>}
              </details>)}
            </div>
            {tripState?.accessibility_needs && (
              <p className="consult-help" role="status">
                {answerArabic
                  ? 'تنبيه وصول: لم يتم التحقق من ملاءمة المعالم أو الانتقالات للكراسي المتحركة. أكد التفاصيل مع الجهات الرسمية قبل الحجز.'
                  : 'Accessibility notice: no attraction or transfer in this plan is verified wheelchair-accessible. Confirm details with operators before booking.'}
              </p>
            )}
            {!!itinerary.warnings?.length && (
              <details className="consult-day">
                <summary>{answerArabic ? 'تنبيهات مهمة قبل السفر' : 'Important travel notes'} ({itinerary.warnings.length})</summary>
                <ul>{itinerary.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>
              </details>
            )}
            <div className="consult-actions"><button type="button" onClick={saveTrip}>{lang === 'ar' ? 'افتح الرحلة في المخطط' : 'Open in Trip Planner'}</button>
              <button type="button" onClick={saveTripToAccount} disabled={busy}>{lang === 'ar' ? 'حفظ الرحلة في حسابي' : 'Save itinerary to my account'}</button>
              <button type="button" onClick={exportTrip}>{lang === 'ar' ? 'نزّل الرحلة' : 'Download itinerary'}</button></div>
            <small>{itinerary.disclaimer}</small>
          </section>}
          {home && <div className="mg-quick-prompts" aria-label={lang === 'ar' ? 'أسئلة مقترحة' : 'Suggested questions'}>{[1,2,3].map(n => <button type="button" key={n} onClick={() => setPrompt(t(`guide.prompt${n}`))}>{t(`guide.prompt${n}`)}</button>)}<button type="button" onClick={() => setPrompt(lang === 'ar' ? 'أنا جاي مصر شهر وعايز برنامج بين القاهرة والأقصر وأسوان والغردقة.' : 'Plan a month in Egypt: Cairo, Luxor, Aswan, and Hurghada.')}>{lang === 'ar' ? 'خطط رحلة شهر' : 'Plan a month'}</button></div>}
          <div className="chat-cloud-tools" aria-label={lang === 'ar' ? 'محادثاتك المحفوظة' : 'Saved conversations'}>
            <button type="button" onClick={saveConversation} disabled={busy || !messages.length}>{lang === 'ar' ? 'حفظ المحادثة في حسابي' : 'Save conversation to account'}</button>
            <button type="button" onClick={refreshConversations} disabled={busy}>{lang === 'ar' ? 'عرض المحادثات المحفوظة' : 'Show saved chats'}</button>
            {savedConversations.length > 0 && <div className="chat-cloud-restore">
              <select aria-label={lang === 'ar' ? 'اختيار محادثة محفوظة' : 'Choose saved chat'} value={selectedConversation} onChange={e => setSelectedConversation(e.target.value)}>
                <option value="">{lang === 'ar' ? 'اختر محادثة' : 'Choose a conversation'}</option>
                {savedConversations.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
              </select>
              <button type="button" disabled={busy || !selectedConversation} onClick={restoreConversation}>{lang === 'ar' ? 'استرجاع' : 'Restore'}</button>
              <button type="button" disabled={busy || !selectedConversation} onClick={deleteConversation}>{lang === 'ar' ? 'حذف المحفوظة' : 'Delete saved'}</button>
            </div>}
            {cloudStatus && <small role="status">{cloudStatus}</small>}
          </div>
          <div className="chat-compose">
            <ErrorNote text={error} />
            {error && prompt.trim().length >= 2 && <button className="chat-retry" type="button" disabled={busy} onClick={() => submitQuestion(prompt.trim())}>{t('guide.retry')}</button>}
            <form onSubmit={send}>
              <input aria-label={t('guide.askAria')} placeholder={t('guide.placeholder')} maxLength={1200} value={prompt} onChange={e => setPrompt(e.target.value)} dir="auto" />
              <button className="send-button" type="submit" disabled={busy || prompt.trim().length < 2} aria-label={t('guide.send')}><SendHorizontal size={19} /></button>
            </form>
            <small>{t('guide.privacy')}</small>
          </div>
        </section>
        <aside className="guide-side">
          <div className="side-card suggested">
            <span className="eyebrow">{t('guide.side.eyebrow')}</span>
            <h3>{t('guide.side.h3')}</h3>
            {[1, 2, 3].map(n => (
              <button key={n} onClick={() => setPrompt(t(`guide.prompt${n}`))}>
                <span><MessageCircle size={16} /></span>{t(`guide.prompt${n}`)}<ArrowUpRight size={15} />
              </button>))}
          </div>
          <div className="side-card suggested">
            <span className="eyebrow">TRAVEL CONSULTANT</span>
            <h3>{lang === 'ar' ? 'كوّن رحلة كاملة بالكلام' : 'Plan a full journey in chat'}</h3>
            <button type="button" onClick={() => setPrompt(lang === 'ar'
              ? 'أنا جاي مصر أسبوعين، عايز أول أسبوع آثار والقاهرة والأقصر، والأسبوع التاني بحر في الغردقة.'
              : 'I am visiting Egypt for two weeks: the first week for history in Cairo and Luxor, the second week for beaches in Hurghada.')}>{lang === 'ar' ? 'جرّب رحلة أسبوعين: آثار وبحر' : 'Try 14 days: history + Red Sea'}</button>
          </div>
          <div className="side-card grounded">
            <div className="grounded-icon"><ShieldCheck size={26} /></div>
            <h3>{t('guide.grounded.h')}</h3>
            <p>{t('guide.grounded.p')}</p>
            <small>{t('guide.grounded.s')}</small>
          </div>
        </aside>
      </div>
    </main>
  )
}
