import test from 'node:test'
import assert from 'node:assert/strict'
import { isValidItinerary, isValidPlannerPlan, isValidTripState, isCompatibleTripPlan } from '../src/tripValidation.js'

const day = (number = 1) => ({ day: number, city: 'Cairo', stops: [{place: {id:'giza',name:'Giza Pyramids'}}] })
const state = () => ({days:2, phases:[{days:2, kind:'history', cities:['Cairo'],interests:['history']}],pace:'balanced'})

test('rejects malformed or imported itineraries before React renders them', () => {
  assert.equal(isValidItinerary({days:[day()]}),true)
  for (const bad of [null,{}, {days:'broken'}, {days:[]}, {days:[null]},
    {days:[{day:1,city:'Cairo',stops:[null]}]},
    {days:[{...day(),stops:[{}]}]},
    {days:[{...day(),stops:[{place:{id:'x'}}]}]},
    {days:[day(2)]},
    {days:[{...day(),activity_ideas:3}]},
    {days:[{...day(),travel:'invalid'}]},
    {days:[{...day(),travel:{minutes:'oops',from_city:'Luxor'}}]}
  ]) assert.equal(isValidItinerary(bad),false,JSON.stringify(bad))
})

test('checks actual itinerary day allocations before restoring a trip state', () => {
  assert.equal(isValidTripState(state()),true)
  assert.equal(isValidTripState({days:20}),false)
  assert.equal(isValidTripState({...state(),days:3}),false)
  assert.equal(isValidTripState({...state(),phases:[{days:2,kind:'history',cities:['Cairo','Cairo']}]}),false)
  assert.equal(isValidTripState({...state(),phases:[{days:2,kind:'beach',cities:[]}]}),false)
})

test('restores a saved day edit only when the edited day satisfies it', () => {
  const trip = {...state(), day_overrides: {'2': {max_stops: 1, family_friendly: true}}}
  const plan = {days: [day(1), {...day(2), stops: [{place: {id:'museum', name:'Museum', family_friendly:true}}]}]}
  assert.equal(isCompatibleTripPlan(trip, plan), true)
  plan.days[1].stops[0].place.family_friendly = false
  assert.equal(isCompatibleTripPlan(trip, plan), false)
  assert.equal(isValidTripState({...trip, day_overrides: {'3': {max_stops:1, family_friendly:true}}}), false)
})

// Regression: preserving just the total number of days is not sufficient.
test('never restore a well-formed but misallocated itinerary', async () => {
  const { isCompatibleTripPlan } = await import('../src/tripValidation.js')
  const trip = { days: 20, phases: [
    { kind: 'history', days: 13, cities: ['Cairo'], interests: ['history'] },
    { kind: 'beach', days: 7, cities: ['Hurghada'], interests: ['beaches'] }
  ], pace: 'balanced', family: false }
  const plan = { days: [
    ...Array.from({ length: 13 }, (_, i) => ({ day: i + 1, city: 'Cairo', phase_kind: 'history', stops: [] })),
    ...Array.from({ length: 7 }, (_, i) => ({ day: i + 14, city: 'Hurghada', phase_kind: 'beach', stops: [] }))
  ] }
  assert.equal(isCompatibleTripPlan(trip, plan), true)
  plan.days[13].city = 'Cairo'
  assert.equal(isValidItinerary(plan), true, 'structurally valid on purpose')
  assert.equal(isCompatibleTripPlan(trip, plan), false, 'allocation 14/6 must never replace 13/7')
})


test('rejects incorrect cities and phase categories even when total days match', async () => {
  const { isCompatibleTripPlan } = await import('../src/tripValidation.js')
  const trip = { days: 3, phases: [
    { kind: 'history', days: 2, cities: ['Cairo', 'Luxor'], interests: ['history'] },
    { kind: 'beach', days: 1, cities: ['Hurghada'], interests: ['beaches'] }
  ] }
  const plan = {days: [
    {day: 1, city: 'Cairo', phase_kind: 'history', stops: []},
    {day: 2, city: 'Luxor', phase_kind: 'history', stops: []},
    {day: 3, city: 'Hurghada', phase_kind: 'beach', stops: []}
  ]}
  assert.equal(isCompatibleTripPlan(trip, plan), true)
  plan.days[1].city = 'Cairo'
  assert.equal(isCompatibleTripPlan(trip, plan), false, 'one of the explicit destinations disappeared')
  plan.days[1].city = 'Luxor'
  plan.days[2].phase_kind = 'history'
  assert.equal(isCompatibleTripPlan(trip, plan), false, 'invalid phase category must not restore')
})


