(function () {
  'use strict';

  var authModalPromise = null;

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

  function syncLoginLinks() {
    var signedIn = isSignedIn();
    var href = signedIn ? 'dashboard.html' : 'signup.html';
    var label = signedIn ? 'Dashboard' : 'Log in';
    var links = document.querySelectorAll('[data-omo-login]');
    for (var i = 0; i < links.length; i += 1) {
      links[i].href = href;
      links[i].textContent = label;
      links[i].hidden = false;
      if (signedIn) links[i].removeAttribute('aria-haspopup');
      else links[i].setAttribute('aria-haspopup', 'dialog');
    }

    if (!signedIn) loadAuthModal();
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
    var menus = document.querySelectorAll('.omo-nav-menu');
    for (var i = 0; i < menus.length; i += 1) initMenu(menus[i]);

    syncLoginLinks();
    if (!subscribeToAuthChanges()) loadAuthAdapter();
    document.addEventListener('click', handleLoginClick);

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
