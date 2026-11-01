export class ApiError extends Error {
  constructor(message, { code = 'http', status } = {}) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

/** Same-origin API wrapper with a bounded request lifetime.
 * Chat allows a longer timeout because the AI provider may retry once.
 */
export async function api(path, { method = 'GET', body, token, ifMatch, headers = {} } = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), ['/chat','/consult'].includes(path) ? 65000 : 20000)
  try {
    const response = await fetch(`/api${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(ifMatch ? { 'If-Match': ifMatch } : {}), ...headers },
      signal: controller.signal,
      ...(body === undefined ? {} : { body: JSON.stringify(body) })
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail = data?.detail
      const message = typeof detail === 'string' ? detail :
        Array.isArray(detail) ? detail.map(d => d.msg).join('; ') :
        `Request failed (${response.status})`
      throw new ApiError(message, { status: response.status })
    }
    return data
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (controller.signal.aborted) {
      throw new ApiError('Request timed out. Please try again.', { code: 'timeout' })
    }
    throw new ApiError('Cannot connect to the backend. Start the FastAPI server on port 8000.', { code: 'network' })
  } finally {
    clearTimeout(timeout)
  }
}
