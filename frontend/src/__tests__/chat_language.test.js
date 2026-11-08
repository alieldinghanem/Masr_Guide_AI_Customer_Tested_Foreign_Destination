import { describe, expect, it } from 'vitest'
import { inferChatLanguage } from '../chatLanguage'

describe('chat response language', () => {
  it('follows full English and Arabic visitor messages across site locales', () => {
    expect(inferChatLanguage('Tell me about Karnak', 'Arabic')).toBe('English')
    expect(inferChatLanguage('I want to visit الأهرامات', 'Arabic')).toBe('English')
    expect(inferChatLanguage('حدثني عن الكرنك', 'English')).toBe('Arabic')
    expect(inferChatLanguage('عايز أزور Karnak', 'English')).toBe('Arabic')
  })

  it('keeps context for short acknowledgements and honours explicit requests', () => {
    expect(inferChatLanguage('ok', 'Arabic')).toBe('Arabic')
    expect(inferChatLanguage('Cairo', 'Arabic')).toBe('Arabic')
    expect(inferChatLanguage('رد بالإنجليزي عن القاهرة', 'Arabic')).toBe('English')
  })
})
