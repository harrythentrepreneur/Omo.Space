/* submissions.js — authenticated owner view of all hosted workflow submissions. */
(function () {
  'use strict';

  var states = {
    loading: document.getElementById('submissions-loading'),
    'signed-out': document.getElementById('submissions-signed-out'),
    empty: document.getElementById('submissions-empty'),
    error: document.getElementById('submissions-error'),
    populated: document.getElementById('submissions-list')
  };
  var list = states.populated;
  var retryButton = document.getElementById('submissions-retry');
  var signInButton = document.getElementById('submissions-sign-in');
  var errorMessage = document.getElementById('submissions-error-message');
  var requestId = 0;

  if (!list) return;

  function apiBase() {
    return String(window.OMO_API_BASE || '').replace(/\/+$/, '');
  }

  function showState(name) {
    Object.keys(states).forEach(function (key) {
      if (states[key]) states[key].hidden = key !== name;
    });
  }

  function statusLabel(status) {
    var labels = {
      queued: 'Queued',
      processing: 'Processing',
      needs_review: 'Needs review',
      ready_for_deploy: 'Ready to deploy',
      ready_for_publish: 'Ready to publish',
      deployed: 'Live',
      failed: 'Needs attention'
    };
    return labels[status] || 'Submitted';
  }

  function formatDate(value) {
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Recently updated';
    try {
      return 'Updated ' + new Intl.DateTimeFormat(undefined, {
        month: 'short', day: 'numeric', year: date.getFullYear() === new Date().getFullYear() ? undefined : 'numeric'
      }).format(date);
    } catch (error) {
      return 'Recently updated';
    }
  }

  function sessionToken() {
    if (!window.Clerk || !window.Clerk.session || typeof window.Clerk.session.getToken !== 'function') {
      return Promise.reject(new Error('Your verified sign-in session is unavailable.'));
    }
    return Promise.resolve(window.Clerk.session.getToken()).then(function (token) {
      if (!token) throw new Error('Your sign-in session expired. Sign in again.');
      return token;
    });
  }

  function fetchSubmissions() {
    return sessionToken().then(function (token) {
      return fetch(apiBase() + '/api/submissions?limit=20', {
        method: 'GET',
        headers: { Authorization: 'Bearer ' + token, Accept: 'application/json' }
      });
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (body) {
        if (!response.ok) {
          var error = new Error(body.message || body.error || 'Your submissions could not be loaded.');
          error.status = response.status;
          throw error;
        }
        return Array.isArray(body.submissions) ? body.submissions : [];
      });
    });
  }

  function renderSubmissions(submissions) {
    list.replaceChildren();
    submissions.forEach(function (submission) {
      if (!submission || typeof submission.id !== 'string' || typeof submission.name !== 'string') return;

      var row = document.createElement('li');
      row.className = 'submission-row';
      var link = document.createElement('a');
      link.className = 'submission-link';
      link.href = 'submission.html?id=' + encodeURIComponent(submission.id);

      var content = document.createElement('div');
      var name = document.createElement('p');
      name.className = 'submission-name';
      name.textContent = submission.name;
      var meta = document.createElement('div');
      meta.className = 'submission-meta';
      var badge = document.createElement('span');
      badge.className = 'status-badge';
      badge.dataset.status = String(submission.status || '');
      badge.textContent = statusLabel(submission.status);
      var updated = document.createElement('time');
      updated.dateTime = submission.updated_at || submission.created_at || '';
      updated.textContent = formatDate(submission.updated_at || submission.created_at);
      meta.append(badge, updated);
      content.append(name, meta);

      var arrow = document.createElement('span');
      arrow.className = 'row-arrow';
      arrow.setAttribute('aria-hidden', 'true');
      arrow.textContent = '→';
      link.append(content, arrow);
      row.appendChild(link);
      list.appendChild(row);
    });

    if (list.childNodes.length) {
      showState('populated');
    } else {
      showState('empty');
    }
  }

  function loadSubmissions() {
    var activeRequest = ++requestId;
    showState('loading');
    return fetchSubmissions().then(function (submissions) {
      if (activeRequest !== requestId) return;
      if (!submissions.length) {
        list.replaceChildren();
        showState('empty');
        return;
      }
      renderSubmissions(submissions);
    }).catch(function (error) {
      if (activeRequest !== requestId) return;
      if (error && error.status === 401) {
        showState('signed-out');
        return;
      }
      errorMessage.textContent = error && error.message || 'Your submissions are safe. Try loading them again.';
      showState('error');
    });
  }

  function resolveAuth() {
    requestId += 1;
    showState('loading');
    if (!window.ClerkAuth || typeof window.ClerkAuth.ensureLoaded !== 'function') {
      errorMessage.textContent = 'Sign-in could not start. Refresh the page and try again.';
      showState('error');
      return Promise.resolve();
    }
    return Promise.resolve(window.ClerkAuth.ensureLoaded()).then(function () {
      if (!window.ClerkAuth.isSignedIn()) {
        showState('signed-out');
        return;
      }
      return loadSubmissions();
    }).catch(function () {
      errorMessage.textContent = 'Sign-in could not start. Refresh the page and try again.';
      showState('error');
    });
  }

  retryButton.addEventListener('click', resolveAuth);
  signInButton.addEventListener('click', function () {
    if (window.ClerkAuth && typeof window.ClerkAuth.signIn === 'function') window.ClerkAuth.signIn();
  });
  if (window.ClerkAuth && typeof window.ClerkAuth.onAuthChange === 'function') {
    window.ClerkAuth.onAuthChange(resolveAuth);
  }
  resolveAuth();
})();
