/* clerk.js — Clerk auth for the Omo storefront, with a local demo fallback.
 *
 * Exposes window.ClerkAuth =
 *   { isSignedIn, signIn, signOut, signUp, getUser, onAuthChange }.
 */
(function () {
  'use strict';

  var PLACEHOLDER = 'pk_test_placeholder';
  var USER_KEY = 'cognition_user';
  var realClerk = null;
  var loadPromise = null;
  var pendingModal = '';
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
        email: 'demo@cognition.cv',
        firstName: 'Demo',
        lastName: 'Shopper',
        username: 'demo-shopper',
        demo: true
      };
      try { localStorage.setItem(USER_KEY, JSON.stringify(user)); } catch (e) {}
    }
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
    if (kind === 'signup' && realClerk.openSignUp) realClerk.openSignUp();
    else realClerk.openSignIn();
  }

  function initClerk(resolve, reject) {
    if (!window.Clerk) { reject(new Error('Clerk SDK did not load.')); return; }
    window.Clerk.load({ publishableKey: getKey() }).then(function () {
      realClerk = window.Clerk;
      realClerk.addListener(function () { fire(); });
      openPendingModal();
      fire();
      resolve(realClerk);
    }).catch(reject);
  }

  function loadRealClerk() {
    if (demoMode()) return null;
    if (loadPromise) return loadPromise;
    loadPromise = new Promise(function (resolve, reject) {
      if (window.Clerk) { initClerk(resolve, reject); return; }

      var script = document.getElementById('clerk-js');
      if (!script) {
        script = document.createElement('script');
        script.id = 'clerk-js';
        script.src = 'https://cdn.clerk.com/v1/clerk.browser.js';
        script.async = true;
        script.crossOrigin = 'anonymous';
        script.setAttribute('data-clerk-publishable-key', getKey());
      }
      script.addEventListener('load', function () { initClerk(resolve, reject); }, { once: true });
      script.addEventListener('error', function () { reject(new Error('Clerk SDK could not load.')); }, { once: true });
      if (!script.parentNode) document.head.appendChild(script);
    }).catch(function () {
      var failedScript = document.getElementById('clerk-js');
      if (failedScript && !window.Clerk && failedScript.parentNode) {
        failedScript.parentNode.removeChild(failedScript);
      }
      loadPromise = null;
      pendingModal = '';
      fire();
      return null;
    });
    return loadPromise;
  }

  function openRealModal(kind) {
    pendingModal = kind;
    if (realClerk) { openPendingModal(); return null; }
    return loadRealClerk();
  }

  if (!demoMode()) loadRealClerk();

  window.ClerkAuth = {
    isSignedIn: function () {
      return demoMode() ? !!loadUser() : !!(realClerk && realClerk.user);
    },
    signIn: function () {
      return demoMode() ? demoSignIn() : openRealModal('signin');
    },
    signUp: function () {
      return demoMode() ? demoSignIn() : openRealModal('signup');
    },
    signOut: function () {
      if (demoMode()) return demoSignOut();
      if (realClerk) return realClerk.signOut();
      var ready = loadRealClerk();
      return ready && ready.then(function (clerk) { if (clerk) return clerk.signOut(); });
    },
    getUser: function () {
      if (demoMode()) return loadUser();
      if (!realClerk || !realClerk.user) return null;
      var user = realClerk.user;
      var primaryEmail = user.primaryEmailAddress || (user.emailAddresses && user.emailAddresses[0]);
      return {
        id: user.id,
        email: primaryEmail ? primaryEmail.emailAddress : '',
        firstName: user.firstName || '',
        lastName: user.lastName || '',
        username: user.username || '',
        demo: false
      };
    },
    onAuthChange: function (callback) {
      if (typeof callback === 'function') listeners.push(callback);
      return callback;
    }
  };
})();
