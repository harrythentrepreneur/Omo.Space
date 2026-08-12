/* library.js — the logged-in library view for the Omo storefront.
 *
 * Works with clerk.js. Shows two sections, same Workshop Green look as the
 * storefront (it reuses the site's own .listing-card / .button styles):
 *   (a) Upvoted   — slugs the user upvoted (localStorage cognition_votes_v1)
 *   (b) Purchased — purchases recorded by the buy CTA (cognition_purchases_v1)
 * Clicking a card reuses the storefront's own detail dialog (it replays a
 * card click inside #listing-feed, so no dialog renderer is duplicated).
 *
 * Exposes window.LibraryView = { show, hide }.
 */
(function () {
  'use strict';

  var VOTE_KEY = 'cognition_votes_v1';
  var PURCHASE_KEY = 'cognition_purchases_v1';

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // Read the same single catalog as the storefront.
  function productMap() {
    var PRODUCTS = {};
    (window.OMO_CATALOG || []).forEach(function (s) {
      if (s && s.slug && !PRODUCTS[s.slug]) PRODUCTS[s.slug] = s;
    });
    return PRODUCTS;
  }

  function readJSON(key, fallback) {
    try {
      var raw = localStorage.getItem(key);
      if (!raw) return fallback;
      var v = JSON.parse(raw);
      return v == null ? fallback : v;
    } catch (e) { return fallback; }
  }

  function upvotedSlugs() {
    var votes = readJSON(VOTE_KEY, {});
    var out = [];
    Object.keys(votes).forEach(function (s) { if (votes[s]) out.push(s); });
    return out;
  }

  function purchases() {
    var list = readJSON(PURCHASE_KEY, []);
    return Array.isArray(list) ? list : [];
  }

  function cardHTML(p, owned) {
    var comingSoon = p.status === 'coming-soon' || p.chargeable === false || p.active === false;
    var price = comingSoon ? 'Coming soon' : '$' + Number(p.runPrice || p.priceRun || 0).toFixed(2) + '/run';
    var visual = p.icon
      ? '<div class="listing-cover icon-cover" aria-hidden="true"><img src="' + esc(p.icon) + '" alt="" loading="lazy"></div>'
      : (p.cover
          ? '<div class="listing-cover" aria-hidden="true"><img src="' + esc(p.cover) + '" alt="" loading="lazy"><span class="cover-emoji">' + esc(p.emoji) + '</span></div>'
          : '<div class="listing-cover" aria-hidden="true" style="display:flex;align-items:center;justify-content:center"><span style="font-size:52px;line-height:1">' + esc(p.emoji) + '</span></div>');
    return '<article class="listing-card sig-cut" data-lib-slug="' + esc(p.slug) + '" tabindex="0" role="link" aria-label="Open the workflow page for ' + esc(p.name) + ' in a new tab">' +
      visual +
      '<div class="listing-body">' +
      '<h3 class="listing-name">' + esc(p.name) + '</h3>' +
      '<p class="listing-promise">' + esc(p.promise) + '</p>' +
      '<p class="listing-maker">by <span class="maker-handle">' + esc(p.maker) + '</span></p>' +
      '<div class="listing-footer">' +
        '<p class="listing-price">' + (owned && !comingSoon ? 'Yours &middot; ' : '') + price + '</p>' +
      '</div>' +
      '</div>' +
    '</article>';
  }

  var view = null;

  function injectStyles() {
    if (document.getElementById('library-styles')) return;
    var css =
      '.library-view{position:fixed;top:0;left:0;right:0;bottom:0;z-index:200;overflow-y:auto;background:var(--canvas);padding:28px 24px 96px}' +
      '.library-shell{max-width:var(--shell,1160px);margin:0 auto}' +
      '.library-head{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:32px}' +
      '.library-title{font-family:var(--display);font-size:clamp(30px,5vw,44px);font-weight:600;letter-spacing:-0.01em;margin:0}' +
      '.library-title .wordmark-dot{color:var(--orange)}' +
      '.library-sub{margin:6px 0 0;color:var(--moss);font-size:15px}' +
      '.library-section{margin-bottom:40px}' +
      '.library-section-title{font-family:var(--display);font-size:24px;font-weight:600;margin:0 0 4px}' +
      '.library-section-sub{margin:0 0 16px;color:var(--moss);font-size:14.5px}' +
      '.library-grid{display:grid;gap:20px;grid-template-columns:1fr}' +
      '@media(min-width:640px){.library-grid{grid-template-columns:repeat(2,1fr)}}' +
      '@media(min-width:1000px){.library-grid{grid-template-columns:repeat(3,1fr)}}' +
      '.library-empty{border:1px dashed var(--rule);border-radius:14px;background:var(--surface);padding:28px;color:var(--moss);font-size:15px}' +
      '.library-view .listing-card{cursor:pointer}';
    var style = document.createElement('style');
    style.id = 'library-styles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  function openListing(slug) {
    // Reuse the storefront's own detail dialog by replaying a card click
    // inside #listing-feed — no duplicated dialog renderer.
    var feed = document.getElementById('listing-feed');
    if (!feed) return;
    var temp = document.createElement('article');
    temp.setAttribute('data-slug', slug);
    feed.appendChild(temp);
    var ev = document.createEvent('MouseEvents');
    ev.initEvent('click', true, true);
    temp.dispatchEvent(ev);
    feed.removeChild(temp);
  }

  function render() {
    var PRODUCTS = productMap();
    var user = window.ClerkAuth ? ClerkAuth.getUser() : null;
    var userName = (user && (user.firstName || user.email)) ? (user.firstName || user.email) : 'friend';

    var upvoted = upvotedSlugs().map(function (slug) { return PRODUCTS[slug]; }).filter(Boolean);
    var owned = purchases().map(function (it) { return PRODUCTS[it.slug]; }).filter(Boolean);

    var upHTML = upvoted.map(function (p) { return cardHTML(p, false); }).join('');
    var upEmpty = 'You haven\u2019t upvoted anything yet \u2014 go find a helper you like.';
    var ownHTML = owned.map(function (p) { return cardHTML(p, true); }).join('');
    var ownEmpty = 'Nothing here yet. Try a demo, then buy the ones you love \u2014 they\u2019ll show up here.';

    view.innerHTML =
      '<div class="library-shell">' +
        '<header class="library-head">' +
          '<div>' +
            '<h1 class="library-title">Your library<span class="wordmark-dot">.</span></h1>' +
            '<p class="library-sub">Signed in as ' + esc(userName) + ' \u2014 everything you upvoted and bought, in one place.</p>' +
          '</div>' +
          '<button class="button button-secondary button-small" type="button" data-lib-back>Back to the store</button>' +
        '</header>' +
        '<section class="library-section">' +
          '<h2 class="library-section-title">Upvoted</h2>' +
          '<p class="library-section-sub">Helpers you upvoted.</p>' +
          (upHTML ? '<div class="library-grid">' + upHTML + '</div>' : '<div class="library-empty">' + upEmpty + '</div>') +
        '</section>' +
        '<section class="library-section">' +
          '<h2 class="library-section-title">Purchased</h2>' +
          '<p class="library-section-sub">Helpers you own \u2014 one-time license, files are yours.</p>' +
          (ownHTML ? '<div class="library-grid">' + ownHTML + '</div>' : '<div class="library-empty">' + ownEmpty + '</div>') +
        '</section>' +
      '</div>';
  }

  function ensureView() {
    if (view) return view;
    injectStyles();
    view = document.createElement('section');
    view.id = 'library-view';
    view.className = 'library-view';
    view.setAttribute('aria-label', 'Your library');
    view.addEventListener('click', function (e) {
      var back = e.target.closest('[data-lib-back]');
      if (back) { window.LibraryView.hide(); return; }
      var card = e.target.closest('[data-lib-slug]');
      if (card) openListing(card.dataset.libSlug);
    });
    view.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { window.LibraryView.hide(); return; }
      if (e.key !== 'Enter' && e.key !== ' ') return;
      var card = e.target.closest('[data-lib-slug]');
      if (!card) return;
      e.preventDefault();
      openListing(card.dataset.libSlug);
    });
    document.body.appendChild(view);
    return view;
  }

  window.LibraryView = {
    show: function () {
      if (window.ClerkAuth && !ClerkAuth.isSignedIn()) {
        ClerkAuth.signIn();
        return;
      }
      ensureView();
      render();
      view.hidden = false;
      document.body.style.overflow = 'hidden'; // lock scroll behind the overlay
      view.scrollTop = 0;
      var first = view.querySelector('button');
      if (first) first.focus({ preventScroll: true });
    },
    hide: function () {
      if (!view) return;
      view.hidden = true;
      document.body.style.overflow = '';
    }
  };
})();
