(function () {
  'use strict';

  var status = document.getElementById('pilot-status');
  var authButton = document.getElementById('pilot-auth');
  var token = '';
  try { token = String(new URLSearchParams(window.location.search).get('token') || '').trim(); } catch (error) {}

  function setStatus(message) { status.textContent = message; }
  function apiUrl() { return '/api/pilot/claim?token=' + encodeURIComponent(token); }

  function friendlyError(code, fallback) {
    if (code === 'pilot_token_expired') return 'This free-book link has expired. Reply to the pilot email for a fresh link.';
    if (code === 'pilot_token_reused') return 'This free book has already been claimed.';
    if (code === 'pilot_token_invalid' || code === 'pilot_grant_mismatch') return 'This free-book link is not valid.';
    if (code === 'authentication_required' || code === 'invalid_session_token') return 'Please log in again to claim your free book.';
    return fallback || 'We could not claim the free book just now. Please try again.';
  }

  async function readJson(response) {
    var data;
    try { data = await response.json(); } catch (error) { data = {}; }
    if (!response.ok) {
      var failure = new Error(friendlyError(data.error, data.message));
      failure.code = data.error || 'pilot_claim_failed';
      throw failure;
    }
    return data;
  }

  async function redeem() {
    if (!window.Clerk || !window.Clerk.session || typeof window.Clerk.session.getToken !== 'function') {
      throw new Error('Your sign-in session is not ready. Please try again.');
    }
    var sessionToken = await window.Clerk.session.getToken();
    if (!sessionToken) throw new Error('Please log in again to claim your free book.');
    setStatus('Adding your free book…');
    var result = await readJson(await fetch(apiUrl(), {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + sessionToken, 'Content-Type': 'application/json' },
      body: '{}'
    }));
    setStatus(result.message || 'Your free book is ready. Taking you to the builder…');
    window.setTimeout(function () { window.location.assign(result.continue_url); }, 700);
  }

  async function start() {
    if (!/^v1\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(token) || token.length > 4096) {
      setStatus('This free-book link is not valid.');
      return;
    }
    try {
      var ready = await readJson(await fetch(apiUrl(), { headers: { Accept: 'application/json' } }));
      setStatus(ready.message);
      if (!window.ClerkAuth || typeof window.ClerkAuth.ensureLoaded !== 'function') throw new Error('Sign-in could not load.');
      await window.ClerkAuth.ensureLoaded();
      if (window.ClerkAuth.isSignedIn()) return redeem();
      authButton.hidden = false;
    } catch (error) {
      setStatus(friendlyError(error.code, error.message));
    }
  }

  authButton.addEventListener('click', function () {
    authButton.disabled = true;
    if (window.OmoSignupModal && typeof window.OmoSignupModal.open === 'function') {
      window.OmoSignupModal.open();
      authButton.disabled = false;
    } else {
      setStatus('Sign-in could not load. Refresh the page and try again.');
    }
  });

  start();
})();
