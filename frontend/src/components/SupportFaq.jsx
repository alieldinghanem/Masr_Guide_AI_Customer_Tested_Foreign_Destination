import React from 'react'

export default function SupportFaq({ ar = false }) {
  const items = ar ? [
    ['إزاي أعدّل يوم في الرحلة؟', 'اكتب مثلًا: «خلي اليوم الثالث نشاط واحد مناسب للأطفال» أو «خلي اليوم الأول وصول وراحة فقط». راجع الجدول بعد التعديل، واحفظه في حسابك لو عايز ترجع له من جهاز تاني.'],
    ['ليه الشات بيسألني قبل تغيير المدن؟', 'تغيير المدن أو زيادة أيام البحر ممكن يحتاج نقل أيام أو زيادة مدة الرحلة. حدد المدينة وعدد الأيام وهل الإجمالي ثابت، عشان نحافظ على اختياراتك.'],
    ['إزاي أرجع لحسابي أو أغيّر كلمة المرور؟', 'ادخل من صفحة حسابي. لحساب Google استخدم استعادة الحساب داخل Google. استعادة حساب البريد تظهر عند تفعيل خدمة إرسال البريد؛ لو غير متاحة ستظهر رسالة واضحة.'],
    ['ليه الصورة مش بتطلع سعر أحيانًا؟', 'الصورة لا تثبت الخامة أو الأصالة. نحتاج المدينة والمقاس والخامة ومراجع أسعار حديثة مطابقة؛ عندما لا تتوفر لا نختلق رقمًا.'],
  ] : [
    ['How do I edit a trip day?', 'Try “Make Day 3 one family-friendly activity” or “Day 1 must be arrival and rest only.” Review the updated itinerary and save it to your account to access it on another device.'],
    ['Why does the guide ask before changing cities?', 'Adding beach time may require moving days or extending the trip. Specify the destination, number of days and whether the total duration should stay fixed.'],
    ['How do I recover my account?', 'Open My Account. Recover Google accounts through Google. Email account recovery appears when mail delivery is configured; the page discloses when it is unavailable.'],
    ['Why might a photo have no price estimate?', 'A photo cannot verify material or authenticity. We need the city, material, dimensions and matching recent price references. When they are unavailable, we do not invent a price.'],
  ]
  return <section className="support-faq" aria-label={ar ? 'مساعدة سريعة' : 'Quick help'}><h2>{ar ? 'نساعدك تبدأ من هنا' : 'Start here'}</h2>
    <div className="support-actions"><a className="btn secondary" href="#/account">{ar ? 'حسابي' : 'My Account'}</a><a className="btn secondary" href="#/guide">{ar ? 'ارجع للمرشد' : 'Open the guide'}</a><a className="btn secondary" href="#/essentials">{ar ? 'السلامة والمساعدة' : 'Travel safety'}</a></div>
    {items.map(([question, answer]) => <details key={question}><summary>{question}</summary><p>{answer}</p></details>)}
  </section>
}
