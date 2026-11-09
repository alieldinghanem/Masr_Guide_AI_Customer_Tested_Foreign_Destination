# Google Sign-In setup for Masr Guide AI

Google sign-in uses **Google Identity Services (GIS)** and verifies a signed ID token **server-side**. It does not use a Gemini API key or store Google passwords. An OAuth **Web application Client ID** is required; a client secret is **not** needed for this GIS ID-token flow.

## 1. Create a Google OAuth client

In [Google Cloud Console](https://console.cloud.google.com/apis/credentials), create or select a project, configure the Google Auth Platform branding/consent details, then create an **OAuth 2.0 Client ID** with type **Web application**.

Add these **Authorized JavaScript origins** as appropriate:
- `https://masr-guide-ai-customer-tested-foreign-8aro.onrender.com`
- `http://localhost:5173`
- `http://127.0.0.1:5173`

For this GIS popup/button callback approach, an authorized redirect URI is not used. Configure test users or publication status in Google Cloud if Google's consent configuration requires it.

Copy the public ID ending in `.apps.googleusercontent.com`.

## 2. Configure the running environment

Set **`GOOGLE_CLIENT_ID`** to that OAuth Web Client ID in Render's service environment variables (and local `backend/.env` during development). The example and Render Blueprint list the variable. Do not commit real credentials.

The browser requests `GET /api/auth/google/config`, displays Google's official button when the ID is configured, receives an ID credential in the GIS callback, and posts it to `POST /api/auth/google`. The backend verifies signature, expiry, audience, issuer, and `email_verified` through Google's public keys and then issues the site's existing bearer session.

## 3. Protect traveler data before enabling signup

This project disables **new** user registration on temporary public-preview storage. The restriction applies to Google signup too. First configure **persistent Neon PostgreSQL** for traveler data via `NEON_DATABASE_URL`, validate persistence through a restart/redeploy and backup restore, and only then set `MASR_DURABLE_STORAGE_CONFIRMED=true`. Do not set that flag based on assumptions.

If storage is not confirmed, already-linked Google identities may still sign in to existing accounts, but new Google users receive a 503 response.

## 4. Existing accounts and privacy

- **New user:** Continue with Google creates a local account and local session.
- **Returning Google user:** Continue with Google restores the **same** account, trips, favorites, reviews, and conversations.
- **Existing email/password account:** Sign in normally first, then click **Link your Google account** while signed in. The Google identity must have the **same verified email**. Matching email alone does not silently link accounts.
- **Account deletion:** Local password or reauthentication with the **linked** Google identity is required. Deleting a Google-only account remains possible.
- **Sign out:** Revokes the site's local token; it does not sign out of the user's Google account.
- Password and Google token handling remains entirely on the backend. Never log, store, or commit Google ID tokens. Do not store the Google client secret.

## 5. Verify the implementation

Run backend tests, especially `pytest backend/tests/test_google_signin_20261109.py` with imports configured for this repo, and frontend build/lint. In a production-like browser on the authorized origin, test Google login with two real Google test accounts, same-account re-login, an existing password account linking flow, account deletion, logout, and persistence after redeploy.

Do not deploy or enable public Google signup before verified durable storage is configured.
