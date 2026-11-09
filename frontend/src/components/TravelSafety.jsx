import React, { useState } from 'react'
import { ExternalLink, Phone, ShieldAlert } from 'lucide-react'
import { useI18n } from '../i18n'

const HELP_SOURCE = 'https://www.gov.uk/foreign-travel-advice/egypt/getting-help'
const SECURITY_SOURCE = 'https://www.gov.uk/foreign-travel-advice/egypt/safety-and-security'
const VERIFIED = '2026-11-03'

const CONTACTS = [
  { number: '123', en: 'Ambulance', ar: 'الإسعاف', purposeEn: 'Medical emergency', purposeAr: 'حالة طبية طارئة' },
  { number: '122', en: 'Police', ar: 'الشرطة', purposeEn: 'Immediate danger or crime', purposeAr: 'خطر عاجل أو جريمة' },
  { number: '126', en: 'Tourist police', ar: 'شرطة السياحة', purposeEn: 'Tourist safety assistance', purposeAr: 'مساعدة أمنية للسائحين' },
  { number: '180', en: 'Fire', ar: 'المطافئ', purposeEn: 'Fire emergency', purposeAr: 'حريق طارئ' },
]

const SCENARIOS = [
  { id: 'medical', en: 'Medical emergency', ar: 'طوارئ طبية', stepsEn: ['Call 123 for an ambulance and state your exact location.', 'Contact your insurer or medical assistance provider as soon as possible.'], stepsAr: ['اتصل بالإسعاف على 123 وحدد مكانك بدقة.', 'تواصل مع شركة التأمين أو جهة المساعدة الطبية في أقرب وقت.'], contacts: ['123'], source: HELP_SOURCE },
  { id: 'threat', en: 'Threat or harassment', ar: 'تهديد أو تحرش', stepsEn: ['Move to a safe, populated place if you can.', 'For immediate danger, call police on 122; tourist police are available on 126.', 'Record details only when it is safe to do so.'], stepsAr: ['انتقل إلى مكان آمن ومزدحم إذا أمكن.', 'لو فيه خطر فوري اتصل بالشرطة على 122؛ شرطة السياحة على 126.', 'سجّل التفاصيل فقط إذا كان ذلك آمنًا.'], contacts: ['122', '126'], source: HELP_SOURCE },
  { id: 'passport', en: 'Lost passport', ar: 'فقدان جواز السفر', stepsEn: ['Report the loss to the police and ask for a written report.', 'Contact your own embassy or consulate for replacement travel documents.', 'Tell your travel provider if your journey is affected.'], stepsAr: ['أبلغ الشرطة عن الفقدان واطلب محضرًا مكتوبًا.', 'تواصل مع سفارة أو قنصلية بلدك لاستخراج وثيقة سفر بديلة.', 'أبلغ شركة السفر إذا تأثرت رحلتك.'], contacts: ['122'], source: SECURITY_SOURCE },
  { id: 'belongings', en: 'Lost or stolen belongings', ar: 'فقدان أو سرقة المتعلقات', stepsEn: ['Move somewhere safe and report a theft to the police.', 'Block stolen bank cards using your bank’s official channel.', 'Contact your insurer if you have travel cover.'], stepsAr: ['انتقل لمكان آمن وأبلغ الشرطة في حالة السرقة.', 'أوقف البطاقات المسروقة من خلال القنوات الرسمية للبنك.', 'تواصل مع شركة التأمين لو عندك تغطية سفر.'], contacts: ['122'], source: HELP_SOURCE },
  { id: 'transport', en: 'Taxi or transport dispute', ar: 'خلاف مع سائق أو وسيلة نقل', stepsEn: ['If you feel unsafe, leave the vehicle in a safe public place.', 'Keep the vehicle or booking details and any receipt.', 'For a threatening situation call 122 or tourist police on 126.'], stepsAr: ['لو مش حاسس بالأمان، انزل في مكان عام وآمن.', 'احتفظ ببيانات السيارة أو الحجز وأي إيصال.', 'في حالة التهديد اتصل بالشرطة على 122 أو شرطة السياحة على 126.'], contacts: ['122', '126'], source: HELP_SOURCE },
  { id: 'scam', en: 'Suspected scam or overcharge', ar: 'اشتباه في نصب أو مبالغة بالسعر', stepsEn: ['Do not share payment details or pay again under pressure.', 'Keep receipts and booking records.', 'If threatened, move to safety and call police or tourist police.'], stepsAr: ['لا تشارك بيانات الدفع ولا تدفع مرة أخرى تحت الضغط.', 'احتفظ بالإيصالات وبيانات الحجز.', 'لو فيه تهديد انتقل لمكان آمن واتصل بالشرطة أو شرطة السياحة.'], contacts: ['122', '126'], source: HELP_SOURCE },
]

