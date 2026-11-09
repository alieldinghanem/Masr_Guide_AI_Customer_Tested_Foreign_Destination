import React from 'react'
import { CircleAlert, Sunrise } from 'lucide-react'
import { useI18n } from '../i18n'
import { DESTINATION_MEDIA } from './EditorialMedia'

export const CITY_IMAGES = {
  ...DESTINATION_MEDIA,
  'Abu Simbel': '/assets/antique-map.jpeg', // generic travel illustration, not presented as a site photograph
}


export const getMapUrl = p => {
  if (!p) return ''
  const { lat, lng } = p
  const bbox = [lng - 0.055, lat - 0.035, lng + 0.055, lat + 0.035].join('%2C')
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat}%2C${lng}`
}

export function ErrorNote({ text }) {
  if (!text) return null
  return <div className="error-note" role="alert"><CircleAlert size={18} />{text}</div>
}

export function Logo({ go }) {
  const { t } = useI18n()
  return (
    <button type="button" className="logo" onClick={() => go('home')} aria-label={t('logo.aria')}>
      <span className="logo-icon"><Sunrise size={23} strokeWidth={2.5} /></span>
      <span dir="ltr">MASR<span className="logo-light">GUIDE</span><span className="logo-ai">.AI</span><small>{t('logo.small')}</small></span>
    </button>
  )
}
