import React from 'react'
import { describe, expect, it, vi } from 'vitest'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider, useI18n } from '../i18n'
import TravelerCommunity from '../components/TravelerCommunity'
import VisitorComments from '../components/VisitorComments'
import { PLACES, mockApi } from './fixtures'

const SESSION = { token: 'community-test-token', user: { id: 'unit-user' } }
const sample = (extra = {}) => ({ id: 'a'.repeat(32), body: 'Visit early and take a break from the midday heat.', topic: 'tip', target_id: 'karnak', author: 'Traveler #AB12CD', is_owner: true, liked: false, likes_count: 0, replies_count: 0, version: 1, created_at: '2026-11-23T12:00:00+00:00', updated_at: '2026-11-23T12:00:00+00:00', ...extra })
const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data })
function SwitchLanguage() { const { lang, setLang } = useI18n(); return <button onClick={() => setLang(lang === 'en' ? 'ar' : 'en')}>Change language</button> }
const wrap = (node, lang = 'en') => <I18nProvider initial={lang}>{node}<SwitchLanguage /></I18nProvider>

function communityApi({ initial = [], enabled = true, intercept } = {}) {
  mockApi()
  const original = fetch
  let posts = initial
  const replies = []
  const calls = []
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    const path = String(url).replace('/api', '')
    const method = options.method || 'GET'
    const body = options.body ? JSON.parse(options.body) : null
    if (!path.startsWith('/community/')) return original(url, options)
    const call = { path, method, body }
    calls.push(call)
    const handled = intercept?.(call)
    if (handled) return handled
    if (path === '/community/status') return response({ posting_enabled: enabled })
    if (path.startsWith('/community/posts') && method === 'GET' && !/\/[a-f0-9]{32}/.test(path)) {
      const params = new URLSearchParams(path.split('?')[1])
      return response({ posts: posts.filter(post => !params.get('topic') || post.topic === params.get('topic')), next_cursor: null })
    }
    if (path === '/community/posts' && method === 'POST') {
      const post = sample({ ...body, id: body.client_id })
      posts = [post, ...posts]
      return response({ post }, 201)
    }
    if (path.endsWith('/replies')) {
      if (method === 'POST') {
        const reply = sample({ ...body, id: body.client_id })
        replies.push(reply)
        posts = posts.map(post => ({ ...post, replies_count: replies.length }))
        return response({ reply }, 201)
      }
      return response({ replies, next_cursor: null })
    }
    if (path.endsWith('/like')) {
      posts = posts.map(post => ({ ...post, liked: method === 'PUT', likes_count: method === 'PUT' ? 1 : 0 }))
      return response({ post: posts[0] })
    }
    if (path === '/community/content-reports') return response({ status: 'reported' }, 202)
    if (method === 'PATCH') { posts = posts.map(post => ({ ...post, body: body.body, version: post.version + 1 })); return response({ ok: true }) }
    if (method === 'DELETE') { posts = []; return response({ ok: true }) }
    return response({ post: posts[0] })
  }))
  return calls
}

