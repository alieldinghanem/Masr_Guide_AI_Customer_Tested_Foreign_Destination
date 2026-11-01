import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const component = readFileSync(new URL('../src/components/Guide.jsx', import.meta.url), 'utf8')
const translations = readFileSync(new URL('../src/messages.js', import.meta.url), 'utf8')

for (const mode of ['openai-configured', 'openai-rag', 'openai-intent+local-planner', 'hotel-openai-assisted']) {
  test(`GPT mode ${mode} has React status and AR/EN label`, () => {
    assert.ok(component.includes(`'${mode}'`))
    assert.equal(translations.split(`'guide.status.${mode}'`).length, 3)
  })
}
