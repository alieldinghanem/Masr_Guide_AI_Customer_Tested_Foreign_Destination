# Google sign-in and account registration

Email signup now requires matching password confirmation in the website. The API accepts an optional confirmation for backward compatibility and rejects mismatches when supplied.

Google Identity Services uses the official Google button and server-side google-auth validation. Configure an OAuth 2.0 **Web application** client in the owner Google Cloud project, with the exact authorized JavaScript origin:

`https://masr-guide-ai-customer-tested-foreign-8aro.onrender.com`

Set the public client identifier as `GOOGLE_CLIENT_ID` in the server environment after approval to release. A Gemini API key is unrelated. No client secret is required by this ID-token flow. Configure Google consent branding, contact and privacy information; testing mode only permits permitted test users. Production access depends on the owner publishing the Google application and any review Google requires. Do not claim live Google login until an actual account completes the flow on the deployed origin.

The backend checks signed ID tokens, audience, issuer, expiry and a single-use browser-bound nonce. It identifies users by Google subject, never automatically by email. Existing email accounts require their current site password before linking; their ID, trips and favorites remain unchanged. New Google-only accounts support Gmail or verified Workspace addresses. External-provider Google emails must first register a local account and then prove its password to link safely.

Google-only accounts have no site password and use fresh same-account Google reauthentication plus explicit confirmation to delete their data. Their password recovery remains with Google. Credentials and Google deletion proofs are never stored in browser storage. Database identity mapping survives full PostgreSQL backups; existing account tables are preserved by additive schema setup.

If `GOOGLE_CLIENT_ID` is missing, the UI explicitly reports that Google is not enabled and keeps email signup available. This is not a verified Google connection. Unit tests use real cryptographic signatures with isolated certificates; frontend tests simulate the official SDK. Neither replaces a live Google OAuth acceptance check.

References: https://developers.google.com/identity/gsi/web/guides/verify-google-id-token and https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid
