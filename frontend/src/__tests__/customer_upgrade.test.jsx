import React from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { mockApi, planFor } from './fixtures'
import { matchesPlaceSearch } from '../placeSearch'
import { CHAT_LANGUAGE_KEY, conversationLanguage, restoreChatLanguage } from '../chatLanguage'

describe('customer journey regressions', () => {
  it('matches Arabic spelling variants in names, cities and coastal search', () => {
    for (const query of ['الأهرامات', 'اهرامات', 'أهرامات', 'اَلْأَهْرَامَات']) {
      expect(matchesPlaceSearch(query, ['أهرامات الجيزة'])).toBe(true)
    }
    expect(matchesPlaceSearch('اسكندرية شاطئ', ['شاطئ في الإسكندرية'])).toBe(true)
    expect(matchesPlaceSearch('KARNAK Luxor', ['Karnak Temple', 'Luxor'])).toBe(true)
    expect(matchesPlaceSearch('دهب', ['شاطئ الإسكندرية'])).toBe(false)
  })

  it('restores conversation language while ignoring invalid stored preferences', () => {
    const messages = [{ role: 'user', text: 'Tell me about Cairo' }, { role: 'user', text: 'ok' }]
    expect(conversationLanguage(messages, 'Arabic')).toBe('English')
    sessionStorage.setItem(CHAT_LANGUAGE_KEY, 'invalid')
    expect(restoreChatLanguage(messages, 'Arabic')).toBe('English')
    sessionStorage.setItem(CHAT_LANGUAGE_KEY, 'French')
    expect(restoreChatLanguage(messages, 'Arabic')).toBe('French')
  })

  it('keeps English reply preference after a remount in an Arabic site', async () => {
    localStorage.setItem('masr-guide-lang', 'ar')
    mockApi()
    const user = userEvent.setup()
    const first = render(<App />)
    await user.selectOptions(await screen.findByLabelText('لغة الرد'), 'English')
    first.unmount()
    render(<App />)
    expect(await screen.findByLabelText('لغة الرد')).toHaveValue('English')
    expect(document.documentElement.lang).toBe('ar')
  })

  it('shows guest save feedback outside collapsed options and preserves the draft on sign in', async () => {
    const itinerary = planFor({ pace: 'balanced', language: 'en' })
    itinerary.days[1].stops = []
    itinerary.total_places = 1
    const calls = mockApi({ chat: { answer: 'Your itinerary.', mode: 'local-planner', sources: [], itinerary,
      trip_state: { days: 2, phases: [{ kind: 'history', days: 2, cities: ['Giza', 'Luxor'], interests: ['history'] }], pace: 'balanced', family: false } } })
    localStorage.setItem('masr-guide-lang', 'en')
    const user = userEvent.setup()
    render(<App />)
    await user.type(await screen.findByLabelText('Ask the tour guide'), 'Plan 2 days in Giza and Luxor')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await user.click(await screen.findByRole('button', { name: 'Save itinerary to my account' }))
    const status = screen.getByText(/Sign in to save your itinerary/).closest('[role="status"]')
    expect(status.closest('details')).toBeNull()
    expect(screen.getByText(/Day 2 — Luxor · Transfer & rest/)).toBeInTheDocument()
    expect(screen.queryByText(/Replace Hurghada/)).not.toBeInTheDocument()
    const draft = sessionStorage.getItem('masr-guide-consult-plan-v2')
    await user.click(screen.getByRole('button', { name: 'Sign in / create account' }))
    await waitFor(() => expect(window.location.hash).toBe('#/account'))
    expect(sessionStorage.getItem('masr-guide-consult-plan-v2')).toBe(draft)
    expect(calls.some(call => call.path === '/my/trips')).toBe(false)
  })
})
