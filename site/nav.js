(function () {
  'use strict';

  var authModalPromise = null;
  var contextualCatalogPromise = null;
  var balanceClientPromise = null;
  var balanceInFlight = null;
  var balanceRequestId = 0;
  var authResolutionStarted = false;
  var authResolved = false;
  var authSubscribed = false;
  var authLinksPrimed = false;
  var lastResolvedAuthKey = '';
  var freshGrantState = null;
  var BALANCE_CACHE_PREFIX = 'omo_nav_balance_v1:';
  var BALANCE_TIMEOUT_MS = 5000;
  var SESSION_RETRY_MS = 250;
  var SIGNUP_GRANT_CENTS = 500;
  var FRESH_ACCOUNT_MAX_AGE_MS = 2 * 60 * 1000;
  var FRESH_GRANT_RETRY_MS = 1000;
  var AUTH_HINT_KEY = 'omo_nav_auth_hint_v1';
  var AUTH_HINT_MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000;

  function installCreditStyles() {
    if (document.getElementById('omo-nav-credit-styles')) return;

    var style = document.createElement('style');
    style.id = 'omo-nav-credit-styles';
    style.textContent =
      '.omo-site-header{position:relative;top:auto;border-bottom:1px solid #D9E2DC;background:#F2F6F1;backdrop-filter:none;-webkit-backdrop-filter:none}' +
      '.omo-site-header>.omo-nav-row{width:min(1160px,calc(100% - 48px));min-height:68px;margin-inline:auto;padding-block:8px}' +
      '.omo-nav-row>.omo-nav-brand{flex:1 1 auto}' +
      '.omo-nav-brand{gap:7px}' +
      '.omo-nav-brand .wordmark{min-height:44px;align-self:auto}' +
      '.omo-nav-menu-toggle{width:36px;height:36px;min-height:36px;padding:0;border:0;border-radius:999px;background:#E8E8E6;color:var(--pine,#17352C);box-shadow:none;transition:background-color .15s ease}' +
      '.omo-nav-menu-toggle:hover,.omo-nav-menu-toggle[aria-expanded="true"]{border-color:transparent;background:#F6F0E7;box-shadow:none;transform:none}' +
      '.omo-nav-menu-toggle:focus-visible{border-color:transparent;background:#F6F0E7;outline:3px solid rgba(255,107,61,.3);outline-offset:2px}' +
      '.omo-nav-chevron{position:relative;display:block;width:13px;height:13px;font-size:0;line-height:1;transition:transform .15s ease}' +
      '.omo-nav-chevron::before{content:"";position:absolute;top:2px;left:2px;width:7px;height:7px;border-right:2px solid currentColor;border-bottom:2px solid currentColor;transform:rotate(45deg)}' +
      '.omo-nav-menu-toggle[aria-expanded="true"] .omo-nav-chevron{transform:rotate(180deg)}' +
      '.omo-nav-popover{top:calc(100% + 8px);width:min(292px,calc(100vw - 24px));max-height:calc(100dvh - 86px);overflow-y:auto;padding:10px;border:1px solid rgba(23,53,44,.08);border-radius:15px;background:#FFFFFF;box-shadow:0 20px 48px rgba(23,53,44,.16),0 3px 10px rgba(23,53,44,.09)}' +
      '.omo-nav-primary-links{display:grid;gap:2px}' +
      '.omo-nav-popover .omo-nav-primary-links>a,.omo-nav-popover .omo-nav-logout>a{min-height:48px;display:grid;grid-template-columns:32px minmax(0,1fr);align-items:center;gap:11px;padding:8px;border-radius:10px;background:transparent;color:var(--pine,#17352C);font-size:13.5px;font-weight:650;line-height:1.25;box-shadow:none}' +
      '.omo-nav-popover .omo-nav-primary-links>a:hover,.omo-nav-popover .omo-nav-primary-links>a:focus-visible,.omo-nav-popover .omo-nav-primary-links>a[aria-current="page"],.omo-nav-popover .omo-nav-logout>a:hover,.omo-nav-popover .omo-nav-logout>a:focus-visible{color:var(--pine,#17352C);background:#F6F0E7;box-shadow:none;text-decoration:none}' +
      '.omo-nav-static-icon{width:32px;height:32px;display:grid;place-items:center;border-radius:8px;background:#E9E9E7;color:#777A77;font-size:18px;font-weight:500;line-height:1}' +
      '.omo-nav-sell .omo-nav-static-icon{background:#FFF0E8;color:#C65B3A}' +
      '.omo-nav-static-label{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
      '.omo-nav-logout{margin-top:6px;padding-top:0;border-top:0}' +
      '.omo-nav-popover .omo-nav-logout>a{color:#4D5B56}' +
      '.omo-nav-login{min-width:96px;justify-content:center}' +
      '.omo-nav-login.omo-nav-credit{width:96px;min-width:96px;max-width:96px;gap:6px;padding-inline:9px;border-radius:999px;font-variant-numeric:tabular-nums}' +
      '.omo-nav-credit-icon{font-size:16px;line-height:1}' +
      '.omo-nav-credit-amount{min-width:0;overflow:hidden;text-overflow:ellipsis}' +
      '.omo-nav-credit-spinner{width:13px;height:13px;flex:0 0 13px;border:2px solid var(--mint,#BDEFD4);border-top-color:var(--pine,#17352C);border-radius:50%;animation:omo-nav-credit-spin .7s linear infinite}' +
      '.omo-nav-credit.is-balance-unavailable .omo-nav-credit-icon{opacity:.52}' +
      '@keyframes omo-nav-credit-spin{to{transform:rotate(360deg)}}' +
      '.omo-nav-workflow-identity{min-width:0;max-width:min(310px,calc(100vw - 190px));min-height:40px;display:inline-flex;align-items:center;gap:8px;flex:0 1 auto;color:var(--pine,#17352C);text-decoration:none}' +
      '.omo-nav-workflow-identity:hover,.omo-nav-workflow-identity:focus-visible{color:var(--pine,#17352C);text-decoration:none}' +
      '.omo-nav-workflow-identity:focus-visible{outline:3px solid rgba(255,107,61,.34);outline-offset:2px}' +
      '.omo-nav-context-thumb{width:30px;height:30px;display:grid;place-items:center;flex:0 0 30px;overflow:hidden;border-radius:8px;background:var(--cream,#F4F1E8);font-size:17px}' +
      '.omo-nav-context-thumb img{width:100%;height:100%;display:block;object-fit:cover}' +
      '.omo-nav-context-name{min-width:0;overflow:hidden;color:var(--pine,#17352C);font:600 15px/1.12 "Fraunces",Georgia,serif;letter-spacing:-.015em;text-overflow:ellipsis;white-space:nowrap}' +
      '@media(max-width:820px){.omo-site-header>.omo-nav-row{width:100%;padding-inline:max(16px,env(safe-area-inset-left));padding-right:max(16px,env(safe-area-inset-right))}.omo-nav-row>.omo-nav-brand{min-width:0;position:static}.omo-nav-menu{position:static}.omo-nav-menu-toggle{width:44px;height:44px;min-height:44px}.omo-nav-popover{max-height:calc(100dvh - 84px);overscroll-behavior:contain;-webkit-overflow-scrolling:touch;scrollbar-gutter:stable}.omo-nav-login{min-height:44px;max-width:42vw;overflow:hidden;text-overflow:ellipsis}.omo-nav-workflow-identity{min-height:44px}}' +
      '@media(max-width:480px){.omo-nav-popover{left:max(12px,env(safe-area-inset-left));right:max(12px,env(safe-area-inset-right));width:auto;max-width:none}.omo-nav-workflow-identity{max-width:calc(100vw - 214px);gap:6px}.omo-nav-context-thumb{width:28px;height:28px;flex-basis:28px}.omo-nav-context-name{font-size:13px}}' +
      '@media(prefers-reduced-motion:reduce){.omo-nav-credit-spinner{animation:omo-nav-credit-pulse 1s ease-in-out infinite alternate}@keyframes omo-nav-credit-pulse{to{opacity:.45}}}';
    document.head.appendChild(style);
  }

  function isSignedIn() {
    if (window.ClerkAuth && typeof window.ClerkAuth.isSignedIn === 'function') {
      return window.ClerkAuth.isSignedIn();
    }

    if (!demoAuthConfigured()) return false;
    try {
      var user = JSON.parse(window.localStorage.getItem('cognition_user') || 'null');
      return !!(user && user.id);
    } catch (error) {
      return false;
    }
  }

  function currentUser() {
    if (window.ClerkAuth && typeof window.ClerkAuth.getUser === 'function') {
      return window.ClerkAuth.getUser();
    }

    if (!demoAuthConfigured()) return null;
    try {
      return JSON.parse(window.localStorage.getItem('cognition_user') || 'null');
    } catch (error) {
      return null;
    }
  }

  function persistedUser() {
    try {
      var user = JSON.parse(window.localStorage.getItem('cognition_user') || 'null');
      return user && user.id ? user : null;
    } catch (error) {
      return null;
    }
  }

  function demoAuthConfigured() {
    if (window.location && window.location.protocol === 'file:') return true;
    var key = typeof window.CLERK_PUBLISHABLE_KEY === 'string'
      ? window.CLERK_PUBLISHABLE_KEY.trim()
      : '';
    return !!key && (key === 'pk_test_placeholder' || !/^pk_(test|live)_/.test(key));
  }

  function readSignedInHint() {
    var demoUser = demoAuthConfigured() ? persistedUser() : null;
    if (demoUser) return { userId: String(demoUser.id) };

    try {
      var hint = JSON.parse(window.localStorage.getItem(AUTH_HINT_KEY) || 'null');
      var age = Date.now() - Number(hint && hint.confirmedAt);
      if (!hint || hint.state !== 'signed-in' || !hint.userId || !isFinite(age) ||
          age < 0 || age > AUTH_HINT_MAX_AGE_MS) return null;
      return { userId: String(hint.userId) };
    } catch (error) {
      return null;
    }
  }

  function writeSignedInHint(userId) {
    if (!userId) return;
    try {
      window.localStorage.setItem(AUTH_HINT_KEY, JSON.stringify({
        state: 'signed-in',
        userId: String(userId),
        confirmedAt: Date.now()
      }));
    } catch (error) {}
  }

  function clearSignedInHint() {
    try { window.localStorage.removeItem(AUTH_HINT_KEY); } catch (error) {}
  }

  function formatBalance(cents) {
    return (Math.max(0, Number(cents)) / 100).toFixed(2);
  }

  function balanceCacheKey(userId) {
    return BALANCE_CACHE_PREFIX + encodeURIComponent(String(userId));
  }

  function readCachedBalance(userId) {
    if (!userId) return null;
    try {
      var cached = JSON.parse(window.localStorage.getItem(balanceCacheKey(userId)) || 'null');
      var cents = Number(cached && cached.balanceCents);
      var cachedAt = Number(cached && cached.cachedAt);
      if (!cached || cached.userId !== userId || !isFinite(cents) || cents < 0 ||
          Math.round(cents) !== cents || !isFinite(cachedAt) || cachedAt <= 0) return null;
      return { balanceCents: cents, cachedAt: cachedAt };
    } catch (error) {
      return null;
    }
  }

  function writeCachedBalance(account) {
    var userId = String(account && account.userId || '');
    var cents = Number(account && account.balanceCents);
    if (!userId || !isFinite(cents) || cents < 0 || Math.round(cents) !== cents) return;
    try {
      window.localStorage.setItem(balanceCacheKey(userId), JSON.stringify({
        userId: userId,
        balanceCents: cents,
        cachedAt: Date.now()
      }));
    } catch (error) {}
  }

  function clerkAccountCreatedAt(userId) {
    var clerkUser = window.Clerk && window.Clerk.user;
    if (!clerkUser || String(clerkUser.id || '') !== String(userId || '')) return 0;
    var value = clerkUser.createdAt;
    var timestamp = value && typeof value.getTime === 'function' ? value.getTime() : Number(value);
    if (!isFinite(timestamp)) timestamp = Date.parse(String(value || ''));
    if (isFinite(timestamp) && timestamp > 0 && timestamp < 100000000000) timestamp *= 1000;
    return isFinite(timestamp) ? timestamp : 0;
  }

  function isFreshClerkAccount(userId, cached) {
    if (!userId || cached || demoAuthConfigured()) return false;
    var createdAt = clerkAccountCreatedAt(userId);
    var age = Date.now() - createdAt;
    return createdAt > 0 && age >= 0 && age <= FRESH_ACCOUNT_MAX_AGE_MS;
  }

  function clearFreshGrant(state) {
    if (state && freshGrantState !== state) return;
    if (freshGrantState && freshGrantState.timer) window.clearTimeout(freshGrantState.timer);
    freshGrantState = null;
  }

  function activeFreshGrant(userId) {
    return freshGrantState && freshGrantState.userId === userId ? freshGrantState : null;
  }

  function renderCreditLink(link, balanceCents, state) {
    var hasBalance = balanceCents != null && isFinite(Number(balanceCents));
    var formatted = hasBalance ? formatBalance(balanceCents) : '';
    var icon = document.createElement('span');
    icon.className = state === 'loading' ? 'omo-nav-credit-spinner' : 'omo-nav-credit-icon';
    icon.setAttribute('aria-hidden', 'true');
    if (state !== 'loading') icon.textContent = '\u25d2';

    link.textContent = '';
    link.appendChild(icon);
    var amount = document.createElement('span');
    amount.className = 'omo-nav-credit-amount';
    amount.textContent = hasBalance ? '$' + formatted : (state === 'unavailable' ? '\u2014' : '$\u2026');
    link.appendChild(amount);
    link.href = '/billing.html';
    link.hidden = false;
    link.classList.remove('omo-nav-auth-pending');
    link.classList.add('omo-nav-credit');
    link.classList.remove('is-balance-loading');
    link.classList.remove('is-balance-unavailable');
    link.removeAttribute('aria-busy');
    link.removeAttribute('tabindex');
    link.setAttribute('data-omo-auth-state', 'signed-in');
    link.setAttribute('aria-live', 'polite');

    if (state === 'loading') {
      link.classList.add('is-balance-loading');
      link.setAttribute('aria-busy', 'true');
      link.setAttribute('aria-label', hasBalance ? '$' + formatted + ' in credits, refreshing' : 'Loading credit balance');
      link.title = hasBalance ? 'Refreshing $' + formatted + ' balance' : 'Loading balance';
    } else if (state === 'unavailable') {
      link.classList.add('is-balance-unavailable');
      link.setAttribute('aria-label', hasBalance
        ? '$' + formatted + ' last known balance \u2014 view billing'
        : 'Balance unavailable \u2014 view billing');
      link.title = 'Balance unavailable \u2014 view billing';
    } else {
      link.setAttribute('aria-label', '$' + formatted + ' in credits \u2014 view billing');
      link.title = '$' + formatted + ' in credits';
    }
  }

  function renderAllCreditLinks(balanceCents, state) {
    var links = document.querySelectorAll('[data-omo-login]');
    for (var i = 0; i < links.length; i += 1) renderCreditLink(links[i], balanceCents, state);
  }

  function validAuthSlug(value) {
    var slug = String(value || '').trim();
    return /^[a-z0-9][a-z0-9-]{0,100}$/i.test(slug) ? slug : '';
  }

  function validatedAuthDestination() {
    var pathname = window.location.pathname || '/';
    var page = (pathname.split('/').pop() || '').toLowerCase();
    var params;
    try { params = new URLSearchParams(window.location.search || ''); }
    catch (error) { params = new URLSearchParams(); }
    var slug = validAuthSlug(params.get(page === 'dashboard.html' || page === 'dashboard' ? 'open' : 'slug'));
    if (page === 'run.html' || page === 'run') return slug ? '/run.html?slug=' + encodeURIComponent(slug) : '/dashboard.html';
    if (page === 'workflow.html' || page === 'workflow') return slug ? '/workflow.html?slug=' + encodeURIComponent(slug) : '/dashboard.html';
    if (page === 'api.html' || page === 'api') return '/api.html';
    if (page === 'dashboard.html' || page === 'dashboard') {
      return '/dashboard.html' + (slug ? '?open=' + encodeURIComponent(slug) : '');
    }
    return '/dashboard.html';
  }

  function authOptions() {
    var target = validatedAuthDestination();
    var parsed = new URL(target, window.location.origin);
    var slug = validAuthSlug(parsed.searchParams.get(parsed.pathname === '/dashboard.html' ? 'open' : 'slug'));
    return {
      returnTo: target,
      open: slug,
      destination: parsed.pathname === '/run.html' ? 'run' : ''
    };
  }

  function canonicalLoginHref() {
    return '/signup.html?mode=login&return_to=' + encodeURIComponent(validatedAuthDestination());
  }

  function renderLoginFeedback(link, message, withFallback) {
    if (typeof link.insertAdjacentElement !== 'function') return;
    var id = link.getAttribute('data-omo-login-status-id');
    if (!id) {
      id = 'omo-login-status-' + Math.random().toString(36).slice(2, 9);
      link.setAttribute('data-omo-login-status-id', id);
    }
    var status = document.getElementById(id);
    if (!status) {
      status = document.createElement('span');
      status.id = id;
      status.setAttribute('role', 'status');
      status.setAttribute('aria-live', 'polite');
      status.style.cssText = 'display:block;margin-top:6px;font-size:12px;line-height:1.35;color:var(--moss,#6F7E77)';
      link.insertAdjacentElement('afterend', status);
    }
    status.textContent = message || '';
    status.hidden = !message;
    if (message && withFallback) {
      status.appendChild(document.createTextNode(' '));
      var fallback = document.createElement('a');
      fallback.href = canonicalLoginHref();
      fallback.textContent = 'Continue on the sign-in page.';
      status.appendChild(fallback);
    }
    if (message) link.setAttribute('aria-describedby', id);
    else link.removeAttribute('aria-describedby');
  }

  function renderSignedOutLink(link) {
    link.href = canonicalLoginHref();
    link.hidden = false;
    link.classList.remove('omo-nav-auth-pending');
    link.classList.remove('omo-nav-credit');
    link.classList.remove('is-balance-loading');
    link.classList.remove('is-balance-unavailable');
    link.textContent = 'Log in';
    link.setAttribute('data-omo-auth-state', 'signed-out');
    link.setAttribute('aria-haspopup', 'dialog');
    link.removeAttribute('aria-label');
    link.removeAttribute('aria-live');
    link.removeAttribute('aria-busy');
    link.removeAttribute('tabindex');
    link.removeAttribute('title');
    link.removeAttribute('aria-controls');
    renderLoginFeedback(link, '', false);
  }

  function primeAuthLinks() {
    if (authResolved || lastResolvedAuthKey || authLinksPrimed) return;
    var hint = readSignedInHint();
    var cached = hint ? readCachedBalance(hint.userId) : null;
    var links = document.querySelectorAll('[data-omo-login]');
    if (!links.length) return;
    authLinksPrimed = true;
    for (var i = 0; i < links.length; i += 1) {
      if (hint) {
        links[i].href = '/billing.html';
        links[i].hidden = false;
        renderCreditLink(links[i], cached && cached.balanceCents, 'loading');
        links[i].removeAttribute('aria-haspopup');
        links[i].removeAttribute('aria-controls');
      } else {
        renderSignedOutLink(links[i]);
      }
    }
  }

  function loadCreditsClient() {
    if (window.OmoCredits && typeof window.OmoCredits.getBalance === 'function') {
      return Promise.resolve(window.OmoCredits);
    }
    if (balanceClientPromise) return balanceClientPromise;

    balanceClientPromise = new Promise(function (resolve, reject) {
      var script = document.querySelector('script[src="credits.js"],script[src$="/credits.js"]');
      var created = false;
      if (!script) {
        script = document.createElement('script');
        script.src = 'credits.js';
        script.async = true;
        script.setAttribute('data-omo-credits-client', '');
        created = true;
      }

      function loaded() {
        if (window.OmoCredits && typeof window.OmoCredits.getBalance === 'function') resolve(window.OmoCredits);
        else reject(new Error('The balance client did not initialize.'));
      }
      script.addEventListener('load', loaded, { once: true });
      script.addEventListener('error', function () {
        reject(new Error('The balance client could not be loaded.'));
      }, { once: true });
      if (created) document.head.appendChild(script);
      else window.setTimeout(function () {
        if (window.OmoCredits && typeof window.OmoCredits.getBalance === 'function') resolve(window.OmoCredits);
        else if (document.readyState !== 'loading') reject(new Error('The balance client did not initialize.'));
      }, 0);
    });
    return balanceClientPromise;
  }

  function wait(delayMs) {
    return new Promise(function (resolve) { window.setTimeout(resolve, delayMs); });
  }

  function balanceWithSessionRetry(client, deadline, options) {
    return client.getBalance(options).catch(function (error) {
      if (!error || error.code !== 'no_session' || Date.now() + SESSION_RETRY_MS >= deadline) throw error;
      return wait(SESSION_RETRY_MS).then(function () {
        return balanceWithSessionRetry(client, deadline, options);
      });
    });
  }

  function withTimeout(promise, delayMs) {
    return new Promise(function (resolve, reject) {
      var settled = false;
      var timer = window.setTimeout(function () {
        if (settled) return;
        settled = true;
        var error = new Error('The balance request timed out.');
        error.code = 'timeout';
        reject(error);
      }, delayMs);

      Promise.resolve(promise).then(function (value) {
        if (settled) return;
        settled = true;
        window.clearTimeout(timer);
        resolve(value);
      }, function (error) {
        if (settled) return;
        settled = true;
        window.clearTimeout(timer);
        reject(error);
      });
    });
  }

  function requestCreditBalance(userId, options) {
    var force = !!(options && options.force);
    if (!force && balanceInFlight && balanceInFlight.userId === userId) return balanceInFlight.promise;
    var deadline = Date.now() + BALANCE_TIMEOUT_MS;
    var request = loadCreditsClient().then(function (client) {
      return balanceWithSessionRetry(client, deadline, force ? { force: true } : null);
    });
    var promise = withTimeout(request, BALANCE_TIMEOUT_MS);
    if (force) return promise;
    balanceInFlight = { userId: userId, promise: promise };
    promise.then(function () {
      if (balanceInFlight && balanceInFlight.promise === promise) balanceInFlight = null;
    }, function () {
      if (balanceInFlight && balanceInFlight.promise === promise) balanceInFlight = null;
    });
    return promise;
  }

  function accountIsCurrent(requestId, userId) {
    var activeUser = currentUser();
    return requestId === balanceRequestId && activeUser && activeUser.id === userId && isSignedIn();
  }

  function acceptCreditAccount(account, requestId, userId, finalAttempt) {
    if (!accountIsCurrent(requestId, userId)) return false;
    var fresh = activeFreshGrant(userId);
    var cents = Number(account && account.balanceCents);
    if (fresh && !finalAttempt && isFinite(cents) && cents < SIGNUP_GRANT_CENTS) {
      renderAllCreditLinks(SIGNUP_GRANT_CENTS, 'loading');
      return false;
    }
    clearFreshGrant(fresh);
    writeCachedBalance(account);
    renderAllCreditLinks(account.balanceCents, 'ready');
    return true;
  }

  function finishFreshGrantRetry(state, account) {
    if (!accountIsCurrent(state.requestId, state.userId) || freshGrantState !== state) return;
    state.retrySettled = true;
    if (account) {
      acceptCreditAccount(account, state.requestId, state.userId, true);
      return;
    }
    clearFreshGrant(state);
    var cached = readCachedBalance(state.userId);
    renderAllCreditLinks(cached && cached.balanceCents, 'unavailable');
  }

  function retryFreshGrant(state) {
    if (!accountIsCurrent(state.requestId, state.userId) || freshGrantState !== state) return;
    state.timer = null;
    state.retryStarted = true;
    requestCreditBalance(state.userId, { force: true }).then(function (account) {
      finishFreshGrantRetry(state, account);
    }).catch(function () {
      finishFreshGrantRetry(state, null);
    });
  }

  function beginFreshGrant(requestId, userId, cached) {
    clearFreshGrant();
    if (!isFreshClerkAccount(userId, cached)) return null;
    // /api/me guarantees this idempotent grant. Show it as refreshing for a
    // just-created Clerk account, but never persist it before the server agrees.
    var state = {
      requestId: requestId,
      userId: userId,
      retryStarted: false,
      retrySettled: false,
      timer: null
    };
    freshGrantState = state;
    state.timer = window.setTimeout(function () { retryFreshGrant(state); }, FRESH_GRANT_RETRY_MS);
    return state;
  }

  function refreshCreditBalance(requestId, userId) {
    var freshRequest = activeFreshGrant(userId);
    requestCreditBalance(userId).then(function (account) {
      if (freshRequest && freshRequest.retryStarted) return;
      acceptCreditAccount(account, requestId, userId, false);
    }).catch(function () {
      if (freshRequest && freshRequest.retryStarted) return;
      if (!accountIsCurrent(requestId, userId)) return;
      var fresh = activeFreshGrant(userId);
      if (fresh && !fresh.retrySettled) {
        renderAllCreditLinks(SIGNUP_GRANT_CENTS, 'loading');
        return;
      }
      var cached = readCachedBalance(userId);
      renderAllCreditLinks(cached && cached.balanceCents, 'unavailable');
    });
  }

  function handleCreditUpdate(event) {
    var account = event && event.detail;
    var activeUser = currentUser();
    if (!account || !activeUser || account.userId !== activeUser.id || !isSignedIn()) return;
    if (account.mode === 'loading' || account.balanceCents == null || !isFinite(Number(account.balanceCents))) {
      var cached = readCachedBalance(activeUser.id);
      var freshLoading = activeFreshGrant(activeUser.id);
      renderAllCreditLinks(cached ? cached.balanceCents : (freshLoading ? SIGNUP_GRANT_CENTS : null), 'loading');
      return;
    }
    var fresh = activeFreshGrant(activeUser.id);
    if (fresh && !fresh.retrySettled && Number(account.balanceCents) < SIGNUP_GRANT_CENTS) {
      renderAllCreditLinks(SIGNUP_GRANT_CENTS, 'loading');
      return;
    }
    clearFreshGrant(fresh);
    writeCachedBalance(account);
    renderAllCreditLinks(account.balanceCents, 'ready');
  }

  function syncLoginLinks() {
    if (!authResolved) {
      primeAuthLinks();
      return;
    }

    var signedIn = isSignedIn();
    var user = signedIn ? currentUser() : null;
    var userId = user && user.id;
    var authKey = signedIn ? 'signed-in:' + (userId || '') : 'signed-out';
    if (authKey === lastResolvedAuthKey) return;
    lastResolvedAuthKey = authKey;
    var cached = userId ? readCachedBalance(userId) : null;
    var requestId = ++balanceRequestId;
    var fresh = signedIn && userId ? beginFreshGrant(requestId, userId, cached) : null;
    if (!fresh) clearFreshGrant();
    var links = document.querySelectorAll('[data-omo-login]');
    for (var i = 0; i < links.length; i += 1) {
      if (signedIn) {
        links[i].href = '/billing.html';
        links[i].hidden = false;
        renderCreditLink(links[i], cached ? cached.balanceCents : (fresh ? SIGNUP_GRANT_CENTS : null), 'loading');
        links[i].removeAttribute('aria-haspopup');
        links[i].removeAttribute('aria-controls');
      } else {
        renderSignedOutLink(links[i]);
      }
    }

    if (signedIn) {
      writeSignedInHint(userId);
      if (userId) refreshCreditBalance(requestId, userId);
      else renderAllCreditLinks(null, 'unavailable');
    } else {
      clearSignedInHint();
      loadAuthModal();
    }
    var popovers = document.querySelectorAll('.omo-nav-popover');
    for (var j = 0; j < popovers.length; j += 1) syncLogoutItem(popovers[j]);
  }

  function authModalApi() {
    if (window.OmoAuth && typeof window.OmoAuth.open === 'function') return window.OmoAuth;
    if (window.OmoSignupModal && typeof window.OmoSignupModal.openSignIn === 'function') {
      return {
        open: function (mode, options) {
          if (mode === 'login') window.OmoSignupModal.openSignIn(options);
          else window.OmoSignupModal.open(options);
        }
      };
    }
    return null;
  }

  function loadAuthModal() {
    var api = authModalApi();
    if (api) return Promise.resolve(api);
    if (authModalPromise) return authModalPromise;

    authModalPromise = new Promise(function (resolve, reject) {
      var script = document.createElement('script');
      script.src = '/signup-modal.js';
      script.onload = function () {
        var loadedApi = authModalApi();
        if (loadedApi) resolve(loadedApi);
        else reject(new Error('The Omo login popup did not initialize.'));
      };
      script.onerror = function () {
        reject(new Error('The Omo login popup could not be loaded.'));
      };
      document.head.appendChild(script);
    }).catch(function (error) {
      authModalPromise = null;
      throw error;
    });

    return authModalPromise;
  }

  function handleLoginClick(event) {
    var link = event.target.closest && event.target.closest('[data-omo-login]');
    if (!link) return;
    if (link.getAttribute('data-omo-auth-state') === 'pending') {
      event.preventDefault();
      return;
    }
    if (isSignedIn()) return;

    event.preventDefault();
    link.setAttribute('aria-busy', 'true');
    link.textContent = 'Opening sign-in…';
    renderLoginFeedback(link, 'Loading the secure sign-in form…', false);
    loadAuthModal().then(function (api) {
      link.removeAttribute('aria-busy');
      link.textContent = 'Log in';
      renderLoginFeedback(link, '', false);
      api.open('login', authOptions());
    }).catch(function (error) {
      window.console.error(error);
      link.removeAttribute('aria-busy');
      link.textContent = 'Retry login';
      renderLoginFeedback(link, 'Login popup unavailable.', true);
    });
  }

  function syncLogoutItem(popover) {
    var item = popover.querySelector('.omo-nav-logout');
    if (!isSignedIn()) {
      if (item) item.remove();
      return;
    }

    if (!item) {
      item = document.createElement('div');
      item.className = 'omo-nav-logout';

      var link = document.createElement('a');
      link.href = '#';
      link.setAttribute('data-omo-logout', '');
      decorateStaticMenuLink(link, 'Log out', '\u21aa', 'logout');
      item.appendChild(link);
    }

    popover.appendChild(item);
  }

  function handleLogoutClick(event) {
    var link = event.target.closest && event.target.closest('[data-omo-logout]');
    if (!link) return;

    event.preventDefault();
    if (!window.ClerkAuth || typeof window.ClerkAuth.signOut !== 'function') return;

    link.setAttribute('aria-busy', 'true');
    link.setAttribute('aria-disabled', 'true');
    setStaticMenuLabel(link, 'Signing out…');
    var result;
    try { result = window.ClerkAuth.signOut(); }
    catch (error) {
      link.removeAttribute('aria-busy');
      link.removeAttribute('aria-disabled');
      setStaticMenuLabel(link, 'Log out failed — try again');
      return;
    }

    Promise.resolve(result).then(function () {
      syncLoginLinks();
    }).catch(function () {
      link.removeAttribute('aria-busy');
      link.removeAttribute('aria-disabled');
      setStaticMenuLabel(link, 'Log out failed — try again');
    });
  }

  function subscribeToAuthChanges() {
    if (!window.ClerkAuth || typeof window.ClerkAuth.onAuthChange !== 'function') return false;
    if (authSubscribed) return true;
    authSubscribed = true;
    window.ClerkAuth.onAuthChange(function () {
      if (authResolved) syncLoginLinks();
    });
    return true;
  }

  function beginAuthResolution() {
    if (!window.ClerkAuth) return false;
    subscribeToAuthChanges();
    if (authResolutionStarted) return true;
    authResolutionStarted = true;

    var ready;
    try {
      ready = typeof window.ClerkAuth.ensureLoaded === 'function'
        ? window.ClerkAuth.ensureLoaded()
        : null;
    } catch (error) {
      authResolutionStarted = false;
      return true;
    }

    Promise.resolve(ready).then(function () {
      authResolved = true;
      syncLoginLinks();
    }).catch(function () {
      // A Clerk load failure is not evidence that the user is signed out.
      // Keep the hinted pill, or the no-hint signed-out default, unchanged.
      authResolutionStarted = false;
    });
    return true;
  }

  function loadAuthAdapter() {
    function loadScript(src, onLoad) {
      var script = document.createElement('script');
      script.src = src;
      script.onload = onLoad;
      document.head.appendChild(script);
    }

    function loadClerk() {
      loadScript('/clerk.js', function () {
        beginAuthResolution();
      });
    }

    if (typeof window.CLERK_PUBLISHABLE_KEY === 'string') loadClerk();
    else loadScript('/key-config.js', loadClerk);
  }

  function setStaticMenuLabel(link, label) {
    var text = link.querySelector('.omo-nav-static-label');
    if (text) text.textContent = label;
    else link.textContent = label;
  }

  function decorateStaticMenuLink(link, label, icon, kind) {
    if (link.querySelector('.omo-nav-static-icon')) {
      setStaticMenuLabel(link, label);
      return;
    }

    link.textContent = '';
    link.classList.add('omo-nav-menu-row');
    if (kind) link.classList.add('omo-nav-' + kind);

    var tile = document.createElement('span');
    tile.className = 'omo-nav-static-icon';
    tile.setAttribute('aria-hidden', 'true');
    tile.textContent = icon;
    link.appendChild(tile);

    var text = document.createElement('span');
    text.className = 'omo-nav-static-label';
    text.textContent = label;
    link.appendChild(text);
  }

  function prepareMenuLinks(popover) {
    if (popover.querySelector('.omo-nav-primary-links')) return;

    var links = [];
    for (var i = 0; i < popover.children.length; i += 1) {
      if (popover.children[i].tagName === 'A') links.push(popover.children[i]);
    }
    if (!links.length) return;

    var group = document.createElement('div');
    group.className = 'omo-nav-primary-links';
    popover.insertBefore(group, links[0]);
    for (var j = 0; j < links.length; j += 1) {
      var href = links[j].getAttribute('href') || '';
      if (/sell\.html(?:[?#]|$)/.test(href)) decorateStaticMenuLink(links[j], 'Sell Workflow', '+', 'sell');
      else decorateStaticMenuLink(links[j], 'Discover', '\u2316', 'discover');
      group.appendChild(links[j]);
    }
  }

  function workflowContext() {
    var page = (window.location.pathname.split('/').pop() || '').toLowerCase();
    if (page !== 'workflow.html' && page !== 'run.html') return null;

    var slug = '';
    try { slug = (new URLSearchParams(window.location.search || '').get('slug') || '').trim(); }
    catch (error) { return null; }
    return slug ? { slug: slug, page: page } : null;
  }

  function catalogWorkflow(slug) {
    var catalog = window.OMO_VISIBLE_CATALOG || [];
    for (var itemIndex = 0; itemIndex < catalog.length; itemIndex += 1) {
      if (catalog[itemIndex] && catalog[itemIndex].slug === slug) {
        return catalog[itemIndex];
      }
    }
    return null;
  }

  function loadContextualCatalog() {
    if (contextualCatalogPromise) return contextualCatalogPromise;

    function load(source, globalName) {
      if (window[globalName]) return Promise.resolve();
      return new Promise(function (resolve) {
        var script = document.createElement('script');
        script.src = source;
        script.onload = resolve;
        script.onerror = resolve;
        document.head.appendChild(script);
      });
    }

    contextualCatalogPromise = load('catalog.js', 'OMO_CATALOG');
    return contextualCatalogPromise;
  }

  function appendIdentityIcon(container, product) {
    var icon = typeof product.icon === 'string' ? product.icon : '';
    var source = product.cover || (/[/\.]|^https?:/.test(icon) ? icon : '');
    var emoji = product.emoji || (!source && icon) || '\u2726';

    function showEmoji() {
      container.textContent = emoji;
    }

    if (!source) {
      showEmoji();
      return;
    }

    var image = document.createElement('img');
    image.src = source;
    image.alt = '';
    image.addEventListener('error', showEmoji, { once: true });
    container.appendChild(image);
  }

  function renderContextualWorkflowIdentity(context, product) {
    var wordmark = document.querySelector('.omo-nav-brand .wordmark');
    var name = product && (product.name || product.title);
    if (!wordmark || !name) return;

    var identity = document.createElement('a');
    identity.className = 'omo-nav-workflow-identity';
    identity.href = '/workflow.html?slug=' + encodeURIComponent(context.slug);
    identity.setAttribute('aria-label', name + ' workflow listing');
    identity.title = name;

    var icon = document.createElement('span');
    icon.className = 'omo-nav-context-thumb';
    icon.setAttribute('aria-hidden', 'true');
    appendIdentityIcon(icon, product);
    identity.appendChild(icon);

    var title = document.createElement('span');
    title.className = 'omo-nav-context-name';
    title.textContent = name;
    identity.appendChild(title);
    wordmark.replaceWith(identity);
  }

  function installContextualWorkflowIdentity() {
    var context = workflowContext();
    if (!context) return;

    var product = catalogWorkflow(context.slug);
    if (product) {
      renderContextualWorkflowIdentity(context, product);
      return;
    }

    if (window.OMO_CATALOG) return;
    loadContextualCatalog().then(function () {
      var loadedProduct = catalogWorkflow(context.slug);
      if (loadedProduct) renderContextualWorkflowIdentity(context, loadedProduct);
    });
  }

  function initMenu(menu) {
    var toggle = menu.querySelector('.omo-nav-menu-toggle');
    var popover = menu.querySelector('.omo-nav-popover');
    if (!toggle || !popover) return;
    if (!toggle.title) toggle.title = 'Menu';
    prepareMenuLinks(popover);

    function closeMenu(returnFocus) {
      if (toggle.getAttribute('aria-expanded') !== 'true') return;
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Menu');
      toggle.title = 'Menu';
      popover.hidden = true;
      if (returnFocus) toggle.focus();
    }

    toggle.addEventListener('click', function () {
      var shouldOpen = toggle.getAttribute('aria-expanded') !== 'true';
      toggle.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
      toggle.setAttribute('aria-label', shouldOpen ? 'Close menu' : 'Menu');
      toggle.title = shouldOpen ? 'Close menu' : 'Menu';
      popover.hidden = !shouldOpen;
      if (shouldOpen) window.setTimeout(function () { syncLogoutItem(popover); }, 0);
    });

    popover.addEventListener('click', function (event) {
      if (event.target.closest('a')) closeMenu(false);
    });

    document.addEventListener('click', function (event) {
      if (!menu.contains(event.target)) closeMenu(false);
    });

    document.addEventListener('focusin', function (event) {
      if (!menu.contains(event.target)) closeMenu(false);
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') closeMenu(true);
    });

    window.addEventListener('resize', function () { closeMenu(false); });
    window.addEventListener('pagehide', function () { closeMenu(false); });
  }

  function skipAutomaticAuthForInvalidSubmission() {
    var page = (window.location.pathname.split('/').pop() || '').toLowerCase();
    if (page !== 'submission' && page !== 'submission.html') return false;
    var id = '';
    try { id = new URLSearchParams(window.location.search || '').get('id') || ''; }
    catch (error) { return true; }
    return !/^sub_[A-Za-z0-9_-]{8,100}$/.test(id);
  }

  function init() {
    installCreditStyles();
    primeAuthLinks();
    window.addEventListener('omo:credits', handleCreditUpdate);
    installContextualWorkflowIdentity();
    var menus = document.querySelectorAll('.omo-nav-menu');
    for (var i = 0; i < menus.length; i += 1) initMenu(menus[i]);

    if (!skipAutomaticAuthForInvalidSubmission() && !beginAuthResolution()) loadAuthAdapter();
    document.addEventListener('click', handleLoginClick);
    document.addEventListener('click', handleLogoutClick);

    window.addEventListener('storage', function (event) {
      if (event.key === 'cognition_user') syncLoginLinks();
    });
  }

  // nav.js is deferred in the page head, so apply the persisted sign-in hint
  // before DOMContentLoaded/first paint. Clerk chooses the real state later.
  installCreditStyles();
  primeAuthLinks();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

/* Keep personalized menu content isolated from the shared nav/auth behavior. */
(function (doc) {
  var style = doc.createElement('link');
  style.rel = 'stylesheet';
  style.href = '/menu-workflows.css?v=5';
  doc.head.appendChild(style);

  var script = doc.createElement('script');
  script.src = '/menu-workflows.js?v=4';
  doc.head.appendChild(script);
})(document);
