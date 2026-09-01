/* submission.js — authenticated owner-only submission progress. */
(function () {
  'use strict';

  var SUBMISSION_ID_RE = /^sub_[A-Za-z0-9_-]{8,100}$/;
  var NONTERMINAL_STATUSES = new Set(['queued', 'processing', 'ready_for_deploy', 'ready_for_publish']);
  var POLL_INTERVAL_MS = 5000;
  var STATUS_MODEL = {
    queued: {
      label: 'Queued', title: 'Queued for review', stage: 1,
      copy: 'Your upload is safely queued. It is not live; review must select a runtime before build gates can begin.'
    },
    needs_review: {
      label: 'Needs review', title: 'A review decision is needed', stage: 1,
      copy: 'Automated progress has paused at review. If an owner action is eligible, it appears beside the submission details.'
    },
    processing: {
      label: 'Building', title: 'Build and test gates are running', stage: 2,
      copy: 'The reviewed source is being compiled and checked. A successful build is still not a live workflow.'
    },
    ready_for_deploy: {
      label: 'Build ready', title: 'Build complete — release gates are next', stage: 3,
      copy: 'Build and canary evidence is complete. Merge, deployment, publication, and promotion checks still have to pass.'
    },
    ready_for_publish: {
      label: 'Release ready', title: 'Ready for final publishing gates', stage: 3,
      copy: 'The release is ready for final verification and promotion. The workflow is not live yet.'
    },
    failed: {
      label: 'Needs attention', title: 'A gate did not pass', stage: 2,
      copy: 'Progress stopped safely. Nothing was published. An eligible reviewed build may be retried from this page.'
    },
    deployed: {
      label: 'Live', title: 'Your workflow is deployed', stage: 4,
      copy: 'Every required gate passed and the published workflow is now live.'
    }
  };

  var statePanel = document.getElementById('submission-state');
  var stateTitle = document.getElementById('state-title');
  var stateCopy = document.getElementById('state-copy');
  var stateActions = document.getElementById('state-actions');
  var detailPanel = document.getElementById('submission-detail');
  var refreshButton = document.getElementById('refresh-submission');
  var refreshNote = document.getElementById('refresh-note');
  var actions = document.getElementById('submission-actions');
  var actionError = document.getElementById('action-error');
  var pollTimer = null;
  var loadSequence = 0;
  var submissionId = new URLSearchParams(window.location.search).get('id') || '';

  if (!statePanel || !detailPanel || !refreshButton) return;

  function isValidSubmissionId(id) {
    return SUBMISSION_ID_RE.test(String(id || ''));
  }

  function apiBase() {
    return String(window.OMO_API_BASE || '').replace(/\/+$/, '');
  }

  function clearChildren(element) {
    if (element) element.replaceChildren();
  }

  function makeButton(label, className, handler) {
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'button ' + className;
    button.textContent = label;
    button.addEventListener('click', handler);
    return button;
  }

  function showState(title, copy, options) {
    stopPolling();
    stateTitle.textContent = title;
    stateCopy.textContent = copy;
    clearChildren(stateActions);
    detailPanel.hidden = true;
    statePanel.hidden = false;
    refreshButton.hidden = !!(options && options.hideRefresh);
    refreshButton.disabled = false;
    refreshNote.textContent = '';
  }

  function renderInvalidId() {
    showState(
      'This submission link is not valid.',
      'Open a submission from your private submissions list instead of editing the address.',
      { hideRefresh: true }
    );
    var back = document.createElement('a');
    back.className = 'button button-primary';
    back.href = 'submissions.html';
    back.textContent = 'Back to all submissions';
    stateActions.appendChild(back);
  }

  function renderSignedOut() {
    showState('Sign in to view this submission.', 'Submission progress is private and available only to its owner.', { hideRefresh: true });
    stateActions.appendChild(makeButton('Sign in', 'button-primary', function () {
      if (window.ClerkAuth && typeof window.ClerkAuth.signIn === 'function') window.ClerkAuth.signIn();
    }));
    var back = document.createElement('a');
    back.className = 'button button-secondary';
    back.href = 'submissions.html';
    back.textContent = 'All submissions';
    stateActions.appendChild(back);
  }

  function renderLoadError(kind) {
    if (kind === 'not_found') {
      showState('This submission was not found in your account.', 'It may not exist, or it belongs to a different signed-in account.', { hideRefresh: false });
      return;
    }
    if (kind === 'signed_out') {
      renderSignedOut();
      return;
    }
    showState('We could not load this submission.', 'Your private data was not displayed. Refresh the status or try again shortly.', { hideRefresh: false });
  }

  function ensureAuthenticated() {
    if (!window.ClerkAuth || typeof window.ClerkAuth.ensureLoaded !== 'function') {
      return Promise.reject({ kind: 'unavailable' });
    }
    return Promise.resolve(window.ClerkAuth.ensureLoaded()).then(function () {
      if (!window.ClerkAuth.isSignedIn()) throw { kind: 'signed_out' };
      return true;
    });
  }

  function sessionToken() {
    if (!window.Clerk || !window.Clerk.session || typeof window.Clerk.session.getToken !== 'function') {
      return Promise.reject({ kind: 'signed_out' });
    }
    return Promise.resolve(window.Clerk.session.getToken()).then(function (token) {
      if (!token) throw { kind: 'signed_out' };
      return token;
    });
  }

  function parseResponse(response, fallback) {
    return response.json().catch(function () { return {}; }).then(function (body) {
      if (response.ok) return body;
      if (response.status === 401 || response.status === 403) throw { kind: 'signed_out' };
      if (response.status === 404) throw { kind: 'not_found' };
      var error = new Error(fallback);
      error.kind = 'request_failed';
      throw error;
    });
  }

  function authenticatedRequest(path, options, fallback) {
    options = options || {};
    return sessionToken().then(function (token) {
      return fetch(apiBase() + path, {
        method: options.method || 'GET',
        headers: { Authorization: 'Bearer ' + token, Accept: 'application/json' }
      });
    }).then(function (response) {
      return parseResponse(response, fallback);
    });
  }

  function fetchSubmission() {
    return authenticatedRequest(
      '/api/submissions/' + encodeURIComponent(submissionId),
      { method: 'GET' },
      'Could not load this submission.'
    ).then(function (body) {
      if (!body.submission || body.submission.id !== submissionId) throw { kind: 'not_found' };
      return body.submission;
    });
  }

  function postAction(suffix, fallback) {
    return authenticatedRequest(
      '/api/submissions/' + encodeURIComponent(submissionId) + suffix,
      { method: 'POST' },
      fallback
    ).then(function (body) {
      return body.submission || null;
    });
  }

  function statusModel(status) {
    return STATUS_MODEL[status] || STATUS_MODEL.queued;
  }

  function formatDate(value) {
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Not available';
    try {
      return new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium', timeStyle: 'short'
      }).format(date);
    } catch (error) {
      return date.toLocaleString();
    }
  }

  function runtimeText(submission) {
    if (!submission.selected_runtime) return 'Runtime pending review';
    var runtime = submission.selected_runtime === 'worker-native' ? 'Worker native' : 'Modal hosted';
    if (!submission.runtime_policy) return runtime;
    return runtime + ' · ' + String(submission.runtime_policy).replace(/[_:-]+/g, ' ');
  }

  function visibilityText(value) {
    return value === 'public' ? 'Marketplace' : 'Visibility unavailable';
  }

  function requestedRuntimeText(value) {
    if (value === 'worker-native') return 'Worker native';
    if (value === 'modal-hosted') return 'Modal hosted';
    return 'Automatic selection';
  }

  function failureText(code) {
    var messages = {
      build_or_deploy_failed: 'The reviewed build or deploy gate failed.',
      canary_or_internal_failed: 'A canary or internal verification gate failed.',
      generated_source_hash_mismatch: 'Generated source identity did not match the reviewed upload.',
      source_identity_mismatch: 'Stored source identity did not match the reviewed upload.',
      profile_identity_mismatch: 'The reviewed profile identity did not match.',
      slug_collision: 'A workflow already uses this slug. Exact-source approval is required to continue.',
      reviewed_profile_required: 'A reviewed runtime profile is required before build gates can run.'
    };
    return messages[code] || 'A protected review or release gate did not pass.';
  }

  function timelineStage(submission) {
    if (submission.status === 'deployed') return 4;
    if (['ready_for_deploy', 'ready_for_publish'].includes(submission.status)) return 3;
    if (submission.status === 'processing') return 2;
    if (submission.status === 'failed') {
      if (submission.release && submission.release.phase) return 3;
      if (submission.build_evidence || submission.selected_runtime) return 2;
      return 1;
    }
    return 1;
  }

  function renderTimeline(submission) {
    var stage = timelineStage(submission);
    var steps = document.querySelectorAll('#submission-timeline [data-stage]');
    steps.forEach(function (step, index) {
      var failedHere = submission.status === 'failed' && index === stage;
      var actionHere = submission.status === 'needs_review' && index === stage;
      step.classList.toggle('is-done', index < stage || submission.status === 'deployed');
      step.classList.toggle('is-current', index === stage && !['failed', 'deployed', 'needs_review'].includes(submission.status));
      step.classList.toggle('is-failed', failedHere);
      step.classList.toggle('is-action', actionHere);
      var dot = step.querySelector('.timeline-dot');
      if (dot) dot.textContent = index < stage || submission.status === 'deployed' ? '✓' : failedHere || actionHere ? '!' : String(index + 1);
    });
  }

  function renderNotice(submission) {
    var notice = document.getElementById('status-notice');
    var title = document.getElementById('notice-title');
    var copy = document.getElementById('notice-copy');
    notice.classList.remove('is-error');
    if (submission.status === 'failed' || (submission.status === 'needs_review' && submission.failure_code)) {
      notice.hidden = false;
      notice.classList.toggle('is-error', submission.status === 'failed');
      title.textContent = submission.status === 'failed' ? 'Stopped safely' : 'Review note';
      copy.textContent = failureText(submission.failure_code);
      return;
    }
    if (!submission.selected_runtime && ['queued', 'needs_review'].includes(submission.status)) {
      notice.hidden = false;
      title.textContent = 'Runtime pending review';
      copy.textContent = 'No runtime has been selected yet. This is expected until an Omo agent completes the runtime review.';
      return;
    }
    notice.hidden = true;
    title.textContent = '';
    copy.textContent = '';
  }

  function isApprovalEligible(submission) {
    return !!(submission && submission.status === 'needs_review' &&
      submission.failure_code === 'slug_collision' && isValidSubmissionId(submission.id));
  }

  function isRetryEligible(submission) {
    var retryableFailureCodes = ['build_or_deploy_failed', 'canary_or_internal_failed', 'profile_identity_mismatch'];
    var preRuntimeCanary = retryableFailureCodes.includes(submission.failure_code) &&
      !submission.selected_runtime && !submission.runtime_policy;
    var reviewedRuntime = submission.selected_runtime === 'worker-native' || submission.selected_runtime === 'modal-hosted';
    return !!(submission.status === 'failed' && retryableFailureCodes.includes(submission.failure_code) &&
      (preRuntimeCanary || reviewedRuntime) && /^[a-f0-9]{64}$/.test(String(submission.source_sha256 || '')) &&
      isValidSubmissionId(submission.id));
  }

  function setActionError(message) {
    actionError.textContent = message || '';
    actionError.hidden = !message;
  }

  function runAction(button, pendingLabel, suffix, fallback) {
    button.disabled = true;
    var originalLabel = button.textContent;
    button.textContent = pendingLabel;
    setActionError('');
    stopPolling();
    return postAction(suffix, fallback).then(function (submission) {
      if (submission) renderSubmission(submission);
      return loadSubmission({ manual: true });
    }).catch(function (error) {
      if (error && (error.kind === 'signed_out' || error.kind === 'not_found')) {
        renderLoadError(error.kind);
        return;
      }
      setActionError(fallback);
    }).finally(function () {
      button.disabled = false;
      button.textContent = originalLabel;
    });
  }

  function renderActions(submission) {
    clearChildren(actions);
    setActionError('');
    if (isApprovalEligible(submission)) {
      var approve = makeButton('Approve exact-match update', 'button-accent', function () {
        var confirmed = window.confirm('Approval sends it back through build/test/deploy gates and does not instantly publish. Continue?');
        if (!confirmed) return;
        runAction(approve, 'Approving…', '/approve', 'Could not approve this submission.');
      });
      actions.appendChild(approve);
      var approvalCopy = document.createElement('p');
      approvalCopy.className = 'action-copy';
      approvalCopy.textContent = 'Approval re-enters gated build checks; it does not publish immediately.';
      actions.appendChild(approvalCopy);
    }
    if (isRetryEligible(submission)) {
      var retry = makeButton('Retry gated build', 'button-accent', function () {
        var confirmed = window.confirm('Retry this reviewed gated build? This does not publish or change the selected runtime.');
        if (!confirmed) return;
        runAction(retry, 'Retrying…', '/retry', 'Could not retry this submission.');
      });
      actions.appendChild(retry);
      var retryCopy = document.createElement('p');
      retryCopy.className = 'action-copy';
      retryCopy.textContent = 'Retry uses the same reviewed source and runtime decision.';
      actions.appendChild(retryCopy);
    }
    if (submission.status === 'deployed' && submission.published_slug) {
      var liveLink = document.createElement('a');
      liveLink.className = 'button button-primary';
      liveLink.href = 'run.html?slug=' + encodeURIComponent(submission.published_slug);
      liveLink.textContent = 'Open live workflow';
      actions.appendChild(liveLink);
    }
  }

  function renderSubmission(submission) {
    var model = statusModel(submission.status);
    document.getElementById('page-title').textContent = submission.name || 'Submission progress';
    document.getElementById('status-title').textContent = model.title;
    document.getElementById('status-badge').textContent = model.label;
    document.getElementById('status-copy').textContent = model.copy;
    document.getElementById('detail-id').textContent = submission.id;
    document.getElementById('detail-slug').textContent = submission.slug;
    document.getElementById('detail-visibility').textContent = visibilityText(submission.visibility);
    document.getElementById('detail-runtime').textContent = runtimeText(submission);
    document.getElementById('detail-requested').textContent = requestedRuntimeText(submission.requested_runtime);
    document.getElementById('detail-created').textContent = formatDate(submission.created_at);
    document.getElementById('detail-updated').textContent = formatDate(submission.updated_at);
    renderTimeline(submission);
    renderNotice(submission);
    renderActions(submission);
    statePanel.hidden = true;
    detailPanel.hidden = false;
    refreshButton.hidden = false;
    refreshButton.disabled = false;
    refreshNote.textContent = 'Checked ' + formatDate(new Date().toISOString()) + '.';
    if (NONTERMINAL_STATUSES.has(submission.status)) {
      schedulePoll();
    } else {
      stopPolling();
    }
  }

  function stopPolling() {
    if (pollTimer !== null) {
      window.clearTimeout(pollTimer);
      pollTimer = null;
    }
  }

  function schedulePoll() {
    stopPolling();
    pollTimer = window.setTimeout(function () {
      pollTimer = null;
      loadSubmission({ quiet: true });
    }, POLL_INTERVAL_MS);
  }

  function loadSubmission(options) {
    options = options || {};
    var sequence = ++loadSequence;
    if (!options.quiet) {
      refreshButton.disabled = true;
      refreshNote.textContent = options.manual ? 'Refreshing…' : '';
    }
    return fetchSubmission().then(function (submission) {
      if (sequence !== loadSequence) return;
      renderSubmission(submission);
    }).catch(function (error) {
      if (sequence !== loadSequence) return;
      if (options.quiet && error && error.kind === 'request_failed') {
        refreshNote.textContent = 'Live update paused. Use Refresh status to try again.';
        stopPolling();
        return;
      }
      renderLoadError(error && error.kind);
    }).finally(function () {
      if (sequence === loadSequence) refreshButton.disabled = false;
    });
  }

  refreshButton.addEventListener('click', function () {
    stopPolling();
    ensureAuthenticated().then(function () {
      return loadSubmission({ manual: true });
    }).catch(function (error) {
      renderLoadError(error && error.kind);
    });
  });

  if (!isValidSubmissionId(submissionId)) {
    renderInvalidId();
    return;
  }

  ensureAuthenticated().then(function () {
    return loadSubmission();
  }).catch(function (error) {
    renderLoadError(error && error.kind);
  });
})();
