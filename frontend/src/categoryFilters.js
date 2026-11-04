/** Classify a place by its actual experience rather than the city's location.
 * A coastal city can also contain libraries, shopping centers and historic sites.
 */
const HERITAGE_PRIORITY = [
  'giza-pyramids', 'grand-egyptian-museum', 'bab-zuwayla', 'great-sphinx',
  'egyptian-museum-tahrir', 'saqqara', 'karnak', 'luxor-temple',
  'valley-of-kings', 'abu-simbel',
]
export const RELIGIOUS_GROUP_ORDER = ['mosques', 'churches', 'synagogues']
const RELIGIOUS_PLACES = {
  mosques: ['sultan-hassan-mosque', 'al-rifai-mosque', 'ibn-tulun-mosque', 'al-azhar-mosque', 'al-hakim-mosque'],
  churches: ['hanging-church', 'st-catherine-monastery'],
  synagogues: ['ben-ezra-synagogue'],
}
const RELIGIOUS_RANK = new Map(RELIGIOUS_GROUP_ORDER.flatMap((group, groupIndex) =>
  RELIGIOUS_PLACES[group].map((id, placeIndex) => [id, { group, groupIndex, placeIndex }])))
const COAST_PRIORITY = [
  'naama-bay', 'giftun-island', 'dahab-lagoon',
  'el-gouna', 'ras-mohammed', 'blue-hole-dahab', 'hurghada-marina',
  'montaza-gardens', 'qaitbay',
]
const COASTAL_LANDMARKS = new Set(['qaitbay', 'montaza-gardens'])
const SWIMMING_BEACHES = new Set(['naama-bay', 'giftun-island'])

export function getReligiousGroup(place) {
  return RELIGIOUS_RANK.get(place?.id)?.group || null
}

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

/** Keep nonreligious sights first, then group mosques, churches and synagogues. */
export function orderCategoryPlaces(places, type) {
  const priority = type === 'heritage' ? HERITAGE_PRIORITY : type === 'coast' ? COAST_PRIORITY : null
  if (!priority) return places
  const rank = new Map(priority.map((id, index) => [id, index]))
  return places.map((place, index) => ({ place, index })).sort((a, b) => {
    if (type === 'heritage') {
      const first = RELIGIOUS_RANK.get(a.place.id)
      const second = RELIGIOUS_RANK.get(b.place.id)
      const groupDifference = (first?.groupIndex ?? -1) - (second?.groupIndex ?? -1)
      if (groupDifference) return groupDifference
      if (first && second) return first.placeIndex - second.placeIndex || a.index - b.index
    }
    return (rank.get(a.place.id) ?? Infinity) - (rank.get(b.place.id) ?? Infinity) || a.index - b.index
  }).map(({ place }) => place)
}
