import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { MESSAGES } from './messages'

const STORAGE_KEY = 'masr-guide-lang'
const I18nContext = createContext(null)

export function interpolate(template, vars = {}) {
  return template.replace(/\{(\w+)\}/g, (_, k) => (vars[k] === undefined ? `{${k}}` : String(vars[k])))
}

function initialLang() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'ar' || saved === 'en') return saved
  } catch { /* storage may be disabled */ }
  return typeof navigator !== 'undefined' && /^ar/i.test(navigator.language || '') ? 'ar' : 'en'
}

export function I18nProvider({ children, initial, cityNamesAr = {} }) {
  const [lang, setLangState] = useState(initial || initialLang)
  useEffect(() => {
    document.documentElement.lang = lang
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr'
  }, [lang])
  const setLang = useCallback(next => {
    setLangState(next)
    try { localStorage.setItem(STORAGE_KEY, next) } catch { /* ignore */ }
  }, [])
  const value = useMemo(() => {
    const dict = MESSAGES[lang]
    const t = (key, vars) => interpolate(dict[key] ?? MESSAGES.en[key] ?? key, vars)
    const ar = lang === 'ar'
    return {
      lang, setLang, t, dir: ar ? 'rtl' : 'ltr',
      cityName: c => (ar ? cityNamesAr[c] || c : c),
      cityNameAr: c => cityNamesAr[c] || c,
      placeName: p => (ar && p.name_ar ? p.name_ar : p.name),
      placeSummary: p => (ar && p.summary_ar ? p.summary_ar : p.description),
      category: c => t(`cat.${c}`),
      interestName: i => t(`int.${i}`),
      duration: m => {
        const h = Math.floor(m / 60), r = m % 60
        return h ? `${h}${t('unit.h')}${r ? ` ${r}${t('unit.m')}` : ''}` : `${m}${t('unit.m')}`
      },
    }
  }, [lang, setLang, cityNamesAr])
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used inside <I18nProvider>')
  return ctx
}

/** Turn an API/network error into a localised message. */
export function errorText(err, t) {
  if (err?.code === 'network') return t('err.network')
  if (err?.code === 'timeout') return t('err.timeout')
  if (err?.status === 429) return t('err.rate')
  return err?.message || ''
}
