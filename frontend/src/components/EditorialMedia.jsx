import React from 'react'

// Each landmark has its own, identity-checked photograph. Do not reuse the
// city's photo for unrelated monuments, hotels or museums. Wikimedia Commons
// source pages, photographer credits and licenses are linked in /photo-credits.html.
// If a photo cannot be loaded, show the neutral themed cover, not a wrong photo.
const commons = filename =>
  `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(filename)}?width=1000`

export const PHOTO_FILES = {
  'giza-pyramids': 'The Pyramids of GIZA.jpg',
  'great-sphinx': 'GREAT SPHINX OF GIZA.jpg',
  'grand-egyptian-museum': 'Grand Egyptian Museum Facade.jpg',
  saqqara: 'Saqqara stepped pyramid.jpg',
  citadel: 'Citadel of Saladin in Cairo.jpg',
  'egyptian-museum-tahrir': 'Facade of the Egyptian Museum, Tahrir Square, Cairo, Egypt2.jpg',
  'khan-el-khalili': 'Khan El-Khalili.jpg',
  'al-azhar-park': 'Al Azhar park.jpg',
  'ibn-tulun-mosque': 'Ibn Tulun Mosque Courtyard (28835589172).jpg',
  karnak: 'Karnak R11.jpg',
  'luxor-temple': 'Entrance of Luxor Temple.JPG',
  'valley-of-kings': 'Thebes, Luxor, Egypt, Valley of the Kings from above.jpg',
  hatshepsut: 'Temple of Hatshepsut.jpg',
  'colossi-memnon': 'Colossi of Memnon, Egypt 00.jpg',
  philae: 'Philae temple, front view.jpg',
  'aswan-high-dam': 'AswanHighDam Egypt.jpg',
  'abu-simbel': 'Abu Simbel Temple 2022.jpg',
  'bibliotheca-alexandrina': 'Bibliotheca Alexandrina GLAM EGY 05.jpg',
  qaitbay: 'Citadel Qaitbay Alexandria.jpg',
  'montaza-gardens': 'Montaza Palace, Alexandria.jpg',
  'giftun-island': 'Giftun island.jpg',
  'siwa-fortress': 'Shali fortress.jpg',
  'siwa-salt-lakes': 'Outside Siwa Salt Lakes00.jpg',
  'wadi-el-hitan': 'Wadi AlHitan.jpg',
  'st-catherine-monastery': "A full view of Saint Catherine's Monastery.jpg",
  'blue-hole-dahab': 'Dahab Blue Hole.jpg',
}

export const LANDMARK_MEDIA = Object.fromEntries(
  Object.entries(PHOTO_FILES).map(([id, file]) => [id, commons(file)])
)

// City photographs are representative landmarks IN THAT CITY; the more specific
// landmark pages never fall back to a generic city picture.
export const DESTINATION_MEDIA = {
  Giza: LANDMARK_MEDIA['giza-pyramids'],
  Cairo: LANDMARK_MEDIA.citadel,
  Luxor: LANDMARK_MEDIA.karnak,
  Aswan: LANDMARK_MEDIA.philae,
  'Abu Simbel': LANDMARK_MEDIA['abu-simbel'],
  Alexandria: LANDMARK_MEDIA.qaitbay,
  Hurghada: LANDMARK_MEDIA['giftun-island'],
  Siwa: LANDMARK_MEDIA['siwa-fortress'],
  Fayoum: LANDMARK_MEDIA['wadi-el-hitan'],
  Dahab: LANDMARK_MEDIA['blue-hole-dahab'],
  'Saint Catherine': LANDMARK_MEDIA['st-catherine-monastery'],
}

export const EXPERIENCE_MEDIA = {
  history: LANDMARK_MEDIA.hatshepsut,
  beaches: LANDMARK_MEDIA['giftun-island'],
  culture: LANDMARK_MEDIA['khan-el-khalili'],
  food: commons('Egyptian food Koshary.jpg'),
  nature: LANDMARK_MEDIA['siwa-salt-lakes'],
  adventure: LANDMARK_MEDIA['wadi-el-hitan'],
  museums: LANDMARK_MEDIA['grand-egyptian-museum'],
  family: LANDMARK_MEDIA['al-azhar-park'],
}

export function EditorialImage({ src, alt, className = '', eager = false, fallback = null }) {
  const [failed, setFailed] = React.useState(false)
  React.useEffect(() => setFailed(false), [src])
  const actual = failed ? fallback : src
  return actual
    ? <img src={actual} alt={alt} className={className} loading={eager ? 'eager' : 'lazy'}
        decoding="async" onError={() => setFailed(true)} />
    : <span className={`mg-editorial-no-image ${className}`} aria-label="No verified photograph available" />
}
