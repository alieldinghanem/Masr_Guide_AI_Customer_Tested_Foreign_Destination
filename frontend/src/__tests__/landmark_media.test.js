import { describe, expect, it } from 'vitest'
import { PHOTO_FILES, LANDMARK_MEDIA, DESTINATION_MEDIA } from '../components/EditorialMedia'

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
})
