/** Safe boundaries for persisted itinerary data, including older browser sessions.
 * Keep this file dependency-free so the contract can be tested with Node alone.
 */
// Frontend read guard mirrors the backend's _validate_saved_itinerary.
// This is defense-in-depth, not a substitute for server-side authorization.
const validLabel = (value, max) => typeof value === 'string' && value.trim().length > 0 && value.length <= max

export function isValidItinerary(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data) || !Array.isArray(data.days) ||
      data.days.length < 1 || data.days.length > 30) return false
  if ('total_places' in data && (!Number.isInteger(data.total_places) || data.total_places < 0)) return false
  if ('accessibility_needs' in data && typeof data.accessibility_needs !== 'boolean') return false
  return data.days.every((day, index) =>
    day && typeof day === 'object' && !Array.isArray(day) &&
    Number.isInteger(day.day) && day.day === index + 1 &&
    validLabel(day.city, 100) &&
    Array.isArray(day.stops) && day.stops.length <= 25 &&
    day.stops.every(stop => stop && typeof stop === 'object' && !Array.isArray(stop) &&
      stop.place && typeof stop.place === 'object' && !Array.isArray(stop.place) &&
      validLabel(stop.place.id, 160) && validLabel(stop.place.name, 160)) &&
    (!('activity_ideas' in day) || (Array.isArray(day.activity_ideas) &&
      day.activity_ideas.length <= 25 && day.activity_ideas.every(x => typeof x === 'string' && x.length <= 400))) &&
    (!('travel' in day) || day.travel === null || (
      day.travel && typeof day.travel === 'object' && !Array.isArray(day.travel) &&
      validLabel(day.travel.from_city, 160) &&
      typeof day.travel.minutes === 'number' && Number.isFinite(day.travel.minutes) &&
      day.travel.minutes >= 0))
  )
}

/** The Planner additionally renders human-readable route, stop and note fields.
 * Validate those fields before hydrating a saved/untrusted browser document.
 */
export function isValidPlannerPlan(plan) {
  return isValidItinerary(plan) &&
    (!('route' in plan) || (Array.isArray(plan.route) && plan.route.length <= 30 &&
      plan.route.every(x => validLabel(x, 100)))) &&
    (!('warnings' in plan) || (Array.isArray(plan.warnings) && plan.warnings.length <= 50 &&
      plan.warnings.every(x => typeof x === 'string' && x.length <= 500))) &&
    (!('disclaimer' in plan) || typeof plan.disclaimer === 'string') &&
    (!('pace' in plan) || typeof plan.pace === 'string') &&
    plan.days.every(day =>
      typeof day.estimated_activity_minutes === 'number' &&
      Number.isFinite(day.estimated_activity_minutes) && day.estimated_activity_minutes >= 0 &&
      (!('rest_minutes' in day) || (Number.isInteger(day.rest_minutes) && day.rest_minutes >= 0 && day.rest_minutes <= 240)) &&
      (!('note' in day) || day.note === null || typeof day.note === 'string') &&
      day.stops.every(stop =>
        (!('matched' in stop) || (Array.isArray(stop.matched) &&
          stop.matched.every(x => typeof x === 'string'))) &&
        (!('why' in stop) || typeof stop.why === 'string') &&
        (!('suggested_visit_minutes' in stop) || (typeof stop.suggested_visit_minutes === 'number' &&
          Number.isFinite(stop.suggested_visit_minutes) && stop.suggested_visit_minutes >= 0))
      )
    )
}

export function isValidTripState(state) {
  if (!state || typeof state !== 'object' || !Number.isInteger(state.days)
      || state.days < 1 || state.days > 30 || !Array.isArray(state.phases)
      || state.phases.length === 0 || state.phases.length > 5) return false
  if ('lighter_cities' in state && (!Array.isArray(state.lighter_cities) || state.lighter_cities.length > 5 ||
      state.lighter_cities.some(city => typeof city !== 'string' || !city.trim()) ||
      new Set(state.lighter_cities).size !== state.lighter_cities.length)) return false
  if ('day_overrides' in state && (state.day_overrides === null ||
      typeof state.day_overrides !== 'object' || Array.isArray(state.day_overrides) ||
      Object.keys(state.day_overrides).length > 30 ||
      Object.entries(state.day_overrides).some(([day, edit]) =>
        !/^[1-9]\d*$/.test(day) || Number(day) > state.days ||
        !edit || typeof edit !== 'object' || edit.max_stops !== 1 ||
        typeof edit.family_friendly !== 'boolean'))) return false
  let count = 0
  for (const phase of state.phases) {
    if (!phase || !Number.isInteger(phase.days) || phase.days < 1 ||
        !['history', 'beach', 'mixed'].includes(phase.kind) ||
        !Array.isArray(phase.cities) || phase.cities.length === 0 || phase.cities.length > 5 ||
        phase.cities.some(city => typeof city !== 'string' || !city.trim()) ||
        new Set(phase.cities).size !== phase.cities.length || phase.days < phase.cities.length) return false
    count += phase.days
  }
  const plannedCities = new Set(state.phases.flatMap(phase => phase.cities))
  return count === state.days && (!state.lighter_cities || state.lighter_cities.every(city => plannedCities.has(city)))
}

/** Cross-check what the traveler requested against the *actual* returned days.
 * Validation must fail closed: matching only total days does not protect a
 * 13 Cairo + 7 Hurghada plan from silently changing to 14 + 6.
 */
export function isCompatibleTripPlan(state, itinerary) {
  if (!isValidTripState(state) || !isValidItinerary(itinerary) ||
      itinerary.days.length !== state.days) return false
  let offset = 0
  for (const phase of state.phases) {
    const segment = itinerary.days.slice(offset, offset + phase.days)
    if (segment.length !== phase.days ||
        segment.some(day => !phase.cities.includes(day.city) ||
          ('phase_kind' in day && day.phase_kind !== phase.kind)) ||
        phase.cities.some(city => !segment.some(day => day.city === city))) return false
    offset += phase.days
  }
  if (state.day_overrides && Object.entries(state.day_overrides).some(([day, edit]) => {
    const entry = itinerary.days[Number(day) - 1]
    return !entry || entry.stops.length > edit.max_stops ||
      (edit.family_friendly && entry.stops.some(stop => stop.place.family_friendly !== true))
  })) return false
  return offset === itinerary.days.length
}
