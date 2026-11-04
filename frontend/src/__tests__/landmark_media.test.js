import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { PHOTO_FILES, LANDMARK_MEDIA, LANDMARK_THUMBNAILS, PHOTO_CREDITS, DESTINATION_MEDIA, LANDMARK_FRAMING, getLandmarkFraming } from '../components/EditorialMedia'

describe('landmark photo accuracy', () => {
  it('bundles both image sizes and source credits for every curated attraction', () => {
    expect(Object.keys(PHOTO_FILES)).toHaveLength(53)
    expect(new Set(Object.values(PHOTO_FILES)).size).toBe(53)
    expect(Object.keys(PHOTO_CREDITS)).toEqual(Object.keys(PHOTO_FILES))
    for (const [id, filename] of Object.entries(PHOTO_FILES)) {
      expect(id).toBeTruthy()
      expect(filename).toMatch(/\.(?:jpe?g|png)$/i)
      for (const [path, minimumBytes] of [[LANDMARK_MEDIA[id], 30000], [LANDMARK_THUMBNAILS[id], 4000]]) {
        expect(path).toMatch(/^\/assets\/places\/[a-z0-9-]+(?:-thumb)?\.jpg$/)
        const bytes = readFileSync(`public${path}`)
        expect(bytes.length).toBeGreaterThan(minimumBytes)
        expect([...bytes.subarray(0, 3)]).toEqual([0xff, 0xd8, 0xff])
      }
      expect(PHOTO_CREDITS[id].author).toBeTruthy()
      expect(PHOTO_CREDITS[id].url).toContain('https://commons.wikimedia.org/wiki/File:')
      expect(PHOTO_CREDITS[id].license).toMatch(/^(CC |Public domain)/)
      if (PHOTO_CREDITS[id].license !== 'Public domain') expect(PHOTO_CREDITS[id].licenseUrl).toContain('https://creativecommons.org/licenses/')
    }
  })
  it('has a representative, nonempty photo for all twelve destination cities', () => {
    const cities = ['Giza','Cairo','Luxor','Aswan','Abu Simbel','Alexandria','Sharm El Sheikh','Hurghada','Siwa','Fayoum','Dahab','Saint Catherine']
    expect(Object.keys(DESTINATION_MEDIA).sort()).toEqual(cities.sort())
    for (const city of cities) expect(DESTINATION_MEDIA[city]).toMatch(/^\/assets\/places\//)
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
      expect(framing['--mg-image-position']).toMatch(/^\d{1,3}% \d{1,3}%$/)
      expect(framing['--mg-mobile-image-position']).toMatch(/^\d{1,3}% \d{1,3}%$/)
    }
    expect(Object.keys(LANDMARK_FRAMING).length).toBeGreaterThan(20)
    expect(getLandmarkFraming('unknown-place')['--mg-image-position']).toBe('50% 50%')
  })
})
