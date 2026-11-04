import React from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import { isValidPlan } from '../components/Planner'
import { mockApi, planFor } from './fixtures'
import { VISITOR_COUNTRY_KEY } from '../visitorLocale'

const setup = async opts => {
  const calls = mockApi(opts)
  const user = userEvent.setup()
  localStorage.setItem('masr-guide-lang', opts?.lang || 'en')
  render(<App />)
  await waitFor(() => expect(calls.some(c => c.path === '/places')).toBe(true))
  return { calls, user }
}
const nav = name => {
  const arabic = document.documentElement.lang === 'ar'
  const primary = within(screen.getByRole('navigation', { name: arabic ? 'التنقل الرئيسي' : 'Primary navigation' }))
  const quick = within(screen.getByRole('navigation', { name: arabic ? 'التنقل السريع' : 'Quick navigation' }))
  return primary.queryByRole('button', { name }) || quick.queryByRole('button', { name }) || screen.getAllByRole('button', { name })[0]
}

describe('startup', () => {
  it('shows a localised error when the backend is unreachable', async () => {
    mockApi({ failNetwork: true })
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot connect to the backend')
  })
})

describe('navigation and language', () => {
  it('uses the detected Arabic locale for the chat reply language', async () => {
    sessionStorage.setItem(VISITOR_COUNTRY_KEY, 'EG')
    const calls = mockApi()
    const user = userEvent.setup()
    render(<App />)
    const question = await screen.findByLabelText('اسأل المرشد السياحي')
    expect(document.documentElement.dir).toBe('rtl')
    await user.type(question, 'Tell me about Karnak')
    await user.click(screen.getByRole('button', { name: 'إرسال' }))
    await waitFor(() => expect(calls.find(call => call.path === '/consult')?.body?.language).toBe('Arabic'))
  })

  it('opens working AI chat on the homepage', async () => {
    await setup()
    expect(await screen.findByRole('heading', { level: 1, name: /Discover Egypt, your way/ })).toBeInTheDocument()
    expect(screen.getByLabelText('Ask the tour guide')).toBeInTheDocument()
  })

  it('switches the whole UI to Arabic with RTL and back', async () => {
    const { user } = await setup()
    await user.click(screen.getByRole('button', { name: 'Switch to Arabic' }))
    expect(document.documentElement.dir).toBe('rtl')
    expect(nav('المرشد الذكي')).toBeInTheDocument()
    expect(screen.getByLabelText('اسأل المرشد السياحي')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'التبديل إلى الإنجليزية' }))
    expect(document.documentElement.dir).toBe('ltr')
    expect(nav('AI guide')).toBeInTheDocument()
  })

  it('starts in Arabic when the saved language is Arabic', async () => {
    await setup({ lang: 'ar' })
    expect(document.documentElement.dir).toBe('rtl')
    expect(await screen.findByRole('heading', { level: 1, name: /اكتشف مصر بطريقتك/ })).toBeInTheDocument()
  })

  it('offers four real start actions and an honest traveler reviews page', async () => {
    const { user } = await setup()
    const welcome = screen.getByRole('log', { name: 'Conversation' })
    expect(within(welcome).getByRole('button', { name: 'Plan my trip' })).toBeInTheDocument()
    expect(within(welcome).getByRole('button', { name: 'Explore Egypt' })).toBeInTheDocument()
    expect(within(welcome).getByRole('button', { name: 'Safety & help' })).toBeInTheDocument()
    await user.click(within(welcome).getByRole('button', { name: 'Traveler reviews' }))
    expect(window.location.hash).toBe('#/reviews')
    expect(screen.getByRole('heading', { name: 'No visitor ratings yet' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Rate a place or beach destination' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Explore places in Egypt' }))
    expect(window.location.hash).toBe('#/explore')
  })

  it('lets a visitor rate a coastal destination and updates the public ranking', async () => {
    const { user, calls } = await setup()
    await user.click(nav('Traveler reviews'))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Choose a destination' }), 'coast:marsa-alam')
    await user.click(screen.getByRole('button', { name: 'Rate Marsa Alam 5 out of 5' }))
    await waitFor(() => expect(calls.some(call => call.path === '/ratings/coast%3Amarsa-alam' && call.body?.rating === 5)).toBe(true))
    expect(await screen.findByText('Your rating: 5 / 5')).toBeInTheDocument()
    expect(screen.getByRole('listitem')).toHaveTextContent('Marsa Alam')
    expect(screen.getByRole('listitem')).toHaveTextContent('5 / 5')
  })

  it('offers source-backed emergency contacts and scenario steps in both languages', async () => {
    const { user } = await setup()
    await user.click(nav('Travel safety'))
    expect(screen.getByRole('heading', { name: 'Travel safety & help' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Call Ambulance 123' })).toHaveAttribute('href', 'tel:123')
    await user.click(screen.getByRole('button', { name: 'Lost passport' }))
    expect(screen.getByText(/Contact your own embassy or consulate/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Check source/ })).toHaveAttribute('href', 'https://www.gov.uk/foreign-travel-advice/egypt/getting-help')
    await user.click(screen.getByRole('button', { name: 'Switch to Arabic' }))
    expect(screen.getByRole('heading', { name: 'السلامة والمساعدة أثناء الرحلة' })).toBeInTheDocument()
    expect(screen.getByText(/تواصل مع سفارة أو قنصلية بلدك/)).toBeInTheDocument()
  })
})

