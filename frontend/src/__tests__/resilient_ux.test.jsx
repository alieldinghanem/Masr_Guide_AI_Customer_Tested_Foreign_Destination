import React from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { mockApi } from './fixtures'
import { MESSAGES } from '../messages'

const reply = (data, status = 200) => ({ ok: status < 400, status, json: async () => data })
beforeEach(() => {
  window.history.replaceState(null, '', '/#/explore')
  localStorage.setItem('masr-guide-lang', 'en')
})

describe('recoverable visitor experience', () => {
  it('does not mistake an unavailable status endpoint for temporary account storage', async () => {
    window.history.replaceState(null, '', '/#/account')
    mockApi()
    const original = fetch
    vi.stubGlobal('fetch', vi.fn((url, options) => String(url) === '/api/health'
      ? Promise.resolve(reply({ detail: 'Temporarily unavailable' }, 503)) : original(url, options)))
    render(<App />)
    await screen.findByRole('button', { name: 'Retry connection' })
    expect(screen.getByText(/Checking registration availability/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Create an account' })).not.toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/Storage is temporary|temporary-storage public preview/)
  })

  it.each(['/health', '/cities'])('keeps attractions usable when %s fails and recovers on retry', async failedPath => {
    mockApi()
    const original = fetch
    let failing = true
    vi.stubGlobal('fetch', vi.fn((url, options) => {
      if (String(url) === `/api${failedPath}` && failing) return Promise.resolve(reply({ detail: 'Temporarily unavailable' }, 503))
      return original(url, options)
    }))
    render(<App />)
    expect(await screen.findByRole('button', { name: 'Retry connection' })).toBeInTheDocument()
    expect(screen.getAllByText('Karnak Temple Complex').length).toBeGreaterThan(0)
    failing = false
    await userEvent.click(screen.getByRole('button', { name: 'Retry connection' }))
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Retry connection' })).not.toBeInTheDocument())
    expect(screen.getAllByText('Karnak Temple Complex').length).toBeGreaterThan(0)
  })

  it.each(['en', 'ar'])('retries failed account favorites without a false empty or synced state (%s)', async lang => {
    localStorage.setItem('masr-guide-lang', lang)
    sessionStorage.setItem('masr-account-session-v4', JSON.stringify({ token: 'test-only-session', user: { email: 'visitor@example.org' } }))
    window.history.replaceState(null, '', '/#/saved')
    mockApi()
    const original = fetch
    let settle
    let favoriteRequests = 0
    vi.stubGlobal('fetch', vi.fn((url, options) => {
      if (String(url) === '/api/my/favorites') {
        favoriteRequests++
        return favoriteRequests === 1 ? new Promise(resolve => { settle = resolve }) : Promise.resolve(reply({ place_ids: ['karnak'] }))
      }
      return original(url, options)
    }))
    render(<App />)
    const loading = lang === 'ar' ? 'جار تحميل المفضلة...' : 'Loading favorites...'
    const empty = lang === 'ar' ? 'لسه مفيش أماكن محفوظة' : 'Your Egypt wishlist starts here'
    const synced = lang === 'ar' ? 'مزامنة مع حسابك.' : 'Synced with your travel account.'
    expect(await screen.findByText(loading)).toBeInTheDocument()
    expect(screen.queryByText(empty)).not.toBeInTheDocument()
    expect(screen.queryByText(synced)).not.toBeInTheDocument()
    await act(async () => settle(reply({ detail: 'Temporarily unavailable' }, 503)))
    expect(await screen.findByText(MESSAGES[lang]['saved.error.load'])).toBeInTheDocument()
    expect(screen.queryByText(empty)).not.toBeInTheDocument()
    expect(screen.queryByText(synced)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: MESSAGES[lang]['nav.retry'] }))
    expect(await screen.findByText(synced)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: lang === 'ar' ? 'معبد الكرنك' : 'Karnak Temple Complex' })).toBeInTheDocument()
    expect(screen.queryByText(MESSAGES[lang]['saved.error.load'])).not.toBeInTheDocument()
    expect(favoriteRequests).toBe(2)
  })

  it.each(['en', 'ar'])('shows visitor-facing network recovery guidance (%s)', async lang => {
    localStorage.setItem('masr-guide-lang', lang)
    mockApi({ failNetwork: true })
    render(<App />)
    expect(await screen.findByText(MESSAGES[lang]['err.network'])).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/FastAPI|8000/)
  })
})
