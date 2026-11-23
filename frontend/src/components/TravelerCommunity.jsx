import React, { useCallback, useEffect, useRef, useState } from 'react'
import { MessageCircle, ThumbsUp, UsersRound, MapPin, Send, ShieldCheck } from 'lucide-react'
import { api } from '../api'
import { useI18n } from '../i18n'
import { COASTAL_DESTINATIONS } from '../coastalDestinations'
import TravelerReviews from './TravelerReviews'
import { EditorialImage, LANDMARK_MEDIA, PhotoCredit } from './EditorialMedia'
import { COASTAL_MEDIA } from '../coastalMedia'

const uid = () => [...crypto.getRandomValues(new Uint8Array(16))].map(value => value.toString(16).padStart(2, '0')).join('')
const topics = ['question', 'experience', 'tip']
const labels = {
  en: {
    posts: 'Posts & discussions', places: 'Place reviews', title: 'Travel Egypt, together.',
    intro: 'Ask fellow travelers, share an experience or leave a practical tip. Link your post to a destination if it helps.',
    question: 'Question', experience: 'Experience', tip: 'Travel tip', all: 'All topics',
    topic: 'Post topic', destination: 'Destination (optional)', anywhere: 'Across Egypt',
    filterDestination: 'Filter posts by destination', allDestinations: 'All destinations',
    search: 'Search community posts', draft: 'Your post', placeholder: 'What would you like to ask or share?',
    publish: 'Publish post', posting: 'Publishing…', signIn: 'Sign in to join the conversation',
    unavailable: 'Posting is currently unavailable. You can still read discussions and place reviews.',
    guidelines: 'Keep it helpful and respectful. Do not share phone numbers, private travel details or payment information. Links and email addresses are not allowed.',
    disclosure: 'Posts are opinions from registered accounts. Visits and advice are not independently verified.',
    loading: 'Loading posts…', loadError: 'Could not load posts. Your draft is unchanged.', retry: 'Try again',
    empty: 'Start the conversation', emptyBody: 'No posts yet. Ask about your trip or share something useful.',
    noResults: 'No matching posts', clear: 'Clear filters', more: 'Load more posts', like: 'Like', replies: 'Replies',
    reply: 'Your reply', sendReply: 'Post reply', replyLoading: 'Loading replies…', replyError: 'Could not load replies.',
    noReplies: 'No replies yet. Be the first to help.', moreReplies: 'Load more replies',
    edit: 'Edit', remove: 'Delete', confirm: 'Delete this content?', confirmDelete: 'Confirm deletion', cancel: 'Cancel', save: 'Save changes',
    report: 'Report', reason: 'Report reason', sendReport: 'Send report', reported: 'Report sent for human review.',
    spam: 'Spam', abuse: 'Abuse', unsafe: 'Unsafe advice', privacy: 'Privacy', misinformation: 'Misinformation',
    conflict: 'This content changed. Refresh before trying again; your draft is still here.',
    authError: 'Your session expired. Sign in again.', validation: 'Write 5–2000 characters without links or email addresses.',
    rateError: 'Too many requests. Wait a minute and try again.', actionError: 'Could not save this change. Please try again.',
    deleted: 'Content deleted.', published: 'Your post is published.', details: 'Destination details', edited: 'Updated',
    startPost: 'Write a post', closeComposer: 'Close composer',
  },
  ar: {
    posts: 'المنشورات والنقاشات', places: 'تجارب الأماكن', title: 'اكتشف مصر مع ناس زيّك.',
    intro: 'اسأل المسافرين، احكي تجربتك، أو شارك نصيحة مفيدة. تقدر تربط منشورك بمكان لو حابب.',
    question: 'سؤال', experience: 'تجربة', tip: 'نصيحة سفر', all: 'كل المواضيع',
    topic: 'نوع المنشور', destination: 'المكان (اختياري)', anywhere: 'عن مصر عمومًا',
    filterDestination: 'تصفية المنشورات حسب المكان', allDestinations: 'كل الأماكن',
    search: 'ابحث في منشورات المجتمع', draft: 'منشورك', placeholder: 'حابب تسأل عن إيه أو تشاركنا بإيه؟',
    publish: 'انشر المنشور', posting: 'جارٍ النشر…', signIn: 'سجّل الدخول وشارك في النقاش',
    unavailable: 'النشر غير متاح حاليًا. تقدر تقرأ النقاشات وتجارب الأماكن.',
    guidelines: 'خلّي كلامك مفيد ومحترم. لا تشارك أرقام تليفونات أو تفاصيل سفر خاصة أو بيانات دفع. الروابط وعناوين البريد غير مسموحة.',
    disclosure: 'المنشورات آراء من حسابات مسجلة، والزيارات والنصائح غير موثقة بشكل مستقل.',
    loading: 'جارٍ تحميل المنشورات…', loadError: 'تعذر تحميل المنشورات. مسودة منشورك لم تتغير.', retry: 'حاول مرة أخرى',
    empty: 'ابدأ أول نقاش', emptyBody: 'لسه مفيش منشورات. اسأل عن رحلتك أو شارك معلومة مفيدة.',
    noResults: 'لا توجد منشورات مطابقة', clear: 'مسح الفلاتر', more: 'عرض منشورات أكثر', like: 'إعجاب', replies: 'التعليقات',
    reply: 'تعليقك', sendReply: 'انشر التعليق', replyLoading: 'جارٍ تحميل التعليقات…', replyError: 'تعذر تحميل التعليقات.',
    noReplies: 'لسه مفيش تعليقات. كن أول من يساعد.', moreReplies: 'عرض تعليقات أكثر',
    edit: 'تعديل', remove: 'حذف', confirm: 'تحذف المحتوى ده؟', confirmDelete: 'تأكيد الحذف', cancel: 'إلغاء', save: 'حفظ التعديل',
    report: 'إبلاغ', reason: 'سبب البلاغ', sendReport: 'إرسال البلاغ', reported: 'تم إرسال البلاغ للمراجعة البشرية.',
    spam: 'رسائل مزعجة', abuse: 'إساءة', unsafe: 'نصيحة خطرة', privacy: 'خصوصية', misinformation: 'معلومة خاطئة',
    conflict: 'المحتوى اتغير. أعد تحميله قبل المحاولة؛ مسودتك ما زالت موجودة.',
    authError: 'انتهت جلسة الدخول. سجّل الدخول مرة أخرى.', validation: 'اكتب من 5 إلى 2000 حرف بدون روابط أو عناوين بريد.',
    rateError: 'طلبات كثيرة. انتظر دقيقة وحاول مرة أخرى.', actionError: 'تعذر حفظ التغيير. حاول مرة أخرى.',
    deleted: 'تم حذف المحتوى.', published: 'تم نشر منشورك.', details: 'تفاصيل المكان', edited: 'تم التعديل',
    startPost: 'اكتب منشورًا', closeComposer: 'إغلاق الكتابة',
  },
}
const errorKey = error => error.status === 401 ? 'authError' : error.status === 409 ? 'conflict' : error.status === 422 ? 'validation' : error.status === 429 ? 'rateError' : 'actionError'

