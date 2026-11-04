export function sortCoastalGuides(items, ratings, mode) {
  if (mode !== 'rated') return items
  return items.map((item, index) => ({ item, index })).sort((a, b) => {
    const first = ratings[`coast:${a.item.id}`]
    const second = ratings[`coast:${b.item.id}`]
    return (second?.count ? 1 : 0) - (first?.count ? 1 : 0)
      || (second?.average || 0) - (first?.average || 0)
      || (second?.count || 0) - (first?.count || 0)
      || a.index - b.index
  }).map(({ item }) => item)
}
