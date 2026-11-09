import React, { useState } from 'react'
import { CircleAlert, Wallet } from 'lucide-react'
import { useI18n } from '../i18n'
const KEY = 'masr-budget-estimate-v5'
const defaults = {people:2, nights:7, days:8, hotel:0, meals:0, local:0, intercity:0, activities:0, budget:15000}
const read = () => {try {return {...defaults,...JSON.parse(localStorage.getItem(KEY)||'{}')}} catch {return defaults}}
const fields = [
 ['hotel','Accommodation per night / room','الإقامة لكل ليلة / غرفة'],
 ['meals','Food per day / traveller','الأكل لكل يوم / مسافر'],
 ['local','Local transport per day / group','مواصلات يومية / المجموعة'],
 ['intercity','Total intercity transport','إجمالي الانتقالات بين المدن'],
 ['activities','Total tickets and activities','إجمالي التذاكر والأنشطة']
]
export default function Budget() {
 const {lang}=useI18n(), ar=lang==='ar'
 const [v,setV]=useState(read)
 const update=(key,value)=>{const next={...v,[key]:Math.min(100000000,Math.max(0,Number(value)||0))};setV(next);try{localStorage.setItem(KEY,JSON.stringify(next))}catch{/* unavailable */}}
 const nights=Math.max(0,Number(v.nights)),days=Math.max(1,Number(v.days)),people=Math.max(1,Number(v.people))
 const lines=[{title:ar?'الإقامة':'Accommodation',value:v.hotel*nights},{title:ar?'الأكل':'Meals',value:v.meals*people*days},{title:ar?'مواصلات محلية':'Local transfers',value:v.local*days},{title:ar?'الانتقالات بين المدن':'Intercity travel',value:v.intercity},{title:ar?'التذاكر والأنشطة':'Activities & tickets',value:v.activities}]
 const total=lines.reduce((x,y)=>x+y.value,0), diff=v.budget-total
 const money=n=>Math.round(n).toLocaleString(ar?'ar-EG':'en-US')+' EGP'
 return <main className="portal-page"><section className="portal-hero"><div className="container"><span className="eyebrow light">YOUR TRAVEL BUDGET</span><h1>{ar?'ميزانيتك في مصر':'Plan your Egypt budget'}</h1><p>{ar?'حاسبة تفاعلية بالأرقام اللي إنت تدخلها. مش أسعار سوق حية ولا وعد بتوافر الحجز.':'An interactive planning calculator driven by your own estimates, not live market prices or guaranteed offers.'}</p></div></section>
 <div className="container portal-content"><div className="portal-two"><div className="portal-form budget-form"><h2>{ar?'تفاصيل الرحلة':'Travel details'}</h2><div className="budget-input-grid">{[['people','Travellers','عدد المسافرين'],['nights','Nights','عدد الليالي'],['days','Days','عدد الأيام'],['budget','Target budget (EGP)','الميزانية المستهدفة (جنيه)']].map(([key,en,arabic])=><label key={key}>{ar?arabic:en}<input type="number" min={0} max={100000000} value={v[key]} onChange={e=>update(key,e.target.value)}/></label>)}</div><h2>{ar?'التكاليف المتوقعة':'Your assumed costs'}</h2>{fields.map(([key,en,arabic])=><label key={key}>{ar?arabic:en}<input type="number" min="0" max="100000000" value={v[key]} onChange={e=>update(key,e.target.value)}/></label>)}<button className="btn secondary" onClick={()=>{setV(defaults);localStorage.removeItem(KEY)}} type="button">{ar?'إعادة ضبط الأرقام':'Reset estimates'}</button></div><aside className="budget-summary"><Wallet size={34}/><span className="portal-kicker">{ar?'ملخص تقريبي':'PERSONAL COST ESTIMATE'}</span><h2>{money(total)}</h2><p>{ar?'الإجمالي بحسب الأرقام اللي أدخلتها':'Total from your entered assumptions'}</p><div className="budget-lines">{lines.map(line=><div key={line.title}><span>{line.title}</span><strong>{money(line.value)}</strong></div>)}</div><div className={'budget-difference '+(diff<0?'over':'under')}><strong>{diff>=0?ar?'متبقي من الميزانية':'Budget remaining':ar?'زيادة على الميزانية':'Over target budget'}</strong><span>{money(Math.abs(diff))}</span></div><div className="portal-disclosure"><CircleAlert size={20}/>{ar?'الأرقام ليست أسعار حية. تحقق من الأسعار والتذاكر والمواصلات قبل الدفع.':'These are not live prices. Confirm accommodation, transport and tickets with providers before booking.'}</div></aside></div></div></main>
}
