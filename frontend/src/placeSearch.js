// Search spelling variants without changing the curated order of collections.
export function normalizePlaceSearch(value = '') {
  return String(value).normalize('NFKD').toLowerCase()
    .replace(/[\u064b-\u065f\u0670\u0640]/g, '')
    .replace(/[أإآٱ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه')
    .replace(/[^\p{L}\p{N}]+/gu, ' ').trim()
    .split(/\s+/).map(word => word.startsWith('ال') && word.length > 3 ? word.slice(2) : word).join(' ')
}

export function matchesPlaceSearch(query, fields) {
  const tokens = normalizePlaceSearch(query).split(' ').filter(Boolean)
  const text = normalizePlaceSearch(fields.filter(Boolean).join(' '))
  return tokens.every(token => text.includes(token))
}
