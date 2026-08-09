/* stripe.js — Stripe Checkout for purchases and credit top-ups, with a
 * local simulated fallback while the shared publishable key is a placeholder.
 *
 * Exposes window.StripePay = { getKey, isConfigured, checkout, topup }.
 */
(function () {
  'use strict';

  var PLACEHOLDER = 'pk_test_placeholder';
  var PURCHASE_KEY = 'cognition_purchases_v1';
  var BALANCE_KEY = 'omo_balance_v1';

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

  function recordPurchase(slug, listing) {
    var purchases = [];
    try { purchases = JSON.parse(localStorage.getItem(PURCHASE_KEY) || '[]'); } catch (e) { purchases = []; }
    if (!Array.isArray(purchases)) purchases = [];
    if (!purchases.some(function (purchase) { return purchase && purchase.slug === slug; })) {
      purchases.push({
        slug: slug,
        priceOwn: listing && listing.priceOwn != null ? listing.priceOwn : null,
        date: new Date().toISOString()
      });
      try { localStorage.setItem(PURCHASE_KEY, JSON.stringify(purchases)); } catch (e) {}
    }
  }

  function simulateCheckout(slug, listing, callbacks) {
    recordPurchase(slug, listing);
    if (callbacks && typeof callbacks.onSuccess === 'function') {
      callbacks.onSuccess({ slug: slug, simulated: true });
    }
  }

  function simulateTopup(amountUsd, callbacks) {
    var balance = Number(localStorage.getItem(BALANCE_KEY));
    if (!isFinite(balance)) balance = 10;
    balance = Math.round((balance + amountUsd) * 100) / 100;
    try { localStorage.setItem(BALANCE_KEY, String(balance)); } catch (e) {}
    notice('Demo mode: added $' + amountUsd.toFixed(2) + ' to your local balance.');
    if (callbacks && typeof callbacks.onSuccess === 'function') {
      callbacks.onSuccess({ amountUsd: amountUsd, balance: balance, simulated: true });
    }
  }

  function post(path, payload, callbacks) {
    return fetch(apiUrl(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
    if (!isConfigured() || !isFinite(priceUsd) || priceUsd <= 0) {
      simulateCheckout(slug, listing, callbacks);
      return;
    }
    return post('/api/checkout', {
      slug: slug,
      priceUsd: priceUsd,
      email: user && user.email ? user.email : '',
      mode: 'payment'
    }, callbacks);
  }

  function topup(amountUsd, callbacks) {
    var amount = Number(amountUsd);
    if (!isFinite(amount) || amount <= 0) {
      fail(callbacks, 'Choose a valid top-up amount.');
      return;
    }
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
    topup: topup
  };
})();
