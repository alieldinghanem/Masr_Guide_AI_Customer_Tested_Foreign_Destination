// ISO 3166-1 alpha-2 codes for the 22 Arab League member states.
const ARAB_COUNTRIES = new Set([
  'AE', 'BH', 'DJ', 'DZ', 'EG', 'IQ', 'JO', 'KM', 'KW', 'LB', 'LY',
  'MA', 'MR', 'OM', 'PS', 'QA', 'SA', 'SD', 'SO', 'SY', 'TN', 'YE',
])

export const VISITOR_COUNTRY_KEY = 'masr-guide-visitor-country-v1'

export function languageForCountry(country) {
  const code = typeof country === 'string' ? country.trim().toUpperCase() : ''
  if (!/^[A-Z]{2}$/.test(code)) return null
  return ARAB_COUNTRIES.has(code) ? 'ar' : 'en'
}

export async function lookupVisitorCountry(signal) {
  const response = await fetch('https://api.country.is/', {
    credentials: 'omit',
    signal,
  })
  if (!response.ok) return null
  const country = (await response.json())?.country
  return languageForCountry(country) ? country.trim().toUpperCase() : null
}
