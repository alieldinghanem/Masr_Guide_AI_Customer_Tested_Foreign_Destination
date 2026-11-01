import test from 'node:test'
import assert from 'node:assert/strict'
import { likelyPaymentNumber, scrubPaymentNumber } from '../src/paymentSafety.js'

test('browser blocks test card data even with spaces', () => {
  assert.equal(likelyPaymentNumber('Card: 4111 1111 1111 1111'), true)
})
test('browser removes card data without removing adjacent travel text', () => {
  const cleaned = scrubPaymentNumber('Egypt trip, card 4111 1111 1111 1111, thanks')
  assert.equal(cleaned.includes('4111'), false)
  assert.equal(cleaned.includes('Egypt trip'), true)
  assert.equal(cleaned.includes('redacted'), true)
})
test('browser does not block ordinary travel dates or entry visa queries', () => {
  assert.equal(likelyPaymentNumber('Do I need an entry visa in 2026?'), false)
})
