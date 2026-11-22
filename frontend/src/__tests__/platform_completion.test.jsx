import React from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from '../i18n'
import AccountEmail from '../components/AccountEmail'
import VisitorComments from '../components/VisitorComments'
import CoastalDetails from '../components/CoastalDetails'
import { COASTAL_DESTINATIONS } from '../coastalDestinations'
import App from '../App'
import { mockApi } from './fixtures'
import { isValidTripState } from '../tripValidation'

beforeEach(() => window.history.replaceState(null, '', '/'))
const reply = data => ({ ok: true, status: 200, json: async () => data })
const wrap = component => render(<I18nProvider initial="en">{component}</I18nProvider>)

describe('platform completion', () => {
  it('discloses unconfigured email without pretending a link was sent', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => reply({ password_recovery: false, email_verification: false })))
    wrap(<AccountEmail />)
    expect(await screen.findByText('Email password recovery is not available yet.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Request reset link' })).not.toBeInTheDocument()
  })

  it('consumes reset links from the fragment, strips them from the URL and never stores the token', async () => {
    const token = 'a'.repeat(54)
    window.history.replaceState(null, '', `/#/account?action=reset&token=${token}`)
    const calls = []
    vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
      calls.push({ url, body: options.body && JSON.parse(options.body) })
      return reply(String(url).endsWith('/confirm') ? { status: 'password_updated' } : { password_recovery: true })
    }))
    const done = vi.fn()
    const user = userEvent.setup()
    wrap(<AccountEmail onPasswordReset={done} />)
    expect(window.location.hash).toBe('#/account')
    await user.type(screen.getByLabelText('New password'), 'Replacement-password-2026!')
    await user.click(screen.getByRole('button', { name: 'Set new password' }))
    expect(await screen.findByText(/Password changed/)).toBeInTheDocument()
    expect(done).toHaveBeenCalledOnce()
    expect(calls.find(call => String(call.url).endsWith('/confirm')).body.token).toBe(token)
    expect(JSON.stringify(sessionStorage)).not.toContain(token)
    expect(JSON.stringify(localStorage)).not.toContain(token)
  })

  it('reports a public comment without sending a claimed author identity', async () => {
    const calls = []
    const id = 'b'.repeat(32)
    vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
      calls.push({ url, ...options })
      return reply(String(url).endsWith('/comments') ? { comments: [{ comment_id: id, name: 'Traveler #123', comment: 'A public comment.', updated_at: '2026-11-22' }], count: 1 } : { status: 'reported' })
    }))
    const user = userEvent.setup()
    wrap(<VisitorComments targetId="giza-pyramids" session={{ token: 'member-token' }} />)
    await user.click(await screen.findByRole('button', { name: 'Report' }))
    await user.selectOptions(screen.getByLabelText('Report reason'), 'privacy')
    await user.click(screen.getByRole('button', { name: 'Send report' }))
    expect(await screen.findByText('Report sent for review.')).toBeInTheDocument()
    const request = calls.find(call => String(call.url).endsWith('/community/reports'))
    expect(JSON.parse(request.body)).toEqual({ target_id: 'giza-pyramids', comment_id: id, reason: 'privacy' })
    expect(request.headers.Authorization).toBe('Bearer member-token')
  })

  it('offers maps, unique destination text and a reversible coastal favorite action', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => reply({ comments: [] })))
    const toggle = vi.fn()
    const user = userEvent.setup()
    wrap(<CoastalDetails destination={COASTAL_DESTINATIONS.find(item => item.id === 'dahab')} toggleSaved={toggle} />)
    expect(screen.getByTitle('Map search for Dahab')).toHaveAttribute('src', expect.stringContaining('maps.google.com'))
    expect(screen.getByText(/town lagoon and Blue Lagoon/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Save this place' }))
    expect(toggle).toHaveBeenCalledWith('coast:dahab')
  })

  it('opens privacy information directly from the footer', async () => {
    mockApi()
    localStorage.setItem('masr-guide-lang', 'en')
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Privacy', exact: true }))
    expect(await screen.findByRole('heading', { name: 'Your privacy and data' })).toBeInTheDocument()
  })

  it('validates new traveler profiles and retains compatibility with old saved trips', () => {
    const state = { days: 3, phases: [{ kind: 'history', days: 3, cities: ['Cairo'] }] }
    expect(isValidTripState(state)).toBe(true)
    const profile = { adults: 2, children_ages: [4, 7], food_preferences: ['halal'] }
    expect(isValidTripState({ ...state, traveler_profile: profile })).toBe(true)
    expect(isValidTripState({ ...state, traveler_profile: { ...profile, children_ages: [true] } })).toBe(false)
    expect(isValidTripState({ ...state, traveler_profile: { ...profile, food_preferences: ['invented'] } })).toBe(false)
  })
})
