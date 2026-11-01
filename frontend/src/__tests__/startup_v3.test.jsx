import React from 'react'
import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { mockApi } from './fixtures'

beforeEach(() => {
  window.history.replaceState(null, '', '/')
  localStorage.clear()
  localStorage.setItem('masr-guide-lang', 'en')
})

const renderApp = async () => {
  mockApi()
  const user = userEvent.setup()
  render(<App />)
  await screen.findByRole('heading', {level:1, name:/Discover Egypt, your way/})
  return user
}

describe('TravelTech discovery MVP', () => {
  it('navigates beyond AI into real destination, experiences and essentials views', async () => {
    const user = await renderApp()
    await user.click(within(screen.getByRole('navigation', {name:'Primary navigation'})).getByRole('button', {name: 'Recommendations'}))
    expect(screen.getByRole('heading', {name:/Find your next/})).toBeInTheDocument()
    expect(screen.getByText('Mediterranean soul')).toBeInTheDocument()
    await user.click(within(screen.getByRole('navigation', {name:'Primary navigation'})).getByRole('button', {name:'Travel Tips'}))
    expect(screen.getByRole('heading', {name:/Travel with/})).toBeInTheDocument()
    await user.click(within(screen.getByRole('navigation', {name:'Primary navigation'})).getByRole('button', {name:'Travel Tips'}))
    expect(screen.getByRole('link', {name:/Egypt e-Visa/})).toHaveAttribute('href','https://www.visa2egypt.gov.eg/')
  })

  it('saves an attraction locally and it stays visible under Saved places', async () => {
    const user=await renderApp()
    await user.click(within(screen.getByRole('navigation', {name:'Primary navigation'})).getByRole('button',{name:'Recommendations'}))
    await user.click((await screen.findAllByRole('button',{name:'Explore places'}))[0])
    await user.click(screen.getByRole('button',{name:'Save place'}))
    expect(JSON.parse(localStorage.getItem('masr-guide-saved-places-v3'))).toHaveLength(1)
    await user.click(within(screen.getByRole('banner')).getByRole('button',{name:'Saved places'}))
    expect(screen.getByText('1 saved places')).toBeInTheDocument()
    await user.click(screen.getByRole('button',{name:'Remove'}))
    expect(JSON.parse(localStorage.getItem('masr-guide-saved-places-v3'))).toHaveLength(0)
  })

  it('filters discovery by experience theme', async () => {
    const user = await renderApp()
    await user.click(within(screen.getByRole('contentinfo')).getByRole('button',{name:'Experiences'}))
    await user.click((await screen.findAllByRole('button',{name:'Explore places'}))[0])
    expect(window.location.hash).toBe('#/explore')
    expect(screen.getByRole('combobox',{name:'Filter interest'})).not.toHaveValue('__all__')
  })
})
