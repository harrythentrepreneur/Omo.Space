(function () {
  'use strict';

  var STORAGE_KEY = 'omo_waitlist_v1';
  var EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  var SUCCESS_MESSAGE = "You're on the list — we'll email you when it opens 🎉";
  var DUPLICATE_MESSAGE = 'Already on the list!';

  function setMessage(note, state, message) {
    note.dataset.state = state;
    note.textContent = message;
    note.hidden = false;
  }

  function saveLocally(email, source) {
    var entries = [];
    try {
      var saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      if (Array.isArray(saved)) entries = saved;
    } catch (error) {}

    var already = entries.some(function (entry) {
      return entry && typeof entry.email === 'string' && entry.email.toLowerCase() === email;
    });
    if (already) return 'already';

    entries.push({ email: email, source: source || null, date: new Date().toISOString() });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
    return 'added';
  }

  function canUseStaticFallback(response) {
    return response && (response.status === 404 || response.status === 405 || response.status === 501);
  }

  document.querySelectorAll('[data-waitlist-form]').forEach(function (form) {
    var emailInput = form.querySelector('input[type="email"]');
    var submit = form.querySelector('button[type="submit"]');
    var note = form.querySelector('[data-waitlist-note]');
    if (!emailInput || !submit || !note) return;

    form.addEventListener('submit', async function (event) {
      event.preventDefault();
      var email = emailInput.value.trim().toLowerCase();
      var source = String(form.dataset.source || '').trim().toLowerCase();

      if (!EMAIL_PATTERN.test(email) || email.length > 254) {
        emailInput.setAttribute('aria-invalid', 'true');
        setMessage(note, 'error', 'That email looks a little off — try it once more.');
        emailInput.focus();
        return;
      }

      var originalLabel = submit.textContent;
      submit.disabled = true;
      submit.textContent = 'Joining…';
      emailInput.removeAttribute('aria-invalid');
      setMessage(note, 'sending', 'Adding you to the list…');

      try {
        var response;
        try {
          response = await fetch('/api/waitlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify({ email: email, source: source || undefined }),
          });
        } catch (networkError) {
          response = null;
        }

        var status;
        var payload = null;
        if (response && response.ok) {
          payload = await response.json();
          status = payload.status;
        } else if (!response || canUseStaticFallback(response)) {
          status = saveLocally(email, source);
        } else {
          try { payload = await response.json(); } catch (parseError) {}
          throw new Error(payload && payload.message || 'We could not join the waitlist right now. Please try again.');
        }

        if (status !== 'added' && status !== 'already') {
          throw new Error('We could not confirm the waitlist signup. Please try again.');
        }
        emailInput.value = '';
        setMessage(note, 'success', status === 'already' ? DUPLICATE_MESSAGE : SUCCESS_MESSAGE);
      } catch (error) {
        setMessage(note, 'error', error && error.message || 'We could not join the waitlist right now. Please try again.');
      } finally {
        submit.disabled = false;
        submit.textContent = originalLabel;
      }
    });
  });
})();
