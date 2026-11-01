/** Classify a place by its actual experience rather than the city's location.
 * A coastal city can also contain libraries, shopping centers and historic sites.
 */
export function matchesPlaceCategory(place, type) {
  if (!place || typeof place !== 'object') return false
  const category = String(place.category || '').toLowerCase()
  const tags = Array.isArray(place.tags) ? place.tags.map(tag => String(tag).toLowerCase()) : []
  if (type === 'coast') return category === 'beach' || tags.includes('beaches')
  if (type === 'heritage') return ['heritage', 'museum'].includes(category) || (category === 'landmark' && tags.includes('history'))
  return false
}