function Stamp({ value, lang }) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : <time dateTime={value}>{new Intl.DateTimeFormat(lang, { dateStyle: 'medium', timeStyle: 'short' }).format(date)}</time>
}

function ContentActions({ content, kind, session, onSignIn, onChange, copy }) {
  const [mode, setMode] = useState('')
  const [draft, setDraft] = useState('')
  const [version, setVersion] = useState(content.version)
  const [reason, setReason] = useState('spam')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const begin = next => { setVersion(content.version); setDraft(content.body); setMode(next); setError(''); setNotice('') }
  const submit = async event => {
    event.preventDefault(); setBusy(true); setError('')
    try {
      if (mode === 'report') {
        await api('/community/content-reports', { method: 'POST', token: session.token,
          body: { kind, content_id: content.id, version, reason } })
        setNotice('reported')
      } else {
        await api(`/community/${kind === 'post' ? 'posts' : 'replies'}/${content.id}`, {
          method: mode === 'edit' ? 'PATCH' : 'DELETE', token: session.token,
          body: mode === 'edit' ? { body: draft.trim(), version } : { version }
        })
        onChange(mode === 'delete' ? 'delete' : 'edit')
      }
      setMode('')
    } catch (failure) { setError(errorKey(failure)) }
    finally { setBusy(false) }
  }
  return <div className="social-content-actions">
    {content.is_owner ? <><button type="button" disabled={busy} onClick={() => begin('edit')}>{copy.edit}</button><button type="button" disabled={busy} onClick={() => begin('delete')}>{copy.remove}</button></>
      : <button type="button" disabled={busy} onClick={() => session?.token ? begin('report') : onSignIn?.()}>{copy.report}</button>}
    {mode && <form onSubmit={submit}>
      {mode === 'edit' && <label>{copy.edit}<textarea required minLength={5} maxLength={2000} rows={3} value={draft} disabled={busy} onChange={event => setDraft(event.target.value)} /></label>}
      {mode === 'delete' && <p>{copy.confirm}</p>}
      {mode === 'report' && <label>{copy.reason}<select value={reason} onChange={event => setReason(event.target.value)}>{['spam', 'abuse', 'unsafe', 'privacy', 'misinformation'].map(item => <option value={item} key={item}>{copy[item]}</option>)}</select></label>}
      <button type="submit" disabled={busy || (mode === 'edit' && draft.trim().length < 5)}>{mode === 'edit' ? copy.save : mode === 'delete' ? copy.confirmDelete : copy.sendReport}</button>
      <button type="button" disabled={busy} onClick={() => { setMode(''); setError('') }}>{copy.cancel}</button>
    </form>}
    {error && <p role="alert">{copy[error]}</p>}{notice && <p role="status">{copy[notice]}</p>}
  </div>
}

