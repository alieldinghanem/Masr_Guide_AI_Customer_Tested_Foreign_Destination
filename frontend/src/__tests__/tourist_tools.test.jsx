import React from 'react'
import { expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PhotoHelper from '../components/PhotoHelper'
import VisitFacts from '../components/VisitFacts'

it('requires an image and provider consent before sending a photo', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch)
  const user = userEvent.setup(); render(<PhotoHelper />)
  await user.click(screen.getByRole('button', { name: 'Compare a product price by photo' }))
  expect(screen.getByRole('button', { name: 'Analyze and compare' })).toBeDisabled()
  await user.click(screen.getByRole('checkbox'))
  expect(screen.getByRole('button', { name: 'Analyze and compare' })).toBeDisabled()
  expect(fetch).not.toHaveBeenCalled()
})

it('photo upload can show an honest no-estimate result and remove it', async () => {
  vi.stubGlobal('createImageBitmap', vi.fn(async () => ({ width: 100, height: 100, close: vi.fn() })))
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ drawImage: vi.fn() })
  vi.spyOn(HTMLCanvasElement.prototype, 'toDataURL').mockReturnValue('data:image/jpeg;base64,encoded-photo')
  const fetch = vi.fn(async () => ({ ok: true, json: async () => ({ observation: { title: 'Papyrus print', confidence: 'high' }, estimate: null, references: [], message: 'Not enough matching references.' }) }))
  vi.stubGlobal('fetch', fetch)
  const user = userEvent.setup(); render(<PhotoHelper />)
  await user.click(screen.getByRole('button', { name: 'Compare a product price by photo' }))
  await user.upload(screen.getByLabelText('Product photo'), new File(['bytes'], 'product.jpg', { type: 'image/jpeg' }))
  await user.type(screen.getByLabelText('City'), 'Cairo')
  await user.click(screen.getByRole('checkbox'))
  await user.click(screen.getByRole('button', { name: 'Analyze and compare' }))
  expect(await screen.findByText('Not enough matching references.')).toBeInTheDocument()
  expect(JSON.parse(fetch.mock.calls[0][1].body).provider_consent).toBe(true)
  await user.click(screen.getByRole('button', { name: 'Remove photo and result' }))
  expect(screen.queryByAltText('Product photo preview')).not.toBeInTheDocument()
  expect(screen.queryByText('Papyrus print')).not.toBeInTheDocument()
  expect(JSON.stringify(sessionStorage) + JSON.stringify(localStorage)).not.toContain('encoded-photo')
})

it('uses the official museum ticket link and labels duration as approximate', () => {
  render(<VisitFacts place={{ id: 'grand-egyptian-museum', visit_minutes: 180, family_friendly: true }} />)
  expect(screen.getByRole('link', { name: 'Official ticketing website' })).toHaveAttribute('href', 'https://tickets.gem.eg/')
  expect(screen.getByText('180 minutes, approximately')).toBeInTheDocument()
})
