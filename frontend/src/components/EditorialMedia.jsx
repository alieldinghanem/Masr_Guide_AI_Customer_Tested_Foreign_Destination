import React from 'react'

// Curated Egypt-specific Unsplash images. No misleading image reuse for another city.
// See docs/EDITORIAL_IMAGE_CREDITS.md. If unavailable, the component retains
// a destination-coloured backdrop rather than showing an unrelated location.
const photo = id => `https://images.unsplash.com/${id}?auto=format&fit=crop&w=1100&q=80`
export const DESTINATION_MEDIA = {
  Giza: photo('photo-1678747365851-2f2ebb09911d'),
  Cairo: photo('photo-1719659018185-8a239c35fb4a'),
  Luxor: photo('photo-1609101652237-b4704a00bc50'),
  Aswan: photo('photo-1644517270263-4112379d97ca'),
  Hurghada: photo('photo-1722264221977-3a933a891199'),
  Alexandria: photo('photo-1682090500311-9e57a5a57390'),
  Siwa: photo('photo-1771838877341-36157f26dd58'),
  Dahab: photo('photo-1666593198332-127af3e3536d'),
}
export const EXPERIENCE_MEDIA = {
  history: DESTINATION_MEDIA.Luxor,
  beaches: DESTINATION_MEDIA.Hurghada,
  culture: DESTINATION_MEDIA.Aswan,
  food: '/assets/hieroglyphics.jpeg',
  nature: DESTINATION_MEDIA.Siwa,
  adventure: DESTINATION_MEDIA.Dahab,
  museums: '/assets/gem.jpeg',
  family: DESTINATION_MEDIA.Cairo,
}

export function EditorialImage({ src, alt, className = '', eager = false, fallback = null }) {
  const [failed, setFailed] = React.useState(false)
  React.useEffect(() => setFailed(false), [src])
  const actual = failed ? fallback : src
  return actual ? (
    <img src={actual} alt={alt} className={className} loading={eager ? 'eager' : 'lazy'} decoding="async"
      onError={() => setFailed(true)} />
  ) : null
}