const mergeReplies = (old, extra) => [...new Map([...old, ...extra].map(item => [item.id, item])).values()]
  .sort((a, b) => a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id))

function Thread({ postId, session, onSignIn, onChanged, copy, lang, posting }) {
  const [replies, setReplies] = useState([])
  const [cursor, setCursor] = useState(null)
  const [busy, setBusy] = useState(false)
  const [state, setState] = useState('loading')
  const [attempt, setAttempt] = useState(0)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')
  const requestId = useRef(uid())
  const generation = useRef(0)
  const invalidate = useCallback(() => { generation.current++ }, [])
  const load = useCallback(async (next = null) => {
    const request = ++generation.current
    setState('loading')
    try {
      const data = await api(`/community/posts/${postId}/replies${next ? `?cursor=${next}` : ''}`, { token: session?.token })
      if (request !== generation.current) return
      setReplies(old => next ? mergeReplies(old, data.replies || []) : data.replies || [])
      setCursor(data.next_cursor); setState('ready')
    } catch { if (request === generation.current) setState('error') }
  }, [postId, session?.token])
  useEffect(() => { load(); return invalidate }, [load, attempt, invalidate])
  const send = async event => {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const data = await api(`/community/posts/${postId}/replies`, { method: 'POST', token: session.token, body: { body: draft.trim(), client_id: requestId.current } })
      setReplies(old => mergeReplies(old, [data.reply])); setDraft(''); requestId.current = uid(); onChanged()
    } catch (failure) { setError(errorKey(failure)) }
    finally { setBusy(false) }
  }
  return <section className="social-thread" aria-label={copy.replies}>
    {state === 'loading' && <p role="status">{copy.replyLoading}</p>}
    {state === 'error' && <div role="alert"><p>{copy.replyError}</p><button type="button" onClick={() => setAttempt(value => value + 1)}>{copy.retry}</button></div>}
    {state === 'ready' && !replies.length && <p>{copy.noReplies}</p>}
    {replies.map(item => <article key={item.id} className="social-reply"><strong>{lang === 'ar' ? item.author.replace('Traveler #', 'مسافر #') : item.author}</strong><Stamp value={item.created_at} lang={lang} /><p dir="auto">{item.body}</p>
      <ContentActions content={item} kind="reply" session={session} onSignIn={onSignIn} copy={copy} onChange={() => { load(); onChanged() }} />
    </article>)}
    {cursor && <button type="button" disabled={state === 'loading'} onClick={() => load(cursor)}>{copy.moreReplies}</button>}
    {session?.token && posting ? <form onSubmit={send}><label>{copy.reply}<textarea required minLength={5} maxLength={2000} value={draft} rows={2} disabled={busy} onChange={event => { setDraft(event.target.value); requestId.current = uid() }} /></label>
      <button type="submit" disabled={busy || state !== 'ready' || draft.trim().length < 5}>{copy.sendReply}</button>{error && <p role="alert">{copy[error]}</p>}
    </form> : !session?.token ? <button type="button" onClick={onSignIn}>{copy.signIn}</button> : null}
  </section>
}