export default function TravelSafety() {
  const { lang } = useI18n()
  const ar = lang === 'ar'
  const [selected, setSelected] = useState(null)
  const scenario = SCENARIOS.find(item => item.id === selected)
  return <section className="safety-help" aria-labelledby="safety-help-title">
    <div className="safety-head"><ShieldAlert size={25} aria-hidden="true" /><div>
      <h2 id="safety-help-title">{ar ? 'السلامة والمساعدة أثناء الرحلة' : 'Travel safety & help'}</h2>
      <p>{ar ? 'اختار المشكلة عشان تشوف خطوات سريعة وجهات الاتصال المناسبة.' : 'Choose a situation for quick steps and relevant contacts.'}</p>
    </div></div>
    <div className="safety-contacts" aria-label={ar ? 'أرقام الطوارئ' : 'Emergency contacts'}>
      {CONTACTS.map(contact => <article className="safety-contact" key={contact.number}>
        <strong>{ar ? contact.ar : contact.en}</strong>
        <span>{ar ? contact.purposeAr : contact.purposeEn}</span>
        <a href={`tel:${contact.number}`} aria-label={`${ar ? 'اتصل بـ' : 'Call'} ${ar ? contact.ar : contact.en} ${contact.number}`}><Phone size={17} aria-hidden="true" />{contact.number}</a>
      </article>)}
    </div>
    <p className="safety-source">{ar ? 'المصدر الرسمي: إرشادات الحكومة البريطانية للسفر إلى مصر. تم التحقق من الأرقام في' : 'Official source: UK government Egypt travel advice. Numbers checked on'} {VERIFIED}. <a href={HELP_SOURCE} target="_blank" rel="noopener noreferrer">{ar ? 'راجع المصدر' : 'Check source'} <ExternalLink size={14} aria-hidden="true" /></a></p>
    <h3>{ar ? 'إيه المشكلة اللي بتواجهك؟' : 'What do you need help with?'}</h3>
    <div className="safety-choices">{SCENARIOS.map(item => <button type="button" key={item.id} aria-pressed={selected === item.id} onClick={() => setSelected(item.id)}>{ar ? item.ar : item.en}</button>)}</div>
    {scenario && <div className="safety-steps" role="region" aria-label={ar ? scenario.ar : scenario.en}>
      <h4>{ar ? scenario.ar : scenario.en}</h4>
      <ol>{(ar ? scenario.stepsAr : scenario.stepsEn).map(step => <li key={step}>{step}</li>)}</ol>
      <p>{ar ? 'جهات الاتصال المناسبة:' : 'Relevant contacts:'} {scenario.contacts.map(number => <a href={`tel:${number}`} key={number}>{number}</a>)}</p>
      <a href={scenario.source} target="_blank" rel="noopener noreferrer">{ar ? 'إرشادات المصدر' : 'Source guidance'} <ExternalLink size={14} aria-hidden="true" /></a>
    </div>}
    <p className="safety-disclaimer">{ar ? 'Masr Guide AI لا يرسل فرق إنقاذ أو بلاغات. في الخطر الفوري اتصل بخدمات الطوارئ مباشرة.' : 'Masr Guide AI cannot dispatch help or file reports. For immediate danger, call emergency services directly.'}</p>
  </section>
}
