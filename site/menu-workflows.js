/* Signed-in workflow shortcuts for the shared Omo navigation menu. */
(function () {
  'use strict';

  var VOTE_KEY = 'cognition_votes_v1';
  var PURCHASE_KEY = 'cognition_purchases_v1';
  var catalogPromise = null;

  function readJSON(key, fallback) {
    try {
      var raw = window.localStorage.getItem(key);
      if (!raw) return fallback;
      var value = JSON.parse(raw);
      return value == null ? fallback : value;
    } catch (error) {
      return fallback;
    }
  }

  function allowsLocalUserFallback() {
    if (window.location && window.location.protocol === 'file:') return true;
    var key = typeof window.CLERK_PUBLISHABLE_KEY === 'string' ? window.CLERK_PUBLISHABLE_KEY.trim() : '';
    return !!key && (key === 'pk_test_placeholder' || !/^pk_(test|live)_/.test(key));
  }

  function isSignedIn() {
    if (window.ClerkAuth && typeof window.ClerkAuth.isSignedIn === 'function') {
      return window.ClerkAuth.isSignedIn();
    }
    if (!allowsLocalUserFallback()) return false;

    var user = readJSON('cognition_user', null);
    return !!(user && user.id);
  }

  function purchaseSlug(item) {
    if (typeof item === 'string') return item;
    return item && typeof item.slug === 'string' ? item.slug : '';
  }

  function capturePurchaseReturn() {
    var params;
    try {
      params = new URLSearchParams(window.location.search || '');
    } catch (error) {
      return;
    }

    var slug = params.get('purchased') || '';
    var sessionId = params.get('session_id') || '';
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) ||
        !/^cs_[A-Za-z0-9_]+$/.test(sessionId)) return;

    var saved = readJSON(PURCHASE_KEY, []);
    var purchases = Array.isArray(saved) ? saved : [];
    for (var i = 0; i < purchases.length; i += 1) {
      if (purchaseSlug(purchases[i]) === slug) return;
    }

    purchases.push({
      slug: slug,
      sessionId: sessionId,
      purchasedAt: new Date().toISOString()
    });
    try { window.localStorage.setItem(PURCHASE_KEY, JSON.stringify(purchases)); } catch (error) {}
  }

  function workflowStates() {
    var items = {};
    var order = [];
    var votes = readJSON(VOTE_KEY, {});

    if (votes && typeof votes === 'object' && !Array.isArray(votes)) {
      Object.keys(votes).forEach(function (slug) {
        if (!votes[slug]) return;
        items[slug] = { slug: slug, upvoted: true, bought: false };
        order.push(slug);
      });
    }

    var purchases = readJSON(PURCHASE_KEY, []);
    if (Array.isArray(purchases)) {
      purchases.forEach(function (purchase) {
        var slug = purchaseSlug(purchase);
        if (!slug) return;
        if (!items[slug]) {
          items[slug] = { slug: slug, upvoted: false, bought: true };
          order.push(slug);
        } else {
          items[slug].bought = true;
        }
      });
    }

    return order.map(function (slug) { return items[slug]; });
  }

  function addProducts(products, list) {
    (list || []).forEach(function (product) {
      if (product && product.slug && !products[product.slug]) products[product.slug] = product;
    });
  }

  function productMap() {
    var products = {};
    addProducts(products, window.OMO_VISIBLE_CATALOG);
    return products;
  }

  function loadCatalogScript(source, globalName) {
    if (window[globalName]) return Promise.resolve();

    return new Promise(function (resolve) {
      var script = document.createElement('script');
      script.src = source;
      script.async = true;
      script.onload = resolve;
      script.onerror = resolve;
      document.head.appendChild(script);
    });
  }

  function ensureCatalog() {
    if (!catalogPromise) {
      catalogPromise = loadCatalogScript('catalog.js', 'OMO_CATALOG');
    }
    return catalogPromise;
  }

  function statusLabel(item) {
    if (item.bought && item.upvoted) return 'Bought · Upvoted';
    return item.bought ? 'Bought' : 'Upvoted';
  }

  function fallbackName(slug) {
    return slug.split('-').map(function (word) {
      return word ? word.charAt(0).toUpperCase() + word.slice(1) : '';
    }).join(' ');
  }

  function appendThumbnail(container, product) {
    var source = product && product.cover;
    var emoji = product && product.emoji ? product.emoji : '\u2726';

    function showEmoji() {
      container.textContent = emoji;
    }

    if (!source) {
      showEmoji();
      return;
    }

    var image = document.createElement('img');
    image.src = source;
    image.alt = '';
    image.addEventListener('error', showEmoji, { once: true });
    container.appendChild(image);
  }

  function ensureSection(popover) {
    var section = popover.querySelector('.omo-nav-workflows');
    if (section) return section;

    section = document.createElement('section');
    section.className = 'omo-nav-workflows';
    section.setAttribute('aria-label', 'Your workflows');

    var label = document.createElement('h2');
    label.className = 'omo-nav-workflows-label';
    label.textContent = 'Your workflows';
    section.appendChild(label);

    var content = document.createElement('div');
    content.className = 'omo-nav-workflows-list';
    section.appendChild(content);
    popover.insertBefore(section, popover.querySelector('.omo-nav-logout'));
    return section;
  }

  function renderSection(popover, items, products) {
    items = items.filter(function (item) { return !!products[item.slug]; });
    var section = ensureSection(popover);
    var list = section.querySelector('.omo-nav-workflows-list');
    list.textContent = '';

    if (!items.length) {
      var empty = document.createElement('div');
      empty.className = 'omo-nav-workflows-empty';

      var emptyIcon = document.createElement('span');
      emptyIcon.className = 'omo-nav-workflows-empty-icon';
      emptyIcon.setAttribute('aria-hidden', 'true');
      emptyIcon.textContent = '\u2726';
      empty.appendChild(emptyIcon);

      var emptyCopy = document.createElement('span');
      emptyCopy.textContent = 'Upvote or buy a workflow to see it here';
      empty.appendChild(emptyCopy);
      list.appendChild(empty);
      return;
    }

    items.forEach(function (item) {
      var product = products[item.slug];
      var name = product && product.name ? product.name : fallbackName(item.slug);
      var link = document.createElement('a');
      link.className = 'omo-nav-workflow-link';
      if (item.upvoted) link.classList.add('is-upvoted');
      if (item.bought) link.classList.add('is-bought');
      if (item.upvoted && item.bought) link.classList.add('is-combo');
      link.href = '/workflow.html?slug=' + encodeURIComponent(item.slug);
      link.target = '_blank';
      link.rel = 'noopener';
      link.setAttribute('aria-label', name + ', ' + statusLabel(item) + ', opens in a new tab');

      var thumbnail = document.createElement('span');
      thumbnail.className = 'omo-nav-workflow-thumb';
      thumbnail.setAttribute('aria-hidden', 'true');
      appendThumbnail(thumbnail, product);
      link.appendChild(thumbnail);

      var copy = document.createElement('span');
      copy.className = 'omo-nav-workflow-copy';

      var title = document.createElement('span');
      title.className = 'omo-nav-workflow-name';
      title.textContent = name;
      copy.appendChild(title);

      var status = document.createElement('span');
      status.className = 'omo-nav-workflow-status';
      status.textContent = statusLabel(item);
      link.appendChild(copy);
      link.appendChild(status);
      list.appendChild(link);
    });
  }

  function syncSections() {
    var popovers = document.querySelectorAll('.omo-nav-popover');
    if (!isSignedIn()) {
      for (var i = 0; i < popovers.length; i += 1) {
        var oldSection = popovers[i].querySelector('.omo-nav-workflows');
        if (oldSection) oldSection.remove();
      }
      return;
    }

    var items = workflowStates();
    var products = productMap();
    for (var j = 0; j < popovers.length; j += 1) {
      renderSection(popovers[j], items, products);
    }

    if (items.length && !window.OMO_CATALOG) {
      ensureCatalog().then(function () {
        if (!isSignedIn()) {
          syncSections();
          return;
        }
        var freshProducts = productMap();
        var freshItems = workflowStates();
        for (var k = 0; k < popovers.length; k += 1) {
          renderSection(popovers[k], freshItems, freshProducts);
        }
      });
    }
  }

  function init() {
    capturePurchaseReturn();
    syncSections();

    document.addEventListener('click', function (event) {
      if (event.target.closest('.omo-nav-menu-toggle')) syncSections();
    });
    window.addEventListener('storage', syncSections);
    if (window.ClerkAuth && typeof window.ClerkAuth.onAuthChange === 'function') {
      window.ClerkAuth.onAuthChange(syncSections);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