function PostCard({ post, session, onSignIn, copy, lang, targets, onOpenTarget, onUpdate, onRemove, posting }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const target = targets.find(item => item.id === post.target_id)
  const coastalPhoto = target?.id.startsWith('coast:') ? COASTAL_MEDIA[target.id.slice(6)] : null
  const photo = coastalPhoto?.photo || LANDMARK_MEDIA[target?.id]
  const refresh = async () => {
    try { onUpdate((await api(`/community/posts/${post.id}`, { token: session?.token })).post) }
    catch (failure) { if (failure.status === 404) onRemove(post.id); else setError(errorKey(failure)) }
  }
  const like = async () => {
    if (!session?.token) { onSignIn?.(); return }
    setBusy(true); setError('')
    try { onUpdate((await api(`/community/posts/${post.id}/like`, { method: post.liked ? 'DELETE' : 'PUT', token: session.token })).post) }
    catch (failure) { setError(errorKey(failure)) }
    finally { setBusy(false) }
  }
  return <article className="social-post">
    <header><span className="social-avatar" aria-hidden="true"><UsersRound size={20} /></span><div><strong>{lang === 'ar' ? post.author.replace('Traveler #', 'مسافر #') : post.author}</strong><Stamp value={post.created_at} lang={lang} /></div><span className="social-topic">{copy[post.topic]}</span></header>
    {post.version > 1 && <small>{copy.edited}</small>}
    <p className="social-body" dir="auto">{post.body}</p>
    {target && photo && <div className="social-place-preview"><button type="button" aria-label={`${copy.details}: ${target.label}`} onClick={() => onOpenTarget?.(target.id)}><EditorialImage src={photo} alt="" /></button>
      {coastalPhoto ? <small><a href={coastalPhoto.source} target="_blank" rel="noopener noreferrer">{coastalPhoto.author}</a> · <a href={coastalPhoto.licenseUrl} target="_blank" rel="noopener noreferrer">{coastalPhoto.license}</a></small> : <PhotoCredit id={target.id} ar={lang === 'ar'} />}
    </div>}
    {target && <button type="button" className="social-place" onClick={() => onOpenTarget?.(target.id)}><MapPin size={15} aria-hidden="true" />{target.label} · {copy.details}</button>}
    <div className="social-post-controls"><button type="button" aria-pressed={!!post.liked} disabled={busy || (session?.token && !posting)} onClick={like}><ThumbsUp size={17} aria-hidden="true" />{copy.like} <span>{post.likes_count}</span></button>
      <button type="button" aria-expanded={open} onClick={() => setOpen(value => !value)}><MessageCircle size={17} aria-hidden="true" />{copy.replies} <span>{post.replies_count}</span></button></div>
    {error && <p role="alert">{copy[error]} <button type="button" onClick={refresh}>{copy.retry}</button></p>}
    <ContentActions content={post} kind="post" session={session} onSignIn={onSignIn} copy={copy} onChange={action => action === 'delete' ? onRemove(post.id) : refresh()} />
    {open && <Thread postId={post.id} session={session} onSignIn={onSignIn} onChanged={refresh} copy={copy} lang={lang} posting={posting} />}
  </article>
}

