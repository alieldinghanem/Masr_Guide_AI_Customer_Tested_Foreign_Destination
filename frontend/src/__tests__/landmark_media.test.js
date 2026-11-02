import { describe, expect, it } from 'vitest'
import { PHOTO_FILES, LANDMARK_MEDIA, DESTINATION_MEDIA, LANDMARK_FRAMING, getLandmarkFraming } from '../components/EditorialMedia'

describe('landmark photo accuracy', () => {
  it('gives each curated attraction its own real distinct licensed-image file', () => {
    expect(Object.keys(PHOTO_FILES)).toHaveLength(50)
    expect(new Set(Object.values(PHOTO_FILES)).size).toBe(50)
    for (const [id, filename] of Object.entries(PHOTO_FILES)) {
      expect(id).toBeTruthy()
      expect(filename).toMatch(/\.(?:jpe?g|png)$/i)
      expect(LANDMARK_MEDIA[id]).toContain('https://commons.wikimedia.org/wiki/Special:FilePath/')
      expect(LANDMARK_MEDIA[id]).toContain(encodeURIComponent(filename))
    }
  })
  it('has a representative, nonempty photo for all twelve destination cities', () => {
    const cities = ['Giza','Cairo','Luxor','Aswan','Abu Simbel','Alexandria','Sharm El Sheikh','Hurghada','Siwa','Fayoum','Dahab','Saint Catherine']
    expect(Object.keys(DESTINATION_MEDIA).sort()).toEqual(cities.sort())
    for (const city of cities) expect(DESTINATION_MEDIA[city]).toContain('Special:FilePath/')
  })
  it('uses a wider courtyard photo and preserves the subject on narrow phones', () => {
    expect(PHOTO_FILES['ibn-tulun-mosque']).toBe('Mosque of Ibn Tulun 2019.jpg')
    const framing = getLandmarkFraming('ibn-tulun-mosque')
    expect(framing['--mg-image-position']).toBe('50% 65%')
    expect(framing['--mg-mobile-image-position']).toBe('50% 67%')
  })
  it('provides valid CSS focal positions and safe fallbacks for all places', () => {
    for (const id of Object.keys(PHOTO_FILES)) {
      const framing = getLandmarkFraming(id)
      expect(framing['--mg-image-position']).toMatch(/^\\d{1,3}% \\d{1,3}%$/)
      expect(framing['--mg-mobile-image-position']).toMatch(/^\\d{1,3}% \\d{1,3}%$/)
    }
    expect(Object.keys(LANDMARK_FRAMING).length).toBeGreaterThan(20)
    expect(getLandmarkFraming('unknown-place')['--mg-image-position']).toBe('50% 50%')
  })
})
