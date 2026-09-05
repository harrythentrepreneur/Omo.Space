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
  var verificationTitle = document.getElementById('auth-verification-title');
  var verificationCopy = verificationView && verificationView.querySelector('.auth-modal__verification-copy');
  var code = document.getElementById('auth-code');
  var codeLabel = verificationForm && verificationForm.querySelector('label[for="auth-code"]');
  var verifyButton = document.getElementById('auth-verify');
  var verificationEmail = document.getElementById('auth-verification-email');
  var verificationError = document.getElementById('auth-verification-error');
  var resendButton = document.getElementById('auth-resend');
  var resendRow = resendButton && resendButton.parentNode;
  var mode = 'signup';
  var busy = false;
  var activeVerification = null;
  var lastFocused = null;
  var activeOpenTarget = '';
  var activeDestination = '';
  var activeReturnTo = '';
  var backgroundState = [];

  if (!modal || !card || !form) return;

  // The lockup was 72px tall in the original modal. Keep it centered while
  // giving the form heading more room, including on pages with older CSS.
  if (logo) logo.style.height = '52px';

  function validOpenTarget(value) {
    var slug = String(value || '').trim();
    return /^[a-z0-9][a-z0-9-]{0,100}$/i.test(slug) ? slug : '';
  }

  function validatedReturnTo(value) {
    if (!value) return '';
    var target;
    try { target = new URL(String(value), window.location.origin); }
    catch (error) { return ''; }
    if (target.origin !== window.location.origin) return '';
    var path = target.pathname.replace(/\/+$/, '') || '/';
    var slug;
    if (path === '/api' || path === '/api.html') return '/api.html';
    if (path === '/dashboard' || path === '/dashboard.html') {
      slug = validOpenTarget(target.searchParams.get('open'));
      return '/dashboard.html' + (slug ? '?open=' + encodeURIComponent(slug) : '');
    }
    if (path === '/workflow' || path === '/workflow.html' || path === '/run' || path === '/run.html') {
      slug = validOpenTarget(target.searchParams.get('slug'));
      if (!slug) return '';
      return (path.indexOf('/run') === 0 ? '/run.html' : '/workflow.html') + '?slug=' + encodeURIComponent(slug);
    }
    return '';
  }

  function redirectTarget() {
    if (activeReturnTo) return activeReturnTo;
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
    var verificationCode = code.value.trim();
    var strategy = activeVerification && activeVerification.strategy;
    var codeValid = /^(?:email_code|phone_code|totp)$/.test(strategy || '')
      ? /^\d{6}$/.test(verificationCode)
      : verificationCode.length > 0;
    verifyButton.disabled = busy || !activeVerification || activeVerification.requiresCode === false || !codeValid;
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

  function setBackgroundInert(inert) {
    if (inert) {
      backgroundState = [];
      Array.prototype.forEach.call(document.body.children, function (element) {
        if (element === modal || element.tagName === 'SCRIPT') return;
        backgroundState.push({
          element: element,
          ariaHidden: element.getAttribute('aria-hidden'),
          inert: !!element.inert
        });
        element.setAttribute('aria-hidden', 'true');
        element.inert = true;
      });
      return;
    }
    backgroundState.forEach(function (state) {
      if (state.ariaHidden == null) state.element.removeAttribute('aria-hidden');
      else state.element.setAttribute('aria-hidden', state.ariaHidden);
      state.element.inert = state.inert;
    });
    backgroundState = [];
  }

  function open(nextMode, options) {
    lastFocused = document.activeElement;
    activeOpenTarget = validOpenTarget(options && options.open);
    activeDestination = options && options.destination === 'run' ? 'run' : '';
    activeReturnTo = validatedReturnTo(options && options.returnTo);
    setMode(nextMode || 'signup');
    activeVerification = null;
    formView.hidden = false;
    verificationView.hidden = true;
    if (modal.hidden) setBackgroundInert(true);
    modal.hidden = false;
    document.body.classList.add('auth-modal-open');
    window.requestAnimationFrame(function () {
      (mode === 'signup' ? firstName : email).focus();
    });
  }

  function close() {
    if (modal.hidden) return;
    modal.hidden = true;
    setBackgroundInert(false);
    document.body.classList.remove('auth-modal-open');
    setMessage(errorMessage, '');
    setMessage(verificationError, '');
    activeVerification = null;
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

  function verificationFactor(result) {
    var nextStep = result && result.nextStep;
    var nextVerification = nextStep && nextStep.verification;
    if (nextVerification && nextVerification.strategy) return nextVerification;

    var factors = (result && result.supportedSecondFactors) ||
      (nextStep && nextStep.supportedSecondFactors) || [];
    if (!Array.isArray(factors)) factors = [factors];
    var preferred = ['email_code', 'phone_code', 'totp', 'backup_code', 'email_link'];
    var normalized = factors.map(function (factor) {
      return typeof factor === 'string' ? { strategy: factor } : factor;
    }).filter(function (factor) { return factor && factor.strategy; });
    for (var index = 0; index < preferred.length; index += 1) {
      var match = normalized.filter(function (factor) { return factor.strategy === preferred[index]; })[0];
      if (match) return match;
    }
    return normalized[0] || null;
  }

  function readableStrategy(strategy) {
    var labels = {
      email_code: 'email code',
      phone_code: 'text-message code',
      totp: 'authenticator-app code',
      backup_code: 'backup code',
      email_link: 'email-link'
    };
    return labels[strategy] || String(strategy || 'additional').replace(/_/g, ' ');
  }

  function signInStateError(result) {
    var status = String((result && result.status) || 'unknown');
    var nextStep = result && result.nextStep;
    var factor = verificationFactor(result);
    var strategy = factor && factor.strategy;
    var description = nextStep && (nextStep.description || nextStep.message);
    if (!description && nextStep && nextStep.verification) {
      description = nextStep.verification.description || nextStep.verification.message;
    }
    var detail = description || (strategy ? readableStrategy(strategy) + ' verification' : 'Clerk status "' + status + '"');
    if (window.console && typeof window.console.error === 'function') {
      window.console.error('[Omo auth] Unhandled Clerk sign-in state', {
        status: status,
        strategy: strategy || null,
        resultKeys: result && typeof result === 'object' ? Object.keys(result) : [],
        nextStepKeys: nextStep && typeof nextStep === 'object' ? Object.keys(nextStep) : []
      });
    }
    var error = new Error('Sign-in is waiting for ' + detail + ' (status: ' + status + ').');
    error.code = 'sign_in_' + status;
    return error;
  }

  function setVerificationCopy(prefix, destination, suffix) {
    if (!verificationCopy) return;
    verificationCopy.textContent = prefix;
    if (destination) {
      var strong = document.createElement('strong');
      strong.id = 'auth-verification-email';
      strong.textContent = destination;
      verificationCopy.appendChild(strong);
      verificationEmail = strong;
    }
    if (suffix) verificationCopy.appendChild(document.createTextNode(suffix));
  }

  function showVerificationView(details) {
    var strategy = details.strategy || 'verification_code';
    var destination = details.destination || '';
    var requiresCode = strategy !== 'email_link';
    activeVerification = {
      kind: details.kind,
      strategy: strategy,
      factor: details.factor || { strategy: strategy },
      controller: details.controller,
      signIn: details.signIn || null,
      requiresCode: requiresCode
    };

    verificationTitle.textContent = 'Verify your account';
    codeLabel.textContent = 'Verification code';
    verifyButton.textContent = 'Verify';
    verifyButton.dataset.defaultLabel = 'Verify';
    code.inputMode = 'text';
    code.minLength = 1;
    code.maxLength = 128;
    code.parentNode.hidden = !requiresCode;
    verifyButton.hidden = !requiresCode;
    resendRow.hidden = !/^(?:email_code|phone_code|email_link)$/.test(strategy);

    if (strategy === 'email_code') {
      verificationTitle.textContent = 'Check your email';
      setVerificationCopy('Enter the verification code sent to ', destination || email.value.trim(), '.');
      codeLabel.textContent = 'Email verification code';
      verifyButton.textContent = 'Verify email';
      verifyButton.dataset.defaultLabel = 'Verify email';
      code.inputMode = 'numeric';
      code.minLength = 6;
      code.maxLength = 6;
    } else if (strategy === 'phone_code') {
      verificationTitle.textContent = 'Check your phone';
      setVerificationCopy(
        destination ? 'Enter the verification code sent by text message to ' : 'Enter the verification code sent by text message.',
        destination,
        destination ? '.' : ''
      );
      codeLabel.textContent = 'Text-message code';
      verifyButton.textContent = 'Verify phone';
      verifyButton.dataset.defaultLabel = 'Verify phone';
      code.inputMode = 'numeric';
      code.minLength = 6;
      code.maxLength = 6;
    } else if (strategy === 'totp') {
      setVerificationCopy('Enter the 6-digit code from your authenticator app.');
      codeLabel.textContent = 'Authenticator code';
      code.inputMode = 'numeric';
      code.minLength = 6;
      code.maxLength = 6;
    } else if (strategy === 'backup_code') {
      verificationTitle.textContent = 'Use a backup code';
      setVerificationCopy('Enter one of the backup codes saved for this account.');
      codeLabel.textContent = 'Backup code';
    } else if (strategy === 'email_link') {
      verificationTitle.textContent = 'Check your email';
      setVerificationCopy('Open the verification link sent to ', destination || email.value.trim(), '.');
    } else {
      setVerificationCopy('Enter the code required for ' + readableStrategy(strategy) + ' verification.');
    }

    formView.hidden = true;
    verificationView.hidden = false;
    card.setAttribute('aria-labelledby', 'auth-verification-title');
    card.removeAttribute('aria-describedby');
    code.value = '';
    setMessage(verificationError, '');
    updateValidity();
    (requiresCode ? code : resendButton).focus();
  }

  function methodOwner(primary, fallback, methodNames) {
    var candidates = [primary, fallback];
    for (var candidateIndex = 0; candidateIndex < candidates.length; candidateIndex += 1) {
      var candidate = candidates[candidateIndex];
      for (var methodIndex = 0; candidate && methodIndex < methodNames.length; methodIndex += 1) {
        if (typeof candidate[methodNames[methodIndex]] === 'function') {
          return { owner: candidate, method: candidate[methodNames[methodIndex]] };
        }
      }
    }
    return null;
  }

  function factorDestination(factor) {
    return factor.safeIdentifier || factor.emailAddress || factor.phoneNumber || '';
  }

  function prepareSignInVerification(signIn, result, factor) {
    var strategy = factor.strategy;
    if (!/^(?:email_code|phone_code|email_link)$/.test(strategy)) return Promise.resolve(result);
    var preparer = methodOwner(result, signIn, ['prepareSecondFactorVerification', 'prepareSecondFactor']);
    if (!preparer) return Promise.reject(new Error('Clerk could not prepare ' + readableStrategy(strategy) + ' verification.'));
    var params = { strategy: strategy };
    if (factor.emailAddressId) params.emailAddressId = factor.emailAddressId;
    if (factor.phoneNumberId) params.phoneNumberId = factor.phoneNumberId;
    try {
      return Promise.resolve(preparer.method.call(preparer.owner, params));
    } catch (error) {
      return Promise.reject(error);
    }
  }

  function finishSignIn(result) {
    close();
    return activateSession(result);
  }

  function handoffToClerk(result) {
    if (!window.Clerk || typeof window.Clerk.openSignIn !== 'function') throw signInStateError(result);
    var destination = new URL(redirectTarget(), window.location.href).href;
    close();
    window.Clerk.openSignIn({
      fallbackRedirectUrl: destination,
      signUpFallbackRedirectUrl: destination
    });
  }

  function handleSignInStatus(signIn, result) {
    if (result && result.status === 'complete') return finishSignIn(result);
    var status = result && result.status;
    if (status === 'needs_first_factor' || status === 'needs_new_password') {
      return handoffToClerk(result);
    }
    if (status === 'needs_verification' || status === 'needs_second_factor' || status === 'needs_client_trust') {
      var factor = verificationFactor(result);
      if (!factor) return handoffToClerk(result);
      return prepareSignInVerification(signIn, result, factor).then(function (prepared) {
        var controller = methodOwner(prepared, signIn, ['attemptSecondFactorVerification', 'attemptSecondFactor']);
        showVerificationView({
          kind: 'signin',
          strategy: factor.strategy,
          factor: factor,
          destination: factorDestination(factor),
          controller: controller,
          signIn: signIn
        });
      });
    }
    throw signInStateError(result);
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
          showVerificationView({
            kind: 'signup',
            strategy: 'email_code',
            destination: email.value.trim(),
            controller: signUp
          });
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
        return handleSignInStatus(signIn, result);
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
    var verification = activeVerification;
    if (!verification) {
      setMessage(verificationError, 'The verification session expired. Please close this popup and sign up again.');
      return;
    }

    var attempt;
    var params;
    if (verification.kind === 'signup') {
      var signUp = verification.controller || clerkSignUp();
      if (signUp && typeof signUp.attemptEmailAddressVerification === 'function') {
        attempt = { owner: signUp, method: signUp.attemptEmailAddressVerification };
        params = { code: code.value.trim() };
      }
    } else {
      attempt = verification.controller;
      params = { strategy: verification.strategy, code: code.value.trim() };
    }
    if (!attempt || typeof attempt.method !== 'function') {
      setMessage(verificationError, 'Clerk could not continue ' + readableStrategy(verification.strategy) + ' verification. Please close this popup and try again.');
      return;
    }

    verificationError.style.color = '';
    setMessage(verificationError, '');
    setBusy(true, verifyButton, 'Verifying…');
    Promise.resolve(attempt.method.call(attempt.owner, params)).then(function (result) {
      if (verification.kind === 'signin') return handleSignInStatus(attempt.owner, result);
      if (!result || result.status !== 'complete') throw new Error('Email verification is not complete yet.');
      return activateSession(result);
    }).catch(function (error) {
      setMessage(verificationError, friendlyError(error, 'verify'));
    }).finally(function () {
      setBusy(false, verifyButton, '');
    });
  }

  function resendCode() {
    var verification = activeVerification;
    if (!verification) return;
    resendButton.disabled = true;
    setMessage(verificationError, '');
    var request;
    if (verification.kind === 'signup') {
      var signUp = verification.controller || clerkSignUp();
      if (!signUp || typeof signUp.prepareEmailAddressVerification !== 'function') {
        request = Promise.reject(new Error('Clerk could not resend the email verification code.'));
      } else {
        request = signUp.prepareEmailAddressVerification({ strategy: 'email_code' });
      }
    } else {
      var factor = verification.factor || { strategy: verification.strategy };
      var controller = verification.signIn || (verification.controller && verification.controller.owner);
      request = prepareSignInVerification(controller, controller, factor);
    }
    Promise.resolve(request).then(function (prepared) {
      if (verification.kind === 'signin') {
        verification.signIn = prepared || verification.signIn;
        verification.controller = methodOwner(
          prepared,
          verification.signIn,
          ['attemptSecondFactorVerification', 'attemptSecondFactor']
        ) || verification.controller;
      }
      setMessage(verificationError, verification.strategy === 'email_link' ? 'A new verification link is on its way.' : 'A new code is on its way.');
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
    var canonicalOptions = {};
    try {
      var params = new URLSearchParams(window.location.search);
      requestedMode = params.get('mode') || params.get('auth') || '';
      hasOpenTarget = params.has('open');
      canonicalOptions = {
        returnTo: params.get('return_to') || '',
        open: params.get('open') || '',
        destination: params.get('destination') === 'run' ? 'run' : ''
      };
      if (document.referrer) {
        var referrer = new URL(document.referrer);
        cameFromOmoPage = referrer.origin === window.location.origin &&
          !/(^|\/)signup(?:\.html)?\/?$/.test(referrer.pathname);
      }
    } catch (error) {}
    var canonicalMode = requestedMode === 'login' || (!requestedMode && !hasOpenTarget && cameFromOmoPage) ? 'login' : 'signup';
    function continueCanonicalAuth() {
      activeOpenTarget = validOpenTarget(canonicalOptions.open);
      activeDestination = canonicalOptions.destination;
      activeReturnTo = validatedReturnTo(canonicalOptions.returnTo);
      if (window.ClerkAuth && window.ClerkAuth.isSignedIn && window.ClerkAuth.isSignedIn()) {
        redirectAfterAuth();
        return;
      }
      open(canonicalMode, canonicalOptions);
    }
    if (window.ClerkAuth && typeof window.ClerkAuth.ensureLoaded === 'function') {
      Promise.resolve(window.ClerkAuth.ensureLoaded()).then(continueCanonicalAuth, continueCanonicalAuth);
    } else {
      continueCanonicalAuth();
    }
  }
})();
