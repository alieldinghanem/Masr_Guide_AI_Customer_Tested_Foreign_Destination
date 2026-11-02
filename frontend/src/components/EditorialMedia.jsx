import React from 'react'

// Every photographed attraction below has a unique filename that was validated
// against Wikimedia Commons' MediaWiki imageinfo API on 2026-11-02.
// Do not substitute a city-wide image for a specific unrelated attraction.
// Full source/licence credits: /photo-credits.html
const commons = file => `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(file)}?width=1000`

export const PHOTO_FILES = {
  "giza-pyramids": "The Pyramids of GIZA.jpg",
  "great-sphinx": "GREAT SPHINX OF GIZA.jpg",
  "grand-egyptian-museum": "Grand Egyptian Museum 2025.jpg",
  "saqqara": "Pyramid of Djoser 2010.jpg",
  "citadel": "Cairo Citadel (14609281270).jpg",
  "egyptian-museum-tahrir": "Facade of the Egyptian Museum, Tahrir Square, Cairo, Egypt1.jpg",
  "nmec": "National Museum of Egyptian Civilization (NMEC) in Cairo, Egypt 13.jpg",
  "khan-el-khalili": "Khan El-Khalili.jpg",
  "al-azhar-park": "Al-Azhar Park Cairo (2).jpg",
  "coptic-cairo": "Cairo - Coptic area - Hanging Church from courtyard.JPG",
  "museum-of-islamic-art": "Museum of Islamic Art Cairo DSCF7680.jpg",
  "gayer-anderson-museum": "Gayer-Anderson Museum, Cairo 01.jpg",
  "sultan-hassan-mosque": "Mosque-Madrassa of Sultan Hassan.jpg",
  "al-rifai-mosque": "Kairo Rifai Moschee BW 1.jpg",
  "manial-palace-museum": "Mohamed Ali's Palace, Manial, Cairo, Egypt.jpg",
  "baron-empain-palace": "The exterior of the Baron Empain palace.jpg",
  "ibn-tulun-mosque": "Ibn Tulun Mosque, Cairo11.jpg",
  "al-azhar-mosque": "The Courtyard of Al-Azhar Mosque, Cairo, Egypt.jpg",
  "nilometer-roda": "Cairo Roda Nilometer panorama.jpg",
  "al-hakim-mosque": "Al-Hakim Mosque in Cairo.jpg",
  "karnak": "Templo de Karnak, Luxor, Egipto, 2022-04-03, DD 148.jpg",
  "luxor-temple": "The remaining obelisk and the two 25m. statues of Ramses II - The entrance pylon - Luxor Temple (14075065830).jpg",
  "valley-of-kings": "Luxor Valley of the Kings D.jpg",
  "hatshepsut": "Temple of Hatshepsut, Deir el-Bahari, Luxor, Egypt.jpg",
  "colossi-memnon": "Colossi of Memnon, Egypt 00.jpg",
  "philae": "Philae temple, front view.jpg",
  "aswan-high-dam": "AswanHighDam Egypt.jpg",
  "nubian-museum": "Aswan Nubian Museum entrance.jpg",
  "elephantine-island": "Aswan Elephantine Island R02.jpg",
  "abu-simbel": "Abu Simbel Temple 2022.jpg",
  "bibliotheca-alexandrina": "Bibliotheca Alexandrina GLAM EGY 05.jpg",
  "qaitbay": "Citadel Qaitbay Alexandria.jpg",
  "montaza-gardens": "Alexandria - Montaza Palace garden.JPG",
  "catacombs-kom-shoqafa": "Catacombs of Kom El Shoqafa, Alexandria, Egypt.jpg",
  "ras-mohammed": "Ras Mohammed national park - panoramio.jpg",
  "naama-bay": "Naama Bay Beach R01.jpg",
  "soho-square": "Sharm Soho Square R01.jpg",
  "giftun-island": "Giftun island, Hurghada, Egypt - Explore - Flickr - cattan2011.jpg",
  "hurghada-marina": "Hurghada Marina 007.jpg",
  "el-gouna": "El Gouna New Marina R18.jpg",
  "siwa-fortress": "Shali Fortress in Siwa Oasis.jpg",
  "siwa-salt-lakes": "Salt Lakes in Siwa oasis.jpg",
  "oracle-temple": "Siwa Oasis, Temple of the Oracle of Amun, Egypt.jpg",
  "wadi-el-hitan": "Wadi Hitan (Whale Valley) Panorama.jpg",
  "qarun-lake": "Qaroun Lake Fayoum - Egypt.jpg",
  "tunis-village": "Eveline Pottery School - Fayoum (1).JPG",
  "st-catherine-monastery": "A full view of Saint Catherine's Monastery.jpg",
  "mount-sinai": "Lever de soleil Mont Sinaï Egypte - Sunrise Mount Sinai Egypt - Photo image picture (12859772904).jpg",
  "blue-hole-dahab": "Dahab Blue Hole.jpg",
  "dahab-lagoon": "Dahab, Windsurfing in Lagoon.jpg",
}

export const LANDMARK_MEDIA = Object.fromEntries(
  Object.entries(PHOTO_FILES).map(([id, filename]) => [id, commons(filename)])
)

// Cover photos are characteristic views of the named destination, not a shared
// picture used across all attractions inside that destination.
export const DESTINATION_MEDIA = {
  Giza: LANDMARK_MEDIA['giza-pyramids'],
  Cairo: LANDMARK_MEDIA.citadel,
  Luxor: LANDMARK_MEDIA.karnak,
  Aswan: LANDMARK_MEDIA.philae,
  'Abu Simbel': LANDMARK_MEDIA['abu-simbel'],
  Alexandria: LANDMARK_MEDIA.qaitbay,
  'Sharm El Sheikh': LANDMARK_MEDIA['ras-mohammed'],
  Hurghada: LANDMARK_MEDIA['giftun-island'],
  Siwa: LANDMARK_MEDIA['siwa-fortress'],
  Fayoum: LANDMARK_MEDIA['wadi-el-hitan'],
  Dahab: LANDMARK_MEDIA['dahab-lagoon'],
  'Saint Catherine': LANDMARK_MEDIA['st-catherine-monastery'],
}

// Eight different, topic-relevant visuals for the eight editorial categories.
export const EXPERIENCE_MEDIA = {
  history: LANDMARK_MEDIA.hatshepsut,
  beaches: LANDMARK_MEDIA['naama-bay'],
  culture: LANDMARK_MEDIA['khan-el-khalili'],
  food: commons('Egyptian food Koshary.jpg'),
  nature: LANDMARK_MEDIA['siwa-salt-lakes'],
  adventure: LANDMARK_MEDIA['wadi-el-hitan'],
  museums: LANDMARK_MEDIA['grand-egyptian-museum'],
  family: LANDMARK_MEDIA['al-azhar-park'],
}

// A failed/unmapped image never silently displays a different location.
// A decorative fallback avoids a broken image glyph and repeated thumbnails.
export function EditorialImage({ src, alt, className = '', eager = false, fallback = null }) {
  const [failed, setFailed] = React.useState(false)
  React.useEffect(() => setFailed(false), [src])
  const actual = failed ? fallback : src
  return actual
    ? <img src={actual} alt={alt} className={className} loading={eager ? 'eager' : 'lazy'}
        decoding="async" onError={() => setFailed(true)} />
    : <span className={`mg-editorial-no-image ${className}`} aria-hidden="true" />
}
