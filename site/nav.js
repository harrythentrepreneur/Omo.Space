(function () {
  'use strict';

  var authModalPromise = null;
  var contextualCatalogPromise = null;
  var balanceRequestId = 0;
  var DEMO_BALANCE_KEY = 'omo_balance_v1';

  function installCreditStyles() {
    if (document.getElementById('omo-nav-credit-styles')) return;

    var style = document.createElement('style');
    style.id = 'omo-nav-credit-styles';
    style.textContent =
      '.omo-nav-row>.omo-nav-brand{flex:1 1 auto}' +
      '.omo-nav-brand{gap:7px}' +
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
      '.omo-nav-login.omo-nav-credit{min-width:40px;gap:6px;padding-inline:11px;border-radius:999px;font-variant-numeric:tabular-nums}' +
      '.omo-nav-credit-icon{font-size:16px;line-height:1}' +
      '.omo-nav-workflow-identity{min-width:0;max-width:min(310px,calc(100vw - 190px));min-height:40px;display:inline-flex;align-items:center;gap:8px;flex:0 1 auto;color:var(--pine,#17352C);text-decoration:none}' +
      '.omo-nav-workflow-identity:hover,.omo-nav-workflow-identity:focus-visible{color:var(--pine,#17352C);text-decoration:none}' +
      '.omo-nav-workflow-identity:focus-visible{outline:3px solid rgba(255,107,61,.34);outline-offset:2px}' +
      '.omo-nav-context-thumb{width:30px;height:30px;display:grid;place-items:center;flex:0 0 30px;overflow:hidden;border-radius:8px;background:var(--cream,#F4F1E8);font-size:17px}' +
      '.omo-nav-context-thumb img{width:100%;height:100%;display:block;object-fit:cover}' +
      '.omo-nav-context-name{min-width:0;overflow:hidden;color:var(--pine,#17352C);font:700 15px/1.12 var(--display,"Fraunces",Georgia,serif);letter-spacing:-.015em;text-overflow:ellipsis;white-space:nowrap}' +
      '@media(max-width:480px){.omo-nav-popover{left:0;width:min(292px,calc(100vw - 24px));max-width:calc(100vw - 24px)}.omo-nav-login.omo-nav-credit{padding-inline:9px}.omo-nav-workflow-identity{max-width:calc(100vw - 180px);gap:6px}.omo-nav-context-thumb{width:28px;height:28px;flex-basis:28px}.omo-nav-context-name{font-size:13px}}';
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

  function renderCreditLink(link, balanceCents) {
    var hasBalance = balanceCents != null && isFinite(Number(balanceCents));
    var formatted = hasBalance ? formatBalance(balanceCents) : '';
    var icon = document.createElement('span');
    icon.className = 'omo-nav-credit-icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = '\u25d2';

    link.textContent = '';
    link.appendChild(icon);
    if (hasBalance) {
      var amount = document.createElement('span');
      amount.textContent = '$' + formatted;
      link.appendChild(amount);
    }
    link.classList.add('omo-nav-credit');
    link.setAttribute('aria-label', hasBalance ? '$' + formatted + ' in credits \u2014 view billing' : 'Credits \u2014 view billing');
    link.title = hasBalance ? '$' + formatted + ' in credits' : 'Credits';
  }

  function demoBalanceCents() {
    var user = currentUser();
    if (!user || !user.demo) return null;

    try {
      var raw = window.localStorage.getItem(DEMO_BALANCE_KEY);
      var saved = Number(raw);
      return raw != null && isFinite(saved) ? Math.round(saved * 100) : 500;
    } catch (error) {
      return 500;
    }
  }

  function getClerkSessionToken() {
    if (window.Clerk && window.Clerk.session && typeof window.Clerk.session.getToken === 'function') {
      return window.Clerk.session.getToken().then(function (token) {
        if (!token) throw new Error('No auth token.');
        return token;
      });
    }
    return Promise.reject(new Error('No verified session.'));
  }

  function balanceCentsFromResponse(data) {
    if (data && data.balance_cents != null && isFinite(Number(data.balance_cents))) {
      return Math.round(Number(data.balance_cents));
    }

    var dollars = data && (data.balance_usd != null ? data.balance_usd : data.balance);
    return dollars != null && isFinite(Number(dollars)) ? Math.round(Number(dollars) * 100) : null;
  }

  function refreshCreditBalance(requestId) {
    var fallback = demoBalanceCents();
    if (fallback != null) {
      var demoLinks = document.querySelectorAll('[data-omo-login]');
      for (var i = 0; i < demoLinks.length; i += 1) renderCreditLink(demoLinks[i], fallback);
    }

    getClerkSessionToken().then(function (token) {
      return fetch('/api/me', {
        headers: { Authorization: 'Bearer ' + token, Accept: 'application/json' }
      });
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        return { ok: response.ok, data: data };
      });
    }).then(function (result) {
      if (requestId !== balanceRequestId || !isSignedIn() || !result.ok || !result.data.ok) return;
      var balanceCents = balanceCentsFromResponse(result.data);
      if (balanceCents == null) return;

      var links = document.querySelectorAll('[data-omo-login]');
      for (var i = 0; i < links.length; i += 1) renderCreditLink(links[i], balanceCents);
    }).catch(function () {});
  }

  function syncLoginLinks() {
    var signedIn = isSignedIn();
    var href = signedIn ? 'billing.html' : 'signup.html';
    var requestId = ++balanceRequestId;
    var links = document.querySelectorAll('[data-omo-login]');
    for (var i = 0; i < links.length; i += 1) {
      links[i].href = href;
      links[i].hidden = false;
      if (signedIn) {
        renderCreditLink(links[i], null);
        links[i].removeAttribute('aria-haspopup');
        links[i].removeAttribute('aria-controls');
      } else {
        links[i].classList.remove('omo-nav-credit');
        links[i].textContent = 'Log in';
        links[i].removeAttribute('aria-label');
        links[i].removeAttribute('title');
        links[i].removeAttribute('aria-controls');
        links[i].setAttribute('aria-haspopup', 'dialog');
      }
    }

    if (signedIn) {
      refreshCreditBalance(requestId);
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
      popover.hidden = true;
      if (returnFocus) toggle.focus();
    }

    toggle.addEventListener('click', function () {
      var shouldOpen = toggle.getAttribute('aria-expanded') !== 'true';
      toggle.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
      popover.hidden = !shouldOpen;
      if (shouldOpen) window.setTimeout(function () { syncLogoutItem(popover); }, 0);
    });

    popover.addEventListener('click', function (event) {
      if (event.target.closest('a')) closeMenu(false);
    });

    document.addEventListener('click', function (event) {
      if (!menu.contains(event.target)) closeMenu(false);
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') closeMenu(true);
    });
  }

  function init() {
    installCreditStyles();
    installContextualWorkflowIdentity();
    var menus = document.querySelectorAll('.omo-nav-menu');
    for (var i = 0; i < menus.length; i += 1) initMenu(menus[i]);

    syncLoginLinks();
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
  style.href = 'menu-workflows.css?v=4';
  doc.head.appendChild(style);

  var script = doc.createElement('script');
  script.src = 'menu-workflows.js?v=4';
  doc.head.appendChild(script);
})(document);
