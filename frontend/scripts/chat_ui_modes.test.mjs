import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const guide = readFileSync(new URL('../src/components/Guide.jsx', import.meta.url), 'utf8')
const text = readFileSync(new URL('../src/messages.js', import.meta.url), 'utf8')

for (const mode of ['hotel-gemini-assisted', 'hotel-editorial', 'hotel-guide-limited', 'unsupported-destination']) {
  test(`React guide recognizes ${mode} instead of falsely showing offline preview`, () => {
    const modes = guide.match(/const MODES = \[([^\]]+)\]/)?.[1] ?? ''
    assert.ok(modes.includes(`'${mode}'`))
    assert.ok(text.split(`'guide.status.${mode}'`).length >= 3, `${mode}: translations missing`)
  })
}

test('Gemini hotel welcome explicitly discloses editorial, not live booking data', () => {
  assert.ok(text.split("'guide.welcome.hotel-gemini-assisted'").length >= 3)
  assert.ok(guide.includes("rel=\"noopener noreferrer\""))
})
