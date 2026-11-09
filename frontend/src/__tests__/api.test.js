import { describe, expect, it, vi } from 'vitest'
import { api, ApiError } from '../api'

const respond = (status, data) => vi.stubGlobal('fetch', vi.fn(async () => ({ ok: status < 400, status, json: async () => data })))

describe('api()', () => {
  it('returns parsed JSON and calls the same-origin /api proxy', async () => {
    respond(200, { ok: true })
    expect(await api('/health')).toEqual({ ok: true })
    expect(fetch).toHaveBeenCalledWith('/api/health', expect.objectContaining({ method: 'GET' }))
  })

  it('sends a staff credential only when explicitly passed', async () => {
    respond(200, { ok: true })
    await api('/admin/overview', { headers: { 'X-Admin-Key': 'test-only-placeholder' } })
    expect(fetch.mock.calls[0][1].headers['X-Admin-Key']).toBe('test-only-placeholder')
  })

  it('sends JSON bodies', async () => {
    respond(200, {})
    await api('/chat', { method: 'POST', body: { message: 'hi' } })
    expect(fetch.mock.calls[0][1].body).toBe('{"message":"hi"}')
  })

  it('flags network failures with code=network', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('x') }))
    await expect(api('/x')).rejects.toMatchObject({ code: 'network' })
  })

  it('exposes the HTTP status and string detail', async () => {
    respond(429, { detail: 'Too many guide requests.' })
    const err = await api('/chat').catch(e => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(429)
    expect(err.message).toMatch(/Too many/)
  })

  it('joins FastAPI validation messages', async () => {
    respond(422, { detail: [{ msg: 'bad one' }, { msg: 'bad two' }] })
    await expect(api('/plan')).rejects.toThrow('bad one; bad two')
  })

  it('falls back to a generic message for non-JSON errors', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 500, json: async () => { throw new Error('no json') } })))
    await expect(api('/x')).rejects.toThrow('Request failed (500)')
  })
  it('stops waiting for a non-responsive API and reports a timeout', async () => {
    vi.useFakeTimers()
    try {
      vi.stubGlobal('fetch', vi.fn((_url, options) => new Promise((_resolve, reject) => {
        options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
      })))
      const result = api('/health').catch(error => error)
      await vi.advanceTimersByTimeAsync(20000)
      await expect(result).resolves.toMatchObject({ code: 'timeout' })
    } finally {
      vi.useRealTimers()
    }
  })

})