describe('Discover', () => {
  it('opens a shareable place page with real catalog details and a working save action', async () => {
    const { user } = await setup()
    await user.click(nav('Explore Egypt'))
    await user.type(screen.getByLabelText('Search places'), 'Karnak')
    await user.click(screen.getByRole('button', { name: 'View details' }))
    expect(window.location.hash).toBe('#/place/karnak')
    expect(screen.getByRole('heading', { level: 1, name: 'Karnak Temple Complex' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Place reference' })).toHaveAttribute('href', 'https://example.org/karnak')
    expect(screen.getByRole('heading', { name: 'Rate this place' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Visitor comments/ })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Save place' }))
    expect(screen.getByRole('button', { name: 'Remove saved place' })).toHaveAttribute('aria-pressed', 'true')
    await user.click(within(screen.getByRole('main')).getByRole('button', { name: 'Explore Egypt' }))
    expect(window.location.hash).toBe('#/explore')
  })

  it('opens a photographed heritage place directly and lets visitors comment below its rating', async () => {
    const { user, calls } = await setup()
    await user.click(within(screen.getByRole('contentinfo')).getByRole('button', { name: 'Historical places' }))
    await user.click(await screen.findByRole('button', { name: 'More details about Karnak Temple Complex' }))
    expect(window.location.hash).toBe('#/place/karnak')
    expect(screen.getByRole('img', { name: 'Karnak Temple Complex' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Rate this place' })).toBeInTheDocument()
    await user.type(screen.getByRole('textbox', { name: 'Display name' }), 'Visitor')
    await user.type(screen.getByRole('textbox', { name: 'Your comment about this place' }), 'A great place to visit early.')
    await user.click(screen.getByRole('button', { name: 'Post comment' }))
    expect(await screen.findByText('A great place to visit early.')).toBeInTheDocument()
    expect(calls.some(call => call.path === '/ratings/karnak/comments' && call.method === 'POST')).toBe(true)
    await user.click(within(screen.getByRole('main')).getByRole('button', { name: 'Historical places' }))
    expect(window.location.hash).toBe('#/heritage')
  })

  it('filters by Arabic or English text and shows localised details', async () => {
    const { user } = await setup()
    await user.click(nav('Explore Egypt'))
    expect(screen.getByText('3 places')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Search places'), 'الكرنك')
    expect(screen.getByText('1 places')).toBeInTheDocument()
    const list = screen.getByText('Select a place for details').closest('.place-list')
    expect(within(list).getByText('Karnak Temple Complex')).toBeInTheDocument()
    expect(screen.getByText(/Visit early to avoid the heat/)).toBeInTheDocument()
  })

  it('shows Arabic names and hides English-only tips in Arabic mode', async () => {
    const { user } = await setup({ lang: 'ar' })
    await user.click(nav('اكتشف مصر'))
    expect((await screen.findAllByText('معبد الكرنك')).length).toBeGreaterThan(0)
    expect(screen.queryByText(/Visit early/)).not.toBeInTheDocument()
  })
})

describe('Planner', () => {
  it('sends the request (route optimisation + language) and renders travel info and warnings', async () => {
    const { calls, user } = await setup()
    await user.click(nav('Trip planner'))
    await user.click(screen.getByRole('button', { name: 'Generate my itinerary' }))
    expect(await screen.findByText(/Your suggested/)).toBeInTheDocument()
    const post = calls.find(c => c.path === '/plan')
    expect(post.body).toMatchObject({ optimize_route: true, language: 'en', pace: 'balanced', days: 3 })
    expect(screen.getByText(/Travel from Giza: about 4h \(flight, assumed\)/)).toBeInTheDocument()
    expect(screen.getByText('English warning')).toBeInTheDocument()
    expect(screen.getByText('English disclaimer')).toBeInTheDocument()
    expect(screen.getByText(/Route: Giza → Luxor/)).toBeInTheDocument()
  })

  it('validates days versus cities before calling the API', async () => {
    const { calls, user } = await setup()
    await user.click(nav('Trip planner'))
    await user.click(screen.getByRole('button', { name: 'Giza' }))   // 2 cities now (Cairo is not in fixtures)
    await user.click(screen.getByRole('button', { name: 'Luxor' }))
    const days = screen.getByLabelText(/Number of days/)
    await user.clear(days); await user.type(days, '1')
    await user.click(screen.getByRole('button', { name: 'Generate my itinerary' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/at least one day per selected destination/)
    expect(calls.some(c => c.path === '/plan')).toBe(false)
  })

  it('regenerates the plan in the new language when the UI language changes', async () => {
    const { calls, user } = await setup()
    await user.click(nav('Trip planner'))
    await user.click(screen.getByRole('button', { name: 'Generate my itinerary' }))
    await screen.findByText('English disclaimer')
    await user.click(screen.getByRole('button', { name: 'Switch to Arabic' }))
    expect(await screen.findByText('إخلاء مسؤولية بالعربية')).toBeInTheDocument()
    const posts = calls.filter(c => c.path === '/plan')
    expect(posts).toHaveLength(2)
    expect(posts[1].body.language).toBe('ar')
    expect(screen.getByText(/السفر من الجيزة: حوالي 4س \(بالطيران \(افتراضي\)\)/)).toBeInTheDocument()
  })

  it('saves to localStorage and clears the saved plan', async () => {
    const { user } = await setup()
    await user.click(nav('Trip planner'))
    await user.click(screen.getByRole('button', { name: 'Generate my itinerary' }))
    await user.click(await screen.findByRole('button', { name: 'Save this plan' }))
    expect(localStorage.getItem('masr-guide-plan-v1')).toContain('"days"')
    await user.click(screen.getByRole('button', { name: 'Clear saved plan' }))
    expect(localStorage.getItem('masr-guide-plan-v1')).toBeNull()
  })

  it('only hydrates plans that match the expected shape', () => {
    expect(isValidPlan(planFor({ pace: 'balanced' }))).toBe(true)
    expect(isValidPlan({ days: [{ day: 'x' }] })).toBe(false)
    expect(isValidPlan(null)).toBe(false)
  })
})

describe('Guide', () => {
  it('sends a question, renders the answer and its source link', async () => {
    const { calls, user } = await setup()
    await user.click(nav('AI guide'))
    await user.type(screen.getByLabelText('Ask the tour guide'), 'Tell me about Karnak')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    expect(await screen.findByText('Karnak is a huge temple complex.')).toBeInTheDocument()
    const link = screen.getByRole('link', { name: /\[1\] Karnak Temple Complex/ })
    expect(link).toHaveAttribute('href', 'https://example.org/karnak')
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'))
    expect(calls.find(c => c.path === '/consult').body).toMatchObject({ message: 'Tell me about Karnak', language: 'English' })
  })

  it('uses Arabic as the response language and Arabic source titles in Arabic mode', async () => {
    const { calls, user } = await setup({ lang: 'ar' })
    await user.click(nav('المرشد الذكي'))
    await user.type(screen.getByLabelText('اسأل المرشد السياحي'), 'حدثني عن الكرنك')
    await user.click(screen.getByRole('button', { name: 'إرسال' }))
    expect(await screen.findByRole('link', { name: /\[1\] معبد الكرنك/ })).toBeInTheDocument()
    expect(calls.find(c => c.path === '/consult').body.language).toBe('Arabic')
  })

  it('shows a localised rate-limit error', async () => {
    const { user } = await setup({ chatStatus: 429 })
    await user.click(nav('AI guide'))
    await user.type(screen.getByLabelText('Ask the tour guide'), 'hello there')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Too many requests')
  })

  it('keeps the chat when navigating between sections', async () => {
    const { user } = await setup()
    await user.click(nav('AI guide'))
    await user.type(screen.getByLabelText('Ask the tour guide'), 'Tell me about Karnak')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await screen.findByText('Karnak is a huge temple complex.')
    await user.click(screen.getByRole('button', { name: 'Historical places' })); await user.click(nav('AI guide'))
    expect(screen.getByText('Karnak is a huge temple complex.')).toBeInTheDocument()
  })
})


describe('AI consultant v2', () => {
  it('keeps an English trip and its source titles in English when the site is Arabic', async () => {
    const plan = planFor({ pace: 'balanced', language: 'en' })
    const { user } = await setup({ lang: 'ar', chat: {
      answer: 'Here is your travel itinerary.', mode: 'local-planner',
      sources: [{ number: 1, id: 'karnak', title: 'Karnak Temple Complex', title_ar: 'معبد الكرنك', url: 'https://example.org/karnak' }],
      trip_state: { days: 2, phases: [{ kind: 'history', days: 2, cities: ['Giza', 'Luxor'], interests: ['history'] }], pace: 'balanced', family: false },
      itinerary: plan,
    } })
    await user.click(nav('المرشد الذكي'))
    await user.selectOptions(screen.getByLabelText('لغة الرد'), 'English')
    await user.type(screen.getByLabelText('اسأل المرشد السياحي'), 'Plan 2 days in Giza and Luxor')
    await user.click(screen.getByRole('button', { name: 'إرسال' }))
    expect(await screen.findByText('Your editable Egypt itinerary')).toBeInTheDocument()
    expect(screen.getByLabelText('اسأل المرشد السياحي').compareDocumentPosition(screen.getByRole('region', { name: 'Suggested itinerary' })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByText(/Day 1 — Giza/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /\[1\] Karnak Temple Complex/ })).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('لغة الرد'), 'Arabic')
    expect(screen.getByRole('link', { name: /\[1\] Karnak Temple Complex/ })).toBeInTheDocument()
  })

  it('shows Arabic city and source names when an Arabic message switches the response language', async () => {
    const plan = planFor({ pace: 'balanced', language: 'ar' })
    const { user } = await setup({ chat: {
      answer: 'دي خطة رحلتك.', mode: 'local-planner',
      sources: [{ id: 'karnak', title: 'Karnak Temple Complex', title_ar: 'معبد الكرنك', url: 'https://example.org/karnak' }],
      trip_state: { days: 2, phases: [{ kind: 'history', days: 2, cities: ['Giza', 'Luxor'], interests: ['history'] }], pace: 'balanced', family: false },
      itinerary: plan,
    } })
    await user.click(nav('AI guide'))
    await user.type(screen.getByLabelText('Ask the tour guide'), 'خطط لي يومين في الجيزة والأقصر')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    expect(await screen.findByText('برنامج رحلتك القابل للتعديل')).toBeInTheDocument()
    expect(screen.getByText(/اليوم 1 — الجيزة/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /\[1\] معبد الكرنك/ })).toBeInTheDocument()
    expect(screen.getByText(/اليوم 2 — الأقصر · 1 زيارة/)).toBeInTheDocument()
  })

  it('shows a real structured itinerary from a natural-language trip request', async () => {
    const plan = planFor({ pace: 'balanced', language: 'en' })
    const { user } = await setup({ chat: {
      answer: 'Here is your travel itinerary.', mode: 'local-planner', sources: [],
      trip_state: { days: 2, phases: [{ kind: 'history', days: 2, cities: ['Giza','Luxor'], interests: ['history'] }], pace: 'balanced', family: false },
      itinerary: plan
    } })
    await user.click(nav('AI guide'))
    await user.type(screen.getByLabelText('Ask the tour guide'), 'Plan 2 days in Luxor and Giza')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    expect(await screen.findByText('Your editable Egypt itinerary')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Open in Trip Planner' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Open in Trip Planner' }))
    expect(await screen.findByText('English disclaimer')).toBeInTheDocument()
  })
})
