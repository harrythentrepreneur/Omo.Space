(function () {
  'use strict';

  var API_BASE = (window.OMO_API_BASE || '').replace(/\/+$/, '');
  var SESSION_KEY = 'omo_support_session_v1';
  var signInPanel = document.getElementById('support-signin');
  var signInButton = document.getElementById('support-signin-button');
  var app = document.getElementById('support-chat-app');
  var messages = document.getElementById('support-messages');
  var form = document.getElementById('support-form');
  var input = document.getElementById('support-input');
  var send = document.getElementById('support-send');
  var status = document.getElementById('support-status');

  function randomSession() {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
      return 'support_' + window.crypto.randomUUID().replace(/-/g, '');
    }
    return 'support_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 18);
  }

  function sessionId() {
    var existing = '';
    try { existing = localStorage.getItem(SESSION_KEY) || ''; } catch (error) {}
    if (/^[A-Za-z0-9_-]{8,100}$/.test(existing)) return existing;
    var created = randomSession();
    try { localStorage.setItem(SESSION_KEY, created); } catch (error) {}
    return created;
  }

  function addMessage(text, role) {
    var bubble = document.createElement('div');
    bubble.className = 'support-message support-message-' + role;
    bubble.textContent = text;
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
  }

  function isSignedIn() {
    return !!(window.ClerkAuth && typeof window.ClerkAuth.isSignedIn === 'function' && window.ClerkAuth.isSignedIn());
  }

  function updateAuthState() {
    signInPanel.hidden = true;
    app.hidden = false;
    if (!messages.childElementCount) {
      addMessage('Hi — I’m Omo Support Hermes. Tell me what is stuck, and include a run or submission ID if you have one.', 'agent');
    }
  }

  function token() {
    if (!window.Clerk || !window.Clerk.session || typeof window.Clerk.session.getToken !== 'function') {
      return Promise.resolve('');
    }
    return Promise.resolve(window.Clerk.session.getToken()).then(function (value) {
      return value || '';
    });
  }

  function submitMessage(message) {
    return token().then(function (bearer) {
      var headers = {
        'Content-Type': 'application/json',
        Accept: 'application/json'
      };
      if (bearer) headers.Authorization = 'Bearer ' + bearer;
      return fetch(API_BASE + '/api/support/chat', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
          session_id: sessionId(),
          message: message,
          context: 'Page: ' + window.location.pathname + '; title: ' + document.title
        })
      });
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (body) {
        if (!response.ok) {
          var labels = {
            support_not_configured: 'Support chat is still being connected.',
            support_unavailable: 'Support Hermes is temporarily unavailable.',
            invalid_support_message: 'That message could not be sent.',
            authentication_required: 'Your session expired. Sign in again.'
          };
          throw new Error(labels[body.error] || 'Support Hermes could not reply.');
        }
        if (!body || body.profile !== 'omo-support' || typeof body.message !== 'string') {
          throw new Error('The support service returned an invalid response.');
        }
        return body;
      });
    });
  }

  signInButton.addEventListener('click', function () {
    if (window.ClerkAuth && typeof window.ClerkAuth.signIn === 'function') window.ClerkAuth.signIn();
  });

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var message = input.value.trim();
    if (!message || message.length > 8000 || send.disabled) return;
    addMessage(message, 'user');
    input.value = '';
    send.disabled = true;
    status.textContent = 'Omo Support Hermes is checking…';
    submitMessage(message).then(function (body) {
      addMessage(body.message, 'agent');
      status.textContent = 'Private support session';
    }).catch(function (error) {
      addMessage(error && error.message || 'Support Hermes could not reply.', 'agent');
      status.textContent = 'Not sent';
    }).finally(function () {
      send.disabled = false;
      input.focus();
    });
  });

  if (window.ClerkAuth && typeof window.ClerkAuth.ensureLoaded === 'function') {
    Promise.resolve(window.ClerkAuth.ensureLoaded()).then(updateAuthState).catch(updateAuthState);
  } else {
    updateAuthState();
  }
  if (window.ClerkAuth && typeof window.ClerkAuth.onAuthChange === 'function') {
    window.ClerkAuth.onAuthChange(updateAuthState);
  }
}());
