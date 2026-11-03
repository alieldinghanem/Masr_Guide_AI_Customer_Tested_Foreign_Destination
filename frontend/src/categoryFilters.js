/** Classify a place by its actual experience rather than the city's location.
 * A coastal city can also contain libraries, shopping centers and historic sites.
 */
const HERITAGE_PRIORITY = [
  'giza-pyramids', 'grand-egyptian-museum', 'hanging-church',
  'bab-zuwayla', 'st-catherine-monastery', 'great-sphinx',
  'egyptian-museum-tahrir', 'saqqara', 'karnak', 'luxor-temple',
  'valley-of-kings', 'abu-simbel',
]
const COAST_PRIORITY = [
  'naama-bay', 'giftun-island', 'dahab-lagoon',
  'el-gouna', 'ras-mohammed', 'blue-hole-dahab', 'hurghada-marina',
  'montaza-gardens', 'qaitbay',
]
const COASTAL_LANDMARKS = new Set(['qaitbay', 'montaza-gardens'])
const SWIMMING_BEACHES = new Set(['naama-bay', 'giftun-island'])

export function isSwimmingBeach(place) {
  return !!place && SWIMMING_BEACHES.has(place.id)
}

export function matchesPlaceCategory(place, type) {
  if (!place || typeof place !== 'object') return false
  const category = String(place.category || '').toLowerCase()
  const tags = Array.isArray(place.tags) ? place.tags.map(tag => String(tag).toLowerCase()) : []
  if (type === 'coast') return category === 'beach' || tags.includes('beaches') || COASTAL_LANDMARKS.has(place.id)
  if (type === 'heritage') return ['heritage', 'museum'].includes(category) || (category === 'landmark' && tags.includes('history'))
  return false
}

/** Put the places visitors ask for first, then retain the API's order. */
export function orderCategoryPlaces(places, type) {
  const priority = type === 'heritage' ? HERITAGE_PRIORITY : type === 'coast' ? COAST_PRIORITY : null
  if (!priority) return places
  const rank = new Map(priority.map((id, index) => [id, index]))
  return places.map((place, index) => ({ place, index })).sort((a, b) =>
    (rank.get(a.place.id) ?? Infinity) - (rank.get(b.place.id) ?? Infinity) || a.index - b.index
  ).map(({ place }) => place)
}
