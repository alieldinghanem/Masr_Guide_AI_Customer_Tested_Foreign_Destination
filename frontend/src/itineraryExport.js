export function attractionMapUrl(place) {
  const { lat, lng } = place
  if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) return ''
  return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=16/${lat}/${lng}`
}

export function itineraryDayPurpose(day, restOnly, arabic) {
  if (day.travel) {
    if (!day.stops.length) return arabic ? 'انتقال وراحة' : 'Transfer & rest'
    return arabic ? 'انتقال بين المدن' : 'City transfer'
  }
  if (day.swimming_day) return arabic ? 'سباحة واسترخاء' : 'Swimming & beach time'
  if (restOnly) return arabic ? 'وصول أو راحة بلا زيارات' : 'Arrival / rest — no visits'
  if (!day.stops.length) return arabic ? 'وقت حر — بدون زيارات مجدولة' : 'Free time — no scheduled visits'
  return ''
}

function referenceUrl(raw) {
  if (typeof raw !== 'string') return ''
  try {
    const url = new URL(raw)
    return url.protocol === 'https:' && !url.username && !url.password ? url.href : ''
  } catch {
    return ''
  }
}

export function formatItinerary(plan, { arabic, cityName, dayOverrides, summary }) {
  const minutes = n => `${n} ${arabic ? 'دقيقة' : 'min'}`
  const lines = [
    arabic ? 'مصر جايد — برنامج الرحلة' : 'Masr Guide AI — Travel itinerary',
    summary || (arabic ? `عدد الأيام: ${plan.days.length}` : `Days: ${plan.days.length}`),
    '',
  ]
  for (const day of plan.days) {
    const purpose = itineraryDayPurpose(day, dayOverrides?.[day.day]?.max_stops === 0, arabic)
    lines.push(`${arabic ? 'اليوم' : 'Day'} ${day.day} — ${cityName(day.city)}${purpose ? ` · ${purpose}` : ''}`)
    if (day.travel) {
      const route = `${cityName(day.travel.from_city)} → ${cityName(day.city)}`
      const estimate = minutes(day.travel.minutes)
      const mode = typeof day.travel.mode === 'string' ? day.travel.mode.split(' ')[0] : ''
      const modeName = mode === 'flight' ? (arabic ? 'طيران' : 'flight')
        : mode === 'road' ? (arabic ? 'طريق بري' : 'road') : ''
      const details = modeName ? `${estimate} · ${modeName}` : estimate
      lines.push(arabic ? `انتقال تقريبي: ${route} (${details})` : `Approximate transfer: ${route} (${details})`)
    }
    if (day.rest_minutes > 0) {
      lines.push(arabic ? `راحة مقترحة: ${minutes(day.rest_minutes)}` : `Suggested rest: ${minutes(day.rest_minutes)}`)
    }
    for (const { place, suggested_visit_minutes: visit } of day.stops) {
      const name = arabic && place.name_ar ? place.name_ar : place.name
      lines.push(`- ${name}${Number.isFinite(visit) && visit > 0 ? ` (${minutes(visit)})` : ''}`)
      const map = attractionMapUrl(place)
      const source = referenceUrl(place.source_url)
      if (map) lines.push(`  ${arabic ? 'الخريطة' : 'Map'}: ${map}`)
      if (source) lines.push(`  ${arabic ? 'المصدر' : 'Reference'}: ${source}`)
    }
    if (day.note) lines.push(day.note)
    for (const idea of day.activity_ideas || []) {
      lines.push(`- ${arabic ? 'فكرة اختيارية غير محجوزة' : 'Optional idea (not booked)'}: ${idea}`)
    }
    lines.push('')
  }
  if (plan.warnings?.length) {
    lines.push(arabic ? 'تنبيهات مهمة قبل السفر' : 'Important travel notes', ...plan.warnings, '')
  }
  if (plan.disclaimer) lines.push(plan.disclaimer)
  return lines.join('\n')
}

export function downloadItinerary(plan, options) {
  const url = URL.createObjectURL(new Blob([formatItinerary(plan, options)], { type: 'text/plain;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `masr-guide-itinerary-${options.arabic ? 'ar' : 'en'}.txt`
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
