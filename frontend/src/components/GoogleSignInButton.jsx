import React, { useEffect, useRef, useState } from 'react'

// Google Identity Services delivers a short-lived ID token to our server.
// The backend verifies its signature and audience before issuing a local session.
export default function GoogleSignInButton({ clientId, onCredential, disabled = false }) {
  const target = useRef(null)
  const callback = useRef(onCredential)
  const blocked = useRef(disabled)
  const [error, setError] = useState('')
  useEffect(() => { callback.current = onCredential }, [onCredential])
  useEffect(() => { blocked.current = disabled }, [disabled])

  useEffect(() => {
    if (!clientId) return undefined
    let active = true
    const scriptUrl = 'https://accounts.google.com/gsi/client'
    const render = () => {
      if (!active || !target.current) return
      const identity = window.google?.accounts?.id
      if (!identity) { setError('Google sign-in could not load. Try again or use email and password.'); return }
      target.current.replaceChildren()
      identity.initialize({
        client_id: clientId,
        callback: response => {
          if (!active || blocked.current || !response?.credential) return
          callback.current(response.credential)
        },
      })
      identity.renderButton(target.current, {
        type: 'standard', theme: 'outline', size: 'large',
        text: 'continue_with', shape: 'rectangular', width: 270,
      })
      setError('')
    }
    const onError = () => { if (active) setError('Google sign-in could not load. Try again later.') }
    if (window.google?.accounts?.id) {
      render()
      return () => { active = false }
    }
    let script = document.querySelector('script[data-masr-google-sign-in]')
    if (!script) {
      script = document.createElement('script')
      script.src = scriptUrl
      script.async = true
      script.dataset.masrGoogleSignIn = 'true'
      document.head.appendChild(script)
    }
    script.addEventListener('load', render)
    script.addEventListener('error', onError)
    return () => {
      active = false
      script.removeEventListener('load', render)
      script.removeEventListener('error', onError)
    }
  }, [clientId])

  if (!clientId) return null
  return <div className="google-account-widget">
    <div ref={target} aria-label="Continue with Google" style={{ opacity: disabled ? 0.6 : 1, pointerEvents: disabled ? 'none' : 'auto' }} />
    {error && <small role="alert">{error}</small>}
  </div>
}
