import React from 'react'
import { describe, expect, it, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { mockApi } from './fixtures'

beforeEach(() => { window.history.replaceState(null, '', '/') })

const boot = async (hash = '') => {
  window.history.replaceState(null, '', hash || '/')
  const calls = mockApi()
  localStorage.setItem('masr-guide-lang', 'en')
  render(<App />)
  await waitFor(() => expect(calls.some(c => c.path === '/places')).toBe(true))
  return userEvent.setup()
}

describe('hash routing', () => {
  it('opens the page named in the URL (deep link)', async () => {
    await boot('#/planner')
    expect(await screen.findByRole('heading', { level: 1, name: /Plan your/ })).toBeInTheDocument()
    expect(document.title).toBe('Trip planner · Masr Guide AI')
  })

  it('falls back to Home for unknown routes', async () => {
    await boot('#/nope')
    expect(await screen.findByRole('heading', { level: 1, name: /Discover Egypt, your way/ })).toBeInTheDocument()
  })

  it('updates the URL on navigation and supports the browser back button', async () => {
    const user = await boot()
    await user.click(screen.getByRole('button', { name: 'Explore' }))
    expect(window.location.hash).toBe('#/destinations')
    await user.click(screen.getByRole('button', { name: 'Chat' }))
    expect(window.location.hash).toBe('#/home')
    window.history.back()
    await waitFor(() => expect(window.location.hash).toBe('#/destinations'))
    expect(await screen.findByRole('heading', { level: 1, name: /Find your next/ })).toBeInTheDocument()
  })

  it('marks the active page for assistive technology', async () => {
    const user = await boot()
    await user.click(screen.getByRole('button', { name: 'Explore' }))
    expect(screen.getByRole('button', { name: 'Explore' })).toHaveAttribute('aria-current', 'page')
    expect(within(screen.getByRole('navigation', { name: 'Primary navigation' })).getByRole('button', { name: 'AI Chat' })).not.toHaveAttribute('aria-current')
  })
})

describe('Discover state', () => {
  it('a place opened from elsewhere is visible even if Discover had a conflicting filter', async () => {
    const user = await boot()
    await user.click(screen.getByRole('button', { name: 'Explore' }))
    await user.click((await screen.findAllByRole('button', { name: 'Explore places' }))[0])
    await user.type(screen.getByLabelText('Search places'), 'dahab')
    expect(screen.getByText('1 places')).toBeInTheDocument()
    await user.click(within(screen.getByRole('navigation', { name: 'Primary navigation' })).getByRole('button', { name: 'AI Chat' }))
    await user.click(screen.getByRole('button', { name: 'Historical Places' }))
    await user.click((await screen.findAllByRole('button', { name: /View details/ }))[0])
    expect(await screen.findByRole('heading', { level: 2, name: 'Karnak Temple Complex' })).toBeInTheDocument()
    expect(screen.getByLabelText('Search places')).toHaveValue('')
  })

  it('keeps the user filters when selecting a place inside Discover', async () => {
    const user = await boot('#/explore')
    await user.type(await screen.findByLabelText('Search places'), 'a')
    await user.click(screen.getAllByRole('button', { name: /Dahab Lagoon/ })[0])
    expect(screen.getByLabelText('Search places')).toHaveValue('a')
  })

  it('shows the Arabic visiting tip in Arabic mode', async () => {
    window.history.replaceState(null, '', '#/explore')
    const calls = mockApi()
    localStorage.setItem('masr-guide-lang', 'ar')
    render(<App />)
    await waitFor(() => expect(calls.some(c => c.path === '/places')).toBe(true))
    expect(await screen.findByText(/نصيحة للزيارة/)).toBeInTheDocument()
    expect(screen.getByText(/اذهب مبكراً/)).toBeInTheDocument()
  })
})
