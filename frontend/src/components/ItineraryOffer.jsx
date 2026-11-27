import React from 'react'
import { ArrowUpRight } from 'lucide-react'

export default function ItineraryOffer({ offer, arabic }) {
  return (
    <div className="consult-offer">
      <strong><bdi>{offer.title}</bdi></strong>
      <p><bdi>{offer.description}</bdi></p>
      <p>{arabic ? 'مقدم التجربة' : 'Experience provider'}: <bdi>{offer.partner}</bdi></p>
      <p>{arabic
        ? 'رابط تجاري. قد نحصل على عمولة. أكّد السعر النهائي والتوافر والشروط مع الشريك.'
        : 'Commercial link. We may earn a commission. Confirm the total price, availability and terms with the partner.'}</p>
      <p><bdi>{offer.disclosure}</bdi></p>
      <a href={`/api/go/${encodeURIComponent(offer.id)}?from_itinerary=true`}
        target="_blank" rel="noopener noreferrer sponsored">
        {arabic ? 'التفاصيل لدى الشريك' : 'View details with partner'} <ArrowUpRight size={14} aria-hidden="true" />
      </a>
    </div>
  )
}
