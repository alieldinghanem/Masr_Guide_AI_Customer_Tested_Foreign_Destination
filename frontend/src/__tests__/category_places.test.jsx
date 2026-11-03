import React from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from '../i18n'
import { isSwimmingBeach, matchesPlaceCategory, orderCategoryPlaces } from '../categoryFilters'
import CategoryPlaces from '../components/CategoryPlaces'
import Explore from '../components/Explore'

const entry = (id, city = 'Giza', category = 'Heritage', tags = ['history']) => ({
  id, name:id, name_ar:id, city, category, tags, description:'A catalog place', summary_ar:'مكان في الدليل', visit_minutes:60,
})

describe('category presentation', () => {
  it('ranks the Pyramids and Grand Egyptian Museum before other heritage places without mutating API data', () => {
    const apiOrder = [entry('abu-simbel'), entry('st-catherine-monastery', 'Saint Catherine'), entry('bab-zuwayla', 'Cairo'), entry('hanging-church', 'Cairo'), entry('great-sphinx'), entry('other'), entry('grand-egyptian-museum'), entry('giza-pyramids')]
    expect(orderCategoryPlaces(apiOrder, 'heritage').map(place => place.id)).toEqual([
      'giza-pyramids', 'grand-egyptian-museum', 'hanging-church',
      'bab-zuwayla', 'st-catherine-monastery', 'great-sphinx', 'abu-simbel', 'other',
    ])
    expect(apiOrder[0].id).toBe('abu-simbel')
  })

  it('includes actual waterfront landmarks but not every place in a coastal city', () => {
    expect(matchesPlaceCategory(entry('qaitbay', 'Alexandria', 'Heritage'), 'coast')).toBe(true)
    expect(matchesPlaceCategory(entry('montaza-gardens', 'Alexandria', 'Park', ['nature']), 'coast')).toBe(true)
    expect(matchesPlaceCategory(entry('bibliotheca-alexandrina', 'Alexandria', 'Culture'), 'coast')).toBe(false)
    expect(matchesPlaceCategory(entry('dahab-lagoon', 'Dahab', 'Beach', ['beaches']), 'coast')).toBe(true)
    const coast = [entry('qaitbay'), entry('naama-bay'), entry('ras-mohammed')]
    expect(orderCategoryPlaces(coast, 'coast').map(place => place.id)).toEqual(['naama-bay', 'ras-mohammed', 'qaitbay'])
    expect(isSwimmingBeach(entry('naama-bay'))).toBe(true)
    expect(isSwimmingBeach(entry('giftun-island'))).toBe(true)
    for (const id of ['dahab-lagoon', 'ras-mohammed', 'blue-hole-dahab', 'qaitbay', 'hurghada-marina']) {
      expect(isSwimmingBeach(entry(id))).toBe(false)
    }
  })

  it('separates swimming beach destinations from waterfront sights', async () => {
    const user = userEvent.setup()
    const places = [entry('qaitbay', 'Alexandria', 'Heritage'), entry('ras-mohammed', 'Sharm El Sheikh', 'Nature', ['beaches']), entry('naama-bay', 'Sharm El Sheikh', 'Beach', ['beaches']), entry('giftun-island', 'Hurghada', 'Nature', ['beaches']), entry('dahab-lagoon', 'Dahab', 'Beach', ['beaches'])]
    render(<I18nProvider initial="en"><CategoryPlaces type="coast" places={places} openPlace={vi.fn()} askQuestion={vi.fn()} /></I18nProvider>)
    expect(screen.getByText('10 beach destinations · 2 beach places in the catalog')).toBeInTheDocument()
    expect([...document.querySelectorAll('.mg-coastal-guide h3')].map(el => el.textContent)).toEqual([
      'Sharm El Sheikh', 'North Coast & Alamein', 'Alexandria', 'Marsa Matruh', 'Marsa Alam',
      'Hurghada', 'Dahab', 'Ain Sokhna', 'Nuweiba', 'Safaga',
    ])
    expect(screen.getAllByRole('link', { name:'Destination source' })).toHaveLength(10)
    expect(screen.getByRole('heading', { name:'Marsa Alam' }).closest('.mg-coastal-guide')).toHaveTextContent('Sharm El Luli Beach')
    expect([...document.querySelectorAll('#swimming-beaches-title + p + .mg-category-grid h2')].map(el => el.textContent)).toEqual(['naama-bay', 'giftun-island'])
    expect([...document.querySelectorAll('#coastal-other-title + p + .mg-category-grid h2')].map(el => el.textContent)).toEqual(['dahab-lagoon', 'ras-mohammed', 'qaitbay'])
    await user.type(screen.getByRole('textbox', { name:'Search places' }), 'Marsa Alam')
    expect(screen.getByRole('heading', { name:'Marsa Alam' })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name:'Destination source' })).toHaveLength(1)
    expect(screen.queryByText('No places match that search. Try another term.')).not.toBeInTheDocument()
  })

  it('uses the same landmark priority in the main Explore list', () => {
    const places = [entry('karnak'), entry('st-catherine-monastery', 'Saint Catherine'), entry('hanging-church', 'Cairo'), entry('bab-zuwayla', 'Cairo'), entry('grand-egyptian-museum'), entry('giza-pyramids')]
    render(<I18nProvider initial="en"><Explore places={places} cities={['Giza']} interests={['history']} highlight={null} setHighlight={vi.fn()} askQuestion={vi.fn()} openDetails={vi.fn()} /></I18nProvider>)
    expect([...document.querySelectorAll('.place-row .place-title')].map(el => el.textContent)).toEqual([
      'giza-pyramids', 'grand-egyptian-museum', 'hanging-church', 'bab-zuwayla', 'st-catherine-monastery', 'karnak',
    ])
  })

  it('labels official coastal ideas in Arabic', () => {
    render(<I18nProvider initial="ar"><CategoryPlaces type="coast" places={[]} openPlace={vi.fn()} askQuestion={vi.fn()} /></I18nProvider>)
    expect(screen.getByText('مصر على البحر')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name:'وجهات شاطئية للنزول للمياه' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name:'مرسى علم' })).toBeInTheDocument()
  })

  it('shows the new Cairo heritage sites with individual photo credits', () => {
    const places = [entry('bab-zuwayla', 'Cairo'), entry('hanging-church', 'Cairo'), entry('grand-egyptian-museum'), entry('giza-pyramids')]
    render(<I18nProvider initial="ar"><CategoryPlaces type="heritage" places={places} openPlace={vi.fn()} askQuestion={vi.fn()} /></I18nProvider>)
    expect(screen.getByText('مصر عبر العصور')).toBeInTheDocument()
    expect([...document.querySelectorAll('.mg-place-card h2')].map(el => el.textContent)).toEqual([
      'giza-pyramids', 'grand-egyptian-museum', 'hanging-church', 'bab-zuwayla',
    ])
    expect(screen.getAllByRole('link', { name: /الصورة:/ })).toHaveLength(2)
  })
})
