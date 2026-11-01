# Masr Guide AI v7.4 — Transaction Safety Release

هذه النسخة إصلاح مباشر لأخطاء تعديل الرحلات بشكل صامت. لم نُعد كتابة الموقع أو نلغِ وظائف v7.3.

## تشغيل Windows
1. افتح `Masr_Guide_AI` بعد فك الضغط في VS Code.
2. استخدم `RUN_STARTUP_WINDOWS.bat`، ثم افتح `http://localhost:5173`.
3. شغّل اختبارات Backend بالأوامر:
   ```powershell
   cd backend
   python -m pip install -r requirements-dev.txt
   python -m pytest -q
   cd ..
   python qa_chatbot/blackbox_probe.py
   python qa_chatbot/acceptance_evaluation.py
   ```
4. اختبر واجهة React في Terminal آخر:
   ```powershell
   cd frontend
   npm ci
   npm test
   npm run lint
   npm run build
   ```
5. ضع أي مفتاح Gemini **جديد وغير منشور سابقًا** في `backend/.env` محليًا فقط. لا تشاركه ولا ترفعه إلى GitHub.

النتائج والمعوقات موثقة في `docs/TRANSACTIONAL_AI_GUARDS_V7_4_AR.md`.

GitHub مستودع كود، أما الخدمة الحية فتحتاج Backend Hosting مستمر وبيانات دائمة؛ لا تشغّل نسخة بحسابات مستخدمين حقيقية على SQLite زائل.
