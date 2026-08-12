(function () {
  'use strict';

  var authModalPromise = null;
  var contextualCatalogPromise = null;
  var balanceClientPromise = null;
  var balanceInFlight = null;
  var balanceRequestId = 0;
  var BALANCE_CACHE_PREFIX = 'omo_nav_balance_v1:';

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
      '.omo-nav-menu-toggle{width:44px;height:44px;min-height:44px;padding:0;border:0;border-radius:999px;background:#E8E8E6;color:var(--pine,#17352C);box-shadow:none;transition:background-color .15s ease}' +
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
      '.omo-nav-login{min-height:44px}.omo-nav-login.omo-nav-credit{width:96px;min-width:96px;max-width:96px;gap:6px;padding-inline:9px;border-radius:999px;font-variant-numeric:tabular-nums}' +
      '.omo-nav-credit-icon{font-size:16px;line-height:1}' +
      '.omo-nav-credit-amount{min-width:0;overflow:hidden;text-overflow:ellipsis}' +
      '.omo-nav-credit-spinner{width:13px;height:13px;flex:0 0 13px;border:2px solid var(--mint,#BDEFD4);border-top-color:var(--pine,#17352C);border-radius:50%;animation:omo-nav-credit-spin .7s linear infinite}' +
      '.omo-nav-credit.is-balance-unavailable .omo-nav-credit-icon{opacity:.52}' +
      '@keyframes omo-nav-credit-spin{to{transform:rotate(360deg)}}' +
      '.omo-nav-workflow-identity{min-width:0;max-width:min(310px,calc(100vw - 214px));min-height:44px;display:inline-flex;align-items:center;gap:8px;flex:0 1 auto;color:var(--pine,#17352C);text-decoration:none}' +
      '.omo-nav-workflow-identity:hover,.omo-nav-workflow-identity:focus-visible{color:var(--pine,#17352C);text-decoration:none}' +
      '.omo-nav-workflow-identity:focus-visible{outline:3px solid rgba(255,107,61,.34);outline-offset:2px}' +
      '.omo-nav-context-thumb{width:30px;height:30px;display:grid;place-items:center;flex:0 0 30px;overflow:hidden;border-radius:8px;background:var(--cream,#F4F1E8);font-size:17px}' +
      '.omo-nav-context-thumb img{width:100%;height:100%;display:block;object-fit:cover}' +
      '.omo-nav-context-name{min-width:0;overflow:hidden;color:var(--pine,#17352C);font:600 15px/1.12 "Fraunces",Georgia,serif;letter-spacing:-.015em;text-overflow:ellipsis;white-space:nowrap}' +
      '@media(max-width:760px){.omo-site-header>.omo-nav-row{width:100%;padding-inline:max(16px,env(safe-area-inset-left));padding-right:max(16px,env(safe-area-inset-right))}.omo-nav-row>.omo-nav-brand{min-width:0}.omo-nav-menu{position:static}.omo-nav-popover{max-height:calc(100dvh - 84px);overscroll-behavior:contain;-webkit-overflow-scrolling:touch;scrollbar-gutter:stable}.omo-nav-login{max-width:42vw;overflow:hidden;text-overflow:ellipsis}}' +
      '@media(max-width:480px){.omo-nav-popover{left:max(12px,env(safe-area-inset-left));right:max(12px,env(safe-area-inset-right));width:auto;max-width:none}.omo-nav-workflow-identity{max-width:calc(100vw - 214px);gap:6px}.omo-nav-context-thumb{width:28px;height:28px;flex-basis:28px}.omo-nav-context-name{font-size:13px}}' +
      '@media(prefers-reduced-motion:reduce){.omo-nav-credit-spinner{animation:omo-nav-credit-pulse 1s ease-in-out infinite alternate}@keyframes omo-nav-credit-pulse{to{opacity:.45}}}';
    document.head.appendChild(style);
  }

  function isSignedIn() {
    if (window.ClerkAuth && typeof window.ClerkAuth.isSignedIn === 'function') {
      return window.ClerkAuth.isSignedIn();
    }

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

    try {
      return JSON.parse(window.localStorage.getItem('cognition_user') || 'null');
    } catch (error) {
      return null;
    }
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

  function renderCreditLink(link, balanceCents, state) {
    var hasBalance = balanceCents != null && isFinite(Number(balanceCents));
    var formatted = hasBalance ? formatBalance(balanceCents) : '';
    var icon = document.createElement('span');
    icon.className = state === 'loading' ? 'omo-nav-credit-spinner' : 'omo-nav-credit-icon';
    icon.setAttribute('aria-hidden', 'true');
    if (state !== 'loading') icon.textContent = '\u25d2';

    link.textContent = '';
    link.appendChild(icon);
    if (state !== 'unavailable') {
      var amount = document.createElement('span');
      amount.className = 'omo-nav-credit-amount';
      amount.textContent = hasBalance ? '$' + formatted : '$\u2026';
      link.appendChild(amount);
    }
    link.classList.add('omo-nav-credit');
    link.classList.remove('is-balance-loading');
    link.classList.remove('is-balance-unavailable');
    link.removeAttribute('aria-busy');
    link.setAttribute('aria-live', 'polite');

    if (state === 'loading') {
      link.classList.add('is-balance-loading');
      link.setAttribute('aria-busy', 'true');
      link.setAttribute('aria-label', hasBalance ? '$' + formatted + ' in credits, refreshing' : 'Loading credit balance');
      link.title = hasBalance ? 'Refreshing $' + formatted + ' balance' : 'Loading balance';
    } else if (state === 'unavailable') {
      link.classList.add('is-balance-unavailable');
      link.setAttribute('aria-label', 'Balance unavailable \u2014 view billing');
      link.title = 'Balance unavailable';
    } else {
      link.setAttribute('aria-label', '$' + formatted + ' in credits \u2014 view billing');
      link.title = '$' + formatted + ' in credits';
    }
  }

  function renderAllCreditLinks(balanceCents, state) {
    var links = document.querySelectorAll('[data-omo-login]');
    for (var i = 0; i < links.length; i += 1) renderCreditLink(links[i], balanceCents, state);
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

  function requestCreditBalance(userId) {
    if (balanceInFlight && balanceInFlight.userId === userId) return balanceInFlight.promise;
    var promise = loadCreditsClient().then(function (client) {
      return client.getBalance();
    });
    balanceInFlight = { userId: userId, promise: promise };
    promise.then(function () {
      if (balanceInFlight && balanceInFlight.promise === promise) balanceInFlight = null;
    }, function () {
      if (balanceInFlight && balanceInFlight.promise === promise) balanceInFlight = null;
    });
    return promise;
  }

  function refreshCreditBalance(requestId, userId) {
    requestCreditBalance(userId).then(function (account) {
      var activeUser = currentUser();
      if (requestId !== balanceRequestId || !activeUser || activeUser.id !== userId) return;
      writeCachedBalance(account);
      renderAllCreditLinks(account.balanceCents, 'ready');
    }).catch(function () {
      var activeUser = currentUser();
      if (requestId !== balanceRequestId || !activeUser || activeUser.id !== userId) return;
      renderAllCreditLinks(null, 'unavailable');
    });
  }

  function handleCreditUpdate(event) {
    var account = event && event.detail;
    var activeUser = currentUser();
    if (!account || !activeUser || account.userId !== activeUser.id || !isSignedIn()) return;
    if (account.mode === 'loading' || account.balanceCents == null || !isFinite(Number(account.balanceCents))) {
      var cached = readCachedBalance(activeUser.id);
      renderAllCreditLinks(cached && cached.balanceCents, 'loading');
      return;
    }
    writeCachedBalance(account);
    renderAllCreditLinks(account.balanceCents, 'ready');
  }

  function syncLoginLinks() {
    var signedIn = isSignedIn();
    var user = signedIn ? currentUser() : null;
    var userId = user && user.id;
    var cached = userId ? readCachedBalance(userId) : null;
    var href = signedIn ? 'billing.html' : 'signup.html';
    var requestId = ++balanceRequestId;
    var links = document.querySelectorAll('[data-omo-login]');
    for (var i = 0; i < links.length; i += 1) {
      links[i].href = href;
      links[i].hidden = false;
      if (signedIn) {
        renderCreditLink(links[i], cached && cached.balanceCents, 'loading');
        links[i].removeAttribute('aria-haspopup');
        links[i].removeAttribute('aria-controls');
      } else {
        links[i].classList.remove('omo-nav-credit');
        links[i].classList.remove('is-balance-loading');
        links[i].classList.remove('is-balance-unavailable');
        links[i].textContent = 'Log in';
        links[i].removeAttribute('aria-label');
        links[i].removeAttribute('aria-live');
        links[i].removeAttribute('aria-busy');
        links[i].removeAttribute('title');
        links[i].removeAttribute('aria-controls');
        links[i].setAttribute('aria-haspopup', 'dialog');
      }
    }

    if (signedIn) {
      if (userId) refreshCreditBalance(requestId, userId);
      else renderAllCreditLinks(null, 'unavailable');
    } else {
      loadAuthModal();
      var popovers = document.querySelectorAll('.omo-nav-popover');
      for (var j = 0; j < popovers.length; j += 1) syncLogoutItem(popovers[j]);
    }
  }

  function authModalApi() {
    if (window.OmoAuth && typeof window.OmoAuth.open === 'function') return window.OmoAuth;
    if (window.OmoSignupModal && typeof window.OmoSignupModal.openSignIn === 'function') {
      return {
        open: function (mode) {
          if (mode === 'login') window.OmoSignupModal.openSignIn();
          else window.OmoSignupModal.open();
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
      script.src = 'signup-modal.js';
      script.onload = function () {
        var loadedApi = authModalApi();
        if (loadedApi) resolve(loadedApi);
        else reject(new Error('The Omo login popup did not initialize.'));
      };
      script.onerror = function () {
        reject(new Error('The Omo login popup could not be loaded.'));
      };
      document.head.appendChild(script);
    });

    return authModalPromise;
  }

  function handleLoginClick(event) {
    var link = event.target.closest && event.target.closest('[data-omo-login]');
    if (!link || isSignedIn()) return;

    event.preventDefault();
    loadAuthModal().then(function (api) {
      api.open('login');
    }).catch(function (error) {
      window.console.error(error);
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
    window.ClerkAuth.onAuthChange(syncLoginLinks);
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
      loadScript('clerk.js', function () {
        syncLoginLinks();
        subscribeToAuthChanges();
      });
    }

    if (typeof window.CLERK_PUBLISHABLE_KEY === 'string') loadClerk();
    else loadScript('key-config.js', loadClerk);
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
    var sources = [window.COGNITION_IG_WORKFLOWS || [], window.COGNITION_IG_MORE || []];
    for (var sourceIndex = 0; sourceIndex < sources.length; sourceIndex += 1) {
      for (var itemIndex = 0; itemIndex < sources[sourceIndex].length; itemIndex += 1) {
        if (sources[sourceIndex][itemIndex] && sources[sourceIndex][itemIndex].slug === slug) {
          return sources[sourceIndex][itemIndex];
        }
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

    contextualCatalogPromise = Promise.all([
      load('ig-workflows.js', 'COGNITION_IG_WORKFLOWS'),
      load('ig-more.js', 'COGNITION_IG_MORE')
    ]);
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
    identity.href = 'workflow.html?slug=' + encodeURIComponent(context.slug);
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

    if (window.COGNITION_IG_WORKFLOWS && window.COGNITION_IG_MORE) return;
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

  function init() {
    installCreditStyles();
    window.addEventListener('omo:credits', handleCreditUpdate);
    // Start account I/O before catalog/menu decoration. Billing's shared
    // request is reused when it is already in flight.
    syncLoginLinks();
    installContextualWorkflowIdentity();
    var menus = document.querySelectorAll('.omo-nav-menu');
    for (var i = 0; i < menus.length; i += 1) initMenu(menus[i]);

    if (!subscribeToAuthChanges()) loadAuthAdapter();
    document.addEventListener('click', handleLoginClick);
    document.addEventListener('click', handleLogoutClick);

    window.addEventListener('storage', function (event) {
      if (event.key === 'cognition_user') syncLoginLinks();
    });
  }

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
  style.href = 'menu-workflows.css?v=5';
  doc.head.appendChild(style);

  var script = doc.createElement('script');
  script.src = 'menu-workflows.js?v=4';
  doc.head.appendChild(script);
})(document);
