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
  var PAGE_SIZE = 50;
  var MAX_PAGES = 100;

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

  function formatDate(value, label) {
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) return label + ' time unavailable';
    try {
      return label + ' ' + new Intl.DateTimeFormat(undefined, {
        month: 'short', day: 'numeric', year: date.getFullYear() === new Date().getFullYear() ? undefined : 'numeric',
        hour: 'numeric', minute: '2-digit'
      }).format(date);
    } catch (error) {
      return label + ' ' + date.toLocaleString();
    }
  }

  function visibilityText(value) {
    return value === 'public' ? 'Marketplace' : 'Visibility unavailable';
  }

  function runtimeDecisionText(submission) {
    if (!submission.selected_runtime) return 'Runtime pending review';
    var runtime = submission.selected_runtime === 'worker-native' ? 'Worker native' : 'Modal hosted';
    return submission.runtime_policy
      ? runtime + ' · ' + String(submission.runtime_policy).replace(/[_:-]+/g, ' ')
      : runtime;
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

  function fetchSubmissionPage(token, cursor) {
    var path = '/api/submissions?limit=' + PAGE_SIZE;
    if (cursor) path += '&cursor=' + encodeURIComponent(cursor);
    return fetch(apiBase() + path, {
      method: 'GET',
      headers: { Authorization: 'Bearer ' + token, Accept: 'application/json' }
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (body) {
        if (!response.ok) {
          var error = new Error(body.message || body.error || 'Your submissions could not be loaded.');
          error.status = response.status;
          throw error;
        }
        return {
          submissions: Array.isArray(body.submissions) ? body.submissions : [],
          next_cursor: typeof body.next_cursor === 'string' && body.next_cursor ? body.next_cursor : null
        };
      });
    });
  }

  function fetchSubmissions() {
    return sessionToken().then(function (token) {
      var submissions = [];
      var seenCursors = new Set();
      function loadPage(cursor, pageNumber) {
        if (pageNumber >= MAX_PAGES) throw new Error('Your submission history is unusually large. Refresh and try again.');
        return fetchSubmissionPage(token, cursor).then(function (page) {
          submissions.push.apply(submissions, page.submissions);
          if (!page.next_cursor) return submissions;
          if (seenCursors.has(page.next_cursor)) throw new Error('Submission history pagination could not advance safely.');
          seenCursors.add(page.next_cursor);
          return loadPage(page.next_cursor, pageNumber + 1);
        });
      }
      return loadPage(null, 0);
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
      var slug = document.createElement('p');
      slug.className = 'submission-slug';
      slug.textContent = submission.slug;
      var meta = document.createElement('div');
      meta.className = 'submission-meta';
      var badge = document.createElement('span');
      badge.className = 'status-badge';
      badge.dataset.status = String(submission.status || '');
      badge.textContent = statusLabel(submission.status);
      var visibility = document.createElement('span');
      visibility.textContent = visibilityText(submission.visibility);
      var runtime = document.createElement('span');
      runtime.textContent = runtimeDecisionText(submission);
      var submitted = document.createElement('time');
      submitted.dateTime = submission.created_at || '';
      submitted.textContent = formatDate(submission.created_at, 'Submitted');
      var updated = document.createElement('time');
      updated.dateTime = submission.updated_at || '';
      updated.textContent = formatDate(submission.updated_at, 'Updated');
      meta.append(badge, visibility, runtime, submitted, updated);
      content.append(name, slug, meta);

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
