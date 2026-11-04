import { vi } from 'vitest'

export const PLACES = [
  { id: 'karnak', name: 'Karnak Temple Complex', name_ar: 'معبد الكرنك', city: 'Luxor', category: 'Heritage',
    tags: ['history', 'culture'], lat: 25.7188, lng: 32.6573, visit_minutes: 150,
    description: 'Vast ancient temple complex.', summary_ar: 'مجمع معابد مصري قديم ضخم.',
    details: 'Built over about two thousand years.', tip: 'Visit early to avoid the heat.', tip_ar: 'اذهب مبكراً لتفادي الحر.',
    source_url: 'https://example.org/karnak', family_friendly: true },
  { id: 'great-sphinx', name: 'Great Sphinx', name_ar: 'أبو الهول', city: 'Giza', category: 'Heritage',
    tags: ['history'], lat: 29.9753, lng: 31.1376, visit_minutes: 45,
    description: 'Limestone statue beside the pyramids.', summary_ar: 'تمثال ضخم منحوت من الحجر الجيري.',
    details: 'Carved from bedrock.', tip: 'Pair with the pyramids.', tip_ar: 'اجمعه مع الأهرامات.',
    source_url: 'https://example.org/sphinx', family_friendly: true },
  { id: 'dahab-lagoon', name: 'Dahab Lagoon', name_ar: 'لاجون دهب', city: 'Dahab', category: 'Beach',
    tags: ['beaches', 'adventure'], lat: 28.4983, lng: 34.4895, visit_minutes: 120,
    description: 'Calm lagoon for wind sports.', summary_ar: 'لاجون ساحلي ضحل.',
    details: 'Steady winds.', tip: 'Good for beginners.', tip_ar: 'مناسب للمبتدئين.',
    source_url: 'https://example.org/dahab', family_friendly: true },
]
export const CITIES = ['Dahab', 'Giza', 'Luxor']
export const INTERESTS = ['history', 'culture', 'museums', 'nature', 'beaches', 'adventure', 'food', 'family']
export const CITY_NAMES_AR = { Dahab: 'دهب', Giza: 'الجيزة', Luxor: 'الأقصر' }

export const planFor = (body, extra = {}) => ({
  days: [
    { day: 1, city: 'Giza', stops: [{ place: PLACES[1], suggested_visit_minutes: 45, matched: ['history'], why: 'Matches: history' }],
      estimated_activity_minutes: 45, estimated_travel_minutes: 0, travel: null, note: null },
    { day: 2, city: 'Luxor', stops: [{ place: PLACES[0], suggested_visit_minutes: 150, matched: [], why: 'Matches: popular' }],
      estimated_activity_minutes: 150, estimated_travel_minutes: 240,
      travel: { from_city: 'Giza', minutes: 240, mode: 'flight (assumed)', road_km: 600 }, note: null },
  ],
  warnings: [body.language === 'ar' ? 'تحذير بالعربية' : 'English warning'],
  route: ['Giza', 'Luxor'], route_optimized: true, total_travel_minutes: 240, total_places: 2,
  pace: body.pace, budget_usd: null,
  disclaimer: body.language === 'ar' ? 'إخلاء مسؤولية بالعربية' : 'English disclaimer',
  ...extra,
})

/** Stub window.fetch with an in-memory API. Returns the list of recorded calls. */
export function mockApi({ chat, chatStatus = 200, failNetwork = false } = {}) {
  const calls = []
  const ratingVotes = new Map()
  const visitorComments = new Map()
  vi.stubGlobal('fetch', vi.fn(async (url, opts = {}) => {
    if (failNetwork) throw new TypeError('Failed to fetch')
    const path = String(url).replace(/^\/api/, '')
    const body = opts.body ? JSON.parse(opts.body) : undefined
    calls.push({ path, method: opts.method || 'GET', body })
    const reply = (data, status = 200) => ({ ok: status < 400, status, json: async () => data })
    if (path === '/cities') return reply({ cities: CITIES, interests: INTERESTS, city_names_ar: CITY_NAMES_AR, interest_names_ar: {} })
    if (path === '/places') return reply({ places: PLACES })
    if (path === '/health') return reply({ status: 'ok', guide_mode: 'offline-preview' })
    if (path === '/ratings' && (!opts.method || opts.method === 'GET')) {
      const ratings = {}
      for (const [target, votes] of ratingVotes) ratings[target] = { average: Math.round((Array.from(votes.values()).reduce((sum, value) => sum + value, 0) / votes.size) * 10) / 10, count: votes.size }
      return reply({ ratings, temporary_storage: true })
    }
    if (/^\/ratings\/[^/]+\/comments$/.test(path)) {
      const target = decodeURIComponent(path.slice('/ratings/'.length, -'/comments'.length))
      const comments = visitorComments.get(target) || new Map()
      if (opts.method === 'POST') {
        comments.set(body.visitor_id, { name: body.name, comment: body.comment, updated_at: '2026-11-04 00:00:00' })
        visitorComments.set(target, comments)
      }
      return reply({ comments: [...comments.values()], count: comments.size, temporary_storage: true })
    }
    if (path.startsWith('/ratings/') && opts.method === 'POST') {
      const target = decodeURIComponent(path.slice('/ratings/'.length))
      const votes = ratingVotes.get(target) || new Map()
      votes.set(body.visitor_id, body.rating)
      ratingVotes.set(target, votes)
      return reply({ target_id: target, average: Math.round((Array.from(votes.values()).reduce((sum, value) => sum + value, 0) / votes.size) * 10) / 10, count: votes.size, your_rating: body.rating, temporary_storage: true })
    }
    if (path === '/plan') return reply(planFor(body))
    if (path === '/chat' || path === '/consult') {
      if (chatStatus !== 200) return reply({ detail: 'nope' }, chatStatus)
      return reply(chat || { answer: 'Karnak is a huge temple complex.', mode: 'offline-preview',
        sources: [{ number: 1, id: 'karnak', title: 'Karnak Temple Complex', title_ar: 'معبد الكرنك', url: 'https://example.org/karnak' }] })
    }
    return reply({ detail: 'not found' }, 404)
  }))
  return calls
}
