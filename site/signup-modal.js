/* Omo's default account popup. Uses Clerk's headless API so every auth path
 * keeps the branded Omo form instead of opening Clerk's hosted modal. */
(function () {
  'use strict';

  var AUTH_READY_TIMEOUT_MS = 16000;
  var AUTH_READY_POLL_MS = 50;

  function ensureStyles() {
    if (document.querySelector('link[href$="signup-modal.css"]')) return;
    var stylesheet = document.createElement('link');
    stylesheet.rel = 'stylesheet';
    stylesheet.href = '/signup-modal.css';
    document.head.appendChild(stylesheet);
  }

  function ensureMarkup() {
    if (document.getElementById('signup-modal')) return;
    var wrapper = document.createElement('div');
    wrapper.innerHTML = [
      '<div class="auth-modal" id="signup-modal" hidden>',
        '<section class="auth-modal__card" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title" aria-describedby="auth-modal-subtitle">',
          '<button class="auth-modal__close" id="auth-modal-close" type="button" aria-label="Close">&times;</button>',
          '<img class="auth-modal__logo" src="/logo-sweet-pastel.svg" alt="Omo">',
          '<div class="auth-modal__view" id="auth-form-view">',
            '<h2 class="auth-modal__heading" id="auth-modal-title">Create your Omo account</h2>',
            '<p class="auth-modal__subheading" id="auth-modal-subtitle">to run AI helpers and keep what you build</p>',
            '<form class="auth-modal__form" id="auth-form" novalidate>',
              '<div class="auth-modal__field signup-only">',
                '<input class="auth-modal__input" id="auth-first-name" name="firstName" type="text" autocomplete="given-name" placeholder=" " maxlength="80" required>',
                '<label class="auth-modal__label" for="auth-first-name">First name</label>',
              '</div>',
              '<div class="auth-modal__field signup-only">',
                '<input class="auth-modal__input" id="auth-last-name" name="lastName" type="text" autocomplete="family-name" placeholder=" " maxlength="80" required>',
                '<label class="auth-modal__label" for="auth-last-name">Last name</label>',
              '</div>',
              '<div class="auth-modal__field">',
                '<input class="auth-modal__input" id="auth-email" name="email" type="email" inputmode="email" autocomplete="email" placeholder=" " maxlength="254" required>',
                '<label class="auth-modal__label" for="auth-email">Email</label>',
              '</div>',
              '<div class="auth-modal__field">',
                '<input class="auth-modal__input" id="auth-password" name="password" type="password" autocomplete="new-password" placeholder=" " minlength="8" maxlength="128" required>',
                '<label class="auth-modal__label" for="auth-password">Password</label>',
              '</div>',
              '<p class="auth-modal__message" id="auth-error" role="alert" hidden></p>',
              '<button class="auth-modal__submit" id="auth-submit" type="submit" disabled>Sign up</button>',
              '<p class="auth-modal__fine-print signup-only">By signing up, you agree to our <a href="terms.html" target="_blank" rel="noopener">Terms</a> and <a href="privacy.html" target="_blank" rel="noopener">Privacy Policy</a>.</p>',
            '</form>',
            '<p class="auth-modal__switch"><span id="auth-switch-copy">Already have an account?</span> <button class="auth-modal__switch-button" id="auth-switch" type="button">Log in</button></p>',
          '</div>',
          '<div class="auth-modal__view" id="auth-verification-view" hidden>',
            '<h2 class="auth-modal__heading" id="auth-verification-title">Check your email</h2>',
            '<p class="auth-modal__verification-copy">Enter the verification code sent to <strong id="auth-verification-email"></strong>.</p>',
            '<form class="auth-modal__form" id="auth-verification-form" novalidate>',
              '<div class="auth-modal__field">',
                '<input class="auth-modal__input" id="auth-code" name="code" type="text" inputmode="numeric" autocomplete="one-time-code" placeholder=" " minlength="6" maxlength="6" required>',
                '<label class="auth-modal__label" for="auth-code">Verification code</label>',
              '</div>',
              '<p class="auth-modal__message" id="auth-verification-error" role="alert" hidden></p>',
              '<button class="auth-modal__submit" id="auth-verify" type="submit" disabled>Verify email</button>',
              '<p class="auth-modal__resend-row">Didn\'t get it? <button class="auth-modal__resend" id="auth-resend" type="button">Send a new code</button></p>',
            '</form>',
          '</div>',
        '</section>',
      '</div>'
    ].join('');
    document.body.appendChild(wrapper.firstChild);
  }

  ensureStyles();
  ensureMarkup();

  var modal = document.getElementById('signup-modal');
  var card = modal && modal.querySelector('.auth-modal__card');
  var logo = modal && modal.querySelector('.auth-modal__logo');
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
  var lastFocused = null;
  var activeOpenTarget = '';
  var activeDestination = '';

  if (!modal || !card || !form) return;

  // The lockup was 72px tall in the original modal. Keep it centered while
  // giving the form heading more room, including on pages with older CSS.
  if (logo) logo.style.height = '52px';

  function validOpenTarget(value) {
    var slug = String(value || '').trim();
    return /^[a-z0-9][a-z0-9-]{0,100}$/i.test(slug) ? slug : '';
  }

  function redirectTarget() {
    var slug = activeOpenTarget;
    var destination = activeDestination;
    var pilotToken = '';
    try {
      var pilotParams = new URLSearchParams(window.location.search);
      if (/(^|\/)pilot-claim(?:\.html)?\/?$/.test(window.location.pathname)) {
        pilotToken = String(pilotParams.get('token') || '').trim();
      }
    } catch (error) {}
    if (/^v1\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(pilotToken) && pilotToken.length <= 4096) {
      return '/pilot-claim.html?token=' + encodeURIComponent(pilotToken);
    }
    if (!slug) {
      try { slug = validOpenTarget(new URLSearchParams(window.location.search).get('open')); } catch (error) {}
    }
    if (!destination) {
      try { destination = new URLSearchParams(window.location.search).get('destination') === 'run' ? 'run' : ''; } catch (error) {}
    }
    if (slug && destination === 'run') return 'run.html?slug=' + encodeURIComponent(slug);
    return slug ? 'workflow.html?slug=' + encodeURIComponent(slug) : 'dashboard.html';
  }

  function redirectAfterAuth() {
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

  function open(nextMode, options) {
    lastFocused = document.activeElement;
    activeOpenTarget = validOpenTarget(options && options.open);
    activeDestination = options && options.destination === 'run' ? 'run' : '';
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
    var codeName = (clerkError && clerkError.code) || (error && error.code) || '';
    var raw = (clerkError && (clerkError.longMessage || clerkError.message)) || (error && error.message);
    var detail = codeName + ' ' + (raw || '');

    if (/auth_service_unavailable|clerk (?:sdk|ui bundle)|loading timed out|could not load|failed to fetch|network(?:error)?/i.test(detail)) {
      return 'We couldn\'t reach the sign-in service. Check your connection and try again.';
    }
    if (/identifier.*exists|already.*exists/i.test(detail)) {
      return 'An account with this email already exists. Try logging in instead.';
    }
    if (/password.*(pwned|weak|strong|length|size)/i.test(detail)) {
      return 'Choose a stronger password with at least 8 characters, including a number or symbol.';
    }
    if (/identifier.*(invalid|format)|email.*(invalid|format)/i.test(detail)) {
      return 'Enter a valid email address.';
    }
    if (/credentials|password.*incorrect|identifier.*not_found|session.*invalid/i.test(detail)) {
      return 'That email or password is incorrect. Please try again.';
    }
    if (/too.many|rate.limit|attempts.*exceeded/i.test(detail)) {
      return 'Too many attempts. Take a short break, then try again.';
    }
    if (/code.*incorrect|verification.*failed/i.test(detail)) {
      return 'That code is not correct. Check the email and try again.';
    }
    if (/verification.*expired|code.*expired/i.test(detail)) {
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
    return Promise.resolve(window.Clerk.setActive({ session: sessionId })).then(redirectAfterAuth);
  }

  function serviceUnavailable(message) {
    var error = new Error(message || 'The sign-in service could not load.');
    error.code = 'auth_service_unavailable';
    return error;
  }

  function ensureRealClerk() {
    return new Promise(function (resolve, reject) {
      var settled = false;
      var timeout = window.setTimeout(function () {
        fail(serviceUnavailable('Clerk SDK loading timed out.'));
      }, AUTH_READY_TIMEOUT_MS);

      function succeed(clerk) {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeout);
        resolve(clerk);
      }

      function fail(error) {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeout);
        if (error && error.code === 'auth_service_unavailable') reject(error);
        else reject(serviceUnavailable(error && error.message));
      }

      function check() {
        if (settled) return;
        if (window.ClerkAuth && typeof window.ClerkAuth.ensureLoaded === 'function') {
          Promise.resolve(window.ClerkAuth.ensureLoaded()).then(function (clerk) {
            if (clerk && clerkSignIn()) succeed(clerk);
            else fail(serviceUnavailable());
          }, fail);
          return;
        }
        if (window.Clerk && window.Clerk.loaded && clerkSignIn()) {
          succeed(window.Clerk);
          return;
        }
        window.setTimeout(check, AUTH_READY_POLL_MS);
      }
      check();
    });
  }

  function incompleteSignIn(result) {
    var status = result && result.status;
    var message = 'Sign-in needs another step before it can finish.';
    if (status === 'needs_second_factor') {
      message = 'This account uses two-step verification. Complete the extra verification step to continue.';
    } else if (status === 'needs_first_factor') {
      message = 'This account needs a different verification method before sign-in can finish.';
    } else if (status === 'needs_new_password') {
      message = 'This account needs a new password before sign-in can finish.';
    }
    var error = new Error(message);
    error.code = 'sign_in_' + (status || 'incomplete');
    return error;
  }

  function submitDemo(kind) {
    if (!window.ClerkAuth) return Promise.reject(new Error('Demo sign-in is unavailable. Please refresh and try again.'));
    var action = kind === 'signup' ? window.ClerkAuth.signUp : window.ClerkAuth.signIn;
    if (typeof action !== 'function') return Promise.reject(new Error('Demo sign-in is unavailable. Please refresh and try again.'));
    return Promise.resolve(action.call(window.ClerkAuth)).then(redirectAfterAuth);
  }

  function submitRealSignUp() {
    return ensureRealClerk().then(function () {
      submitButton.textContent = 'Creating account…';
      var signUp = clerkSignUp();
      if (!signUp) throw serviceUnavailable();

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
    });
  }

  function submitRealLogin() {
    return ensureRealClerk().then(function () {
      submitButton.textContent = 'Logging in…';
      var signIn = clerkSignIn();
      if (!signIn) throw serviceUnavailable();
      return Promise.resolve(signIn.create({
        identifier: email.value.trim(),
        password: password.value
      })).then(function (result) {
        if (!result || result.status !== 'complete') throw incompleteSignIn(result);
        return activateSession(result);
      });
    });
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (busy || submitButton.disabled) return;
    setMessage(errorMessage, '');
    var demo = isDemoMode();
    setBusy(true, submitButton, demo ? (mode === 'signup' ? 'Creating account…' : 'Logging in…') : 'Loading…');

    var request;
    try {
      request = demo ? submitDemo(mode) : (mode === 'signup' ? submitRealSignUp() : submitRealLogin());
    } catch (error) {
      request = Promise.reject(error);
    }

    Promise.resolve(request).catch(function (error) {
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
  if (launchButton) launchButton.addEventListener('click', function () { open('signup'); });
  closeButton.addEventListener('click', close);
  modal.addEventListener('click', function (event) { if (event.target === modal) close(); });
  form.addEventListener('input', updateValidity);
  form.addEventListener('submit', handleSubmit);
  verificationForm.addEventListener('input', updateValidity);
  verificationForm.addEventListener('submit', handleVerification);
  switchButton.addEventListener('click', function () { setMode(mode === 'signup' ? 'login' : 'signup'); });
  resendButton.addEventListener('click', resendCode);
  document.addEventListener('keydown', handleKeydown);

  window.OmoSignupModal = {
    open: function (options) { open('signup', options); },
    openSignIn: function (options) { open('login', options); },
    close: close
  };
  window.OmoAuth = {
    open: function (nextMode, options) { open(nextMode, options); },
    close: close
  };

  // signup.html is the canonical auth destination, so arriving there should
  // show this form immediately rather than a second marketing-page click.
  if (/(^|\/)signup(?:\.html)?\/?$/.test(window.location.pathname)) {
    var requestedMode = '';
    var hasOpenTarget = false;
    var cameFromOmoPage = false;
    try {
      var params = new URLSearchParams(window.location.search);
      requestedMode = params.get('mode') || params.get('auth') || '';
      hasOpenTarget = params.has('open');
      if (document.referrer) {
        var referrer = new URL(document.referrer);
        cameFromOmoPage = referrer.origin === window.location.origin &&
          !/(^|\/)signup(?:\.html)?\/?$/.test(referrer.pathname);
      }
    } catch (error) {}
    open(requestedMode === 'login' || (!requestedMode && !hasOpenTarget && cameFromOmoPage) ? 'login' : 'signup');
  }
})();
