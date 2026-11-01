import React from 'react'
import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { mockApi } from './fixtures'

beforeEach(() => {
  localStorage.clear()
  localStorage.setItem('masr-guide-lang','en')
  window.history.replaceState(null,'','/')
})

const boot = async (route = '/') => {
  window.history.replaceState(null,'', route)
  const calls = mockApi()
  render(<App />)
  await waitFor(() => expect(calls.some(c => c.path === '/places')).toBe(true))
  return userEvent.setup()
}

describe('v6 editorial discovery and regression', () => {
  it('starts with AI chat and offers independent heritage destinations', async () => {
    const user = await boot()
    expect(screen.getByRole('heading',{level:1,name:/Discover Egypt, your way/})).toBeInTheDocument()
    expect(screen.getByLabelText('Ask the tour guide')).toBeInTheDocument()
    await user.click(screen.getByRole('button',{name:'Historical Places'}))
    expect(window.location.hash).toBe('#/heritage')
    expect(screen.getByRole('heading',{level:1,name:'Historical places'})).toBeInTheDocument()
  })

  it('keeps operational portfolio and journal routes renderable', async () => {
    await boot('#/project')
    expect(screen.getByRole('heading',{name:'Masr Guide AI',level:1})).toBeInTheDocument()
    expect(screen.getByRole('heading',{name:'Beyond the chatbot'})).toBeInTheDocument()
  })

  it('preserves Arabic RTL and separate coastal navigation', async () => {
    localStorage.setItem('masr-guide-lang','ar')
    const user = await boot()
    expect(document.documentElement.dir).toBe('rtl')
    expect(screen.getByLabelText('اسأل المرشد السياحي')).toBeInTheDocument()
    await user.click(screen.getByRole('button',{name:'الشواطئ والبحر'}))
    expect(window.location.hash).toBe('#/coast')
    expect(screen.getByRole('heading',{level:1,name:'الشواطئ والأماكن البحرية'})).toBeInTheDocument()
  })
})
