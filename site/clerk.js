/* clerk.js — Clerk auth for the Cognition storefront, with a demo fallback.
 *
 * How it works:
 *  - Reads the publishable key from window.CLERK_PUBLISHABLE_KEY (set in
 *    index.html). While the key is the placeholder, or the page is opened
 *    from file://, or Clerk fails to load, the store runs in DEMO MODE:
 *    "signing in" fakes a local user in localStorage (cognition_user) so the
 *    whole flow is testable with zero Clerk credentials.
 *  - With a real key on http(s), loads https://cdn.clerk.com/v1/clerk.browser.js
 *    and drives the real Clerk modal + session. signIn() opens the sign-in
 *    modal (which includes the sign-up path); signUp() opens sign-up directly.
 *
 * Exposes window.ClerkAuth = { isSignedIn, signIn, signOut, signUp, getUser, onAuthChange }.
 */
(function () {
  'use strict';

  var PLACEHOLDER = 'pk_test_placeholder';
  var USER_KEY = 'cognition_user';

  var realClerk = null;
  var realReady = false;
  var clerkFailed = false;
  var pendingSignIn = false;
  var listeners = [];

  function getKey() {
    return (window.CLERK_PUBLISHABLE_KEY || '').trim() || PLACEHOLDER;
  }

  function isPlaceholderKey() {
    var k = getKey();
    // Any key containing 'placeholder' (pk_test_placeholder, pk_live_placeholder,
    // or a partially-pasted one) counts as "not configured yet" → demo mode.
    return !k || k === PLACEHOLDER || k.toLowerCase().indexOf('placeholder') !== -1;
  }

  function isFileProtocol() {
    return window.location && window.location.protocol === 'file:';
  }

  function demoMode() {
    return isFileProtocol() || isPlaceholderKey() || clerkFailed;
  }

  function loadUser() {
    try {
      var raw = localStorage.getItem(USER_KEY);
      if (!raw) return null;
      var u = JSON.parse(raw);
      return u && u.id ? u : null;
    } catch (e) { return null; }
  }

  function saveUser(u) {
    try { localStorage.setItem(USER_KEY, JSON.stringify(u)); } catch (e) {}
  }

  function clearUser() {
    try { localStorage.removeItem(USER_KEY); } catch (e) {}
  }

  function fire() {
    var cbs = listeners.slice();
    cbs.forEach(function (cb) {
      try { cb(); } catch (e) {}
    });
  }

  function demoSignIn() {
    var u = loadUser();
    if (!u) {
      u = {
        id: 'demo-' + Math.random().toString(36).slice(2, 10),
        email: 'demo@cognition.cv',
        firstName: 'Demo',
        lastName: 'Shopper',
        username: 'demo-shopper',
        demo: true
      };
      saveUser(u);
    }
    fire();
    return u;
  }

  function demoSignOut() {
    clearUser();
    fire();
  }

  function loadRealClerk() {
    var s = document.createElement('script');
    s.src = 'https://cdn.clerk.com/v1/clerk.browser.js';
    s.async = true;
    s.onload = function () {
      try {
        if (!window.Clerk) throw new Error('Clerk global missing');
        window.Clerk.load({ publishableKey: getKey() }).then(function () {
          realClerk = window.Clerk;
          realReady = true;
          window.Clerk.addListener(function () { fire(); });
          if (pendingSignIn) {
            pendingSignIn = false;
            realClerk.openSignIn();
          }
          fire();
        }).catch(function () {
          clerkFailed = true;
          if (pendingSignIn) { pendingSignIn = false; demoSignIn(); }
          fire();
        });
      } catch (e) {
        clerkFailed = true;
        if (pendingSignIn) { pendingSignIn = false; demoSignIn(); }
        fire();
      }
    };
    s.onerror = function () {
      clerkFailed = true;
      if (pendingSignIn) { pendingSignIn = false; demoSignIn(); }
      fire();
    };
    document.head.appendChild(s);
  }

  function shouldLoadReal() {
    return !isFileProtocol() && !isPlaceholderKey();
  }

  // The publishable key lives in index.html's inline script, which runs
  // AFTER this file. Re-check once the parser finishes so a real key
  // still activates Clerk; the placeholder keeps everything in demo mode.
  if (shouldLoadReal()) {
    loadRealClerk();
  } else if (typeof setTimeout === 'function') {
    setTimeout(function () {
      if (shouldLoadReal() && !realClerk) loadRealClerk();
    }, 0);
  }

  function openRealModal(kind) {
    if (realClerk && realReady) {
      if (kind === 'signup' && realClerk.openSignUp) realClerk.openSignUp();
      else realClerk.openSignIn();
      return true;
    }
    pendingSignIn = true; // Clerk still loading: open the modal when ready
    return false;
  }

  window.ClerkAuth = {
    isSignedIn: function () {
      if (demoMode()) return !!loadUser();
      if (realClerk && realReady) return !!realClerk.user;
      return false;
    },
    signIn: function () {
      if (demoMode()) return demoSignIn();
      if (realClerk && realReady) {
        realClerk.openSignIn(); // sign-in modal, with the sign-up path inside
        return null;
      }
      pendingSignIn = true; // Clerk still loading: open the modal when ready
      return null;
    },
    signUp: function () {
      if (demoMode()) return demoSignIn();
      if (realClerk && realReady && realClerk.openSignUp) {
        realClerk.openSignUp(); // straight to the create-account modal
        return null;
      }
      return openRealModal('signup');
    },
    signOut: function () {
      if (demoMode()) return demoSignOut();
      if (realClerk && realReady && realClerk.signOut) {
        realClerk.signOut().then(function () { fire(); }).catch(function () { fire(); });
        return;
      }
      demoSignOut();
    },
    getUser: function () {
      if (demoMode()) return loadUser();
      if (realClerk && realReady && realClerk.user) {
        var u = realClerk.user;
        return {
          id: u.id,
          email: u.primaryEmailAddress ? u.primaryEmailAddress.emailAddress : '',
          firstName: u.firstName || '',
          lastName: u.lastName || '',
          username: u.username || '',
          demo: false
        };
      }
      return null;
    },
    onAuthChange: function (cb) {
      if (typeof cb === 'function') listeners.push(cb);
      return cb;
    }
  };
})();
