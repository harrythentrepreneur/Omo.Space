(function () {
  'use strict';

  var authModalPromise = null;
  var balanceRequestId = 0;
  var DEMO_BALANCE_KEY = 'omo_balance_v1';

  function installCreditStyles() {
    if (document.getElementById('omo-nav-credit-styles')) return;

    var style = document.createElement('style');
    style.id = 'omo-nav-credit-styles';
    style.textContent =
      '.omo-nav-menu-toggle{width:38px;min-height:38px;padding:0;border:1px solid #6F7E77;border-radius:999px;background:#E5F1EA;box-shadow:inset 0 1px 0 rgba(255,255,255,.72);transition:background-color .15s ease,border-color .15s ease,box-shadow .15s ease}' +
      '.omo-nav-menu-toggle:hover,.omo-nav-menu-toggle[aria-expanded="true"]{border-color:#2F6A55;background:var(--mint,#BDEFD4);box-shadow:inset 0 1px 0 rgba(255,255,255,.62),0 2px 8px rgba(23,53,44,.12)}' +
      '.omo-nav-menu-toggle:focus-visible{border-color:#2F6A55;background:var(--mint,#BDEFD4);outline:3px solid rgba(255,107,61,.34);outline-offset:2px}' +
      '.omo-nav-chevron{position:relative;display:block;width:14px;height:14px;font-size:0;line-height:1;transition:transform .15s ease}' +
      '.omo-nav-chevron::before{content:"";position:absolute;top:2px;left:2px;width:8px;height:8px;border-right:2px solid currentColor;border-bottom:2px solid currentColor;transform:rotate(45deg)}' +
      '.omo-nav-popover{top:calc(100% + 7px);width:max-content;min-width:216px;max-width:min(252px,calc(100vw - 24px));padding:5px;border:1px solid #81948B;border-radius:10px;background:var(--surface,#FFFFFF);box-shadow:0 16px 34px rgba(23,53,44,.2),0 3px 9px rgba(23,53,44,.13)}' +
      '.omo-nav-popover>a,.omo-nav-popover .omo-nav-logout>a{min-height:32px;padding:0 8px;border-radius:6px;font-size:12.5px}' +
      '.omo-nav-popover a:hover,.omo-nav-popover a:focus-visible{background:#D8EADF;color:var(--pine,#17352C);box-shadow:inset 3px 0 0 #6F7E77;text-decoration:none}' +
      '.omo-nav-popover a[aria-current="page"],.omo-nav-popover a[aria-selected="true"],.omo-nav-popover a.is-active{background:var(--mint,#BDEFD4);color:var(--pine,#17352C);box-shadow:inset 3px 0 0 var(--pine,#17352C);text-decoration:none}' +
      '.omo-nav-login.omo-nav-credit{min-width:40px;gap:6px;padding-inline:11px;border-radius:999px;font-variant-numeric:tabular-nums}' +
      '.omo-nav-credit-icon{font-size:16px;line-height:1}' +
      '.omo-nav-logout{margin-top:6px;padding-top:7px;border-top:1px solid var(--rule,#D9E2DC)}' +
      '@media(max-width:480px){.omo-nav-login.omo-nav-credit{padding-inline:9px}}';
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
    link.setAttribute('aria-label', hasBalance ? '$' + formatted + ' in credits \u2014 open dashboard' : 'Credits \u2014 open dashboard');
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
    var href = signedIn ? 'dashboard.html' : 'signup.html';
    var requestId = ++balanceRequestId;
    var links = document.querySelectorAll('[data-omo-login]');
    for (var i = 0; i < links.length; i += 1) {
      links[i].href = href;
      links[i].hidden = false;
      if (signedIn) {
        renderCreditLink(links[i], null);
        links[i].removeAttribute('aria-haspopup');
      } else {
        links[i].classList.remove('omo-nav-credit');
        links[i].textContent = 'Log in';
        links[i].removeAttribute('aria-label');
        links[i].removeAttribute('title');
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
      link.textContent = 'Log out';
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
    link.textContent = 'Signing out…';
    var result;
    try { result = window.ClerkAuth.signOut(); }
    catch (error) {
      link.removeAttribute('aria-busy');
      link.removeAttribute('aria-disabled');
      link.textContent = 'Log out failed — try again';
      return;
    }

    Promise.resolve(result).then(function () {
      syncLoginLinks();
    }).catch(function () {
      link.removeAttribute('aria-busy');
      link.removeAttribute('aria-disabled');
      link.textContent = 'Log out failed — try again';
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

  function initMenu(menu) {
    var toggle = menu.querySelector('.omo-nav-menu-toggle');
    var popover = menu.querySelector('.omo-nav-popover');
    if (!toggle || !popover) return;
    if (!toggle.title) toggle.title = 'Menu';

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
  style.href = 'menu-workflows.css';
  doc.head.appendChild(style);

  var script = doc.createElement('script');
  script.src = 'menu-workflows.js';
  doc.head.appendChild(script);
})(document);
