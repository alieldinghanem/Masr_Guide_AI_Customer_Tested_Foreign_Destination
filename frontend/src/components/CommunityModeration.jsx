import React, { useState } from 'react'
import { api } from '../api'

export default function CommunityModeration({ staffKey }) {
  const [reports, setReports] = useState([])
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [metrics, setMetrics] = useState(null)
  const [contentReports, setContentReports] = useState([])
  const loadContent = async () => {
    setBusy(true); setMessage('')
    try { setContentReports((await api('/admin/community/content-reports', { headers: { 'X-Admin-Key': staffKey } })).reports || []) }
    catch { setMessage('Could not load post reports. Check staff access.') }
    finally { setBusy(false) }
  }
  const moderateContent = async (id, action) => {
    setBusy(true); setMessage('')
    try {
      await api(`/admin/community/content-reports/${id}`, { method: 'POST', headers: { 'X-Admin-Key': staffKey }, body: { action } })
      await loadContent()
    } catch { setMessage('Content changed or review failed. Refresh before reviewing.'); setBusy(false) }
  }
  const load = async () => {
    setBusy(true); setMessage('')
    try { setReports((await api('/admin/community/reports', { headers: { 'X-Admin-Key': staffKey } })).reports || []) }
    catch { setMessage('Could not load reports. Check staff access.') }
    finally { setBusy(false) }
  }
  const review = async (id, action) => {
    setBusy(true); setMessage('')
    try {
      await api(`/admin/community/reports/${id}`, { method: 'POST', headers: { 'X-Admin-Key': staffKey }, body: { action } })
      await load()
    } catch { setMessage('Review failed. Refresh reports; the comment may have changed.'); setBusy(false) }
  }
  const checkProvider = async () => {
    setBusy(true); setMessage('')
    try {
      const result = await api('/admin/ai-check', { method: 'POST', headers: { 'X-Admin-Key': staffKey } })
      setMessage(result.result === 'success' ? 'Gemini returned the expected test response just now. This does not verify future replies or live facts.' : 'Gemini test failed. Check model access, key, quota and availability.')
    } catch { setMessage('Gemini check is not available. Check staff access and provider configuration.') }
    finally { setBusy(false) }
  }
  const loadMetrics = async () => {
    setBusy(true); setMessage('')
    try { setMetrics(await api('/admin/metrics', { headers: { 'X-Admin-Key': staffKey } })) }
    catch { setMessage('Could not load aggregate counters.') }
    finally { setBusy(false) }
  }
  return <section><h3>Community reports</h3><button type="button" disabled={busy} onClick={load}>Refresh reports</button>
    <button type="button" disabled={busy} onClick={loadContent}>Load post and reply reports</button>
    {contentReports.map(report => <article key={report.id}><strong>{report.kind} · {report.reason} · {report.status}</strong><p>{report.body}</p>{['hide', 'restore', 'dismiss'].map(action => <button type="button" key={action} disabled={busy} onClick={() => moderateContent(report.id, action)}>{action}</button>)}</article>)}
    <p>Reports require human review. Hiding removes the comment from public discussions; restore reverses that decision.</p>
    <button type="button" disabled={busy} onClick={checkProvider}>Test Gemini connection</button><small> Makes one short provider request using your configured quota.</small>
    <button type="button" disabled={busy} onClick={loadMetrics}>Load aggregate counters</button>
    {metrics && <div><p>{metrics.enabled ? 'Daily aggregate counters enabled. No visitor identity or message text.' : 'Aggregate counters are disabled.'}</p>{metrics.counts.map(item => <p key={`${item.day}-${item.event}`}>{item.day} · {item.event}: {item.count}</p>)}</div>}
    {message && <p role="status">{message}</p>}
    {reports.map((report, index) => <article key={`${report.comment_id}-${index}`}><strong>{report.target_id} · {report.reason} · {report.status}</strong>
      <p>{report.comment_text}</p><small>{report.reports} report(s)</small>
      {['hide', 'restore', 'dismiss'].map(action => <button type="button" key={action} disabled={busy} onClick={() => review(report.comment_id, action)}>{action}</button>)}
    </article>)}
  </section>
}