describe('traveler posts and existing place reviews', () => {
  it('keeps place reviews in their own section and opens linked place details', async () => {
    communityApi({ initial: [sample()] })
    const onOpenTarget = vi.fn()
    render(wrap(<TravelerCommunity places={PLACES} onOpenTarget={onOpenTarget} />))
    expect(await screen.findByText(sample().body)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Destination details: Karnak Temple Complex' }))
    expect(onOpenTarget).toHaveBeenCalledWith('karnak')
    expect(screen.getByRole('time')).toHaveAttribute('datetime', sample().created_at)
    await userEvent.click(screen.getByRole('button', { name: 'Place reviews', exact: true }))
    expect(screen.getByRole('heading', { name: 'Rate a place or beach destination' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Travel Egypt, together.' })).not.toBeInTheDocument()
  })

  it.each(['en', 'ar'])('shows retry instead of a false empty community on failure (%s)', async lang => {
    let fail = true
    communityApi({ intercept: call => call.path === '/community/posts' && call.method === 'GET' && fail ? response({}, 503) : null })
    render(wrap(<TravelerCommunity places={PLACES} />, lang))
    const retry = lang === 'ar' ? 'حاول مرة أخرى' : 'Try again'
    expect(await screen.findByRole('button', { name: retry })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: lang === 'ar' ? 'ابدأ أول نقاش' : 'Start the conversation' })).not.toBeInTheDocument()
    fail = false
    await userEvent.click(screen.getByRole('button', { name: retry }))
    expect(await screen.findByRole('heading', { name: lang === 'ar' ? 'ابدأ أول نقاش' : 'Start the conversation' })).toBeInTheDocument()
  })

  it('preserves the draft across a failed send and language change; retry has a stable submission ID', async () => {
    let fail = true
    const calls = communityApi({ intercept: call => call.method === 'POST' && call.path === '/community/posts' && fail ? response({}, 503) : null })
    render(wrap(<TravelerCommunity places={PLACES} session={SESSION} />))
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Write a post' }))
    const draft = screen.getByRole('textbox', { name: 'Your post', exact: true })
    await user.type(draft, 'Which museum is best for a relaxed family visit?')
    await user.click(screen.getByRole('button', { name: 'Publish post', exact: true }))
    expect(await screen.findByText('Could not save this change. Please try again.')).toBeInTheDocument()
    expect(draft).toHaveValue('Which museum is best for a relaxed family visit?')
    await user.click(screen.getByRole('button', { name: 'Change language' }))
    expect(screen.getByRole('textbox', { name: 'منشورك', exact: true })).toHaveValue('Which museum is best for a relaxed family visit?')
    fail = false
    await user.click(screen.getByRole('button', { name: 'انشر المنشور', exact: true }))
    expect(await screen.findByText('تم نشر منشورك.')).toBeInTheDocument()
    const submissions = calls.filter(call => call.method === 'POST' && call.path === '/community/posts')
    expect(submissions).toHaveLength(2)
    expect(submissions[0].body.client_id).toBe(submissions[1].body.client_id)
  })

  it('gates posting honestly when moderation is not configured', async () => {
    communityApi({ enabled: false })
    render(wrap(<TravelerCommunity places={PLACES} session={SESSION} />))
    expect(screen.getByRole('button', { name: 'Write a post' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Write a post' }))
    expect(screen.queryByRole('textbox', { name: 'Your post', exact: true })).not.toBeInTheDocument()
    expect(screen.getByText(/Posting is currently unavailable/)).toBeInTheDocument()
  })

  it('requires sign-in for public interactions', async () => {
    const onSignIn = vi.fn()
    const calls = communityApi({ initial: [sample({ is_owner: false })] })
    render(wrap(<TravelerCommunity places={PLACES} onSignIn={onSignIn} />))
    await screen.findByText(sample().body)
    await userEvent.click(screen.getByRole('button', { name: /Like 0/ }))
    expect(onSignIn).toHaveBeenCalledOnce()
    expect(calls.some(call => call.method === 'PUT')).toBe(false)
  })

  it('likes a post and publishes a reply with updated counts', async () => {
    communityApi({ initial: [sample()] })
    render(wrap(<TravelerCommunity places={PLACES} session={SESSION} />))
    await userEvent.click(await screen.findByRole('button', { name: /Like 0/ }))
    expect(await screen.findByRole('button', { name: /Like 1/ })).toHaveAttribute('aria-pressed', 'true')
    await userEvent.click(screen.getByRole('button', { name: /Replies 0/ }))
    await userEvent.type(await screen.findByRole('textbox', { name: 'Your reply' }), 'Thank you for this practical advice.')
    await userEvent.click(screen.getByRole('button', { name: 'Post reply', exact: true }))
    expect(await screen.findByText('Thank you for this practical advice.')).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /Replies 1/ })).toBeInTheDocument()
  })

  it('preserves an edit when a newer server version rejects it', async () => {
    const calls = communityApi({ initial: [sample()], intercept: call => call.method === 'PATCH' ? response({}, 409) : null })
    render(wrap(<TravelerCommunity places={PLACES} session={SESSION} />))
    await userEvent.click(await screen.findByRole('button', { name: 'Edit', exact: true }))
    const edit = screen.getByRole('textbox', { name: 'Edit', exact: true })
    await userEvent.clear(edit); await userEvent.type(edit, 'My revised travel advice is still a draft.')
    await userEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    expect(await screen.findByText(/This content changed/)).toBeInTheDocument()
    expect(edit).toHaveValue('My revised travel advice is still a draft.')
    expect(calls.find(call => call.method === 'PATCH').body.version).toBe(1)
  })

  it('supports reporting by displayed content version', async () => {
    const calls = communityApi({ initial: [sample({ is_owner: false })] })
    render(wrap(<TravelerCommunity places={PLACES} session={SESSION} />))
    await userEvent.click(await screen.findByRole('button', { name: 'Report', exact: true }))
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Report reason' }), 'unsafe')
    await userEvent.click(screen.getByRole('button', { name: 'Send report', exact: true }))
    expect(await screen.findByText('Report sent for human review.')).toBeInTheDocument()
    expect(calls.find(call => call.path === '/community/content-reports').body).toEqual({ kind: 'post', content_id: 'a'.repeat(32), version: 1, reason: 'unsafe' })
  })

  it('requires a confirmation before removing an owned post', async () => {
    const calls = communityApi({ initial: [sample()] })
    render(wrap(<TravelerCommunity places={PLACES} session={SESSION} />))
    await userEvent.click(await screen.findByRole('button', { name: 'Delete', exact: true }))
    expect(calls.some(call => call.method === 'DELETE')).toBe(false)
    await userEvent.click(screen.getByRole('button', { name: 'Cancel', exact: true }))
    expect(screen.getByText(sample().body)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Delete', exact: true }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirm deletion' }))
    await waitFor(() => expect(screen.queryByText(sample().body)).not.toBeInTheDocument())
    expect(calls.find(call => call.method === 'DELETE').body).toEqual({ version: 1 })
  })

  it('ignores an old filter response after the visitor changes topics', async () => {
    let resolveQuestion
    communityApi({ initial: [sample()], intercept: call => call.path.includes('topic=question') ? new Promise(resolve => { resolveQuestion = resolve }) : null })
    render(wrap(<TravelerCommunity places={PLACES} />))
    await screen.findByText(sample().body)
    const filter = screen.getByRole('group', { name: 'Post topic' })
    await userEvent.click(within(filter).getByRole('button', { name: 'Question', exact: true }))
    await userEvent.click(within(filter).getByRole('button', { name: 'Travel tip', exact: true }))
    await waitFor(() => expect(within(filter).getByRole('button', { name: 'Travel tip' })).toHaveAttribute('aria-pressed', 'true'))
    await act(async () => resolveQuestion(response({ posts: [sample({ body: 'A stale question response.' })], next_cursor: null })))
    expect(screen.queryByText('A stale question response.')).not.toBeInTheDocument()
  })
})

describe('place comment drafts and loading', () => {
  it('keeps a place comment draft when switching languages', async () => {
    mockApi()
    render(wrap(<VisitorComments targetId="karnak" session={SESSION} />))
    const input = await screen.findByRole('textbox', { name: 'Your comment about this place' })
    await waitFor(() => expect(input).not.toBeDisabled())
    await userEvent.type(input, 'A draft about a family visit.')
    await userEvent.click(screen.getByRole('button', { name: 'Change language' }))
    expect(screen.getByRole('textbox', { name: 'تعليقك عن المكان' })).toHaveValue('A draft about a family visit.')
  })

  it('does not present a failed request as no comments and can retry', async () => {
    mockApi()
    const original = fetch
    let fail = true
    vi.stubGlobal('fetch', vi.fn((url, options) => String(url).endsWith('/karnak/comments') && fail ? Promise.resolve(response({}, 503)) : original(url, options)))
    render(wrap(<VisitorComments targetId="karnak" />))
    await screen.findByText('Could not load comments.')
    expect(screen.queryByText('No comments yet. Be the first to comment.')).not.toBeInTheDocument()
    fail = false
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('No comments yet. Be the first to comment.')).toBeInTheDocument()
  })
})
