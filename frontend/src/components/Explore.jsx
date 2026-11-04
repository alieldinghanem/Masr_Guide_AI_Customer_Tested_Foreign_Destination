import React, { useState } from 'react'
import { ArrowRight, ChevronDown, ChevronRight, Bookmark, BookmarkCheck, Clock3, Compass, ExternalLink, Landmark, MapPin, Search } from 'lucide-react'
import { useI18n } from '../i18n'
import { getMapUrl } from './Common'
import { getReligiousGroup, orderCategoryPlaces } from '../categoryFilters'
import DiscoveryNav from './DiscoveryNav'
import { EditorialImage, LANDMARK_MEDIA, getLandmarkFraming } from './EditorialMedia'

const ALL = '__all__'

export default function Explore({ places, cities, interests, highlight, setHighlight, askQuestion, openDetails, savedIds = [], toggleSaved = () => {}, initialInterest = null }) {
  const { t, lang, placeName, placeSummary, cityName, category, interestName, duration } = useI18n()
  const [city, setCity] = useState(ALL)
  const [search, setSearch] = useState('')
  const [interest, setInterest] = useState(initialInterest || ALL)
  const needle = search.trim().toLowerCase()
  const visible = orderCategoryPlaces(places.filter(p =>
    (city === ALL || p.city === city) &&
    (interest === ALL || p.tags.includes(interest)) &&
    [p.name, p.name_ar, p.city, cityName(p.city), p.description, p.summary_ar].filter(Boolean).join(' ').toLowerCase().includes(needle)), 'heritage')
  const current = visible.find(p => p.id === highlight?.id) || visible[0] || null
  return (
    <main className="page-wrap container explore-page">
      <div className="page-intro">
        <span className="eyebrow">{t('explore.eyebrow')}</span>
        <h1>{t('explore.h1a')} <em>{t('explore.h1b')}</em></h1>
        <p>{t('explore.p')}</p>
      </div>
      <DiscoveryNav current="explore" />
      <div className="filter-row">
        <label className="search-wrap"><Search size={18} />
          <input aria-label={t('explore.searchAria')} placeholder={t('explore.searchPlaceholder')} value={search} onChange={e => setSearch(e.target.value)} />
        </label>
        <label className="field-select"><MapPin size={17} />
          <select aria-label={t('explore.filterCity')} value={city} onChange={e => { setCity(e.target.value); setHighlight(null) }}>
            <option value={ALL}>{t('explore.allDestinations')}</option>
            {cities.map(c => <option key={c} value={c}>{cityName(c)}</option>)}
          </select><ChevronDown size={14} />
        </label>
        <label className="field-select"><Compass size={17} />
          <select aria-label={t('explore.filterInterest')} value={interest} onChange={e => { setInterest(e.target.value); setHighlight(null) }}>
            <option value={ALL}>{t('explore.allInterests')}</option>
            {interests.map(v => <option key={v} value={v}>{interestName(v)}</option>)}
          </select><ChevronDown size={14} />
        </label>
      </div>
      <div className="explore-layout">
        <div className="place-list">
          <div className="list-heading"><strong>{t('explore.count', { n: visible.length })}</strong><span>{t('explore.select')}</span></div>
          {visible.map((p, index) => <React.Fragment key={p.id}>
            {getReligiousGroup(p) && getReligiousGroup(p) !== getReligiousGroup(visible[index - 1]) && <h2 className="mg-place-group-heading">{t(`religious.${getReligiousGroup(p)}`)}</h2>}
            <button type="button" className={`place-row ${current?.id === p.id ? 'chosen' : ''}`} onClick={() => setHighlight(p)}>
              <div className="place-mini"><Landmark size={21} /></div>
              <div>
                <small><MapPin size={12} />{cityName(p.city)} · {category(p.category)}</small>
                <strong className="place-title">{placeName(p)}</strong>
                <p>{placeSummary(p)}</p>
                <span><Clock3 size={13} />{t('explore.suggested', { d: duration(p.visit_minutes) })}</span>
              </div>
              <ChevronRight className="place-arrow" size={18} />
            </button>
          </React.Fragment>)}
          {visible.length === 0 && <div className="empty-state">{t('explore.empty')}</div>}
        </div>
        <aside className="place-detail">
          {current ? <>
            {LANDMARK_MEDIA[current.id] && <button type="button" className="detail-photo" style={getLandmarkFraming(current.id)} onClick={() => openDetails(current)} aria-label={`${lang === 'ar' ? 'تفاصيل أكثر عن' : 'More details about'} ${placeName(current)}`}><EditorialImage src={LANDMARK_MEDIA[current.id]} alt="" className="mg-place-img" /><span>{lang === 'ar' ? 'تفاصيل أكثر عن المكان' : 'More about this place'} <ArrowRight size={16} /></span></button>}
            <div className="detail-map">
              <iframe key={current.id} title={t('explore.map', { name: placeName(current) })} src={getMapUrl(current)} loading="lazy" referrerPolicy="no-referrer" />
            </div>
            <div className="detail-content">
              <div className="detail-meta"><MapPin size={15} />{cityName(current.city)} <span className="meta-separator">/</span> {category(current.category)}</div>
              <h2>{placeName(current)}</h2>
              <p>{placeSummary(current)}</p>
              {lang === 'en' && current.details && <p className="detail-more">{current.details}</p>}
              {(lang === 'ar' ? current.tip_ar : current.tip) && (
                <p className="detail-tip"><strong>{t('explore.tip')}:</strong> {lang === 'ar' ? current.tip_ar : current.tip}</p>
              )}
              <div className="tag-list">{current.tags.map(tag => <span key={tag}>{interestName(tag)}</span>)}</div>
              <div className="detail-actions">
                <button type="button" className="btn secondary" onClick={() => openDetails(current)}>{lang === 'ar' ? 'صفحة المكان' : 'View details'} <ArrowRight size={16} /></button>
                <button type="button" className="v3-save-btn" aria-pressed={savedIds.includes(current.id)} onClick={() => toggleSaved(current.id)}>{savedIds.includes(current.id) ? <BookmarkCheck size={17}/> : <Bookmark size={17}/>} {t(savedIds.includes(current.id) ? 'saved.remove' : 'saved.add')}</button>
                <button className="btn primary dark" onClick={() => askQuestion(t('explore.askQ', { name: placeName(current), city: cityName(current.city) }))}>{t('explore.askAi')} <ArrowRight size={16} /></button>
                <a href={current.source_url} target="_blank" rel="noopener noreferrer" className="source-link">{t('explore.ref')} <ExternalLink size={15} /></a>
              </div>
              <p className="micro-note">{t('explore.note', { d: duration(current.visit_minutes) })}</p>
            </div>
          </> : <div className="empty-state">{t('explore.choose')}</div>}
        </aside>
      </div>
    </main>
  )
}
