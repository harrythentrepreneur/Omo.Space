/* credits.js — one balance client for authenticated Omo account surfaces.
 *
 * HTTP(S): Neon `users.balance_cents` via authenticated GET /api/me is the
 * only source of truth. file:// keeps an isolated, clearly labelled preview
 * balance so designers can exercise the static pages without a backend.
 */
(function () {
  'use strict';

  var PREVIEW_BALANCE_KEY = 'omo_balance_v1';
  var PREVIEW_USAGE_KEY = 'omo_usage_v1';
  var PREVIEW_API_KEY = 'omo_apikey_v1';
  var CACHE_MS = 10000;
  var cache = null;
  var inFlight = null;
  var generation = 0;
  var channel = null;

  function apiBase() {
    return String(window.OMO_API_BASE || '').replace(/\/+$/, '');
  }

  function isFilePreview() {
    return !!(window.location && window.location.protocol === 'file:');
  }

  function currentUser() {
    if (!window.ClerkAuth || typeof window.ClerkAuth.getUser !== 'function') return null;
    if (typeof window.ClerkAuth.isSignedIn === 'function' && !window.ClerkAuth.isSignedIn()) return null;
    var user = window.ClerkAuth.getUser();
    return user && user.id ? user : null;
  }

  function accountError(code, message) {
    var error = new Error(message);
    error.code = code;
    return error;
  }

  function getSessionToken() {
    if (!window.Clerk || !window.Clerk.session || typeof window.Clerk.session.getToken !== 'function') {
      return Promise.reject(accountError('no_session', 'A verified sign-in session is not available.'));
    }
    return Promise.resolve(window.Clerk.session.getToken()).then(function (token) {
      if (!token) throw accountError('no_session', 'Your sign-in session has expired. Sign in again.');
      return token;
    });
  }

  function readPreviewNumber(key, fallback) {
    try {
      var raw = window.localStorage.getItem(key);
      var value = Number(raw);
      return raw != null && isFinite(value) ? value : fallback;
    } catch (error) {
      return fallback;
    }
  }

  function readPreviewRuns() {
    try {
      var value = JSON.parse(window.localStorage.getItem(PREVIEW_USAGE_KEY) || '[]');
      return Array.isArray(value) ? value : [];
    } catch (error) {
      return [];
    }
  }

  function previewAccount(user) {
    var balanceUsd = readPreviewNumber(PREVIEW_BALANCE_KEY, 5);
    try { window.localStorage.setItem(PREVIEW_BALANCE_KEY, String(balanceUsd)); } catch (error) {}
    return {
      mode: 'preview',
      userId: user.id,
      balanceCents: Math.round(balanceUsd * 100),
      balanceUsd: Math.round(balanceUsd * 100) / 100,
      currency: 'usd',
      apiKey: (function () { try { return window.localStorage.getItem(PREVIEW_API_KEY) || ''; } catch (error) { return ''; } })(),
      runs: readPreviewRuns(),
      fetchedAt: Date.now()
    };
  }

  function normalizeAccount(data, userId) {
    var cents = Number(data && data.balance_cents);
    if (!data || data.ok !== true || !isFinite(cents) || Math.round(cents) !== cents || cents < 0) {
      throw accountError('invalid_response', 'The balance service returned an invalid response.');
    }
    if (data.currency && String(data.currency).toLowerCase() !== 'usd') {
      throw accountError('invalid_response', 'The balance service returned an unsupported currency.');
    }
    return {
      mode: 'server',
      userId: userId,
      balanceCents: cents,
      balanceUsd: cents / 100,
      currency: 'usd',
      apiKey: String(data.api_key || ''),
      runs: Array.isArray(data.runs) ? data.runs : [],
      signupGranted: data.signup_granted === true,
      fetchedAt: Date.now()
    };
  }

  function formatUsd(cents) {
    return '$' + (Number(cents) / 100).toFixed(2);
  }

  function renderNavBalance(account) {
    if (!account) return;
    var hasBalance = account.balanceCents != null && isFinite(Number(account.balanceCents));
    var links = document.querySelectorAll('[data-omo-login]');
    for (var i = 0; i < links.length; i += 1) {
      var link = links[i];
      var icon = document.createElement('span');
      var amount = document.createElement('span');
      icon.className = 'omo-nav-credit-icon';
      icon.setAttribute('aria-hidden', 'true');
      icon.textContent = '\u25d2';
      link.textContent = '';
      link.appendChild(icon);
      if (hasBalance) {
        amount.textContent = formatUsd(account.balanceCents);
        link.appendChild(amount);
      }
      link.classList.add('omo-nav-credit');
      link.href = 'billing.html';
      link.setAttribute('aria-label', hasBalance ? formatUsd(account.balanceCents) + ' in credits — view billing' : 'Loading credits');
      link.title = hasBalance ? formatUsd(account.balanceCents) + ' in credits' : 'Loading credits';
      if (hasBalance) link.removeAttribute('aria-busy');
      else link.setAttribute('aria-busy', 'true');
    }
  }

  function publish(account) {
    renderNavBalance(account);
    try {
      window.dispatchEvent(new CustomEvent('omo:credits', { detail: account }));
    } catch (error) {}
    return account;
  }

  function requestServerAccount(user, requestGeneration) {
    return getSessionToken().then(function (token) {
      return fetch(apiBase() + '/api/me', {
        headers: { Authorization: 'Bearer ' + token, Accept: 'application/json' }
      });
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) {
          throw accountError(response.status === 401 ? 'unauthorized' : 'request_failed', data.message || data.error || 'Your balance could not be loaded.');
        }
        return normalizeAccount(data, user.id);
      });
    }).then(function (account) {
      var activeUser = currentUser();
      if (requestGeneration !== generation || !activeUser || activeUser.id !== user.id) {
        throw accountError('stale', 'The account changed while the balance was loading.');
      }
      cache = account;
      return publish(account);
    });
  }

  function getBalance(options) {
    options = options || {};
    var user = currentUser();
    if (!user) return Promise.reject(accountError('signed_out', 'Sign in to see your balance.'));

    if (isFilePreview()) {
      cache = previewAccount(user);
      return Promise.resolve(publish(cache));
    }
    if (user.demo) {
      return Promise.reject(accountError('no_session', 'Sign in with a verified account to see real credits.'));
    }

    if (!options.force && cache && cache.userId === user.id && Date.now() - cache.fetchedAt < CACHE_MS) {
      return Promise.resolve(publish(cache));
    }
    if (!options.force && inFlight && inFlight.userId === user.id) return inFlight.promise;

    var requestGeneration = options.force ? ++generation : generation;
    if (options.force) {
      cache = null;
      publish({ mode: 'loading', userId: user.id, balanceCents: null, balanceUsd: null, runs: [] });
    }
    var promise = requestServerAccount(user, requestGeneration);
    inFlight = { userId: user.id, promise: promise };
    promise.then(function () {
      if (inFlight && inFlight.promise === promise) inFlight = null;
    }, function () {
      if (inFlight && inFlight.promise === promise) inFlight = null;
    });
    return promise;
  }

  function invalidate(options) {
    options = options || {};
    generation += 1;
    cache = null;
    inFlight = null;
    if (channel && options.broadcast !== false) {
      try { channel.postMessage({ type: 'invalidate' }); } catch (error) {}
    }
  }

  function refresh() {
    invalidate();
    return getBalance({ force: true });
  }

  window.OmoCredits = {
    getBalance: getBalance,
    refresh: refresh,
    invalidate: invalidate,
    isFilePreview: isFilePreview
  };

  if (typeof window.BroadcastChannel === 'function') {
    try {
      channel = new window.BroadcastChannel('omo-credits-v1');
      channel.onmessage = function (event) {
        if (event && event.data && event.data.type === 'invalidate') {
          invalidate({ broadcast: false });
          if (currentUser()) getBalance({ force: true }).catch(function () {});
        }
      };
    } catch (error) { channel = null; }
  }

  if (window.ClerkAuth && typeof window.ClerkAuth.onAuthChange === 'function') {
    window.ClerkAuth.onAuthChange(function () {
      invalidate();
      if (currentUser()) getBalance({ force: true }).catch(function () {});
    });
  }
})();
