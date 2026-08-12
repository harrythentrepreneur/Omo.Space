/* clerk.js — Clerk auth for the Omo storefront, with a local demo fallback.
 *
 * Exposes window.ClerkAuth =
 *   { isSignedIn, signIn, signOut, signUp, signUpAndRedirect,
 *     getUser, currentUser, onAuthChange }.
 */
(function () {
  'use strict';

  var PLACEHOLDER = 'pk_test_placeholder';
  var CLERK_JS_MAJOR = '6';
  var CLERK_UI_MAJOR = '1';
  var LOAD_TIMEOUT_MS = 15000;
  var USER_KEY = 'cognition_user';
  var realClerk = null;
  var realClerkUser = null;
  var loadPromise = null;
  var loadError = null;
  var pendingModal = '';
  var signUpRedirect = '';
  var listeners = [];

  function getKey() {
    return (window.CLERK_PUBLISHABLE_KEY || '').trim() || PLACEHOLDER;
  }

  function isRealKey() {
    var key = getKey();
    return key !== PLACEHOLDER && /^pk_(test|live)_/.test(key);
  }

  function demoMode() {
    return (window.location && window.location.protocol === 'file:') || !isRealKey();
  }

  // Clerk publishable keys encode the instance's Frontend API hostname and a
  // trailing "$". Clerk serves its browser bundle from that same hostname:
  // https://<frontend-api>/npm/@clerk/clerk-js@6/dist/clerk.browser.js
  function clerkFrontendApi() {
    var match = getKey().match(/^pk_(?:test|live)_(.+)$/);
    if (!match) throw new Error('The Clerk publishable key is invalid.');

    var encoded = match[1].replace(/-/g, '+').replace(/_/g, '/');
    while (encoded.length % 4) encoded += '=';

    var decoded = '';
    try { decoded = window.atob(encoded); }
    catch (e) { throw new Error('The Clerk publishable key could not be decoded.'); }

    if (decoded.slice(-1) !== '$' || decoded.slice(0, -1).indexOf('$') !== -1) {
      throw new Error('The Clerk publishable key has an invalid Frontend API value.');
    }
    var frontendApi = decoded.slice(0, -1);
    if (!/^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$/i.test(frontendApi) ||
        frontendApi.indexOf('.') === -1 || frontendApi.indexOf('..') !== -1) {
      throw new Error('The Clerk publishable key has an invalid Frontend API hostname.');
    }
    return frontendApi;
  }

  function clerkSdkUrl() {
    return 'https://' + clerkFrontendApi() +
      '/npm/@clerk/clerk-js@' + CLERK_JS_MAJOR + '/dist/clerk.browser.js';
  }

  function clerkUiUrl() {
    return 'https://' + clerkFrontendApi() +
      '/npm/@clerk/ui@' + CLERK_UI_MAJOR + '/dist/ui.browser.js';
  }

  function loadUser() {
    try {
      var raw = localStorage.getItem(USER_KEY);
      var user = raw ? JSON.parse(raw) : null;
      return user && user.id ? user : null;
    } catch (e) { return null; }
  }

  function fire() {
    listeners.slice().forEach(function (callback) {
      try { callback(); } catch (e) {}
    });
  }

  function demoSignIn() {
    var user = loadUser();
    if (!user) {
      user = {
        id: 'demo-' + Math.random().toString(36).slice(2, 10),
        email: 'demo@omo.space',
        name: 'Demo Shopper',
        firstName: 'Demo',
        lastName: 'Shopper',
        username: 'demo-shopper',
        demo: true
      };
    }
    user.email = user.email || 'demo@omo.space';
    user.name = user.name || [user.firstName, user.lastName].filter(Boolean).join(' ') || 'Demo Shopper';
    try { localStorage.setItem(USER_KEY, JSON.stringify(user)); } catch (e) {}
    fire();
    return user;
  }

  function demoSignOut() {
    try { localStorage.removeItem(USER_KEY); } catch (e) {}
    fire();
  }

  function openPendingModal() {
    if (!realClerk || !pendingModal) return;
    var kind = pendingModal;
    pendingModal = '';
    if (kind === 'signup' && realClerk.openSignUp) {
      if (signUpRedirect) {
        var absoluteRedirect = new URL(signUpRedirect, window.location.href).href;
        realClerk.openSignUp({
          afterSignUpUrl: absoluteRedirect,
          afterSignInUrl: absoluteRedirect,
          fallbackRedirectUrl: absoluteRedirect,
          signInFallbackRedirectUrl: absoluteRedirect
        });
      } else {
        realClerk.openSignUp();
      }
    }
    else realClerk.openSignIn();
  }

  function dashboardRedirect() {
    var slug = '';
    try { slug = (new URLSearchParams(window.location.search).get('open') || '').trim(); } catch (e) {}
    if (!/^[a-z0-9][a-z0-9-]{0,100}$/i.test(slug)) slug = '';
    return 'dashboard.html' + (slug ? '?open=' + encodeURIComponent(slug) : '');
  }

  function finishSignUpRedirect() {
    if (!signUpRedirect) return false;
    var signedIn = demoMode() ? !!loadUser() : !!realClerkUser;
    if (!signedIn) return false;
    var target = signUpRedirect;
    signUpRedirect = '';
    window.location.assign(target);
    return true;
  }

  function initClerk(resolve, reject) {
    if (!window.Clerk) { reject(new Error('Clerk SDK did not load.')); return; }
    if (typeof window.__internal_ClerkUICtor !== 'function') {
      reject(new Error('Clerk UI bundle did not load.'));
      return;
    }
    var ready;
    try {
      ready = window.Clerk.load({
        ui: { ClerkUI: window.__internal_ClerkUICtor }
      });
    }
    catch (error) { reject(error); return; }
    Promise.resolve(ready).then(function () {
      realClerk = window.Clerk;
      realClerkUser = realClerk.user || null;
      loadError = null;
      realClerk.addListener(function (resources) {
        // Clerk delivers the listener payload before every SDK build updates
        // the singleton's `user` property. Keep the payload as the auth source
        // of truth so navigation reacts to sign-in/sign-out immediately.
        if (resources && Object.prototype.hasOwnProperty.call(resources, 'user')) {
          realClerkUser = resources.user || null;
        } else {
          realClerkUser = realClerk.user || null;
        }
        fire();
        finishSignUpRedirect();
      });
      openPendingModal();
      fire();
      finishSignUpRedirect();
      resolve(realClerk);
    }).catch(reject);
  }

  function loadRealClerk() {
    if (demoMode()) return null;
    if (loadPromise) return loadPromise;
    loadError = null;
    loadPromise = new Promise(function (resolve, reject) {
      var cleanups = [];
      var settled = false;
      var timeout = window.setTimeout(function () {
        fail(new Error('Clerk SDK loading timed out.'));
      }, LOAD_TIMEOUT_MS);

      function cleanupListeners() {
        cleanups.splice(0).forEach(function (cleanup) { cleanup(); });
      }

      function succeed(clerk) {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeout);
        cleanupListeners();
        resolve(clerk);
      }

      function fail(error) {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeout);
        cleanupListeners();
        reject(error instanceof Error ? error : new Error('Clerk SDK could not load.'));
      }

      function waitForScript(id, src, isReady, configure, label) {
        if (isReady()) return Promise.resolve();
        return new Promise(function (scriptResolve, scriptReject) {
          var script = document.getElementById(id);
          if (!script) {
            script = document.createElement('script');
            script.id = id;
            script.src = src;
            script.async = true;
            script.crossOrigin = 'anonymous';
            if (configure) configure(script);
          }

          function cleanup() {
            script.removeEventListener('load', onLoad);
            script.removeEventListener('error', onError);
          }

          function onLoad() {
            cleanup();
            if (isReady()) scriptResolve();
            else scriptReject(new Error(label + ' did not initialize.'));
          }

          function onError() {
            cleanup();
            scriptReject(new Error(label + ' could not load.'));
          }

          cleanups.push(cleanup);
          script.addEventListener('load', onLoad, { once: true });
          script.addEventListener('error', onError, { once: true });
          if (!script.parentNode) document.head.appendChild(script);
        });
      }

      var uiUrl;
      var sdkUrl;
      try {
        uiUrl = clerkUiUrl();
        sdkUrl = clerkSdkUrl();
      } catch (error) {
        fail(error);
        return;
      }

      waitForScript(
        'clerk-ui',
        uiUrl,
        function () { return typeof window.__internal_ClerkUICtor === 'function'; },
        null,
        'Clerk UI bundle'
      ).then(function () {
        if (settled) return;
        return waitForScript(
          'clerk-js',
          sdkUrl,
          function () { return !!window.Clerk; },
          function (script) {
            script.setAttribute('data-clerk-publishable-key', getKey());
            script.setAttribute('data-clerk-js-script', 'true');
          },
          'Clerk SDK'
        );
      }).then(function () {
        if (!settled) initClerk(succeed, fail);
      }).catch(fail);
    }).catch(function (error) {
      var failedUiScript = document.getElementById('clerk-ui');
      if (failedUiScript && typeof window.__internal_ClerkUICtor !== 'function' && failedUiScript.parentNode) {
        failedUiScript.parentNode.removeChild(failedUiScript);
      }
      var failedScript = document.getElementById('clerk-js');
      if (failedScript && !window.Clerk && failedScript.parentNode) {
        failedScript.parentNode.removeChild(failedScript);
      }
      loadPromise = null;
      pendingModal = '';
      loadError = error instanceof Error ? error : new Error('Clerk SDK could not load.');
      fire();
      throw loadError;
    });
    return loadPromise;
  }

  function openRealModal(kind) {
    pendingModal = kind;
    if (realClerk) { openPendingModal(); return null; }
    return loadRealClerk();
  }

  function signUpAndRedirect() {
    signUpRedirect = dashboardRedirect();
    if (demoMode()) {
      var demoUser = demoSignIn();
      finishSignUpRedirect();
      return Promise.resolve(demoUser);
    }
    if (realClerkUser) {
      finishSignUpRedirect();
      return Promise.resolve(realClerkUser);
    }
    return openRealModal('signup');
  }

  function currentUser() {
    if (demoMode()) return loadUser();
    if (!realClerkUser) return null;
    var user = realClerkUser;
    var primaryEmail = user.primaryEmailAddress || (user.emailAddresses && user.emailAddresses[0]);
    return {
      id: user.id,
      email: primaryEmail ? primaryEmail.emailAddress : '',
      name: user.fullName || [user.firstName, user.lastName].filter(Boolean).join(' '),
      firstName: user.firstName || '',
      lastName: user.lastName || '',
      username: user.username || '',
      demo: false
    };
  }

  if (!demoMode()) {
    // Preload for a fast modal. The UI observes errors through getLoadError(),
    // and a later explicit sign-in starts a fresh attempt.
    loadRealClerk().catch(function () {});
  }

  window.ClerkAuth = {
    isSignedIn: function () {
      return demoMode() ? !!loadUser() : !!realClerkUser;
    },
    signIn: function () {
      return demoMode() ? demoSignIn() : openRealModal('signin');
    },
    signUp: function () {
      return demoMode() ? demoSignIn() : openRealModal('signup');
    },
    signUpAndRedirect: signUpAndRedirect,
    signOut: function () {
      if (demoMode()) return demoSignOut();
      if (realClerk) return realClerk.signOut();
      var ready = loadRealClerk();
      return ready && ready.then(function (clerk) { if (clerk) return clerk.signOut(); });
    },
    getUser: currentUser,
    currentUser: currentUser,
    getLoadError: function () { return loadError; },
    onAuthChange: function (callback) {
      if (typeof callback === 'function') listeners.push(callback);
      return callback;
    }
  };
})();
