import React, { useCallback, useEffect, useState } from 'react'
import {
  ArrowRight, ArrowUpRight, Bookmark, CalendarDays, Check, CircleAlert, Clock3, Compass, Download, Printer,
  LoaderCircle, MapPin, ShieldCheck, Trash2, WandSparkles
} from 'lucide-react'
import { api } from '../api'
import { isValidPlannerPlan } from '../tripValidation'
import { errorText, useI18n } from '../i18n'
import { ErrorNote } from './Common'

const PACES = ['relaxed', 'balanced', 'packed']
const SAVED_KEY = 'masr-guide-plan-v1'
const DRAFT_KEY = 'masr-guide-draft-v1'

// Only hydrate objects matching the public itinerary shape (storage may hold older/foreign data).
export const isValidPlan = isValidPlannerPlan

export default function Planner({ cities, interests, openPlace }) {
  const { t, lang, cityName, interestName, placeName, duration } = useI18n()
  const [selectedCities, setSelectedCities] = useState(['Cairo'])
  const [chosenInterests, setChosenInterests] = useState(['history'])
  const [days, setDays] = useState(3)
  const [pace, setPace] = useState('balanced')
  const [family, setFamily] = useState(false)
  const [optimize, setOptimize] = useState(true)
  const [plan, setPlan] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    try {
      const savedPlan = localStorage.getItem(SAVED_KEY)
      const draftPlan = sessionStorage.getItem(DRAFT_KEY)
      const savedData = savedPlan ? JSON.parse(savedPlan) : null
      const draftData = draftPlan ? JSON.parse(draftPlan) : null
      if (isValidPlan(draftData)) { setPlan(draftData); setSaved(false) }
      else if (isValidPlan(savedData)) { setPlan(savedData); setSaved(true) }
    } catch { /* storage may be disabled or data from an older version */ }
  }, [])

  const persist = (data, isSaved) => {
    try {
      if (isSaved) { localStorage.setItem(SAVED_KEY, JSON.stringify(data)); sessionStorage.removeItem(DRAFT_KEY) }
      else { localStorage.removeItem(SAVED_KEY); sessionStorage.setItem(DRAFT_KEY, JSON.stringify(data)) }
    } catch { /* storage may be disabled */ }
  }

  const requestBody = () => ({
    cities: selectedCities, days: Number(days), interests: chosenInterests, pace, family,
    optimize_route: optimize, language: lang, budget_usd: null
  })

  const toggleCity = c => setSelectedCities(old => old.includes(c) ? old.filter(x => x !== c) : [...old, c])
  const toggleInterest = v => setChosenInterests(old => old.includes(v) ? old.filter(x => x !== v) : [...old, v])

  const generate = useCallback(async (body, { keepSaved = false } = {}) => {
    const response = await api('/plan', { method: 'POST', body })
    if (!isValidPlan(response)) throw new Error('The planner returned an invalid itinerary. Your previous plan was not replaced.')
    const withRequest = { ...response, _request: body }
    setPlan(withRequest)
    if (keepSaved) persist(withRequest, true)
    else { setSaved(false); persist(withRequest, false) }
  }, [])

  const submit = async e => {
    e.preventDefault(); setError('')
    if (!selectedCities.length) { setError(t('planner.err.city')); return }
    if (Number(days) < selectedCities.length) { setError(t('planner.err.days')); return }
    setBusy(true)
    try { await generate(requestBody()) }
    catch (err) { setError(errorText(err, t)) }
    finally { setBusy(false) }
  }

  // Re-generate (deterministic, cheap) when the UI language differs from the language the plan
  // was written in, so server-written notes, warnings and the disclaimer match the page.
  useEffect(() => {
    if (!plan?._request || plan._request.language === lang) return
    generate({ ...plan._request, language: lang }, { keepSaved: saved }).catch(() => {})
  }, [lang, plan, saved, generate])

  const save = () => {
    if (!plan) return
    try { localStorage.setItem(SAVED_KEY, JSON.stringify(plan)); sessionStorage.removeItem(DRAFT_KEY); setSaved(true) }
    catch { setError(t('planner.err.storage')) }
  }
  const clear = () => {
    try { localStorage.removeItem(SAVED_KEY); sessionStorage.removeItem(DRAFT_KEY) } catch { /* ignore */ }
    setPlan(null); setSaved(false)
  }
  const download = () => {
    if (!plan) return
    const lines = [t('results.exportTitle'), t('results.summary', { days: plan.days.length, stops: plan.total_places, pace: t(`pace.${plan.pace}`) }), '']
    for (const day of plan.days) {
      lines.push(`${t('day.label', { n: String(day.day).padStart(2, '0') })} — ${cityName(day.city)}`)
      if (day.travel) lines.push(t('day.travel', { from: cityName(day.travel.from_city), d: duration(day.travel.minutes), mode: t(String(day.travel.mode || '').startsWith('flight') ? 'mode.flight' : 'mode.road') }))
      for (const stop of day.stops) lines.push(`- ${placeName(stop.place)} (${duration(stop.suggested_visit_minutes)})`)
      if (!day.stops.length) { lines.push(day.note || t('day.empty')); (day.activity_ideas || []).forEach(idea => lines.push(`  Idea (not booked): ${idea}`)) }
      lines.push('')
    }
    lines.push(...(plan.warnings || []), plan.disclaimer || '')
    const url = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `masr-guide-itinerary-${lang}.txt`
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  const listSep = lang === 'ar' ? '، ' : ', '
  const why = s => s.matched
    ? (s.matched.length ? t('why.matches', { list: s.matched.map(interestName).join(listSep) }) : t('why.matches', { list: t('why.popular') }))
    : s.why

  return (
    <main className="page-wrap container planner-page">
      <div className="page-intro">
        <span className="eyebrow">{t('planner.eyebrow')}</span>
        <h1>{t('planner.h1a')} <em>{t('planner.h1b')}</em></h1>
        <p>{t('planner.p')}</p>
      </div>
      <div className="planner-layout">
        <form className="planner-form" onSubmit={submit}>
          <div className="form-section">
            <div className="form-heading"><span>01</span><div><h2>{t('planner.s1.title')}</h2><p>{t('planner.s1.text')}</p></div></div>
            <div className="chips">{cities.map(c => (
              <button type="button" key={c} className={`chip ${selectedCities.includes(c) ? 'selected' : ''}`} aria-pressed={selectedCities.includes(c)} onClick={() => toggleCity(c)}>
                {selectedCities.includes(c) && <Check size={14} />} {cityName(c)}
              </button>))}
            </div>
          </div>
          <div className="form-section">
            <div className="form-heading"><span>02</span><div><h2>{t('planner.s2.title')}</h2><p>{t('planner.s2.text')}</p></div></div>
            <div className="chips">{interests.map(v => (
              <button type="button" key={v} className={`chip ${chosenInterests.includes(v) ? 'selected' : ''}`} aria-pressed={chosenInterests.includes(v)} onClick={() => toggleInterest(v)}>
                {chosenInterests.includes(v) && <Check size={14} />} {interestName(v)}
              </button>))}
            </div>
          </div>
          <div className="form-section">
            <div className="form-heading"><span>03</span><div><h2>{t('planner.s3.title')}</h2><p>{t('planner.s3.text')}</p></div></div>
            <div className="settings-grid">
              <label>{t('planner.days')} <input type="number" min="1" max="30" value={days} onChange={e => setDays(e.target.value)} required /></label>
              <label>{t('planner.pace')}
                <select value={pace} onChange={e => setPace(e.target.value)}>{PACES.map(k => <option value={k} key={k}>{t(`pace.${k}`)}</option>)}</select>
              </label>
              <label className="check-setting"><input type="checkbox" checked={family} onChange={e => setFamily(e.target.checked)} /><span>{t('planner.family')}<small>{t('planner.familyNote')}</small></span></label>
              <label className="check-setting"><input type="checkbox" checked={optimize} onChange={e => setOptimize(e.target.checked)} /><span>{t('planner.route')}<small>{t('planner.routeNote')}</small></span></label>
            </div>
          </div>
          <ErrorNote text={error} />
          <button disabled={busy || !cities.length} className="btn primary dark generate-btn" type="submit">
            {busy ? <LoaderCircle className="spin" size={18} /> : <WandSparkles size={18} />} {busy ? t('planner.building') : t('planner.generate')} <ArrowRight size={18} />
          </button>
        </form>
        <aside className="planner-side">
          <div className="planner-aside-card">
            <span className="tiny-eyebrow">{t('planner.aside.eyebrow')}</span>
            <div className="aside-illustration"><Compass size={75} strokeWidth={1} /></div>
            <h3>{t('planner.aside.h1')}<br />{t('planner.aside.h2')}</h3>
            <p>{t('planner.aside.p')}</p>
            <div className="aside-row"><ShieldCheck size={18} /> {t('planner.aside.r1')}</div>
            <div className="aside-row"><MapPin size={18} /> {t('planner.aside.r2')}</div>
            <div className="aside-row"><CalendarDays size={18} /> {t('planner.aside.r3')}</div>
          </div>
        </aside>
      </div>

      {plan && (
        <section className="results" aria-live="polite">
          <div className="results-heading">
            <div>
              <span className="eyebrow">{t('results.eyebrow')}</span>
              <h2>{t('results.h2a')} <em>{t('results.h2b')}</em></h2>
              <p>{t('results.summary', { days: plan.days.length, stops: plan.total_places, pace: t(`pace.${plan.pace}`) })}</p>
              {plan.route && plan.route.length > 1 && (
                <p className="route-line">{t('results.route', { route: plan.route.map(cityName).join(lang === 'ar' ? ' ← ' : ' → ') })}{plan.route_optimized ? ` ${t('results.reordered')}` : ''}</p>
              )}
              {plan.total_travel_minutes > 0 && <p className="route-line">{t('results.travelTotal', { d: duration(plan.total_travel_minutes) })}</p>}
            </div>
            <div className="save-actions">
              <button type="button" className="btn secondary" onClick={download}><Download size={16} />{t('results.download')}</button>
              <button type="button" className="btn secondary" onClick={() => window.print()}><Printer size={16} />{t('results.print')}</button>
              <button type="button" className="btn secondary" onClick={save}><Bookmark size={16} />{saved ? t('results.saved') : t('results.save')}</button>
              <button type="button" className="icon-button" onClick={clear} title={t('results.clear')} aria-label={t('results.clear')}><Trash2 size={19} /></button>
            </div>
          </div>
          <ErrorNote text={(plan.warnings || []).join(' ')} />
          <div className="day-list">
            {plan.days.map(d => (
              <article key={d.day} className="day-card">
                <div className="day-title">
                  <span>{t('day.label', { n: String(d.day).padStart(2, '0') })}</span>
                  <h3>{cityName(d.city)}</h3>
                  <small>{t('day.stats', { stops: d.stops.length, d: duration(d.estimated_activity_minutes) })}</small>
                  {d.travel && (
                    <small className="travel-chip">{t('day.travel', {
                      from: cityName(d.travel.from_city), d: duration(d.travel.minutes),
                      mode: t(String(d.travel.mode || '').startsWith('flight') ? 'mode.flight' : 'mode.road')
                    })}</small>
                  )}
                </div>
                {d.stops.length ? (
                  <ol className="stop-list">{d.stops.map(s => (
                    <li key={s.place.id}>
                      <div className="stop-count" />
                      <div>
                        <button onClick={() => openPlace(s.place)}>{placeName(s.place)} <ArrowUpRight size={15} /></button>
                        <p>{why(s)}</p>
                        <small><Clock3 size={13} />{t('stop.suggested', { d: duration(s.suggested_visit_minutes) })}</small>
                      </div>
                    </li>))}
                  </ol>
                ) : <div className="no-stops"><p>{d.note || t('day.empty')}</p>{(d.activity_ideas || []).map((idea,i) => <p key={i} className="planner-idea">{lang === 'ar' ? 'فكرة استرشادية (غير محجوزة): ' : 'Optional idea (not booked): '}{idea}</p>)}</div>}
              </article>
            ))}
          </div>
          <div className="travel-disclaimer"><CircleAlert size={17} />{plan.disclaimer}</div>
        </section>
      )}
    </main>
  )
}
