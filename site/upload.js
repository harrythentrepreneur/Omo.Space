/* upload.js — authenticated creator Markdown intake for Omo hosting. */
(function () {
  'use strict';

  var STORAGE_KEY = 'omo_hosting_preview_v2';
  var MAX_BYTES = 200 * 1024;
  var form = document.getElementById('upload-form');
  var fileInput = document.getElementById('skill-file');
  var fileName = document.getElementById('file-name');
  var fileError = document.getElementById('file-error');
  var nameInput = document.getElementById('workflow-name');
  var dropZone = document.getElementById('drop-zone');
  var progress = document.getElementById('upload-progress');
  var hostedList = document.getElementById('hosted-list');
  var hostedEmpty = document.getElementById('hosted-empty');
  var submitButton = document.getElementById('upload-submit');
  var selectedFile = null;

  if (!form || !fileInput || !nameInput) return;

  function apiBase() {
    return String(window.OMO_API_BASE || '').replace(/\/+$/, '');
  }

  function isFilePreview() {
    return !!(window.location && window.location.protocol === 'file:');
  }

  function readSubmissionIds() {
    try {
      var saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      return Array.isArray(saved) ? saved.filter(function (id) {
        return typeof id === 'string' && /^sub_[A-Za-z0-9_-]{8,100}$/.test(id);
      }) : [];
    } catch (error) {
      return [];
    }
  }

  function writeSubmissionIds(ids) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
      return true;
    } catch (error) {
      return false;
    }
  }

  function formatDate(isoDate) {
    var date = new Date(isoDate);
    if (Number.isNaN(date.getTime())) return 'Just now';
    try {
      return new Intl.DateTimeFormat(undefined, {
        month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
      }).format(date);
    } catch (error) {
      return 'Just now';
    }
  }

  function statusLabel(status) {
    var labels = {
      queued: 'Queued',
      processing: 'Processing',
      needs_review: 'Needs review',
      ready_for_deploy: 'Ready to deploy',
      ready_for_publish: 'Ready to publish',
      deployed: 'Live',
      failed: 'Needs attention',
      local_waiting: 'Waiting locally',
      demo_queued: 'Demo queue'
    };
    return labels[status] || 'Submitted';
  }

  function runtimeDecisionText(submission) {
    if (!submission || !submission.selected_runtime) return 'Runtime pending review';
    var label = submission.selected_runtime === 'worker-native' ? 'Worker native' : 'Modal hosted';
    return submission.runtime_policy ? label + ' · ' + submission.runtime_policy.replace(/[_:-]+/g, ' ') : label;
  }

  function failureReasonText(submission) {
    if (!submission || submission.status !== 'failed' || !submission.failure_code) return '';
    var labels = {
      build_or_deploy_failed: 'Build/deploy failed after owner approval.',
      generated_source_hash_mismatch: 'Generated source hash did not match the reviewed upload.',
      source_identity_mismatch: 'Stored source identity did not match the reviewed upload.',
      canary_or_internal_failed: 'The canary or internal review gate failed.',
      slug_collision: 'A workflow with this slug already exists.',
      reviewed_profile_required: 'A reviewed profile is required before build gates can run.'
    };
    return labels[submission.failure_code] || 'The review gate failed.';
  }

  function renderSubmissions(submissions) {
    if (!hostedList || !hostedEmpty) return;
    submissions = Array.isArray(submissions) ? submissions : [];
    hostedList.replaceChildren();
    hostedEmpty.hidden = submissions.length > 0;

    submissions.forEach(function (submission) {
      if (!submission || typeof submission.name !== 'string') return;
      var item = document.createElement('li');
      item.className = 'hosted-item';
      var title = document.createElement('p');
      title.className = 'hosted-name';
      title.textContent = submission.name;
      var meta = document.createElement('div');
      meta.className = 'hosted-meta';
      var status = document.createElement('span');
      status.className = 'status-badge';
      status.textContent = statusLabel(submission.status);
      var visibility = document.createElement('span');
      visibility.className = 'visibility-badge';
      visibility.textContent = submission.localOnly ? 'Local receipt' : 'Marketplace';
      var date = document.createElement('time');
      date.dateTime = submission.created_at || '';
      date.textContent = formatDate(submission.created_at);
      meta.append(status, visibility, date);
      var runtime = document.createElement('p');
      runtime.className = 'hosted-runtime';
      runtime.textContent = runtimeDecisionText(submission);
      item.append(title, meta);
      item.appendChild(runtime);
      var failureReason = failureReasonText(submission);
      if (failureReason) {
        var failure = document.createElement('p');
        failure.className = 'approval-error';
        failure.textContent = failureReason;
        item.appendChild(failure);
      }
      var releaseLinks = renderReleaseLinks(submission);
      if (releaseLinks) item.appendChild(releaseLinks);
      var approvalPanel = renderApprovalPanel(submission);
      if (approvalPanel) item.appendChild(approvalPanel);
      var retryPanel = renderRetryPanel(submission);
      if (retryPanel) item.appendChild(retryPanel);
      if (submission.status === 'deployed' && submission.published_slug) {
        var open = document.createElement('a');
        open.className = 'button button-accent hosted-open';
        open.href = 'workflow.html?slug=' + encodeURIComponent(submission.published_slug);
        open.textContent = 'Open workflow';
        item.appendChild(open);
      }
      hostedList.appendChild(item);
    });
  }

  function renderReleaseLinks(submission) {
    if (!submission || !submission.release) return null;
    var release = submission.release;
    var panel = document.createElement('div');
    panel.className = 'hosted-release';
    var phase = document.createElement('p');
    phase.className = 'hosted-runtime';
    var phaseText = String(release.phase || '').replace(/[_:-]+/g, ' ');
    phase.textContent = phaseText ? 'Release: ' + phaseText : 'Release pending';
    panel.appendChild(phase);
    var links = document.createElement('div');
    links.className = 'hosted-meta';
    if (submission.release.issue_url) {
      links.appendChild(releaseAnchor(submission.release.issue_url, 'Issue'));
    }
    if (submission.release.pr_url) {
      links.appendChild(releaseAnchor(submission.release.pr_url, 'PR'));
    }
    if (submission.release.merge_sha) {
      var merge = document.createElement('span');
      merge.className = 'visibility-badge';
      merge.textContent = 'main ' + String(submission.release.merge_sha).slice(0, 7);
      links.appendChild(merge);
    }
    if (links.childNodes.length) panel.appendChild(links);
    return panel;
  }

  function releaseAnchor(href, label) {
    var anchor = document.createElement('a');
    anchor.className = 'visibility-badge';
    anchor.href = href;
    anchor.target = '_blank';
    anchor.rel = 'noopener noreferrer';
    anchor.textContent = label;
    return anchor;
  }

  function friendlyName(rawName) {
    return rawName.replace(/\.md$/i, '').replace(/[-_]+/g, ' ').replace(/\s+/g, ' ').trim()
      .replace(/^\w/, function (letter) { return letter.toUpperCase(); });
  }

  function submissionNameFromMarkdown(content) {
    var lines = String(content || '').split(/\r?\n/);
    if (!lines.length || lines[0].trim() !== '---') return '';
    for (var index = 1; index < lines.length; index += 1) {
      if (lines[index].trim() === '---') break;
      var match = /^name:\s*(.*?)\s*$/.exec(lines[index]);
      if (!match || !match[1] || match[1] === '|' || match[1] === '>') continue;
      return match[1].replace(/^(?:"([\s\S]*)"|'([\s\S]*)')$/, function (_all, double, single) {
        return double == null ? single : double;
      }).trim().slice(0, 120);
    }
    return '';
  }

  function setSelectedFile(file) {
    selectedFile = file || null;
    fileError.textContent = '';
    if (!selectedFile) {
      fileName.textContent = 'No file chosen yet';
      return;
    }
    fileName.textContent = selectedFile.name + ' · ' + Math.ceil(selectedFile.size / 1024) + ' KB';
    if (!nameInput.value.trim()) nameInput.value = friendlyName(selectedFile.name);
  }

  function isMarkdownFile(file) {
    return !!(file && /\.md$/i.test(file.name || ''));
  }

  function updateProgress(submission, mode) {
    var preview = mode === 'preview';
    var waiting = mode === 'waiting';
    var status = submission && submission.status || 'queued';
    var steps = progress.querySelectorAll('[data-progress-step]');
    var labels = waiting ? [
      'File checked locally',
      'Secure queue activation pending',
      'Agent review after queueing',
      'Tests + canaries after approval',
      'Publish after every gate passes'
    ] : status === 'deployed' ? [
      'Upload received',
      'Queued for review',
      'Build gates passed',
      'Publish gate passed',
      'Workflow deployed'
    ] : status === 'ready_for_publish' ? [
      'Upload received',
      'Queued for review',
      'Build gates passed',
      'Ready for publish approval',
      'Workflow not live yet'
    ] : status === 'ready_for_deploy' ? [
      'Upload received',
      'Queued for review',
      'Build gates running',
      'Ready for deployment gate',
      'Workflow not live yet'
    ] : [
      'Upload received',
      'Queued for review',
      'Build gates running',
      'Publish gate after approval',
      'Publish after every gate passes'
    ];
    var currentIndex = status === 'deployed' ? 4 : status === 'ready_for_publish' ? 3 : status === 'ready_for_deploy' ? 2 : 1;
    steps.forEach(function (step, index) {
      step.classList.toggle('is-done', index < currentIndex || status === 'deployed');
      step.classList.toggle('is-current', index === currentIndex && status !== 'deployed');
      var label = step.querySelector('span:last-child');
      var dot = step.querySelector('.progress-dot');
      if (label) label.textContent = labels[index];
      if (dot) dot.textContent = index < currentIndex || status === 'deployed' ? '✓' : String(index + 1);
    });
    var title = progress.querySelector('.progress-title');
    var note = progress.querySelector('.progress-demo');
    if (title) title.textContent = preview
      ? 'Demo submission queued locally.'
      : waiting ? 'Saved here to retry.' : statusLabel(status) + '.';
    if (note) note.textContent = preview
      ? 'Local preview only — no file left this browser. Production submissions are stored securely for agent review.'
      : waiting
        ? 'The secure queue is still activating. This browser saved only the workflow name — not the Markdown. Keep the file and retry later.'
        : runtimeDecisionText(submission) + '. Live access appears only after deployment.';
    progress.hidden = false;
    progress.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function rememberSubmissionId(id) {
    if (!/^sub_[A-Za-z0-9_-]{8,100}$/.test(String(id || ''))) return;
    var ids = readSubmissionIds().filter(function (saved) { return saved !== id; });
    ids.push(id);
    writeSubmissionIds(ids.slice(-20));
  }

  function fetchJsonWithAuth(path) {
    return sessionToken().then(function (token) {
      return fetch(apiBase() + path, {
        method: 'GET',
        headers: { Authorization: 'Bearer ' + token, Accept: 'application/json' }
      });
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (body) {
        if (!response.ok) throw new Error(body.message || body.error || 'Could not load submission status.');
        return body;
      });
    });
  }

  function fetchSubmissions() {
    return fetchJsonWithAuth('/api/submissions?limit=20').then(function (body) {
      return Array.isArray(body.submissions) ? body.submissions : [];
    });
  }

  function fetchSubmissionDetail(id) {
    return fetchJsonWithAuth('/api/submissions/' + encodeURIComponent(id)).then(function (body) {
      return body.submission || null;
    });
  }

  function postApproval(submission) {
    return sessionToken().then(function (token) {
      return fetch(apiBase() + '/api/submissions/' + encodeURIComponent(submission.id) + '/approve', {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + token, Accept: 'application/json' }
      });
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (body) {
        if (!response.ok) throw new Error(body.message || body.error || 'Could not approve this submission.');
        return body.submission || null;
      });
    });
  }

  function postRetry(submission) {
    return sessionToken().then(function (token) {
      return fetch(apiBase() + '/api/submissions/' + encodeURIComponent(submission.id) + '/retry', {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + token, Accept: 'application/json' }
      });
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (body) {
        if (!response.ok) throw new Error(body.message || body.error || 'Could not retry this submission.');
        return body.submission || null;
      });
    });
  }

  function isApprovableCollision(submission) {
    return !!(submission &&
      submission.status === 'needs_review' &&
      submission.failure_code === 'slug_collision' &&
      /^sub_[A-Za-z0-9_-]{8,100}$/.test(String(submission.id || '')));
  }

  function isRetryableReviewedBuildFailure(submission) {
    var retryableFailureCodes = ['build_or_deploy_failed', 'canary_or_internal_failed', 'profile_identity_mismatch'];
    var preRuntimeCanary = !!(submission &&
      retryableFailureCodes.includes(submission.failure_code) && !submission.selected_runtime && !submission.runtime_policy);
    var reviewedRuntimeFailure = !!(submission &&
      (submission.selected_runtime === 'worker-native' || submission.selected_runtime === 'modal-hosted'));
    return !!(submission &&
      submission.status === 'failed' &&
      retryableFailureCodes.includes(submission.failure_code) &&
      (preRuntimeCanary || reviewedRuntimeFailure) &&
      /^[a-f0-9]{64}$/.test(String(submission.source_sha256 || '')) &&
      /^sub_[A-Za-z0-9_-]{8,100}$/.test(String(submission.id || '')));
  }

  function renderApprovalPanel(submission) {
    if (!isApprovableCollision(submission)) return null;
    var panel = document.createElement('section');
    panel.className = 'approval-panel';
    panel.setAttribute('aria-label', 'Exact-match slug collision approval');
    var title = document.createElement('p');
    title.className = 'approval-title';
    title.textContent = 'Exact source match found';
    var copy = document.createElement('p');
    copy.className = 'approval-copy';
    copy.textContent = 'This upload matches a reviewed hosted source with the same slug collision; approval sends it back through build/test/deploy gates and does not instantly publish.';
    var error = document.createElement('p');
    error.className = 'approval-error';
    error.setAttribute('aria-live', 'polite');
    error.hidden = true;
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'button button-accent approval-button';
    button.textContent = 'Approve exact-match update';
    button.addEventListener('click', function () {
      error.hidden = true;
      error.textContent = '';
      var confirmed = window.confirm('Approval sends it back through build/test/deploy gates and does not instantly publish. Continue?');
      if (!confirmed) return;
      button.disabled = true;
      button.textContent = 'Approving...';
      postApproval(submission).then(function (detail) {
        if (detail) updateProgress(detail, 'queued');
        return fetchSubmissionDetail(submission.id).then(function (fresh) {
          if (fresh) updateProgress(fresh, 'queued');
          return refreshSubmissions(submission.id);
        });
      }).catch(function (approvalError) {
        error.textContent = approvalError && approvalError.message || 'Could not approve this submission.';
        error.hidden = false;
      }).finally(function () {
        button.disabled = false;
        button.textContent = 'Approve exact-match update';
      });
    });
    panel.append(title, copy, button, error);
    return panel;
  }

  function renderRetryPanel(submission) {
    if (!isRetryableReviewedBuildFailure(submission)) return null;
    var panel = document.createElement('section');
    panel.className = 'approval-panel';
    panel.setAttribute('aria-label', 'Retry reviewed gated build');
    var title = document.createElement('p');
    title.className = 'approval-title';
    title.textContent = 'Reviewed gated build needs another attempt';
    var copy = document.createElement('p');
    copy.className = 'approval-copy';
    copy.textContent = 'Retry sends the same reviewed source back through gated build checks. It does not publish or change the selected runtime.';
    var error = document.createElement('p');
    error.className = 'approval-error';
    error.setAttribute('aria-live', 'polite');
    error.hidden = true;
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'button button-accent approval-button';
    button.textContent = 'Retry gated build';
    button.addEventListener('click', function () {
      error.hidden = true;
      error.textContent = '';
      var confirmed = window.confirm('Retry this reviewed gated build? This does not publish or change the selected runtime.');
      if (!confirmed) return;
      button.disabled = true;
      button.textContent = 'Retrying...';
      postRetry(submission).then(function (detail) {
        if (detail) updateProgress(detail, 'queued');
        return fetchSubmissionDetail(submission.id).then(function (fresh) {
          if (fresh) updateProgress(fresh, 'queued');
          return refreshSubmissions(submission.id);
        });
      }).catch(function (retryError) {
        error.textContent = retryError && retryError.message || 'Could not retry this submission.';
        error.hidden = false;
      }).finally(function () {
        button.disabled = false;
        button.textContent = 'Retry gated build';
      });
    });
    panel.append(title, copy, button, error);
    return panel;
  }

  function setSubmissionMessage(message) {
    if (!hostedEmpty) return;
    hostedEmpty.textContent = message;
    hostedEmpty.hidden = false;
  }

  function refreshSubmissions(focusId) {
    setSubmissionMessage('Loading your submissions…');
    return fetchSubmissions().then(function (submissions) {
      renderSubmissions(submissions);
      if (!submissions.length) setSubmissionMessage('Nothing on the bench yet. Your first upload will show up here.');
      var focused = submissions.find(function (submission) { return submission.id === focusId; });
      if (focused) updateProgress(focused, 'queued');
      return submissions;
    }).catch(function () {
      if (window.ClerkAuth && typeof window.ClerkAuth.isSignedIn === 'function' && !window.ClerkAuth.isSignedIn()) {
        setSubmissionMessage('Sign in to see your submissions.');
      } else {
        setSubmissionMessage('Could not load your submissions. Please refresh or try again shortly.');
      }
      return [];
    });
  }

  function pollSubmission(id) {
    if (!id) return;
    var attempts = 0;
    var timer = window.setInterval(function () {
      attempts += 1;
      fetchSubmissionDetail(id).then(function (submission) {
        if (!submission) return;
        updateProgress(submission, 'queued');
        refreshSubmissions(id);
        if (['deployed', 'failed', 'ready_for_publish'].includes(submission.status) || attempts >= 30) {
          window.clearInterval(timer);
        }
      }).catch(function () {
        if (attempts >= 3) window.clearInterval(timer);
      });
    }, 5000);
  }

  function restoreSubmissionsAfterReload() {
    if (isFilePreview()) {
      renderSubmissions([]);
      return Promise.resolve([]);
    }
    setSubmissionMessage('Loading your submissions…');
    if (!window.ClerkAuth || typeof window.ClerkAuth.ensureLoaded !== 'function') {
      setSubmissionMessage('Could not load your submissions. Please refresh or try again shortly.');
      return Promise.resolve([]);
    }
    return Promise.resolve(window.ClerkAuth.ensureLoaded()).then(function () {
      if (!window.ClerkAuth.isSignedIn()) {
        setSubmissionMessage('Sign in to see your submissions.');
        return [];
      }
      var savedIds = readSubmissionIds();
      var focusId = savedIds.length ? savedIds[savedIds.length - 1] : null;
      return refreshSubmissions(focusId);
    }).catch(function () {
      setSubmissionMessage('Could not load your submissions. Please refresh or try again shortly.');
      return [];
    });
  }

  function sessionToken() {
    if (!window.Clerk || !window.Clerk.session || typeof window.Clerk.session.getToken !== 'function') {
      return Promise.reject(new Error('Your verified sign-in session is not ready. Sign in and try again.'));
    }
    return Promise.resolve(window.Clerk.session.getToken()).then(function (token) {
      if (!token) throw new Error('Your sign-in session expired. Sign in and try again.');
      return token;
    });
  }

  function submitToWorker(payload) {
    return sessionToken().then(function (token) {
      return fetch(apiBase() + '/api/submit', {
        method: 'POST',
        headers: {
          Authorization: 'Bearer ' + token,
          'Content-Type': 'application/json',
          Accept: 'application/json'
        },
        body: JSON.stringify(payload)
      });
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (body) {
        if ([404, 405, 501].includes(response.status)) {
          var unavailable = new Error('The secure submission queue is still activating.');
          unavailable.code = 'queue_unavailable';
          throw unavailable;
        }
        if (!response.ok || response.status !== 202 || !['queued', 'deployed'].includes(body.status)) {
          throw new Error(body.message || body.error || 'Omo could not queue this workflow. Try again.');
        }
        return body;
      });
    });
  }

  function requireSignedIn() {
    if (window.ClerkAuth && typeof window.ClerkAuth.isSignedIn === 'function' && window.ClerkAuth.isSignedIn()) return true;
    fileError.textContent = 'Sign in or create your creator account, then submit again.';
    if (window.ClerkAuth && typeof window.ClerkAuth.signUp === 'function') window.ClerkAuth.signUp();
    return false;
  }

  var privateOption = form.querySelector('input[name="visibility"][value="private"]');
  if (privateOption) {
    privateOption.disabled = true;
    var privateCopy = privateOption.parentElement && privateOption.parentElement.querySelector('.visibility-choice span');
    if (privateCopy) privateCopy.textContent = 'Coming later — owner-only routing is not available in this first version.';
  }

  fileInput.addEventListener('change', function () {
    setSelectedFile(fileInput.files && fileInput.files[0]);
  });

  ['dragenter', 'dragover'].forEach(function (eventName) {
    dropZone.addEventListener(eventName, function (event) {
      event.preventDefault();
      dropZone.classList.add('is-dragging');
    });
  });

  ['dragleave', 'drop'].forEach(function (eventName) {
    dropZone.addEventListener(eventName, function (event) {
      event.preventDefault();
      dropZone.classList.remove('is-dragging');
    });
  });

  dropZone.addEventListener('drop', function (event) {
    setSelectedFile(event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0]);
  });

  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    if (!selectedFile && fileInput.files && fileInput.files[0]) selectedFile = fileInput.files[0];
    if (!isMarkdownFile(selectedFile)) {
      fileError.textContent = selectedFile ? 'Please choose a Markdown (.md) file.' : 'Choose your skill.md or workflow file first.';
      fileInput.focus();
      return;
    }
    if (selectedFile.size > MAX_BYTES) {
      fileError.textContent = 'Markdown files must be 200 KB or smaller.';
      fileInput.focus();
      return;
    }
    if (!nameInput.value.trim()) {
      nameInput.setCustomValidity('Give your workflow a name.');
      nameInput.reportValidity();
      nameInput.setCustomValidity('');
      return;
    }
    if (!requireSignedIn()) return;

    submitButton.disabled = true;
    submitButton.textContent = 'Reading Markdown…';
    fileError.textContent = '';
    try {
      var content = await selectedFile.text();
      if (new TextEncoder().encode(content).length > MAX_BYTES) throw new Error('Markdown files must be 200 KB or smaller.');
      var sourceName = submissionNameFromMarkdown(content);
      if (sourceName) nameInput.value = sourceName;
      var payload = { name: sourceName || nameInput.value.trim(), content: content, visibility: 'public' };
      var result;
      if (isFilePreview()) {
        result = { id: 'preview-' + Date.now(), name: payload.name, slug: '', status: 'queued' };
        updateProgress(result, 'preview');
      } else {
        result = await submitToWorker(payload);
        rememberSubmissionId(result.id);
        var detail = await fetchSubmissionDetail(result.id).catch(function () {
          return { id: result.id, name: payload.name, slug: result.slug, status: result.status };
        });
        updateProgress(detail, detail.status === 'deployed' ? 'deployed' : 'queued');
        await refreshSubmissions(result.id);
        if (detail.status !== 'deployed') pollSubmission(result.id);
      }
      submitButton.textContent = result.status === 'deployed' ? 'Live ✓'
        : (result.duplicate ? 'Already queued ✓' : 'Queued for review ✓');
    } catch (error) {
      if (error && error.code === 'queue_unavailable') {
        updateProgress({ id: 'waiting-' + Date.now(), name: nameInput.value.trim(), slug: '', status: 'local_waiting' }, 'waiting');
        submitButton.textContent = 'Saved here — retry later';
      } else {
        fileError.textContent = error && error.message || 'Omo could not queue this workflow. Try again.';
        submitButton.textContent = 'Submit for hosting →';
      }
    } finally {
      submitButton.disabled = false;
    }
  });

  submitButton.textContent = 'Submit for hosting →';
  if (window.ClerkAuth && typeof window.ClerkAuth.onAuthChange === 'function') {
    window.ClerkAuth.onAuthChange(function () {
      restoreSubmissionsAfterReload();
    });
  }
  restoreSubmissionsAfterReload();
})();
