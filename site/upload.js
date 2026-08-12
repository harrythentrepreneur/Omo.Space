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

  function readSubmissions() {
    try {
      var saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      return Array.isArray(saved) ? saved : [];
    } catch (error) {
      return [];
    }
  }

  function writeSubmissions(submissions) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(submissions));
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
      demo_queued: 'Demo queue'
    };
    return labels[status] || 'Submitted';
  }

  function renderSubmissions() {
    if (!hostedList || !hostedEmpty) return;
    var submissions = readSubmissions();
    hostedList.replaceChildren();
    hostedEmpty.hidden = submissions.length > 0;

    submissions.slice().reverse().forEach(function (submission) {
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
      visibility.textContent = submission.preview ? 'Local preview' : 'Marketplace';
      var date = document.createElement('time');
      date.dateTime = submission.submittedAt || '';
      date.textContent = formatDate(submission.submittedAt);
      meta.append(status, visibility, date);
      item.append(title, meta);
      hostedList.appendChild(item);
    });
  }

  function friendlyName(rawName) {
    return rawName.replace(/\.md$/i, '').replace(/[-_]+/g, ' ').replace(/\s+/g, ' ').trim()
      .replace(/^\w/, function (letter) { return letter.toUpperCase(); });
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

  function showQueued(submission, preview) {
    var steps = progress.querySelectorAll('[data-progress-step]');
    var labels = [
      'Upload received',
      'Queued for agent review',
      'Compile, test + price after review',
      'Modal + Omo canaries',
      'Publish after every gate passes'
    ];
    steps.forEach(function (step, index) {
      step.classList.toggle('is-done', index === 0);
      step.classList.toggle('is-current', index === 1);
      var label = step.querySelector('span:last-child');
      var dot = step.querySelector('.progress-dot');
      if (label) label.textContent = labels[index];
      if (dot) dot.textContent = index === 0 ? '✓' : String(index + 1);
    });
    var title = progress.querySelector('.progress-title');
    var note = progress.querySelector('.progress-demo');
    if (title) title.textContent = preview ? 'Demo submission queued locally.' : 'Your workflow is queued.';
    if (note) note.textContent = preview
      ? 'Local preview only — no file left this browser. Production submissions are stored securely for agent review.'
      : 'Queued is not live. An Omo agent must review the runtime profile; tests and canaries must pass before publishing.';
    progress.hidden = false;
    progress.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    var submissions = readSubmissions();
    submissions.push({
      id: submission.id,
      name: submission.name,
      slug: submission.slug,
      submittedAt: new Date().toISOString(),
      status: preview ? 'demo_queued' : submission.status,
      preview: preview
    });
    writeSubmissions(submissions.slice(-20));
    renderSubmissions();
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
        if (!response.ok || response.status !== 202 || body.status !== 'queued') {
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
      var payload = { name: nameInput.value.trim(), content: content, visibility: 'public' };
      var result;
      if (isFilePreview()) {
        result = { id: 'preview-' + Date.now(), name: payload.name, slug: '', status: 'queued' };
        showQueued(result, true);
      } else {
        result = await submitToWorker(payload);
        showQueued({ id: result.id, name: payload.name, slug: result.slug, status: result.status }, false);
      }
      submitButton.textContent = result.duplicate ? 'Already queued ✓' : 'Queued for review ✓';
    } catch (error) {
      fileError.textContent = error && error.message || 'Omo could not queue this workflow. Try again.';
      submitButton.textContent = 'Submit for hosting →';
    } finally {
      submitButton.disabled = false;
    }
  });

  submitButton.textContent = 'Submit for hosting →';
  renderSubmissions();
})();
