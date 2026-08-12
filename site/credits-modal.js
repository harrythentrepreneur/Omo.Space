/* Omo's reusable credits, top-up, and recent-usage popup. */
(function () {
  'use strict';

  var BALANCE_KEY = 'omo_balance_v1';
  var USAGE_KEY = 'omo_usage_v1';
  var chosenAmount = 20;
  var lastFocused = null;
  var requestId = 0;
  var stripePromise = null;
  var account = { mode: 'loading', balanceUsd: 5, runs: [] };

  function ensureStyles() {
    if (document.querySelector('link[href$="credits-modal.css"]')) return;
    var stylesheet = document.createElement('link');
    stylesheet.rel = 'stylesheet';
    stylesheet.href = 'credits-modal.css';
    document.head.appendChild(stylesheet);
  }

  function modalMarkup() {
    return [
      '<div class="credits-modal" id="credits-modal" hidden>',
        '<section class="credits-modal__card" role="dialog" aria-modal="true" aria-labelledby="credits-modal-title" aria-describedby="credits-modal-subtitle">',
          '<header class="credits-modal__header">',
            '<div class="credits-modal__title-wrap">',
              '<h2 class="credits-modal__title" id="credits-modal-title">Credits</h2>',
              '<p class="credits-modal__subtitle" id="credits-modal-subtitle">Top up and see where your balance went.</p>',
            '</div>',
            '<button class="credits-modal__close" id="credits-modal-close" type="button" aria-label="Close credits">&#10005;</button>',
          '</header>',
          '<div class="credits-modal__body">',
            '<section class="credits-modal__section credits-modal__section--topup" id="topup-card" aria-label="Top up credits">',
              '<p class="card-intro">Your balance pays for cloud runs. Every new account gets $5 free.</p>',
              '<p class="credit-balance" id="credit-balance">$5.00</p>',
              '<p class="empty-credit-note" id="empty-credit-note" hidden>You\u2019re out of credits, but you can keep going in seconds \u2014 top up from $5 below.</p>',
              '<form id="topup-form" novalidate>',
                '<div class="amount-row" role="group" aria-label="Top-up amount">',
                  '<button class="amount-chip is-active" type="button" data-amount="20" aria-pressed="true">$20</button>',
                  '<button class="amount-chip" type="button" data-amount="50" aria-pressed="false">$50</button>',
                  '<button class="amount-chip" type="button" data-amount="100" aria-pressed="false">$100</button>',
                  '<button class="amount-chip" type="button" data-amount="200" aria-pressed="false">$200</button>',
                '</div>',
                '<label class="custom-amount-row" for="custom-amount"><span class="custom-amount-label">Custom $</span><input class="custom-amount" id="custom-amount" type="number" min="5" step="0.01" inputmode="decimal" placeholder="Minimum $5" aria-describedby="topup-note"></label>',
                '<button class="button" id="topup-btn" type="submit">Top up with Stripe</button>',
                '<p class="form-note" id="topup-note" role="status" aria-live="polite"></p>',
              '</form>',
            '</section>',
            '<section class="credits-modal__section" id="usage-card" aria-labelledby="usage-title">',
              '<h2 id="usage-title">Recent usage</h2>',
              '<p class="card-intro">Signed-in helper runs, newest first.</p>',
              '<p class="usage-empty" id="usage-empty">No runs yet \u2014 pick a helper and try it.</p>',
              '<ul class="usage-list" id="usage-list" hidden></ul>',
              '<p class="api-foot">API base: <code id="api-base-label">\u2014</code> \u00b7 Your <code>omo_</code> key is deterministic per account.</p>',
            '</section>',
          '</div>',
          '<p class="credits-modal__footer">Secure checkout by Stripe \u00b7 Recent usage can take a moment to appear.</p>',
        '</section>',
      '</div>'
    ].join('');
  }

  function ensureMarkup() {
    if (document.getElementById('credits-modal')) return;
    var wrapper = document.createElement('div');
    wrapper.innerHTML = modalMarkup();
    document.body.appendChild(wrapper.firstChild);
  }

  ensureStyles();
  ensureMarkup();

  var modal = document.getElementById('credits-modal');
  var card = modal && modal.querySelector('.credits-modal__card');
  var closeButton = document.getElementById('credits-modal-close');
  var form = document.getElementById('topup-form');
  var customAmount = document.getElementById('custom-amount');
  var topupButton = document.getElementById('topup-btn');
  var amountChips = modal ? modal.querySelectorAll('.amount-chip') : [];

  if (!modal || !card || !closeButton || !form) return;

  function apiBase() {
    return String(window.OMO_API_BASE || '').replace(/\/+$/, '');
  }

  function formatUsd(value) {
    var amount = Number(value);
    return '$' + (isFinite(amount) ? amount : 0).toFixed(2);
  }

  function storageGet(key) {
    try { return window.localStorage.getItem(key); }
    catch (error) { return null; }
  }

  function storageSet(key, value) {
    try { window.localStorage.setItem(key, value); }
    catch (error) {}
  }

  function currentUser() {
    if (window.ClerkAuth && typeof window.ClerkAuth.getUser === 'function') {
      var clerkUser = window.ClerkAuth.getUser();
      if (clerkUser && clerkUser.id) return clerkUser;
    }
    try {
      var saved = JSON.parse(storageGet('cognition_user') || 'null');
      return saved && saved.id ? saved : null;
    } catch (error) {
      return null;
    }
  }

  function isDemoUser(user) {
    var key = String(window.CLERK_PUBLISHABLE_KEY || '').trim();
    return window.location.protocol === 'file:' || !!(user && user.demo) || !/^pk_(?:test|live)_/.test(key) || key === 'pk_test_placeholder';
  }

  function getSessionToken() {
    if (window.Clerk && window.Clerk.session && typeof window.Clerk.session.getToken === 'function') {
      return Promise.resolve(window.Clerk.session.getToken()).then(function (token) {
        if (!token) throw new Error('Your sign-in session has expired. Sign in again.');
        return token;
      });
    }
    return Promise.reject(new Error('A verified sign-in session is not available.'));
  }

  function runsFromStorage() {
    try {
      var runs = JSON.parse(storageGet(USAGE_KEY) || '[]');
      return Array.isArray(runs) ? runs : [];
    } catch (error) {
      return [];
    }
  }

  function updateNavBalance(balanceUsd) {
    var links = document.querySelectorAll('[data-omo-login].omo-nav-credit');
    for (var i = 0; i < links.length; i += 1) {
      var link = links[i];
      var icon = document.createElement('span');
      var amount = document.createElement('span');
      icon.className = 'omo-nav-credit-icon';
      icon.setAttribute('aria-hidden', 'true');
      icon.textContent = '\u25d2';
      amount.textContent = formatUsd(balanceUsd);
      link.textContent = '';
      link.appendChild(icon);
      link.appendChild(amount);
      link.setAttribute('aria-label', formatUsd(balanceUsd) + ' in credits \u2014 open credits');
      link.title = formatUsd(balanceUsd) + ' in credits';
    }
  }

  function renderUsage() {
    var list = document.getElementById('usage-list');
    var empty = document.getElementById('usage-empty');
    var runs = Array.isArray(account.runs) ? account.runs : [];
    if (!list || !empty) return;
    list.textContent = '';
    empty.hidden = runs.length > 0;
    list.hidden = runs.length === 0;

    for (var i = 0; i < runs.length; i += 1) {
      var run = runs[i] || {};
      var item = document.createElement('li');
      var slug = document.createElement('span');
      var cost = document.createElement('span');
      var time = document.createElement('span');
      var dateLabel = '';
      try {
        var date = new Date(run.created_at || run.ts);
        if (!isNaN(date.getTime())) dateLabel = date.toLocaleString();
      } catch (error) {}
      item.className = 'usage-row';
      slug.className = 'usage-slug';
      cost.className = 'usage-cost';
      time.className = 'usage-time';
      slug.textContent = run.slug || 'Helper run';
      cost.textContent = formatUsd(run.cost_usd != null ? run.cost_usd : run.costUsd);
      time.textContent = dateLabel;
      item.appendChild(slug);
      item.appendChild(cost);
      item.appendChild(time);
      list.appendChild(item);
    }
  }

  function render() {
    var balance = document.getElementById('credit-balance');
    var emptyNote = document.getElementById('empty-credit-note');
    var baseLabel = document.getElementById('api-base-label');
    if (balance) balance.textContent = formatUsd(account.balanceUsd);
    if (emptyNote) emptyNote.hidden = account.balanceUsd > 0;
    if (baseLabel) baseLabel.textContent = apiBase() || '(same origin)';
    renderUsage();
    updateNavBalance(account.balanceUsd);
  }

  function showNote(message, state) {
    var note = document.getElementById('topup-note');
    if (!note) return;
    note.textContent = message || '';
    note.className = 'form-note' + (state === 'ok' ? ' is-ok' : state === 'error' ? ' is-err' : '');
  }

  function loadDemoAccount() {
    var savedBalance = Number(storageGet(BALANCE_KEY));
    account.mode = 'mock';
    account.balanceUsd = isFinite(savedBalance) ? savedBalance : 5;
    account.runs = runsFromStorage();
    storageSet(BALANCE_KEY, String(account.balanceUsd));
    render();
  }

  function refresh() {
    var user = currentUser();
    var activeRequest = ++requestId;
    if (!user) {
      account.mode = 'unavailable';
      account.balanceUsd = 0;
      account.runs = [];
      render();
      showNote('Sign in to manage credits and see recent usage.', 'error');
      return Promise.resolve(account);
    }

    if (isDemoUser(user)) {
      loadDemoAccount();
      return Promise.resolve(account);
    }

    account.mode = 'loading';
    return getSessionToken().then(function (token) {
      return fetch(apiBase() + '/api/me', {
        headers: { Authorization: 'Bearer ' + token, Accept: 'application/json' }
      });
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        return { ok: response.ok, data: data };
      });
    }).then(function (result) {
      if (activeRequest !== requestId) return account;
      var data = result.data || {};
      if (!result.ok || !data.ok) throw new Error(data.message || 'Your credits could not be loaded.');
      account.mode = 'server';
      account.balanceUsd = Number(data.balance_usd != null ? data.balance_usd : data.balance);
      if (!isFinite(account.balanceUsd)) account.balanceUsd = 0;
      account.runs = Array.isArray(data.runs) ? data.runs : [];
      storageSet(BALANCE_KEY, String(account.balanceUsd));
      storageSet(USAGE_KEY, JSON.stringify(account.runs));
      render();
      return account;
    }).catch(function (error) {
      if (activeRequest !== requestId) return account;
      account.mode = 'unavailable';
      showNote(error && error.message ? error.message : 'Your credits could not be loaded.', 'error');
      render();
      return account;
    });
  }

  function setSelectedAmount(amount) {
    var numeric = Number(amount);
    var matched = false;
    for (var i = 0; i < amountChips.length; i += 1) {
      var active = Number(amountChips[i].getAttribute('data-amount')) === numeric;
      amountChips[i].classList.toggle('is-active', active);
      amountChips[i].setAttribute('aria-pressed', active ? 'true' : 'false');
      if (active) matched = true;
    }
    if (matched) {
      chosenAmount = numeric;
      customAmount.value = '';
    } else if (isFinite(numeric) && numeric > 0) {
      chosenAmount = null;
      customAmount.value = String(numeric);
    }
  }

  function open(options) {
    options = options || {};
    lastFocused = document.activeElement;
    if (options.amount != null) setSelectedAmount(options.amount);
    modal.hidden = false;
    document.body.classList.add('credits-modal-open');
    refresh();
    closeButton.focus({ preventScroll: true });
    window.setTimeout(function () {
      if (!modal.hidden && !modal.contains(document.activeElement)) closeButton.focus({ preventScroll: true });
    }, 0);
  }

  function close() {
    if (modal.hidden) return;
    modal.hidden = true;
    document.body.classList.remove('credits-modal-open');
    if (lastFocused && typeof lastFocused.focus === 'function') lastFocused.focus({ preventScroll: true });
  }

  function setBusy(busy) {
    topupButton.disabled = busy;
    topupButton.setAttribute('aria-busy', busy ? 'true' : 'false');
    topupButton.textContent = busy ? 'Opening Stripe\u2026' : 'Top up with Stripe';
  }

  function loadStripe() {
    if (window.StripePay && typeof window.StripePay.topup === 'function') return Promise.resolve(window.StripePay);
    if (stripePromise) return stripePromise;
    stripePromise = new Promise(function (resolve, reject) {
      var script = document.createElement('script');
      script.src = 'stripe.js';
      script.onload = function () {
        if (window.StripePay && typeof window.StripePay.topup === 'function') resolve(window.StripePay);
        else reject(new Error('Stripe checkout could not be loaded.'));
      };
      script.onerror = function () { reject(new Error('Stripe checkout could not be loaded.')); };
      document.head.appendChild(script);
    });
    return stripePromise;
  }

  function finishDemoTopup(result, amount) {
    account.balanceUsd = result && isFinite(Number(result.balance)) ? Number(result.balance) : account.balanceUsd + amount;
    storageSet(BALANCE_KEY, String(account.balanceUsd));
    render();
    setBusy(false);
    showNote('Demo top-up added ' + formatUsd(amount) + ' to your local balance.', 'ok');
    if (window.__omoDashboard && typeof window.__omoDashboard.refresh === 'function') window.__omoDashboard.refresh();
  }

  function submitTopup(event) {
    event.preventDefault();
    var hasCustom = String(customAmount.value || '').trim() !== '';
    var amount = hasCustom ? Number(customAmount.value) : chosenAmount;
    var cents = Math.round(amount * 100);
    if (!isFinite(amount) || Math.abs(amount * 100 - cents) > .000001 || cents < 500) {
      showNote('Enter at least $5.00, with up to two decimal places.', 'error');
      return;
    }
    amount = cents / 100;
    setBusy(true);
    showNote('', '');

    if (account.mode === 'server') {
      getSessionToken().then(function (token) {
        return fetch(apiBase() + '/api/topup', {
          method: 'POST',
          headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' },
          body: JSON.stringify({ amount_usd: amount })
        });
      }).then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (data) {
          return { ok: response.ok, data: data };
        });
      }).then(function (result) {
        if (!result.ok || !result.data.url) throw new Error(result.data.error || 'Checkout could not start right now.');
        window.location.assign(result.data.url);
      }).catch(function (error) {
        setBusy(false);
        showNote(error && error.message ? error.message : 'Checkout could not start right now.', 'error');
      });
      return;
    }

    loadStripe().then(function (stripe) {
      return stripe.topup(amount, {
        onSuccess: function (result) { finishDemoTopup(result, amount); },
        onError: function (message) {
          setBusy(false);
          showNote(message || 'Checkout could not start right now.', 'error');
        }
      });
    }).catch(function (error) {
      setBusy(false);
      showNote(error && error.message ? error.message : 'Checkout could not start right now.', 'error');
    });
  }

  function handleKeydown(event) {
    if (modal.hidden) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== 'Tab') return;
    var focusable = Array.prototype.filter.call(
      card.querySelectorAll('button:not([disabled]), input:not([disabled]), a[href]'),
      function (element) { return !element.hidden && element.offsetParent !== null; }
    );
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  for (var i = 0; i < amountChips.length; i += 1) {
    amountChips[i].addEventListener('click', function () {
      setSelectedAmount(Number(this.getAttribute('data-amount')) || 20);
    });
  }

  customAmount.addEventListener('input', function () {
    var hasValue = String(customAmount.value || '').trim() !== '';
    chosenAmount = hasValue ? null : 20;
    for (var i = 0; i < amountChips.length; i += 1) {
      var active = !hasValue && Number(amountChips[i].getAttribute('data-amount')) === 20;
      amountChips[i].classList.toggle('is-active', active);
      amountChips[i].setAttribute('aria-pressed', active ? 'true' : 'false');
    }
  });

  closeButton.addEventListener('click', close);
  modal.addEventListener('click', function (event) { if (event.target === modal) close(); });
  form.addEventListener('submit', submitTopup);
  document.addEventListener('keydown', handleKeydown);
  document.addEventListener('click', function (event) {
    var trigger = event.target.closest && event.target.closest('[data-action="topup-credits"]');
    if (!trigger) return;
    event.preventDefault();
    open();
  });
  window.addEventListener('storage', function (event) {
    if (event.key === BALANCE_KEY || event.key === USAGE_KEY) refresh();
  });
  window.addEventListener('omo:open-credits', function (event) { open(event.detail || {}); });

  window.OmoCredits = {
    open: open,
    close: close,
    refresh: refresh,
    update: function (nextAccount) {
      if (!nextAccount) return;
      account.mode = nextAccount.mode || account.mode;
      account.balanceUsd = Number(nextAccount.balanceUsd);
      if (!isFinite(account.balanceUsd)) account.balanceUsd = 0;
      account.runs = Array.isArray(nextAccount.runs) ? nextAccount.runs : [];
      render();
    }
  };

  try {
    var params = new URLSearchParams(window.location.search || '');
    if (params.has('topup')) {
      var result = params.get('topup');
      if (result === 'success') showNote('Payment complete \u2014 refreshing your balance.', 'ok');
      else if (result === 'cancelled') showNote('Top-up cancelled \u2014 your balance was not changed.', 'error');
      else if (result === 'needed') showNote('You\u2019re out of credits. Choose an amount to keep going.', '');
      open();
      if (result === 'success') window.setTimeout(refresh, 1500);
    }
  } catch (error) {}
})();
