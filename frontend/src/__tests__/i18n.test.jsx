import React from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { MESSAGES } from '../messages'
import { I18nProvider, errorText, interpolate, useI18n } from '../i18n'

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
})
