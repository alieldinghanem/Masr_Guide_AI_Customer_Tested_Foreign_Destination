import React, { useEffect, useRef, useState } from 'react'
import { ArrowUpRight, Bookmark, Menu, X, MessageCircle, Compass, UsersRound, ShieldCheck, Waves, Landmark } from 'lucide-react'
import { api } from './api'
import { I18nProvider, errorText, useI18n } from './i18n'
import { ErrorNote, Logo } from './components/Common'
import CategoryPlaces from './components/CategoryPlaces'
import Explore from './components/Explore'
import Planner from './components/Planner'
import Guide from './components/Guide'
import Destinations from './components/Destinations'
import Experiences from './components/Experiences'
import Essentials from './components/Essentials'
import TravelerReviews from './components/TravelerReviews'
import PlaceDetails from './components/PlaceDetails'
import CoastalDetails from './components/CoastalDetails'
import { COASTAL_DESTINATIONS } from './coastalDestinations'
import Saved from './components/Saved'
import Account, { getSession } from './components/Account'
import Budget from './components/Budget'
import {Stories, Offers, Partners, Staff, Project} from './components/Portal'

const GUIDE_LANGUAGE = { en: 'English', ar: 'Arabic' }
const PAGES = ['home', 'heritage', 'coast', 'explore', 'destinations', 'experiences', 'essentials', 'reviews', 'saved', 'planner', 'guide', 'account', 'stories', 'offers', 'partners', 'staff', 'project', 'budget']
const SAVED_PLACES_KEY = 'masr-guide-saved-places-v3'
const pageFromHash = () => {
  const name = window.location.hash.replace(/^#\/?/, '')
  return PAGES.includes(name) || /^(?:place|coast)\/[a-z0-9_-]+$/i.test(name) ? name : 'home'
}

function Shell({ meta }) {
  const { t, lang, setLang } = useI18n()
  const [page, setPage] = useState(pageFromHash)
  // Hash routing (no dependency): deep links like #/planner and working back/forward buttons.
  useEffect(() => {
    const sync = () => setPage(pageFromHash())
    window.addEventListener('popstate', sync)
    window.addEventListener('hashchange', sync)
    return () => { window.removeEventListener('popstate', sync); window.removeEventListener('hashchange', sync) }
  }, [])
  const [mobileOpen, setMobileOpen] = useState(false)
  const [guideMode, setGuideMode] = useState(meta.guideMode)
  const [guideDraft, setGuideDraft] = useState('')
  const [composeFocusKey, setComposeFocusKey] = useState(0)
  // Keep chat history for this browser session while moving between app sections.
  const [guideMessages, setGuideMessages] = useState(() => {
    try {
      const stored = JSON.parse(sessionStorage.getItem('masr-guide-chat-session-v7') || '[]')
      return Array.isArray(stored) ? stored.filter(item => ['user', 'assistant'].includes(item?.role) && typeof item?.text === 'string').slice(-24) : []
    } catch { return [] }
  })
  useEffect(() => {
    try { sessionStorage.setItem('masr-guide-chat-session-v7', JSON.stringify(guideMessages.slice(-24))) } catch { /* private mode or storage quota */ }
  }, [guideMessages])
  const [guideLanguage, setGuideLanguage] = useState(GUIDE_LANGUAGE[lang])
  const guideLanguageChosen = useRef(false)
  useEffect(() => {
    if (!guideLanguageChosen.current) setGuideLanguage(GUIDE_LANGUAGE[lang])
  }, [lang])
  const chooseGuideLanguage = next => {
    guideLanguageChosen.current = true
    setGuideLanguage(next)
  }
  const [highlight, setHighlight] = useState(null)
  const [detailReturnPage, setDetailReturnPage] = useState('explore')
  const [exploreKey, setExploreKey] = useState(0)
  const [exploreInterest, setExploreInterest] = useState(null)
  const [travelerSession, setTravelerSession] = useState(getSession)
  const [reviewReturnPage, setReviewReturnPage] = useState(null)
  // A signed-in visitor only sees their own server-backed favorites, never a
  // different visitor's guest/local favorites while cloud sync is loading.
  const [savedIds, setSavedIds] = useState(() => {
    if (getSession()?.token) return []
    try {
      const parsed = JSON.parse(localStorage.getItem(SAVED_PLACES_KEY) || '[]')
      return Array.isArray(parsed) ? [...new Set(parsed.filter(x => typeof x === 'string'))].slice(0, 500) : []
    } catch { return [] }
  })
  const [favoritesError, setFavoritesError] = useState('')
  const [favoritesLoading, setFavoritesLoading] = useState(!!travelerSession?.token)
  const pendingFavorites = useRef(new Set())
  useEffect(() => {
    if (!travelerSession?.token) { setFavoritesLoading(false); return }
    let active = true
    // Never implicitly copy anonymous-device browsing preferences into an account.
    setSavedIds([])
    setFavoritesLoading(true)
    api('/my/favorites', { token: travelerSession.token })
      .then(data => { if (active) setSavedIds(Array.isArray(data.place_ids) ? data.place_ids : []) })
      .catch(() => { if (active) setFavoritesError('Could not load saved places. Please sign in again or retry.') })
      .finally(() => { if (active) setFavoritesLoading(false) })
    return () => { active = false }
  }, [travelerSession])
  const [discovery, setDiscovery] = useState({ destinations: [], experiences: [], essentials: [] })
  const [ratings, setRatings] = useState({})
  const [myRatings, setMyRatings] = useState({})
  const [ratingsTemporary, setRatingsTemporary] = useState(false)
  useEffect(() => {
    let active = true
    api('/ratings').then(data => {
      if (active) { setRatings(data.ratings || {}); setRatingsTemporary(!!data.temporary_storage) }
    }).catch(() => {})
    return () => { active = false }
  }, [])
  useEffect(() => {
    if (!travelerSession?.token) { setMyRatings({}); return }
    let active = true
    api('/ratings/mine', { token: travelerSession.token })
      .then(data => { if (active) setMyRatings(data.ratings || {}) })
      .catch(() => { if (active) setMyRatings({}) })
    return () => { active = false }
  }, [travelerSession])
  const rate = async (targetId, stars) => {
    const result = await api(`/ratings/${encodeURIComponent(targetId)}`, { method: 'POST', body: { rating: stars }, token: travelerSession?.token })
    setMyRatings(previous => ({ ...previous, [targetId]: stars }))
    setRatings(previous => ({ ...previous, [targetId]: { average: result.average, count: result.count } }))
    return result
  }
  useEffect(() => {
    let live = true
    Promise.allSettled([
      api('/discover/destinations'), api('/discover/experiences'), api('/discover/essentials')
    ]).then(([destinations, experiences, essentials]) => {
      if (live) setDiscovery({
        destinations: destinations.status === 'fulfilled' ? (destinations.value.destinations || []) : [],
        experiences: experiences.status === 'fulfilled' ? (experiences.value.experiences || []) : [],
        essentials: essentials.status === 'fulfilled' ? (essentials.value.essentials || []) : []
      })
    })
    return () => { live = false }
  }, [])
  const toggleSaved = async id => {
    if (!meta.places.some(p => p.id === id) || favoritesLoading || pendingFavorites.current.has(id)) return
    const wasSaved = savedIds.includes(id)
    if (!wasSaved && savedIds.length >= 500) {
      setFavoritesError('A maximum of 500 places can be saved.')
      return
    }
    setFavoritesError('')
    pendingFavorites.current.add(id)
    setSavedIds(old => wasSaved ? old.filter(x => x !== id) : [...old, id])
    try {
      if (travelerSession?.token) {
        await api(`/my/favorites/${encodeURIComponent(id)}`, {
          method: wasSaved ? 'DELETE' : 'POST', token: travelerSession.token
        })
      } else {
        const next = wasSaved ? savedIds.filter(x => x !== id) : [...savedIds, id]
        localStorage.setItem(SAVED_PLACES_KEY, JSON.stringify(next))
      }
    } catch (error) {
      setSavedIds(old => wasSaved ? [...old, id] : old.filter(x => x !== id))
      setFavoritesError(error.message || 'Could not update favorite. Please retry.')
    } finally { pendingFavorites.current.delete(id) }
  }
  useEffect(() => { setGuideMode(meta.guideMode) }, [meta.guideMode])

  const go = name => {
    if (name !== page) window.history.pushState(null, '', `#/${name}`)
    setPage(name); setMobileOpen(false)
    window.scrollTo?.({ top: 0, behavior: 'smooth' })
  }
  useEffect(() => { document.title = `${page.startsWith('place/') ? (meta.places.find(place => place.id === page.slice(6))?.[lang === 'ar' ? 'name_ar' : 'name'] || t('nav.exploreEgypt')) : page.startsWith('coast/') ? (COASTAL_DESTINATIONS.find(item => item.id === page.slice(6))?.[lang === 'ar' ? 'ar' : 'en'] || t('discovery.coast')) : page === 'account' ? 'My Account' : ({home: lang === 'ar' ? 'المرشد الذكي' : 'AI Travel Guide', heritage: lang === 'ar' ? 'الأماكن الأثرية' : 'Historical Places', coast: lang === 'ar' ? 'الشواطئ' : 'Beaches', destinations: lang === 'ar' ? 'الترشيحات' : 'Recommendations', essentials: lang === 'ar' ? 'نصائح السفر' : 'Travel Tips', stories:'Egypt Travel Journal', offers:'Verified Partner Experiences', partners:'Partner With Us', staff:'Staff Studio', project:'Project Case Study',budget:'Travel Budget' }[page] || t(`nav.${page}`))} · Masr Guide AI` }, [page, t, lang, meta.places])
  const askQuestion = q => { setGuideDraft(q); go('home') }
  const startPlanning = () => { if (!guideMessages.length) setGuideDraft(t('guide.planningPrompt')); setComposeFocusKey(key => key + 1); go('home') }
  // Opening a place from elsewhere remounts Discover so stale search/filters cannot hide it.
  const openPlace = p => { setHighlight(p); setExploreInterest(null); setExploreKey(k => k + 1); go('explore') }
  const openDetails = p => { if (p?.id && meta.places.some(place => place.id === p.id)) { setDetailReturnPage(page); go(`place/${p.id}`) } }
  const openCoastalDetails = item => { if (item?.id && COASTAL_DESTINATIONS.some(destination => destination.id === item.id)) go(`coast/${item.id}`) }
  const reviewSignIn = () => { setReviewReturnPage(page); go('account') }
  const exploreTheme = tag => { setHighlight(null); setExploreInterest(tag); setExploreKey(k => k + 1); go('explore') }
  const clearTravelerUi = () => {
    // Clearing storage alone is insufficient: Shell persists across routes.
    setGuideMessages([])
    setGuideDraft('')
    setHighlight(null)
    setSavedIds([])
    setTravelerSession(null)
    setFavoritesError('')
  }
  const switchLanguage = () => {
    const next = lang === 'ar' ? 'en' : 'ar'
    guideLanguageChosen.current = false
    setLang(next); setGuideLanguage(GUIDE_LANGUAGE[next])
  }
  const menu = [['home', t('nav.guide')], ['explore', t('nav.exploreEgypt')], ['reviews', t('nav.reviews')], ['essentials', t('nav.safety')]]
  const { places, cities, interests } = meta

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="nav-wrap container">
          <Logo go={go} />
          <nav id="masr-main-menu" className={`navigation ${mobileOpen ? 'is-open' : ''}`} aria-label={t('nav.aria')}>
            {menu.map(([id, key]) => id === 'explore' ? <div className="nav-discover" key={id}>
              <button type="button" onClick={() => go('explore')} className={['explore', 'heritage', 'coast'].includes(page) || page.startsWith('place/') || page.startsWith('coast/') ? 'active' : ''} aria-current={page === 'explore' ? 'page' : undefined}>{key}</button>
              <div className="nav-discover-submenu" role="group" aria-label={t('discovery.nav')}>
                <button type="button" onClick={() => go('heritage')} aria-current={page === 'heritage' ? 'page' : undefined}><Landmark size={16} />{t('discovery.heritage')}</button>
                <button type="button" onClick={() => go('coast')} aria-current={page === 'coast' ? 'page' : undefined}><Waves size={16} />{t('discovery.coast')}</button>
              </div>
            </div> : <button type="button" key={id} onClick={() => go(id)} className={(page === id || (page === 'guide' && id === 'home')) ? 'active' : ''} aria-current={(page === id || (page === 'guide' && id === 'home')) ? 'page' : undefined}>{key}</button>)}
          </nav>
          <div className="nav-actions">
            <button type="button" className="nav-account-link" onClick={() => go('account')}>{lang === 'ar' ? 'حسابي' : 'My account'}</button>
            <button type="button" className="nav-saved" onClick={() => go('saved')} aria-label={t('nav.saved')} aria-current={page === 'saved' ? 'page' : undefined}><Bookmark size={17}/><span>{savedIds.length}</span></button>
            <button type="button" className="nav-safety" onClick={() => go('essentials')} aria-label={t('nav.safety')} aria-current={page === 'essentials' ? 'page' : undefined}><ShieldCheck size={19}/></button>
            <button type="button" className="lang-toggle" onClick={switchLanguage} aria-label={t('lang.switchAria')} lang={lang === 'ar' ? 'en' : 'ar'}>{t('lang.switch')}</button>
            <button type="button" className="nav-cta" onClick={startPlanning}>{t('nav.plan')} <ArrowUpRight size={16} /></button>
            <button type="button" className="mobile-toggle" onClick={() => setMobileOpen(v => !v)} aria-label={t('nav.toggle')} aria-expanded={mobileOpen} aria-controls="masr-main-menu">{mobileOpen ? <X /> : <Menu />}</button>
          </div>
        </div>
      </header>
      {favoritesError && <div className="container" role="alert"><p className="account-error">{favoritesError}</p></div>}
      {meta.loading && <div className="load-status container" role="status">{t('nav.loading')}</div>}
      {meta.error && (
        <div className="load-error container">
          <ErrorNote text={errorText(meta.error, t)} />
          <button className="btn secondary" type="button" onClick={meta.retry}>{t('nav.retry')}</button>
        </div>
      )}
      {(page === 'home' || page === 'guide') && <div className="mg-chat-home"><Guide prompt={guideDraft} setPrompt={setGuideDraft} composeFocusKey={composeFocusKey} messages={guideMessages} setMessages={setGuideMessages} language={guideLanguage} setLanguage={chooseGuideLanguage} guideMode={guideMode} setGuideMode={setGuideMode} openTrip={() => go('planner')} onNavigate={go} home /></div>}
      {page === 'heritage' && <CategoryPlaces type="heritage" places={places} openDetails={openDetails} askQuestion={askQuestion} ratings={ratings} myRatings={myRatings} onRate={rate} session={travelerSession} onSignIn={reviewSignIn} registrationEnabled={meta.registrationEnabled} />}
      {page === 'coast' && <CategoryPlaces type="coast" places={places} openDetails={openDetails} openCoastalDetails={openCoastalDetails} askQuestion={askQuestion} ratings={ratings} myRatings={myRatings} onRate={rate} session={travelerSession} onSignIn={reviewSignIn} registrationEnabled={meta.registrationEnabled} />}
      {page === 'destinations' && <Destinations destinations={discovery.destinations} places={places} go={go} openPlace={openPlace} askQuestion={askQuestion} />}
      {page === 'experiences' && <Experiences experiences={discovery.experiences} places={places} onExplore={exploreTheme} askQuestion={askQuestion} />}
      {page === 'essentials' && <Essentials items={discovery.essentials} />}
      {page === 'reviews' && <TravelerReviews onExplore={() => go('explore')} places={places} ratings={ratings} myRatings={myRatings} onRate={rate} temporaryStorage={ratingsTemporary} session={travelerSession} onSignIn={reviewSignIn} registrationEnabled={meta.registrationEnabled} />}
      {page === 'saved' && <Saved places={places} savedIds={savedIds} toggleSaved={toggleSaved} openPlace={openPlace} go={go} cloud={!!travelerSession?.token} loading={favoritesLoading} />}
      {page === 'explore' && <Explore key={exploreKey} places={places} cities={cities} interests={interests} highlight={highlight} setHighlight={setHighlight} askQuestion={askQuestion} openDetails={openDetails} savedIds={savedIds} toggleSaved={toggleSaved} initialInterest={exploreInterest} />}
      {page.startsWith('place/') && <PlaceDetails place={places.find(place => place.id === page.slice(6))} onBack={() => go(detailReturnPage)} backLabel={detailReturnPage === 'heritage' ? (lang === 'ar' ? 'الأماكن الأثرية' : 'Historical places') : detailReturnPage === 'coast' ? (lang === 'ar' ? 'الشواطئ والبحر' : 'Beaches & sea') : undefined} askQuestion={askQuestion} saved={savedIds.includes(page.slice(6))} toggleSaved={toggleSaved} ratings={ratings} myRatings={myRatings} onRate={rate} temporaryStorage={ratingsTemporary} session={travelerSession} onSignIn={reviewSignIn} registrationEnabled={meta.registrationEnabled} />}
      {page.startsWith('coast/') && <CoastalDetails destination={COASTAL_DESTINATIONS.find(item => item.id === page.slice(6))} onBack={() => go('coast')} askQuestion={askQuestion} ratings={ratings} myRatings={myRatings} onRate={rate} temporaryStorage={ratingsTemporary} session={travelerSession} onSignIn={reviewSignIn} registrationEnabled={meta.registrationEnabled} />}
      {page === 'planner' && <Planner cities={cities} interests={interests} openPlace={openPlace} />}
      {page === 'account' && <Account registrationEnabled={meta.registrationEnabled} onOpenPlanner={() => go('planner')} onSignOut={clearTravelerUi} onSignIn={next => { setSavedIds([]); setFavoritesError(''); setTravelerSession(next); if (reviewReturnPage) { go(reviewReturnPage); setReviewReturnPage(null) } }} />}
      {page === 'stories' && <Stories go={go} />}
      {page === 'offers' && <Offers go={go} />}
      {page === 'partners' && <Partners />}
      {page === 'staff' && <Staff />}
      {page === 'project' && <Project />}
      {page === 'budget' && <Budget />}

      <footer className="footer">
        <div className="container footer-top">
          <div><Logo go={go} /><p>{t('footer.tagline')}</p></div>
          <div className="footer-links">
            <button onClick={() => go('home')}>{lang === 'ar' ? 'المرشد الذكي' : 'AI Chat'}</button>
            <button onClick={() => go('heritage')}>{lang === 'ar' ? 'الأماكن الأثرية' : 'Historical places'}</button>
            <button onClick={() => go('coast')}>{lang === 'ar' ? 'الشواطئ' : 'Beaches'}</button>
            <button onClick={() => go('destinations')}>{t('footer.destinations')}</button>
            <button onClick={() => go('essentials')}>{t('nav.essentials')}</button>
            <details className="mg-footer-more"><summary>{lang === 'ar' ? 'روابط إضافية' : 'More links'}</summary><div>
              {[[ 'planner', t('footer.plan') ], ['saved', t('nav.saved')], ['account', lang === 'ar' ? 'حسابي' : 'My account'], ['experiences', t('nav.experiences')], ['stories', lang === 'ar' ? 'المجلة' : 'Journal'], ['offers', lang === 'ar' ? 'عروض الشركاء' : 'Partner offers'], ['budget', lang === 'ar' ? 'الميزانية' : 'Budget'], ['partners', lang === 'ar' ? 'انضم كشريك' : 'Partner enquiry'], ['project', lang === 'ar' ? 'عن المشروع' : 'Project case study'], ['staff', lang === 'ar' ? 'الإدارة' : 'Staff']].map(([route, label]) => <button key={route} type="button" onClick={() => go(route)}>{label}</button>)}
            </div></details>
          </div>
        </div>
        <div className="container footer-bottom"><span>{t('footer.copy', { year: new Date().getFullYear() })}</span><span>{t('footer.note')}</span></div>
      </footer>
      <nav className="mg-mobile-tabs" aria-label={lang === 'ar' ? 'التنقل السريع' : 'Quick navigation'}>
        {[[ 'home', MessageCircle, t('nav.guide')], ['explore', Compass, t('nav.explore')], ['reviews', UsersRound, t('nav.reviews')], ['essentials', ShieldCheck, t('nav.safety')]].map(([id, Icon, text]) => <button type="button" key={id} className={(id === page || (id === 'home' && page === 'guide') || (id === 'explore' && (['heritage', 'coast'].includes(page) || page.startsWith('place/') || page.startsWith('coast/')))) ? 'active' : ''} aria-current={id === page ? 'page' : undefined} onClick={() => go(id)}><Icon size={19}/><span>{text}</span></button>)}
      </nav>
    </div>
  )
}

export default function App() {
  const [attempt, setAttempt] = useState(0)
  const [meta, setMeta] = useState({ places: [], cities: [], interests: [], cityNamesAr: {}, guideMode: 'offline-preview', registrationEnabled: true, error: null, loading: true })
  useEffect(() => {
    let active = true
    Promise.all([api('/cities'), api('/places'), api('/health')])
      .then(([loc, attractions, health]) => {
        if (active) setMeta(m => ({ ...m,
          cities: loc.cities, interests: loc.interests, cityNamesAr: loc.city_names_ar || {},
          places: attractions.places, guideMode: health.guide_mode, registrationEnabled: health.registration_enabled !== false, error: null, loading: false
        }))
      })
      .catch(error => { if (active) setMeta(m => ({ ...m, error, loading: false })) })
    return () => { active = false }
  }, [attempt])
  const retry = () => {
    setMeta(m => ({ ...m, error: null, loading: true }))
    setAttempt(v => v + 1)
  }
  return <I18nProvider cityNamesAr={meta.cityNamesAr}><Shell meta={{ ...meta, retry }} /></I18nProvider>
}
