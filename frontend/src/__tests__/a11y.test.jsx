import React from 'react'
import axe from 'axe-core'
import { describe, expect, it } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { mockApi } from './fixtures'

// jsdom cannot compute layout/colours, so colour-contrast and a few visual rules are disabled;
// everything structural (names, roles, labels, landmarks, headings, ARIA) is checked.
const audit = async () => {
  const result = await axe.run(document.body, { iframes: false, rules: { 'color-contrast': { enabled: false } } })
  return result.violations.map(v => `${v.id}: ${v.help} -> ${v.nodes.map(n => n.target.join(' ')).join(' | ')}`)
}

const PAGES = [['Chat', 'AI guide', 'المرشد الذكي'], ['Explore', 'Explore Egypt', 'اكتشف مصر'], ['Reviews', 'Traveler reviews', 'تقييمات المسافرين'], ['Safety', 'Travel safety', 'السلامة والمساعدة'], ['Trip planner', 'Trip planner', 'مخطط الرحلات']]

describe.each([['en', 0], ['ar', 1]])('accessibility (%s)', (lang, i) => {
  it.each(PAGES)('%s page has no axe violations', async (_name, en, ar) => {
    const calls = mockApi()
    localStorage.setItem('masr-guide-lang', lang)
    render(<App />)
    await waitFor(() => expect(calls.some(c => c.path === '/health')).toBe(true))
    const user = userEvent.setup()
    const primary = within(screen.getByRole('navigation', { name: lang === 'ar' ? 'التنقل الرئيسي' : 'Primary navigation' }))
    const action = _name === 'Trip planner'
      ? screen.getByRole('button', { name: lang === 'ar' ? 'خطط لرحلتك' : 'Plan a trip' })
      : primary.getByRole('button', { name: [en, ar][i] })
    await user.click(action)
    if (_name === 'Trip planner') {   // audit the page with a generated result too
      await user.click(screen.getByRole('button', { name: lang === 'en' ? 'Generate my itinerary' : 'أنشئ جدولي' }))
      await screen.findByText(lang === 'en' ? 'English disclaimer' : 'إخلاء مسؤولية بالعربية')
    }
    const found = await audit()
    expect(found).toEqual([])
  })
})
