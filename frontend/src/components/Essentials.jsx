import React from 'react'
import { BookOpen, ExternalLink, Globe2, Landmark, MapPinned, ShieldCheck } from 'lucide-react'
import { useI18n } from '../i18n'
import { ESSENTIAL_FALLBACK } from './TravelData'
import TravelSafety from './TravelSafety'
const ICONS = {entry:Globe2,monuments:Landmark,tickets:BookOpen,transport:MapPinned}
export default function Essentials({ items }) {
 const {lang}=useI18n(), ar=lang==='ar'
 const data=items.length?items:ESSENTIAL_FALLBACK
 return <main className="v3-page"><section className="v3-page-head v3-head-essentials"><div className="container"><span className="v3-overline">{ar?'قبل ما تسافر':'KNOW BEFORE YOU GO'}</span><h1>{ar?'سافر وإنت':'Travel with'} <em>{ar?'مستعد.':'confidence.'}</em></h1><p>{ar?'معلومات عملية ومصادر رسمية تساعدك تجهز لزيارتك لمصر.' : 'Practical essentials and official resources to help you prepare for Egypt.'}</p></div></section>
 <div className="container v3-content"><TravelSafety /><div className="v3-essentials-intro"><ShieldCheck size={25}/><div><strong>{ar?'المعلومة الموثوقة أهم من الرد السريع':'Official information comes first'}</strong><p>{ar?'متطلبات الدخول والتذاكر والمواعيد ممكن تتغير؛ راجع المصدر الرسمي قبل اتخاذ قرار السفر أو الدفع.':'Entry requirements, ticket prices and opening hours may change. Always verify before booking or travelling.'}</p></div></div>
 <div className="v3-essentials-grid">{data.map(item=>{const Icon=ICONS[item.id]||BookOpen;return <article className="v3-essential-card" key={item.id}><div className="v3-essential-icon"><Icon size={26}/></div><h2>{ar?item.title_ar:item.title}</h2><p>{ar?item.detail_ar:item.detail}</p><a href={item.url} target="_blank" rel="noopener noreferrer">{item.source_name} <ExternalLink size={16}/></a></article>})}</div>
 <p className="v3-data-note">{ar?'Masr Guide AI لا يصدر التأشيرات أو يبيع التذاكر، والروابط الخارجية ليست حجوزات شريكة.':'Masr Guide AI does not issue visas or sell tickets here. These external links are references, not affiliate offers.'}</p></div></main>
}
