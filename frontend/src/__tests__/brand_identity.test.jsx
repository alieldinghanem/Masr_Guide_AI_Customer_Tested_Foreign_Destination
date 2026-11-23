import React from 'react'
import { readFileSync } from 'node:fs'
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { I18nProvider } from '../i18n'
import { Logo } from '../components/Common'

describe('approved Masr Guide identity', () => {
  it.each(['en', 'ar'])('keeps an accessible home action and the same brand asset in %s', async language => {
    const go = vi.fn()
    render(<I18nProvider initial={language}><Logo go={go} /></I18nProvider>)
    const button = screen.getByRole('button', { name: language === 'ar' ? 'الصفحة الرئيسية لمصر جايد' : 'Masr Guide AI home' })
    const image = button.querySelector('img')
    expect(image).toHaveAttribute('src', '/assets/brand/masr-guide-logo.svg')
    expect(image).toHaveAttribute('alt', '')
    await userEvent.setup().click(button)
    expect(go).toHaveBeenCalledWith('home')
  })

  it('ships the approved orange artwork with outlined letters and no external font dependency', () => {
    for (const name of ['masr-guide-logo.svg', 'masr-guide-icon.svg']) {
      const svg = readFileSync(`public/assets/brand/${name}`, 'utf8')
      expect(svg).toContain('Masr Guide AI')
      expect(svg).toContain('<path')
      expect(svg).not.toMatch(/<text\b|<script\b|href=|linearGradient/)
      expect([...new Set([...svg.matchAll(/fill="(#[A-Fa-f0-9]+)"/g)].map(match => match[1]))]).toEqual(['#C34A08'])
    }
    expect(readFileSync('public/favicon.svg', 'utf8')).toBe(readFileSync('public/assets/brand/masr-guide-icon.svg', 'utf8'))
  })

  it('provides a real social preview at the metadata dimensions and cache-busts the old favicon', () => {
    const bytes = readFileSync('public/assets/brand/social-preview.png')
    expect(bytes.subarray(1, 4).toString()).toBe('PNG')
    expect([bytes.readUInt32BE(16), bytes.readUInt32BE(20)]).toEqual([1200, 630])
    const html = readFileSync('index.html', 'utf8')
    expect(html).toContain('/favicon.svg?v=brand-20261123')
    expect(html).toContain('/assets/brand/social-preview.png')
    expect(html).toContain('rel="apple-touch-icon"')
  })
})
