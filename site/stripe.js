/* stripe.js — Stripe Checkout for purchases and credit top-ups. Catalog
 * purchases always use the server-created hosted Checkout URL; credit top-ups
 * retain a local demo fallback while the publishable key is a placeholder.
 *
 * Exposes window.StripePay = { getKey, isConfigured, checkout, topup }.
 */
(function () {
  'use strict';

  var PLACEHOLDER = 'pk_test_placeholder';
  var BALANCE_KEY = 'omo_balance_v1';
  var MIN_TOPUP_USD = 5;

  function getKey() {
    return (window.STRIPE_PUBLISHABLE_KEY || '').trim() || PLACEHOLDER;
  }

  function isConfigured() {
    var key = getKey();
    return key !== PLACEHOLDER && /^pk_(test|live)_/.test(key);
  }

  function apiUrl(path) {
    return (window.OMO_API_BASE || '').replace(/\/+$/, '') + path;
  }

  function notice(message) {
    if (typeof document === 'undefined' || !document.body) return;
    var element = document.createElement('div');
    element.setAttribute('role', 'status');
    element.style.cssText =
      'position:fixed;left:50%;bottom:20px;transform:translateX(-50%);z-index:400;' +
      'max-width:min(92vw,480px);padding:12px 18px;border-radius:12px;' +
      'background:#17352C;color:#fff;font:700 14px/1.45 "DM Sans",system-ui,sans-serif;' +
      'box-shadow:0 8px 24px rgba(23,53,44,.25)';
    element.textContent = message;
    document.body.appendChild(element);
    if (typeof setTimeout === 'function') {
      setTimeout(function () {
        if (element.parentNode) element.parentNode.removeChild(element);
      }, 6000);
    }
  }

  function fail(callbacks, message) {
    notice(message);
    if (callbacks && typeof callbacks.onError === 'function') callbacks.onError(message);
  }

  function checkoutAttemptKey(slug, email) {
    var storageKey = 'omo_checkout_attempt_v1:' + slug + ':' + String(email || '').trim().toLowerCase();
    try {
      var saved = sessionStorage.getItem(storageKey);
      if (saved) return saved;
    } catch (e) {}
    var randomPart = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
    var key = 'checkout-' + randomPart;
    try { sessionStorage.setItem(storageKey, key); } catch (e) {}
    return key;
  }

  function simulateTopup(amountUsd, callbacks) {
    var savedBalance = localStorage.getItem(BALANCE_KEY);
    var balance = savedBalance == null ? 5 : Number(savedBalance);
    if (!isFinite(balance)) balance = 5;
    balance = Math.round((balance + amountUsd) * 100) / 100;
    try { localStorage.setItem(BALANCE_KEY, String(balance)); } catch (e) {}
    notice('Demo mode: added $' + amountUsd.toFixed(2) + ' to your local balance.');
    if (callbacks && typeof callbacks.onSuccess === 'function') {
      callbacks.onSuccess({ amountUsd: amountUsd, balance: balance, simulated: true });
    }
  }

  function post(path, payload, callbacks, idempotencyKey) {
    var headers = { 'Content-Type': 'application/json' };
    if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
    return fetch(apiUrl(path), {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(payload)
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (response.status !== 200 || !data.url) {
          throw new Error(data.error || 'Checkout could not start. Please try again.');
        }
        window.location.href = data.url;
        return data;
      });
    }).catch(function (error) {
      fail(callbacks, error && error.message ? error.message : 'Checkout could not start. Please try again.');
      return null;
    });
  }

  function checkout(slug, listing, user, callbacks) {
    var priceUsd = Number(listing && listing.priceOwn);
    if (!slug) {
      fail(callbacks, 'Checkout could not start: missing listing.');
      return;
    }
    var email = user && user.email ? user.email : '';
    return post('/api/checkout', {
      slug: slug,
      priceUsd: priceUsd,
      email: email,
      mode: 'payment'
    }, callbacks, checkoutAttemptKey(slug, email));
  }

  function topup(amountUsd, callbacks) {
    var amount = Number(amountUsd);
    var cents = Math.round(amount * 100);
    if (!isFinite(amount) || Math.abs(amount * 100 - cents) > 0.000001 || cents < MIN_TOPUP_USD * 100) {
      fail(callbacks, 'Top-ups start at $5.00 and support up to two decimal places.');
      return;
    }
    amount = cents / 100;
    if (!isConfigured()) {
      simulateTopup(amount, callbacks);
      return;
    }
    var user = window.ClerkAuth && window.ClerkAuth.getUser ? window.ClerkAuth.getUser() : null;
    if (!user || !user.id) {
      fail(callbacks, 'Sign in before topping up your balance.');
      return;
    }
    return post('/api/topup', { user_id: user.id, amount_usd: amount }, callbacks);
  }

  if (isConfigured() && typeof document !== 'undefined' && document.createElement && document.head && !document.getElementById('stripe-js')) {
    var script = document.createElement('script');
    script.id = 'stripe-js';
    script.src = 'https://js.stripe.com/v3/';
    script.async = true;
    document.head.appendChild(script);
  }

  window.StripePay = {
    getKey: getKey,
    isConfigured: isConfigured,
    checkout: checkout,
    topup: topup,
    minimumTopupUsd: MIN_TOPUP_USD
  };
})();
