/* upload.js — front-end demo for the Omo hosted-workflow intake. */
(function () {
  'use strict';

  var STORAGE_KEY = 'omo_hosting_v1';
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
  var progressTimers = [];

  if (!form || !fileInput || !nameInput) return;

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
      status.textContent = submission.status === 'preparing' ? 'Preparing' : 'Submitted';

      var visibility = document.createElement('span');
      visibility.className = 'visibility-badge';
      visibility.textContent = submission.visibility === 'private' ? 'Private' : 'Marketplace';

      var date = document.createElement('time');
      date.dateTime = submission.submittedAt || '';
      date.textContent = formatDate(submission.submittedAt);

      meta.append(status, visibility, date);
      item.append(title, meta);
      hostedList.appendChild(item);
    });
  }

  function friendlyName(rawName) {
    return rawName
      .replace(/\.md$/i, '')
      .replace(/[-_]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .replace(/^\w/, function (letter) { return letter.toUpperCase(); });
  }

  function setSelectedFile(file) {
    selectedFile = file || null;
    fileError.textContent = '';
    if (!selectedFile) {
      fileName.textContent = 'No file chosen yet';
      return;
    }
    fileName.textContent = selectedFile.name;
    if (!nameInput.value.trim()) nameInput.value = friendlyName(selectedFile.name);
  }

  function isMarkdownFile(file) {
    return !!(file && /\.md$/i.test(file.name || ''));
  }

  function clearProgressTimers() {
    progressTimers.forEach(function (timer) { window.clearTimeout(timer); });
    progressTimers = [];
  }

  function showProgressStage(currentStage) {
    var steps = progress.querySelectorAll('[data-progress-step]');
    steps.forEach(function (step, index) {
      step.classList.toggle('is-done', index < currentStage);
      step.classList.toggle('is-current', index === currentStage);
      var dot = step.querySelector('.progress-dot');
      if (dot && index < currentStage) dot.textContent = '✓';
    });
  }

  function startProgress() {
    clearProgressTimers();
    progress.hidden = false;
    showProgressStage(1);
    progress.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var delay = reduceMotion ? 0 : 650;
    [2, 3, 4].forEach(function (stage, index) {
      progressTimers.push(window.setTimeout(function () {
        showProgressStage(stage);
      }, delay * (index + 1)));
    });
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
    var file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
    setSelectedFile(file);
  });

  form.addEventListener('submit', function (event) {
    event.preventDefault();

    if (!selectedFile && fileInput.files && fileInput.files[0]) selectedFile = fileInput.files[0];
    if (!isMarkdownFile(selectedFile)) {
      fileError.textContent = selectedFile ? 'Please choose a Markdown (.md) file.' : 'Choose your skill.md or workflow file first.';
      fileInput.focus();
      return;
    }

    if (!nameInput.value.trim()) {
      nameInput.setCustomValidity('Give your workflow a name.');
      nameInput.reportValidity();
      nameInput.setCustomValidity('');
      return;
    }

    if (!window.ClerkAuth || typeof ClerkAuth.isSignedIn !== 'function' || !ClerkAuth.isSignedIn()) {
      window.location.assign('signup.html?open=host');
      return;
    }

    var checkedVisibility = form.querySelector('input[name="visibility"]:checked');
    var submission = {
      name: nameInput.value.trim(),
      visibility: checkedVisibility && checkedVisibility.value === 'private' ? 'private' : 'public',
      submittedAt: new Date().toISOString(),
      status: 'preparing'
    };
    var submissions = readSubmissions();
    submissions.push(submission);
    writeSubmissions(submissions);
    renderSubmissions();
    startProgress();

    submitButton.disabled = true;
    submitButton.textContent = 'Hosting started ✓';
    window.setTimeout(function () {
      submitButton.disabled = false;
      submitButton.textContent = 'Start another workflow →';
    }, window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 2200);
  });

  renderSubmissions();
})();
