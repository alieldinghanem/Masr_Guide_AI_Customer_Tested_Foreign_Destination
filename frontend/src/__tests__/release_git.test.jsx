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
  window.location.hash = '#/home'
  render(<App />)
  await waitFor(() => expect(calls.some(c => c.path === '/places')).toBe(true))
  return { calls, user: userEvent.setup() }
}

describe('GitHub release fixes', () => {
  it('shows a configured AI connection as unverified until a model replies', async () => {
    await boot({ guideMode: 'gemini-configured' })
    expect(await screen.findByText(MESSAGES.en['guide.availability.configured'])).toBeInTheDocument()
    expect(screen.queryByText(MESSAGES.en['guide.availability.local'])).not.toBeInTheDocument()
  })

  it('does not call a configured Gemini service offline after a local greeting', async () => {
    const { user } = await boot({ guideMode: 'gemini-configured',
      chat: { answer: 'Welcome to Egypt!', mode: 'local-assistant', sources: [] } })
    await user.type(screen.getByLabelText('Ask the tour guide'), 'Hello')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await screen.findByText('Welcome to Egypt!')
    expect(screen.getByText(MESSAGES.en['guide.availability.configured'])).toBeInTheDocument()
  })

  it('recognizes a Gemini narrated itinerary as an AI reply', async () => {
    const { user } = await boot({ guideMode: 'gemini-configured',
      chat: { answer: 'Your itinerary is ready.', mode: 'gemini-dialogue+local-planner', sources: [] } })
    await user.type(screen.getByLabelText('Ask the tour guide'), 'Plan my Egypt trip')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await screen.findByText('Your itinerary is ready.')
    expect(screen.getByText(MESSAGES.en['guide.availability.ai'])).toBeInTheDocument()
  })

  it('matches account storage guidance and registration to the backend state', async () => {
    const { user } = await boot({ registrationEnabled: true })
    await user.click(screen.getAllByRole('button', { name: /My account/i })[0])
    expect(await screen.findByRole('button', { name: 'Create an account' })).toBeInTheDocument()
    expect(screen.queryByText(/storage is temporary/i)).not.toBeInTheDocument()
  })

  it('warns when account storage is temporary and registration is unavailable', async () => {
    const { user } = await boot({ registrationEnabled: false })
    await user.click(screen.getAllByRole('button', { name: /My account/i })[0])
    expect(await screen.findByText(/storage is temporary in this preview/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Create an account' })).not.toBeInTheDocument()
  })

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
    expect(paths.filter(path => path.endsWith('/ratings'))).toHaveLength(1)
    expect(paths).toHaveLength(10)
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
