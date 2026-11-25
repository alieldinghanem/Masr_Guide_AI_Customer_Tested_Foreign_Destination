import React, { useState } from 'react'
import { Camera } from 'lucide-react'
import { api } from '../api'

export async function preparePhoto(file) {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 10 * 1024 * 1024) throw new Error('image')
  const bitmap = await createImageBitmap(file)
  try {
    const canvas = document.createElement('canvas')
    for (const edge of [960, 720, 480]) {
      const scale = Math.min(1, edge / Math.max(bitmap.width, bitmap.height))
      canvas.width = Math.max(1, Math.round(bitmap.width * scale)); canvas.height = Math.max(1, Math.round(bitmap.height * scale))
      canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height)
      const data = canvas.toDataURL('image/jpeg', .7).split(',')[1]
      if (data.length <= 266664) return data
    }
    throw new Error('image')
  } finally { bitmap.close() }
}

export default function PhotoHelper({ ar = false, disabled = false }) {
  const [open, setOpen] = useState(false)
  const [photo, setPhoto] = useState('')
  const [city, setCity] = useState('')
  const [material, setMaterial] = useState('')
  const [size, setSize] = useState('')
  const [quote, setQuote] = useState('')
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const clear = () => { setPhoto(''); setResult(null); setError(''); setConsent(false); setCity(''); setMaterial(''); setSize(''); setQuote('') }
  async function choose(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setPhoto(''); setResult(null); setBusy(true); setError('')
    try { setPhoto(await preparePhoto(file)) } catch { setError(ar ? 'اختر صورة JPG أو PNG أو WebP واضحة أقل من 10 MB؛ جرّب لقطة أقرب للمنتج.' : 'Choose a clear JPG, PNG or WebP under 10 MB; try a closer product photo.') } finally { setBusy(false) }
  }
  async function submit(event) {
    event.preventDefault()
    if (!consent || !photo || busy || disabled) return
    setBusy(true); setError(''); setResult(null)
    try { setResult(await api('/photo-helper/compare', { method: 'POST', body: { image_base64: photo, provider_consent: true, city, material, size, quoted_egp: quote ? Number(quote) : null, language: ar ? 'ar' : 'en' } })) }
    catch (e) { setError(e.status === 503 ? (ar ? 'تحليل الصور غير متاح حاليًا. لم يتم تقدير سعر.' : 'Photo analysis is currently unavailable. No price was estimated.') : (ar ? 'تعذر التحقق من الصورة. لم يتم تقدير سعر؛ حاول مجددًا.' : 'The photo could not be verified. No price was estimated; please try again.')) }
    finally { setBusy(false) }
  }
  return <div className="photo-helper">
    <button type="button" className="photo-toggle" disabled={disabled || busy} aria-expanded={open} onClick={() => { if (open) clear(); setOpen(!open) }}><Camera size={17} aria-hidden="true" />{ar ? 'قارن سعر منتج بصورة' : 'Compare a product price by photo'}</button>
    {open && <section aria-label={ar ? 'مقارنة منتج بصورة' : 'Photo product comparison'}>
      <p>{ar ? 'للهدايا والمنتجات التذكارية. الصورة لا تثبت الخامة أو الأصالة؛ نطاق السعر يظهر فقط عند وجود مراجع حديثة مطابقة.' : 'For souvenirs and small products. A photo cannot verify material or authenticity; a range appears only with matching recent references.'}</p>
      <form onSubmit={submit}>
        <label>{ar ? 'صورة المنتج' : 'Product photo'}<input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" disabled={busy} onChange={choose} /></label>
        {photo && <><img className="photo-preview" src={`data:image/jpeg;base64,${photo}`} alt={ar ? 'معاينة صورة المنتج' : 'Product photo preview'} /><button type="button" disabled={busy} onClick={clear}>{ar ? 'إزالة الصورة والنتيجة' : 'Remove photo and result'}</button></>}
        <label>{ar ? 'المدينة' : 'City'}<input required minLength={2} maxLength={80} value={city} onChange={e => setCity(e.target.value)} /></label>
        <label>{ar ? 'الخامة حسب البائع (اختياري)' : 'Material stated by seller (optional)'}<input maxLength={80} value={material} onChange={e => setMaterial(e.target.value)} /></label>
        <label>{ar ? 'المقاس والوحدة (اختياري)' : 'Size and unit (optional)'}<input maxLength={80} placeholder={ar ? 'مثل: 20 × 30 سم' : 'e.g. 20 x 30 cm'} value={size} onChange={e => setSize(e.target.value)} /></label>
        <label>{ar ? 'السعر المطلوب بالجنيه (اختياري)' : 'Quoted price in EGP (optional)'}<input type="number" min="0.01" max="10000000" step="0.01" value={quote} onChange={e => setQuote(e.target.value)} /></label>
        <label className="photo-consent"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} />{ar ? 'أوافق على إرسال الصورة والمواصفات إلى Google Gemini للتحليل. الخطة المجانية قد تستخدم المحتوى لتحسين منتجات Google. تجنب تصوير الأشخاص والوثائق والبطاقات. لا تُحفظ الصورة في حسابي.' : 'I agree to send this photo and product details to Google Gemini for analysis. The free tier may use content to improve Google products. Avoid people, documents and cards. The photo is not saved to my account.'}</label>
        <button className="btn secondary" type="submit" disabled={busy || disabled || !photo || !consent}>{busy ? (ar ? 'جارٍ التحليل…' : 'Analyzing…') : (ar ? 'حلّل وقارن' : 'Analyze and compare')}</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {result && <div role="status"><h3>{result.observation.title}</h3><p>{ar ? 'ثقة التعرف على النوع: ' : 'Category recognition confidence: '}{ar ? ({high: 'مرتفعة', medium: 'متوسطة', low: 'منخفضة'}[result.observation.confidence]) : result.observation.confidence}</p><p>{result.message}</p>{result.estimate && <><strong>{result.estimate.min_egp}–{result.estimate.max_egp} EGP</strong><p>{result.estimate.comparison === 'above_reference_range' ? (ar ? 'السعر المطلوب أعلى من عينات المراجع المطابقة؛ اطلب توضيح الفرق وقارن المواصفات.' : 'The quote is above the matching reference samples; ask what explains the difference and compare specifications.') : (ar ? 'راجع المواصفات وشروط البيع قبل القرار.' : 'Check specifications and sale terms before deciding.')}</p></>}{result.references.map((r, i) => <p key={`${r.source_url}-${i}`}><a href={r.source_url} target="_blank" rel="noopener noreferrer">{ar ? 'مرجع السعر' : 'Price reference'} {i + 1}</a> · {r.price_egp} EGP · {r.observed_on}</p>)}</div>}
    </section>}
  </div>
}
