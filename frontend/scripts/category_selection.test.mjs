import test from 'node:test'
import assert from 'node:assert/strict'
import { matchesPlaceCategory } from '../src/categoryFilters.js'

test('coastal city does not automatically make a cultural venue a beach', () => {
  assert.equal(matchesPlaceCategory({ city:'Alexandria', category:'Culture', tags:['culture','museums'] }, 'coast'), false)
  assert.equal(matchesPlaceCategory({ city:'Sharm El Sheikh', category:'Leisure', tags:['food','culture'] }, 'coast'), false)
})

test('actual beach activities remain visible independent of category label', () => {
  assert.equal(matchesPlaceCategory({ city:'Dahab', category:'Nature', tags:['beaches','adventure'] }, 'coast'), true)
  assert.equal(matchesPlaceCategory({ city:'Hurghada', category:'Leisure', tags:['beaches','food'] }, 'coast'), true)
  assert.equal(matchesPlaceCategory({ city:'Dahab', category:'Beach', tags:[] }, 'coast'), true)
})

test('historical, museum and landmark records stay in the history section', () => {
  for (const category of ['Heritage', 'Museum']) {
    assert.equal(matchesPlaceCategory({ category, tags:['culture'] }, 'heritage'), true)
    assert.equal(matchesPlaceCategory({ category, tags:['culture'] }, 'coast'), false)
  }
})

test('a contemporary landmark is not mislabelled as an ancient or historical attraction', () => {
  assert.equal(matchesPlaceCategory({ category:'Landmark', tags:['culture','family'] }, 'heritage'), false)
  assert.equal(matchesPlaceCategory({ category:'Landmark', tags:['history'] }, 'heritage'), true)
})

test('bad records and unknown category pages do not silently match', () => {
  assert.equal(matchesPlaceCategory(null, 'coast'), false)
  assert.equal(matchesPlaceCategory({ category:'Beach' }, 'unknown'), false)
})