test('client rejects values server would refuse before showing restored travel data', () => {
  const badCases = [
    { ...day(), travel: { from_city: 'Luxor', minutes: -4 } },
    { ...day(), travel: { from_city: ' ', minutes: 90 } },
    { ...day(), travel: { from_city: 'Luxor', minutes: Infinity } },
    { ...day(), activity_ideas: ['x'.repeat(401)] },
    { ...day(), activity_ideas: Array.from({ length: 26 }, () => 'Optional') },
    { ...day(), stops: [{ place: { id: '  ', name: 'Giza' } }] },
    { ...day(), stops: [{ place: { id: 'giza', name: 'x'.repeat(161) } }] },
    { ...day(), city: 'X'.repeat(101) }
  ]
  for (const bad of badCases) {
    assert.equal(isValidItinerary({ days: [bad] }), false, JSON.stringify(bad))
  }
  assert.equal(isValidItinerary({days:[{...day(), travel:{from_city:'Luxor',minutes:0}}]}), true)
})


test('planner refuses corrupted persisted display fields without hiding valid drafts', () => {
  const valid = {days: [{...day(), estimated_activity_minutes: 120}], route: ['Cairo'], warnings: ['Check official opening hours']}
  assert.equal(isValidPlannerPlan(valid), true)
  const broken = [
    {...valid, route: {city: 'Cairo'}},
    {...valid, warnings: 'not an array'},
    {...valid, days: [{...day(), estimated_activity_minutes: Infinity}]},
    {...valid, days: [{...day(), estimated_activity_minutes: 15, stops: [{place: {id:'giza', name:'Giza'}, matched: 'wrong-type'}]}]},
    {...valid, days: [{...day(), estimated_activity_minutes: 15, stops: [{place: {id:'giza', name:'Giza'}, why: {untrusted: true}}]}]},
    {...valid, days: [{...day(), estimated_activity_minutes: 15, note: {untrusted: true}}]}
  ]
  for (const item of broken) assert.equal(isValidPlannerPlan(item), false, JSON.stringify(item))
})

test('accessibility requirement remains a strict boolean on imported itineraries', () => {
  assert.equal(isValidItinerary({days:[day()],accessibility_needs:true}), true)
  assert.equal(isValidItinerary({days:[day()],accessibility_needs:false}), true)
  assert.equal(isValidItinerary({days:[day()],accessibility_needs:'yes'}), false)
  assert.equal(isValidItinerary({days:[day()],accessibility_needs:1}), false)
})


test('rest-only day constraints survive restore without accepting scheduled visits', () => {
  const trip = {...state(), day_overrides: {'1': {max_stops: 0, family_friendly: false}}}
  const plan = {days: [{...day(1), stops: [], note: 'Arrival and rest'}, day(2)]}
  assert.equal(isCompatibleTripPlan(trip, plan), true)
  plan.days[0].stops = day(1).stops
  assert.equal(isCompatibleTripPlan(trip, plan), false)
})

test('required attractions and full swimming days are checked against displayed stops', () => {
  const trip = {days:2, phases:[{days:1, kind:'history', cities:['Giza']},{days:1, kind:'beach', cities:['Hurghada']}], required_place_ids:['giza-pyramids'], swimming_days:1}
  const plan = {days:[{...day(1), city:'Giza', phase_kind:'history', stops:[{place:{id:'giza-pyramids',name:'Pyramids'}}]}, {...day(2), city:'Hurghada', phase_kind:'beach', stops:[], swimming_day:true}]}
  assert.equal(isCompatibleTripPlan(trip, plan), true)
  plan.days[1].travel = {from_city:'Giza', minutes:240}
  assert.equal(isCompatibleTripPlan(trip, plan), false)
  delete plan.days[1].travel
  plan.days[0].stops[0].place.id = 'another-place'
  assert.equal(isCompatibleTripPlan(trip, plan), false)
})