function SocialFeed({ places, session, onSignIn, onOpenTarget }) {
  const { lang, placeName } = useI18n()
  const copy = labels[lang]
  const targets = [...COASTAL_DESTINATIONS.map(item => ({ id: `coast:${item.id}`, label: lang === 'ar' ? item.ar : item.en })), ...places.map(item => ({ id: item.id, label: placeName(item) }))]
  const [posts, setPosts] = useState([])
  const [state, setState] = useState('loading')
  const [posting, setPosting] = useState(false)
  const [topic, setTopic] = useState('')
  const [destination, setDestination] = useState('')
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState('')
  const [cursor, setCursor] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const [draft, setDraft] = useState('')
  const [draftTopic, setDraftTopic] = useState('question')
  const [draftTarget, setDraftTarget] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [published, setPublished] = useState(false)
  const [composerOpen, setComposerOpen] = useState(false)
  const requestId = useRef(uid())
  const generation = useRef(0)
  const invalidate = useCallback(() => { generation.current++ }, [])
  useEffect(() => { const timer = setTimeout(() => setSearch(query.trim()), 300); return () => clearTimeout(timer) }, [query])
  useEffect(() => { let active = true; api('/community/status').then(data => { if (active) setPosting(data.posting_enabled === true) }).catch(() => { if (active) setPosting(false) }); return () => { active = false } }, [])
  const load = useCallback(async (next = null) => {
    const request = ++generation.current
    const params = new URLSearchParams()
    if (topic) params.set('topic', topic)
    if (destination) params.set('target_id', destination)
    if (search) params.set('q', search)
    if (next) params.set('cursor', next)
    setState('loading')
    try {
      const data = await api(`/community/posts${params.size ? `?${params}` : ''}`, { token: session?.token })
      if (request !== generation.current) return
      setPosts(old => next ? [...new Map([...old, ...data.posts].map(item => [item.id, item])).values()] : data.posts || [])
      setCursor(data.next_cursor); setState('ready')
    } catch { if (request === generation.current) setState('error') }
  }, [topic, destination, search, session?.token])
  useEffect(() => { load(); return invalidate }, [load, attempt, invalidate])
  const submit = async event => {
    event.preventDefault(); setBusy(true); setError(''); setPublished(false)
    try {
      await api('/community/posts', { method: 'POST', token: session.token, body: { body: draft.trim(), topic: draftTopic, target_id: draftTarget || null, client_id: requestId.current } })
      setDraft(''); requestId.current = uid(); setPublished(true)
      setTopic(''); setDestination(''); setQuery(''); setSearch(''); load()
    } catch (failure) { setError(errorKey(failure)) }
    finally { setBusy(false) }
  }
  return <main className="container page-wrap social-community">
    <span className="eyebrow">{lang === 'ar' ? 'مجتمع المسافرين' : 'TRAVELER COMMUNITY'}</span><h1>{copy.title}</h1><p>{copy.intro}</p>
    <div className="social-disclosure"><ShieldCheck size={18} aria-hidden="true" />{copy.disclosure}</div>
    <div className="social-layout"><aside className="social-composer"><h2>{copy.draft}</h2><p>{copy.guidelines}</p>
      {!posting && <p role="status">{copy.unavailable}</p>}
      {!session?.token ? <button type="button" className="btn primary" onClick={onSignIn}>{copy.signIn}</button> : <><button type="button" className="btn primary" aria-expanded={composerOpen} disabled={busy} onClick={() => setComposerOpen(value => !value)}>{composerOpen ? copy.closeComposer : copy.startPost}</button>{composerOpen && <form onSubmit={submit}>
        <label>{copy.topic}<select value={draftTopic} onChange={event => { setDraftTopic(event.target.value); requestId.current = uid() }} disabled={busy}>{topics.map(item => <option key={item} value={item}>{copy[item]}</option>)}</select></label>
        <label>{copy.destination}<select value={draftTarget} onChange={event => { setDraftTarget(event.target.value); requestId.current = uid() }} disabled={busy}><option value="">{copy.anywhere}</option>{targets.map(item => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label>
        <label>{copy.draft}<textarea placeholder={copy.placeholder} required minLength={5} maxLength={2000} rows={6} value={draft} disabled={busy} aria-describedby="community-post-length" onChange={event => { setDraft(event.target.value); requestId.current = uid() }} /></label>
        <small id="community-post-length">{draft.length} / 2000</small><button type="submit" className="btn primary" disabled={busy || !posting || draft.trim().length < 5}><Send size={16} aria-hidden="true" />{busy ? copy.posting : copy.publish}</button>
        {error && <p role="alert">{copy[error]}</p>}{published && <p role="status">{copy.published}</p>}
      </form>}</>}
    </aside><section className="social-feed" aria-label={copy.posts} aria-busy={state === 'loading'}>
      <div className="social-filters"><label>{copy.search}<input type="search" maxLength={100} value={query} onChange={event => setQuery(event.target.value)} /></label><label>{copy.filterDestination}<select value={destination} onChange={event => setDestination(event.target.value)}><option value="">{copy.allDestinations}</option>{targets.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
        <div role="group" aria-label={copy.topic}>{['', ...topics].map(item => <button type="button" key={item} aria-pressed={topic === item} onClick={() => setTopic(item)}>{copy[item || 'all']}</button>)}</div>
      </div>
      {state === 'loading' && <p role="status">{copy.loading}</p>}
      {state === 'error' && <div role="alert"><p>{copy.loadError}</p><button type="button" onClick={() => setAttempt(value => value + 1)}>{copy.retry}</button></div>}
      {posts.map(post => <PostCard key={post.id} post={post} session={session} onSignIn={onSignIn} copy={copy} lang={lang} targets={targets} onOpenTarget={onOpenTarget} posting={posting}
        onUpdate={item => setPosts(old => old.map(value => value.id === item.id ? item : value))} onRemove={id => setPosts(old => old.filter(item => item.id !== id))} />)}
      {state === 'ready' && !posts.length && !cursor && <div className="social-empty"><UsersRound size={34} aria-hidden="true" /><h2>{topic || destination || search ? copy.noResults : copy.empty}</h2><p>{copy.emptyBody}</p>{(topic || destination || query) && <button type="button" onClick={() => { setTopic(''); setDestination(''); setQuery(''); setSearch('') }}>{copy.clear}</button>}</div>}
      {cursor && <button type="button" className="btn secondary" disabled={state === 'loading'} onClick={() => load(cursor)}>{copy.more}</button>}
    </section></div>
  </main>
}

export default function TravelerCommunity(props) {
  const { lang } = useI18n()
  const [tab, setTab] = useState('posts')
  const copy = labels[lang]
  return <>
    <nav className="container social-tabs" aria-label={lang === 'ar' ? 'أقسام المجتمع' : 'Community sections'}>{['posts', 'places'].map(item => <button type="button" key={item} aria-pressed={tab === item} onClick={() => setTab(item)}>{copy[item]}</button>)}</nav>
    <div hidden={tab !== 'posts'}><SocialFeed key={props.session?.token || 'guest'} {...props} /></div>
    <div hidden={tab !== 'places'}><TravelerReviews {...props} /></div>
  </>
}
