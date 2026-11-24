import React from 'react'
import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from '../i18n'
import Account from '../components/Account'
import GoogleSignIn from '../components/GoogleSignIn'
import { api } from '../api'
vi.mock('../api', () => ({ api: vi.fn() }))
vi.mock('../components/AccountEmail', () => ({ default: () => null }))
const wrap = (component, lang = 'en') => render(<I18nProvider initial={lang}>{component}</I18nProvider>)
let callback
beforeEach(() => {
  sessionStorage.clear(); localStorage.clear()
  api.mockReset().mockImplementation(async path => path === '/auth/google/config' ? { enabled: false } : { trips: [] })
  window.google = { accounts: { id: {
    initialize: vi.fn(config => { callback = config.callback }),
    renderButton: vi.fn(container => { const button = document.createElement('button'); button.textContent = 'Google test identity'; button.onclick = () => callback({ credential: 'signed-google-credential' }); container.append(button) }),
  } } }
})
afterEach(() => { delete window.google; vi.restoreAllMocks() })
it('requires matching password confirmation only for signup', async () => {
  const user = userEvent.setup(); wrap(<Account />)
  expect(screen.queryByLabelText('Confirm password')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Create an account' }))
  expect(screen.getByLabelText('Confirm password')).toBeRequired()
  await user.type(screen.getByLabelText('Email'), 'visitor@example.org')
  await user.type(screen.getByLabelText('Password', { exact: true }), 'My-travel-password-2026')
  await user.type(screen.getByLabelText('Confirm password'), 'A-different-password-2026')
  await user.click(screen.getByRole('button', { name: 'Register' }))
  expect(screen.getByRole('alert')).toHaveTextContent('Passwords do not match')
  expect(api.mock.calls.some(([path]) => path === '/auth/register')).toBe(false)
  await user.clear(screen.getByLabelText('Confirm password'))
  await user.type(screen.getByLabelText('Confirm password'), 'My-travel-password-2026')
  api.mockImplementation(async path => path === '/auth/register' ? { token: 'site-session', user: { email: 'visitor@example.org' } } : { trips: [] })
  await user.click(screen.getByRole('button', { name: 'Register' }))
  await waitFor(() => expect(api).toHaveBeenCalledWith('/auth/register', expect.objectContaining({ body: { email: 'visitor@example.org', password: 'My-travel-password-2026', password_confirmation: 'My-travel-password-2026' } })))
})
it('provides Arabic confirmation', async () => {
  wrap(<Account />, 'ar'); await userEvent.click(screen.getByRole('button', { name: 'إنشاء حساب' }))
  expect(screen.getByLabelText('تأكيد كلمة المرور')).toBeRequired()
})
it('honestly disables an unconfigured Google provider', async () => {
  wrap(<GoogleSignIn />)
  expect(await screen.findByRole('button', { name: 'Continue with Google' })).toBeDisabled()
  expect(screen.getByText(/not enabled on this site yet/)).toBeInTheDocument()
  expect(window.google.accounts.id.initialize).not.toHaveBeenCalled()
})
function enableGoogle(exchange) {
  api.mockImplementation(async (path, options) => {
    if (path === '/auth/google/config') return { enabled: true, client_id: 'public.apps.googleusercontent.com' }
    if (path === '/auth/google/challenge') return { nonce: 'browser-bound-nonce' }
    return exchange(path, options)
  })
}
it('exchanges the official button credential and challenge without storing Google tokens', async () => {
  const done = vi.fn(); enableGoogle(async () => ({ token: 'site-token', user: { id: 'existing' } }))
  wrap(<GoogleSignIn onSuccess={done} />)
  await userEvent.click(await screen.findByRole('button', { name: 'Google test identity' }))
  await waitFor(() => expect(done).toHaveBeenCalledWith({ token: 'site-token', user: { id: 'existing' } }))
  expect(api).toHaveBeenCalledWith('/auth/google', expect.objectContaining({ body: { credential: 'signed-google-credential', nonce: 'browser-bound-nonce' } }))
  expect(window.google.accounts.id.initialize).toHaveBeenCalledWith(expect.objectContaining({ auto_select: false }))
  expect(JSON.stringify(sessionStorage)).not.toContain('signed-google-credential')
})
it('requires the old site password to link Google and supports correcting it', async () => {
  const done = vi.fn(); enableGoogle(async (_path, options) => {
    if (!options.body.existing_password) throw { status: 428 }
    if (options.body.existing_password !== 'Correct-password-2026') throw { status: 403 }
    return { token: 'same-account-token', user: { id: 'existing' } }
  })
  const user = userEvent.setup(); wrap(<GoogleSignIn onSuccess={done} />)
  await user.click(await screen.findByRole('button', { name: 'Google test identity' }))
  await user.type(await screen.findByLabelText('Existing account password'), 'Incorrect-password-2026')
  await user.click(screen.getByRole('button', { name: 'Link Google and sign in' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('current password is incorrect')
  await user.clear(screen.getByLabelText('Existing account password'))
  await user.type(screen.getByLabelText('Existing account password'), 'Correct-password-2026')
  await user.click(screen.getByRole('button', { name: 'Link Google and sign in' }))
  await waitFor(() => expect(done).toHaveBeenCalledWith(expect.objectContaining({ user: { id: 'existing' } })))
})
it('deletes a Google-only account using fresh reauthentication and explicit confirmation', async () => {
  sessionStorage.setItem('masr-account-session-v4', JSON.stringify({ token: 'site-token', user: { email: 'visitor@gmail.com' }, auth_methods: { google: true, password: false } }))
  enableGoogle(async path => path === '/auth/google/reauth-delete' ? { google_proof: 'fresh-delete-proof' } : { trips: [] })
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  const user = userEvent.setup(); wrap(<Account />)
  await user.click(screen.getByRole('button', { name: 'Delete my account' }))
  expect(screen.queryByLabelText('Confirm with your current password')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Permanently delete account' })).toBeDisabled()
  await user.click(await screen.findByRole('button', { name: 'Google test identity' }))
  await screen.findByText('Identity confirmed. Confirm deletion within five minutes.')
  await user.click(screen.getByRole('button', { name: 'Permanently delete account' }))
  await waitFor(() => expect(api).toHaveBeenCalledWith('/my/account', expect.objectContaining({ method: 'DELETE', body: { google_proof: 'fresh-delete-proof', confirmation: 'DELETE MY ACCOUNT' } })))
})
