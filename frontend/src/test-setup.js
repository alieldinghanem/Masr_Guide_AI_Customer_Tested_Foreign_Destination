import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  try { localStorage.clear(); sessionStorage.clear() } catch { /* ignore */ }
  document.documentElement.dir = 'ltr'
  document.documentElement.lang = 'en'
})
window.scrollTo = () => {}
