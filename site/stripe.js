/* stripe.js — Stripe Checkout payments for the Cognition storefront, with a
 * simulated fallback so the whole flow works with zero Stripe credentials.
 *
 * How it works:
 *  - Reads the publishable key from window.STRIPE_PUBLISHABLE_KEY (set in
 *    index.html). While the key is the placeholder ('pk_test_placeholder'),
 *    the store runs in SIMULATED mode: buying records the purchase to
 *    localStorage (cognition_purchases_v1) and calls onSuccess, so the
 *    library + buy flow is fully testable with zero Stripe setup.
 *  - With a real key, creates a Stripe Checkout session via the Cognition
 *    worker (POST https://cognition-demo.pages.dev/api/checkout, which
 *    returns a Checkout URL when the worker has STRIPE_SECRET_KEY set) and
 *    redirects the buyer to Stripe's hosted Checkout page. If the worker is
 *    unreachable or not configured, it falls back to the simulated flow with
 *    a friendly notice.
 *
 * Exposes window.StripePay = { getKey, isConfigured, checkout }.
 */
(function () {
  'use strict';

  var PLACEHOLDER = 'pk_test_placeholder';
  var PURCHASE_KEY = 'cognition_purchases_v1';
  var CHECKOUT_URL = 'https://cognition-demo.pages.dev/api/checkout';

  function getKey() {
    return (window.STRIPE_PUBLISHABLE_KEY || '').trim() || PLACEHOLDER;
  }

  function isConfigured() {
    var k = getKey();
    // Any key containing 'placeholder' counts as "not configured yet".
    return !!k && k !== PLACEHOLDER && k.toLowerCase().indexOf('placeholder') === -1;
  }

  // Load the Stripe.js SDK so redirectToCheckout-style features (and any
  // future Payment Element work) are available once real keys are set.
  // Harmless in demo mode: nothing calls into it.
  function loadStripeJS() {
    if (typeof document === 'undefined' || !document.createElement || !document.head) return;
    if (document.getElementById('stripe-js')) return;
    var s = document.createElement('script');
    s.id = 'stripe-js';
    s.src = 'https://js.stripe.com/v3/';
    s.async = true;
    document.head.appendChild(s);
  }

  // Tiny transient banner for fallback notices — self-contained, no redesign.
  function notice(msg) {
    if (typeof document === 'undefined' || !document.body) return;
    var el = document.createElement('div');
    el.setAttribute('role', 'status');
    el.style.cssText =
      'position:fixed;left:50%;bottom:20px;transform:translateX(-50%);z-index:400;' +
      'max-width:min(92vw,480px);padding:12px 18px;border-radius:12px;' +
      'background:#17352C;color:#fff;font:700 14px/1.45 "DM Sans",system-ui,sans-serif;' +
      'box-shadow:0 8px 24px rgba(23,53,44,.25)';
    el.textContent = msg;
    document.body.appendChild(el);
    if (typeof setTimeout === 'function') {
      setTimeout(function () {
        if (el.parentNode) el.parentNode.removeChild(el);
      }, 6000);
    }
  }

  function recordPurchase(slug, listing) {
    var list = [];
    try { list = JSON.parse(localStorage.getItem(PURCHASE_KEY) || '[]'); } catch (e) { list = []; }
    if (!Array.isArray(list)) list = [];
    var exists = list.some(function (it) { return it && it.slug === slug; });
    if (!exists) {
      list.push({
        slug: slug,
        priceOwn: listing && listing.priceOwn != null ? listing.priceOwn : null,
        date: new Date().toISOString()
      });
      try { localStorage.setItem(PURCHASE_KEY, JSON.stringify(list)); } catch (e) {}
    }
  }

  // Simulated purchase: record it locally and confirm. Used when no real
  // Stripe key is present, or when the checkout worker is unavailable.
  function simulateCheckout(slug, listing, user, callbacks) {
    recordPurchase(slug, listing);
    if (callbacks && typeof callbacks.onSuccess === 'function') {
      callbacks.onSuccess({ slug: slug, simulated: true });
    }
  }

  // Real path: ask the Cognition worker for a Checkout session, then send the
  // buyer to Stripe's hosted page. Falls back to simulateCheckout (with a
  // notice) if the worker is unreachable or not configured.
  function realCheckout(slug, listing, user, callbacks) {
    var priceUsd = listing && listing.priceOwn != null ? listing.priceOwn : 0;
    var payload = { slug: slug, priceUsd: priceUsd, mode: 'payment' };
    if (user && user.email) payload.email = user.email;

    return fetch(CHECKOUT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        return { status: res.status, data: data };
      });
    }).then(function (res) {
      if (res.status === 501 || !res.data || !res.data.url) {
        // Worker alive but Stripe not configured on it yet → simulate locally.
        notice('Live checkout is not configured yet — recorded as a simulated purchase.');
        simulateCheckout(slug, listing, user, callbacks);
        return;
      }
      if (res.status !== 200) {
        if (callbacks && typeof callbacks.onError === 'function') {
          callbacks.onError((res.data && res.data.error) || 'Checkout could not start. Please try again.');
        }
        return;
      }
      window.location.href = res.data.url;
    }).catch(function () {
      notice('Could not reach the checkout server — recorded as a simulated purchase.');
      simulateCheckout(slug, listing, user, callbacks);
    });
  }

  // Public entry: buy a listing. callbacks = { onSuccess(purchase), onError(msg) }.
  // Returns a Promise in the real-checkout path (awaitable in tests); the
  // simulated path completes synchronously.
  function checkout(slug, listing, user, callbacks) {
    if (!isConfigured()) {
      simulateCheckout(slug, listing, user, callbacks);
      return;
    }
    return realCheckout(slug, listing, user, callbacks);
  }

  loadStripeJS();

  window.StripePay = {
    getKey: getKey,
    isConfigured: isConfigured,
    checkout: checkout
  };
})();
