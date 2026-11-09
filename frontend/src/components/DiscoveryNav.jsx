import React from 'react'
import { Compass, Landmark, Waves } from 'lucide-react'
import { useI18n } from '../i18n'

const SECTIONS = [
  ['explore', Compass, 'discovery.all'],
  ['coast', Waves, 'discovery.coast'],
  ['heritage', Landmark, 'discovery.heritage'],
]

export default function DiscoveryNav({ current }) {
  const { t } = useI18n()
  return <nav className="mg-discovery-nav" aria-label={t('discovery.nav')}>
    {SECTIONS.map(([id, Icon, label]) => <a key={id} href={`#/${id}`} className={current === id ? 'active' : ''} aria-current={current === id ? 'page' : undefined}>
      <Icon size={19} aria-hidden="true" /><span>{t(label)}</span>
    </a>)}
  </nav>
}
