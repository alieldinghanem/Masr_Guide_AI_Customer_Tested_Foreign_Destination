import React, { useState } from 'react'
import { api } from '../api'

export default function PartnerOperations({ staffKey }) {
  const [report, setReport] = useState(null)
  const [activity, setActivity] = useState({ referrals: [], bookings: [] })
  const [form, setForm] = useState({ offer_id: '', agreement_reference: '', currency: 'EGP', commission_bps: '', expires_at: '', agreement_confirmed: false })
  const [booking, setBooking] = useState({ contract_id: '', referral_id: '', external_booking_id: '', eligible_amount_minor: '', evidence_reference: '', fulfilled_confirmed: false })
  const [reversal, setReversal] = useState({ id: '', evidence_reference: '' })
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const request = (path, options = {}) => api('/admin/pilot/' + path, { ...options, headers: { 'X-Admin-Key': staffKey } })
  const load = async () => {
    setBusy(true); setMessage('')
    try {
      const [summary, records] = await Promise.all([request('report'), request('activity')])
      setReport(summary); setActivity(records)
    } catch { setMessage('Could not load pilot records.') }
    finally { setBusy(false) }
  }
  const save = async (path, body) => {
    if (busy) return
    setBusy(true); setMessage('')
    try { const result = await request(path, { method: 'POST', body }); setMessage('Recorded. Reference: ' + (result.id || 'updated')); }
    catch (error) { setMessage(error.message) }
    finally { setBusy(false) }
  }
  const field = (name, value, update, type = 'text') => <label key={name}>{name.replaceAll('_', ' ')}<input required type={type} value={value} onChange={event => update(event.target.value)} /></label>
  return <section><h3>Direct partner pilot</h3><p>Use signed agreements and partner-confirmed fulfilment only. These are reconciliation estimates, not collected revenue or automatic payouts. Do not enter customer personal data.</p>
    <button type="button" disabled={busy} onClick={load}>Refresh pilot records</button>
    {message && <p role="status">{message}</p>}
    {report?.agreements?.map(item => <p key={item.id}>{item.partner} · {item.id} · {item.currency} · {item.referrals} referrals · {item.confirmed_bookings} recorded bookings · {item.reversed_bookings} reversed · estimated commission {(item.commission_minor / 100).toFixed(2)}</p>)}
    <details><summary>Record signed agreement</summary><form className="portal-form" onSubmit={event => { event.preventDefault(); save('contracts', { ...form, commission_bps: Number(form.commission_bps), expires_at: new Date(form.expires_at).toISOString() }) }}>
      {['offer_id', 'agreement_reference'].map(name => field(name, form[name], value => setForm(previous => ({ ...previous, [name]: value }))))}
      <label>Currency<select value={form.currency} onChange={event => setForm(previous => ({ ...previous, currency: event.target.value }))}>{['EGP', 'USD', 'EUR', 'GBP'].map(value => <option key={value}>{value}</option>)}</select></label>
      <label>Commission basis points (1000 = 10%)<input required type="number" min={1} max={10000} step={1} value={form.commission_bps} onChange={event => setForm(previous => ({ ...previous, commission_bps: event.target.value }))} /></label>
      {field('expires_at', form.expires_at, value => setForm(previous => ({ ...previous, expires_at: value })), 'datetime-local')}
      <label><input type="checkbox" required checked={form.agreement_confirmed} onChange={event => setForm(previous => ({ ...previous, agreement_confirmed: event.target.checked }))} /> Signed agreement confirmed</label><button disabled={busy} type="submit">Record agreement</button>
    </form></details>
    <details><summary>Record fulfilled booking</summary><form className="portal-form" onSubmit={event => { event.preventDefault(); save('bookings', { ...booking, eligible_amount_minor: Number(booking.eligible_amount_minor) }) }}>
      {['contract_id', 'referral_id', 'external_booking_id', 'evidence_reference'].map(name => field(name, booking[name], value => setBooking(previous => ({ ...previous, [name]: value }))))}
      <label>Eligible amount in minor units (EGP 100 = 10000)<input required type="number" min={1} max={10000000000} step={1} value={booking.eligible_amount_minor} onChange={event => setBooking(previous => ({ ...previous, eligible_amount_minor: event.target.value }))} /></label>
      <label><input type="checkbox" required checked={booking.fulfilled_confirmed} onChange={event => setBooking(previous => ({ ...previous, fulfilled_confirmed: event.target.checked }))} /> Partner confirmed service fulfilment</label><button disabled={busy} type="submit">Record booking</button>
    </form></details>
    <details><summary>Record cancellation or reversal</summary><form className="portal-form" onSubmit={event => { event.preventDefault(); save('bookings/' + encodeURIComponent(reversal.id) + '/reverse', { evidence_reference: reversal.evidence_reference }) }}>
      {field('booking_id', reversal.id, value => setReversal(previous => ({ ...previous, id: value })))}{field('evidence_reference', reversal.evidence_reference, value => setReversal(previous => ({ ...previous, evidence_reference: value })))}<button disabled={busy} type="submit">Record reversal</button>
    </form></details>
    <details><summary>Recent referral and booking references</summary>{activity.referrals.map(item => <p key={item.id}>Referral {item.id} · agreement {item.contract_id}</p>)}{activity.bookings.map(item => <p key={item.id}>Booking {item.id} · {item.status} · provider reference {item.external_booking_id}</p>)}</details>
  </section>
}
