/* Omo's simple account popup. Uses Clerk's headless API when available and
 * keeps ClerkAuth's zero-config demo flow as the fallback. */
(function () {
  'use strict';

  var modal = document.getElementById('signup-modal');
  var card = modal && modal.querySelector('.auth-modal__card');
  var launchButton = document.getElementById('create-account');
  var closeButton = document.getElementById('auth-modal-close');
  var formView = document.getElementById('auth-form-view');
  var verificationView = document.getElementById('auth-verification-view');
  var form = document.getElementById('auth-form');
  var verificationForm = document.getElementById('auth-verification-form');
  var title = document.getElementById('auth-modal-title');
  var subtitle = document.getElementById('auth-modal-subtitle');
  var firstName = document.getElementById('auth-first-name');
  var lastName = document.getElementById('auth-last-name');
  var email = document.getElementById('auth-email');
  var password = document.getElementById('auth-password');
  var submitButton = document.getElementById('auth-submit');
  var errorMessage = document.getElementById('auth-error');
  var switchCopy = document.getElementById('auth-switch-copy');
  var switchButton = document.getElementById('auth-switch');
  var code = document.getElementById('auth-code');
  var verifyButton = document.getElementById('auth-verify');
  var verificationEmail = document.getElementById('auth-verification-email');
  var verificationError = document.getElementById('auth-verification-error');
  var resendButton = document.getElementById('auth-resend');
  var mode = 'signup';
  var busy = false;
  var fallbackPending = false;
  var lastFocused = null;

  if (!modal || !card || !launchButton || !form) return;

  function redirectTarget() {
    var slug = '';
    try { slug = (new URLSearchParams(window.location.search).get('open') || '').trim(); } catch (error) {}
    if (!/^[a-z0-9][a-z0-9-]{0,100}$/i.test(slug)) slug = '';
    return 'dashboard.html' + (slug ? '?open=' + encodeURIComponent(slug) : '');
  }

  function redirectToDashboard() {
    window.location.assign(redirectTarget());
  }

  function isDemoMode() {
    var key = (window.CLERK_PUBLISHABLE_KEY || '').trim();
    return window.location.protocol === 'file:' || !/^pk_(?:test|live)_/.test(key) || key === 'pk_test_placeholder';
  }

  function setMessage(element, message) {
    element.textContent = message || '';
    element.hidden = !message;
  }

  function setBusy(nextBusy, button, label) {
    busy = nextBusy;
    button.setAttribute('aria-busy', nextBusy ? 'true' : 'false');
    button.textContent = nextBusy ? label : button.dataset.defaultLabel;
    updateValidity();
  }

  function nameIsValid(input) {
    return input.value.trim().length > 0;
  }

  function emailIsValid() {
    return email.value.trim().length > 3 && email.validity.valid;
  }

  function passwordIsValid() {
    return password.value.length >= 8;
  }

  function updateValidity() {
    var formValid = emailIsValid() && passwordIsValid();
    if (mode === 'signup') formValid = formValid && nameIsValid(firstName) && nameIsValid(lastName);
    submitButton.disabled = busy || !formValid;
    verifyButton.disabled = busy || !/^\d{6}$/.test(code.value.trim());
  }

  function setMode(nextMode) {
    mode = nextMode === 'login' ? 'login' : 'signup';
    form.classList.toggle('auth-modal__form--login', mode === 'login');
    Array.prototype.forEach.call(form.querySelectorAll('.signup-only'), function (element) {
      element.hidden = mode === 'login';
    });
    title.textContent = mode === 'signup' ? 'Create your Omo account' : 'Welcome back';
    subtitle.textContent = mode === 'signup' ? 'to run AI helpers and keep what you build' : 'Log in to keep building with Omo';
    submitButton.textContent = mode === 'signup' ? 'Sign up' : 'Log in';
    submitButton.dataset.defaultLabel = submitButton.textContent;
    password.autocomplete = mode === 'signup' ? 'new-password' : 'current-password';
    switchCopy.textContent = mode === 'signup' ? 'Already have an account?' : 'New to Omo?';
    switchButton.textContent = mode === 'signup' ? 'Log in' : 'Sign up';
    card.setAttribute('aria-labelledby', 'auth-modal-title');
    card.setAttribute('aria-describedby', 'auth-modal-subtitle');
    setMessage(errorMessage, '');
    updateValidity();
  }

  function open(nextMode) {
    lastFocused = document.activeElement;
    setMode(nextMode || 'signup');
    formView.hidden = false;
    verificationView.hidden = true;
    modal.hidden = false;
    document.body.classList.add('auth-modal-open');
    window.requestAnimationFrame(function () {
      (mode === 'signup' ? firstName : email).focus();
    });
  }

  function close() {
    if (modal.hidden) return;
    modal.hidden = true;
    document.body.classList.remove('auth-modal-open');
    setMessage(errorMessage, '');
    setMessage(verificationError, '');
    if (lastFocused && typeof lastFocused.focus === 'function') lastFocused.focus();
  }

  function friendlyError(error, context) {
    var clerkError = error && error.errors && error.errors[0];
    var codeName = clerkError && clerkError.code ? clerkError.code : '';
    var raw = (clerkError && (clerkError.longMessage || clerkError.message)) || (error && error.message);

    if (/identifier.*exists|already.*exists/i.test(codeName)) {
      return 'An account with this email already exists. Try logging in instead.';
    }
    if (/password.*(pwned|weak|strong|length|size)/i.test(codeName)) {
      return 'Choose a stronger password with at least 8 characters, including a number or symbol.';
    }
    if (/identifier.*(invalid|format)|email.*(invalid|format)/i.test(codeName)) {
      return 'Enter a valid email address.';
    }
    if (/credentials|password.*incorrect|identifier.*not_found|session.*invalid/i.test(codeName)) {
      return 'That email or password is incorrect. Please try again.';
    }
    if (/code.*incorrect|verification.*failed/i.test(codeName)) {
      return 'That code is not correct. Check the email and try again.';
    }
    if (/verification.*expired|code.*expired/i.test(codeName)) {
      return 'That code has expired. Send a new code and try again.';
    }
    if (raw && raw.length < 220) return raw;
    if (context === 'login') return 'We couldn\'t log you in. Check your details and try again.';
    if (context === 'verify') return 'We couldn\'t verify that code. Please try again.';
    return 'We couldn\'t create your account. Please check your details and try again.';
  }

  function clerkSignUp() {
    if (!window.Clerk) return null;
    if (window.Clerk.signUp && typeof window.Clerk.signUp.create === 'function') return window.Clerk.signUp;
    if (window.Clerk.client && window.Clerk.client.signUp && typeof window.Clerk.client.signUp.create === 'function') {
      return window.Clerk.client.signUp;
    }
    return null;
  }

  function clerkSignIn() {
    if (!window.Clerk) return null;
    if (window.Clerk.signIn && typeof window.Clerk.signIn.create === 'function') return window.Clerk.signIn;
    if (window.Clerk.client && window.Clerk.client.signIn && typeof window.Clerk.client.signIn.create === 'function') {
      return window.Clerk.client.signIn;
    }
    return null;
  }

  function activateSession(resource) {
    var sessionId = resource && resource.createdSessionId;
    if (!sessionId || !window.Clerk || typeof window.Clerk.setActive !== 'function') {
      throw new Error('Your account is ready, but the session could not be started. Please log in.');
    }
    return Promise.resolve(window.Clerk.setActive({ session: sessionId })).then(redirectToDashboard);
  }

  function fallbackToClerk(kind) {
    if (!window.ClerkAuth) throw new Error('The sign-in service is still loading. Please try again.');
    fallbackPending = true;
    if (kind === 'signup' && typeof window.ClerkAuth.signUpAndRedirect === 'function') {
      return Promise.resolve(window.ClerkAuth.signUpAndRedirect());
    }
    if (kind === 'login' && typeof window.ClerkAuth.signIn === 'function') {
      return Promise.resolve(window.ClerkAuth.signIn());
    }
    throw new Error('The sign-in service is unavailable. Please refresh and try again.');
  }

  function submitDemo(kind) {
    if (!window.ClerkAuth) return Promise.reject(new Error('Demo sign-in is unavailable. Please refresh and try again.'));
    var action = kind === 'signup' ? window.ClerkAuth.signUpAndRedirect : window.ClerkAuth.signIn;
    if (typeof action !== 'function') return Promise.reject(new Error('Demo sign-in is unavailable. Please refresh and try again.'));
    return Promise.resolve(action.call(window.ClerkAuth)).then(function () {
      if (kind === 'login') redirectToDashboard();
    });
  }

  function submitRealSignUp() {
    var signUp = clerkSignUp();
    if (!signUp) return fallbackToClerk('signup');

    return Promise.resolve(signUp.create({
      firstName: firstName.value.trim(),
      lastName: lastName.value.trim(),
      emailAddress: email.value.trim(),
      password: password.value
    })).then(function (result) {
      if (result && result.status === 'complete' && result.createdSessionId) return activateSession(result);
      return Promise.resolve(signUp.prepareEmailAddressVerification({ strategy: 'email_code' })).then(function () {
        verificationEmail.textContent = email.value.trim();
        formView.hidden = true;
        verificationView.hidden = false;
        card.setAttribute('aria-labelledby', 'auth-verification-title');
        card.removeAttribute('aria-describedby');
        code.value = '';
        setMessage(verificationError, '');
        updateValidity();
        code.focus();
      });
    });
  }

  function submitRealLogin() {
    var signIn = clerkSignIn();
    if (!signIn) return fallbackToClerk('login');
    return Promise.resolve(signIn.create({
      identifier: email.value.trim(),
      password: password.value,
      strategy: 'password'
    })).then(function (result) {
      if (!result || result.status !== 'complete') {
        return fallbackToClerk('login');
      }
      return activateSession(result);
    });
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (busy || submitButton.disabled) return;
    setMessage(errorMessage, '');
    setBusy(true, submitButton, mode === 'signup' ? 'Creating account…' : 'Logging in…');

    var request;
    try {
      request = isDemoMode() ? submitDemo(mode) : (mode === 'signup' ? submitRealSignUp() : submitRealLogin());
    } catch (error) {
      request = Promise.reject(error);
    }

    Promise.resolve(request).catch(function (error) {
      fallbackPending = false;
      setMessage(errorMessage, friendlyError(error, mode));
    }).finally(function () {
      setBusy(false, submitButton, '');
    });
  }

  function handleVerification(event) {
    event.preventDefault();
    if (busy || verifyButton.disabled) return;
    var signUp = clerkSignUp();
    if (!signUp || typeof signUp.attemptEmailAddressVerification !== 'function') {
      setMessage(verificationError, 'The verification session expired. Please close this popup and sign up again.');
      return;
    }

    verificationError.style.color = '';
    setMessage(verificationError, '');
    setBusy(true, verifyButton, 'Verifying…');
    Promise.resolve(signUp.attemptEmailAddressVerification({ code: code.value.trim() })).then(function (result) {
      if (!result || result.status !== 'complete') throw new Error('Email verification is not complete yet.');
      return activateSession(result);
    }).catch(function (error) {
      setMessage(verificationError, friendlyError(error, 'verify'));
    }).finally(function () {
      setBusy(false, verifyButton, '');
    });
  }

  function resendCode() {
    var signUp = clerkSignUp();
    if (!signUp || typeof signUp.prepareEmailAddressVerification !== 'function') return;
    resendButton.disabled = true;
    setMessage(verificationError, '');
    Promise.resolve(signUp.prepareEmailAddressVerification({ strategy: 'email_code' })).then(function () {
      setMessage(verificationError, 'A new code is on its way.');
      verificationError.style.color = '#476f60';
    }).catch(function (error) {
      verificationError.style.color = '';
      setMessage(verificationError, friendlyError(error, 'verify'));
    }).finally(function () {
      resendButton.disabled = false;
    });
  }

  function handleKeydown(event) {
    if (modal.hidden) return;
    if (event.key === 'Escape') {
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

  submitButton.dataset.defaultLabel = 'Sign up';
  verifyButton.dataset.defaultLabel = 'Verify email';
  launchButton.addEventListener('click', function () { open('signup'); });
  closeButton.addEventListener('click', close);
  modal.addEventListener('click', function (event) { if (event.target === modal) close(); });
  form.addEventListener('input', updateValidity);
  form.addEventListener('submit', handleSubmit);
  verificationForm.addEventListener('input', updateValidity);
  verificationForm.addEventListener('submit', handleVerification);
  switchButton.addEventListener('click', function () { setMode(mode === 'signup' ? 'login' : 'signup'); });
  resendButton.addEventListener('click', resendCode);
  document.addEventListener('keydown', handleKeydown);

  if (window.ClerkAuth && typeof window.ClerkAuth.onAuthChange === 'function') {
    window.ClerkAuth.onAuthChange(function () {
      if (fallbackPending && window.ClerkAuth.isSignedIn()) redirectToDashboard();
    });
  }

  window.OmoSignupModal = {
    open: function () { open('signup'); },
    openSignIn: function () { open('login'); },
    close: close
  };
})();
