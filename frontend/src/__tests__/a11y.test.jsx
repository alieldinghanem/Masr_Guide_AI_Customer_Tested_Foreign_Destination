import React from 'react'
import axe from 'axe-core'
import { describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { mockApi } from './fixtures'

// jsdom cannot compute layout/colours, so colour-contrast and a few visual rules are disabled;
// everything structural (names, roles, labels, landmarks, headings, ARIA) is checked.
const audit = async () => {
  const result = await axe.run(document.body, { iframes: false, rules: { 'color-contrast': { enabled: false } } })
  return result.violations.map(v => `${v.id}: ${v.help} -> ${v.nodes.map(n => n.target.join(' ')).join(' | ')}`)
}

const PAGES = [['Chat', 'AI Chat', 'الشات الذكي'], ['Historical', 'Historical Places', 'الأماكن الأثرية'], ['Beaches', 'Beaches', 'الشواطئ والبحر'], ['Recommendations', 'Recommendations', 'الترشيحات'], ['Travel tips', 'Travel Tips', 'نصائح السفر'], ['Trip planner', 'Plan a journey', 'خطط لرحلة']]

describe.each([['en', 0], ['ar', 1]])('accessibility (%s)', (lang, i) => {
  it.each(PAGES)('%s page has no axe violations', async (_name, en, ar) => {
    const calls = mockApi()
    localStorage.setItem('masr-guide-lang', lang)
    render(<App />)
    await waitFor(() => expect(calls.some(c => c.path === '/health')).toBe(true))
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: [en, ar][i] }))
    if (en === 'Trip planner') {   // audit the page with a generated result too
      await user.click(screen.getByRole('button', { name: lang === 'en' ? 'Generate my itinerary' : 'أنشئ جدولي' }))
      await screen.findByText(lang === 'en' ? 'English disclaimer' : 'إخلاء مسؤولية بالعربية')
    }
    const found = await audit()
    expect(found).toEqual([])
  })
})
