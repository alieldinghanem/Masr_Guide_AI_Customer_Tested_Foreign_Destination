import React from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { mockApi } from './fixtures'
import { MESSAGES } from '../messages'

const boot = async opts => {
  const calls = mockApi(opts)
  localStorage.setItem('masr-guide-lang', 'en')
  render(<App />)
  await waitFor(() => expect(calls.some(c => c.path === '/places')).toBe(true))
  return { calls, user: userEvent.setup() }
}

describe('GitHub release fixes', () => {
  it('keeps offline chat notices visitor-facing in English and Arabic', async () => {
    for (const lang of ['en', 'ar']) {
      for (const mode of ['offline-preview', 'local-assistant', 'offline-fallback', 'needs-clarification', 'unsupported-destination', 'trip-saved', 'needs-authentication']) {
        expect(MESSAGES[lang][`guide.welcome.${mode}`]).toBeTruthy()
      }
      expect(MESSAGES[lang]['guide.welcome.offline-preview']).not.toMatch(/API key|مفتاح API/)
    }
    const { user } = await boot({ chat: { answer: 'Welcome to Egypt!', mode: 'local-assistant', sources: [] } })
    await user.type(screen.getByLabelText('Ask the tour guide'), 'Hello')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await screen.findByText('Welcome to Egypt!')
    expect(screen.getByText(MESSAGES.en['guide.availability.local'])).toBeInTheDocument()
    expect(screen.queryByText('guide.welcome.local-assistant')).not.toBeInTheDocument()
  })

  it('allows retry after a failed initial metadata request', async () => {
    let fail = true
    const originalFetch = vi.fn(async (url) => {
      if (fail) throw new Error('offline')
      const path = String(url).replace(/^\/api/, '')
      return { ok: true, status: 200, json: async () => path === '/cities'
        ? { cities: ['Giza'], interests: ['history'], city_names_ar: {} }
        : path === '/places' ? { places: [] } : { guide_mode: 'offline-preview' } }
    })
    vi.stubGlobal('fetch', originalFetch)
    localStorage.setItem('masr-guide-lang', 'en')
    render(<App />)
    const user = userEvent.setup()
    const retry = await screen.findByRole('button', { name: 'Retry connection' })
    fail = false
    await user.click(retry)
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Retry connection' })).not.toBeInTheDocument())
    // Initial metadata requests are retried; discovery metadata also loads after success.
    const paths = originalFetch.mock.calls.map(([url]) => String(url))
    for (const key of ['/cities', '/places', '/health']) {
      expect(paths.filter(path => path.endsWith(key))).toHaveLength(2)
    }
    expect(paths).toHaveLength(9)
  })

  it('clears the chat when requested', async () => {
    const { user } = await boot()
    await user.type(screen.getByLabelText('Ask the tour guide'), 'Tell me about Karnak')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await screen.findByText('Karnak is a huge temple complex.')
    await user.click(screen.getByRole('button', { name: 'Clear chat' }))
    expect(screen.queryByText('Karnak is a huge temple complex.')).not.toBeInTheDocument()
  })

  it('restores failed chat questions without polluting the history', async () => {
    const { user } = await boot({ chatStatus: 429 })
    await user.type(screen.getByLabelText('Ask the tour guide'), 'Tell me about Karnak')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Too many requests')
    expect(screen.getByLabelText('Ask the tour guide')).toHaveValue('Tell me about Karnak')
    expect(screen.getByRole('button', { name: 'Retry message' })).toBeInTheDocument()
    expect(screen.queryByText('Tell me about Karnak', { selector: '.msg-text' })).not.toBeInTheDocument()
  })

  it('offers itinerary download and print actions after generating a plan', async () => {
    const { user } = await boot()
    await user.click(screen.getByRole('button', { name: 'Plan a journey' }))
    await user.click(screen.getByRole('button', { name: 'Generate my itinerary' }))
    expect(await screen.findByRole('button', { name: 'Download itinerary' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Print plan' })).toBeInTheDocument()
  })
})
