import React from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen, act, waitFor } from '@testing-library/react'
import { MESSAGES } from '../messages'
import { I18nProvider, errorText, interpolate, useI18n } from '../i18n'
import { languageForCountry, VISITOR_COUNTRY_KEY } from '../visitorLocale'

describe('message catalogues', () => {
  it('English and Arabic define exactly the same keys', () => {
    const en = Object.keys(MESSAGES.en).sort(), ar = Object.keys(MESSAGES.ar).sort()
    expect(ar.filter(k => !en.includes(k))).toEqual([])
    expect(en.filter(k => !ar.includes(k))).toEqual([])
  })

  it('has no empty strings and Arabic strings contain Arabic text (except brand/names)', () => {
    for (const lang of ['en', 'ar']) for (const [k, v] of Object.entries(MESSAGES[lang])) expect(v.trim(), `${lang}:${k}`).not.toBe('')
    const latinOk = new Set(['lang.switch', 'guide.lang.English', 'guide.lang.French', 'unit.h', 'unit.m'])
    for (const [k, v] of Object.entries(MESSAGES.ar)) {
      if (latinOk.has(k)) continue
      expect(/[\u0600-\u06FF]/.test(v) || /^[\d\s/.:,·{}%-]+$/.test(v), `ar:${k} -> ${v}`).toBe(true)
    }
  })

  it('uses the same {placeholders} in both languages', () => {
    const vars = s => [...s.matchAll(/\{(\w+)\}/g)].map(m => m[1]).sort().join(',')
    for (const k of Object.keys(MESSAGES.en)) expect(vars(MESSAGES.ar[k]), k).toBe(vars(MESSAGES.en[k]))
  })
})

describe('interpolate / errorText', () => {
  it('fills variables and leaves unknown ones visible', () => {
    expect(interpolate('{a} and {b}', { a: 1 })).toBe('1 and {b}')
  })
  it('maps error codes to localised text', () => {
    const t = k => `T:${k}`
    expect(errorText({ code: 'network' }, t)).toBe('T:err.network')
    expect(errorText({ status: 429 }, t)).toBe('T:err.rate')
    expect(errorText({ message: 'raw' }, t)).toBe('raw')
  })
})

function Probe() {
  const { t, lang, setLang, duration, cityName } = useI18n()
  return <div>
    <span data-testid="nav">{t('nav.home')}</span><span data-testid="dur">{duration(150)}</span>
    <span data-testid="city">{cityName('Luxor')}</span><span data-testid="lang">{lang}</span>
    <button onClick={() => setLang('ar')}>ar</button>
  </div>
}

describe('I18nProvider', () => {
  it('defaults to English/LTR and switches to Arabic/RTL', () => {
    render(<I18nProvider initial="en" cityNamesAr={{ Luxor: 'الأقصر' }}><Probe /></I18nProvider>)
    expect(document.documentElement.dir).toBe('ltr')
    expect(screen.getByTestId('dur')).toHaveTextContent('2h 30m')
    expect(screen.getByTestId('city')).toHaveTextContent('Luxor')
    act(() => screen.getByText('ar').click())
    expect(document.documentElement.dir).toBe('rtl')
    expect(document.documentElement.lang).toBe('ar')
    expect(screen.getByTestId('nav')).toHaveTextContent('الرئيسية')
    expect(screen.getByTestId('city')).toHaveTextContent('الأقصر')
    expect(screen.getByTestId('dur')).toHaveTextContent('2س 30د')
    expect(localStorage.getItem('masr-guide-lang')).toBe('ar')
  })

  it('throws a helpful error outside the provider', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})  // React logs the expected render error
    const Bad = () => { useI18n(); return null }
    expect(() => render(<Bad />)).toThrow(/I18nProvider/)
  })

  it('uses the visitor country for the UI, even if the browser language differs', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({ country: 'EG', ip: 'never-stored' }) })))
    render(<I18nProvider><Probe /></I18nProvider>)
    await waitFor(() => expect(screen.getByTestId('lang')).toHaveTextContent('ar'))
    expect(document.documentElement.dir).toBe('rtl')
    expect(sessionStorage.getItem(VISITOR_COUNTRY_KEY)).toBe('EG')
    expect(sessionStorage.getItem(VISITOR_COUNTRY_KEY)).not.toContain('never-stored')
  })

  it('uses English for a visitor outside Arab countries', async () => {
    sessionStorage.setItem(VISITOR_COUNTRY_KEY, 'US')
    vi.stubGlobal('fetch', vi.fn())
    render(<I18nProvider><Probe /></I18nProvider>)
    expect(screen.getByTestId('lang')).toHaveTextContent('en')
    expect(document.documentElement.dir).toBe('ltr')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('honors a saved manual choice', () => {
    localStorage.setItem('masr-guide-lang', 'ar')
    sessionStorage.setItem(VISITOR_COUNTRY_KEY, 'US')
    const lookup = vi.fn()
    vi.stubGlobal('fetch', lookup)
    render(<I18nProvider><Probe /></I18nProvider>)
    expect(screen.getByTestId('lang')).toHaveTextContent('ar')
    expect(lookup).not.toHaveBeenCalled()
  })

  it('keeps a manual language choice on a later visit even when the country differs', () => {
    const firstVisit = render(<I18nProvider initial="en"><Probe /></I18nProvider>)
    act(() => screen.getByText('ar').click())
    expect(localStorage.getItem('masr-guide-lang')).toBe('ar')
    firstVisit.unmount()

    sessionStorage.setItem(VISITOR_COUNTRY_KEY, 'US')
    const lookup = vi.fn()
    vi.stubGlobal('fetch', lookup)
    render(<I18nProvider><Probe /></I18nProvider>)
    expect(screen.getByTestId('lang')).toHaveTextContent('ar')
    expect(document.documentElement.dir).toBe('rtl')
    expect(lookup).not.toHaveBeenCalled()
  })

  it('does not replace a manual choice when a country lookup finishes later', async () => {
    let finishLookup
    vi.stubGlobal('fetch', vi.fn(() => new Promise(resolve => { finishLookup = resolve })))
    render(<I18nProvider><Probe /></I18nProvider>)
    act(() => screen.getByText('ar').click())
    await act(async () => finishLookup({ ok: true, json: async () => ({ country: 'US' }) }))
    expect(screen.getByTestId('lang')).toHaveTextContent('ar')
    expect(document.documentElement.dir).toBe('rtl')
  })
})

describe('country language mapping', () => {
  it('includes every Arab League country and defaults valid other countries to English', () => {
    for (const code of 'AE BH DJ DZ EG IQ JO KM KW LB LY MA MR OM PS QA SA SD SO SY TN YE'.split(' ')) {
      expect(languageForCountry(code), code).toBe('ar')
    }
    expect(languageForCountry('us')).toBe('en')
    expect(languageForCountry('FR')).toBe('en')
    expect(languageForCountry('??')).toBeNull()
  })
})
