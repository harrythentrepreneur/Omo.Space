import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('./nav.js', import.meta.url), 'utf8');

class ClassList {
  constructor() { this.values = new Set(); }
  add(...names) { names.forEach((name) => this.values.add(name)); }
  remove(...names) { names.forEach((name) => this.values.delete(name)); }
  contains(name) { return this.values.has(name); }
  toggle(name, force) {
    if (force === true) this.values.add(name);
    else if (force === false) this.values.delete(name);
    else if (this.values.has(name)) this.values.delete(name);
    else this.values.add(name);
  }
}

class Element {
  constructor(tagName) {
    this.tagName = String(tagName || '').toUpperCase();
    this.attributes = new Map();
    this.children = [];
    this.classList = new ClassList();
    this.hidden = false;
    this.parentNode = null;
    this._text = '';
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map((child) => child.textContent).join(''); }
  set className(value) {
    this.classList = new ClassList();
    String(value || '').split(/\s+/).filter(Boolean).forEach((name) => this.classList.add(name));
  }
  get className() { return [...this.classList.values].join(' '); }
  set id(value) { this.attributes.set('id', String(value)); }
  get id() { return this.attributes.get('id') || ''; }
  set href(value) { this.attributes.set('href', String(value)); }
  get href() { return this.attributes.get('href') || ''; }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.has(name) ? this.attributes.get(name) : null; }
  removeAttribute(name) { this.attributes.delete(name); }
  appendChild(child) { child.parentNode = this; this.children.push(child); return child; }
  addEventListener() {}
  querySelector() { return null; }
}

function makeHarness({ user, stored = {}, getBalance }) {
  const login = new Element('a');
  login.className = 'omo-nav-login';
  login.setAttribute('data-omo-login', '');
  login.textContent = 'Log in';
  const storage = new Map(Object.entries(stored));
  const ids = new Map();
  const authListeners = [];
  const windowListeners = new Map();

  const document = {
    readyState: 'complete',
    head: {
      appendChild(element) {
        element.parentNode = this;
        if (element.id) ids.set(element.id, element);
        return element;
      },
    },
    createElement: (tagName) => new Element(tagName),
    getElementById: (id) => ids.get(id) || null,
    querySelector: () => null,
    querySelectorAll(selector) {
      if (selector === '[data-omo-login]') return [login];
      return [];
    },
    addEventListener() {},
  };

  const window = {
    document,
    console,
    location: { protocol: 'https:', pathname: '/index.html', search: '', href: 'https://omo.space/index.html' },
    localStorage: {
      getItem: (key) => storage.has(key) ? storage.get(key) : null,
      setItem: (key, value) => storage.set(key, String(value)),
      removeItem: (key) => storage.delete(key),
    },
    Clerk: user ? { user } : null,
    ClerkAuth: {
      isSignedIn: () => !!user,
      getUser: () => user && { id: user.id, demo: false },
      ensureLoaded: () => Promise.resolve(null),
      onAuthChange(callback) { authListeners.push(callback); return callback; },
    },
    OmoCredits: { getBalance },
    addEventListener(name, callback) {
      if (!windowListeners.has(name)) windowListeners.set(name, []);
      windowListeners.get(name).push(callback);
    },
    dispatchEvent(event) {
      (windowListeners.get(event.type) || []).forEach((callback) => callback(event));
    },
    setTimeout,
    clearTimeout,
  };
  window.window = window;

  const context = vm.createContext({
    console,
    document,
    window,
    localStorage: window.localStorage,
    URLSearchParams,
    Promise,
    Date,
    setTimeout,
    clearTimeout,
  });
  vm.runInContext(source, context, { filename: 'nav.js' });
  return { login, storage, authListeners, window };
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const flush = async () => { await Promise.resolve(); await Promise.resolve(); await wait(0); };

{
  const calls = [];
  let resolveFirstBalance;
  const freshUser = { id: 'user_fresh', createdAt: new Date() };
  const harness = makeHarness({
    user: freshUser,
    getBalance(options) {
      calls.push(options || null);
      if (calls.length === 1) return new Promise((resolve) => { resolveFirstBalance = resolve; });
      return Promise.resolve({ mode: 'server', userId: freshUser.id, balanceCents: 500 });
    },
  });
  await flush();
  assert.equal(harness.login.textContent, '$5.00', 'fresh signup should show the grant while the server confirms it');
  assert.equal(harness.login.classList.contains('is-balance-loading'), true, 'optimistic grant must remain visibly refreshing');
  assert.equal(calls.length, 1, 'signed-in resolution should fetch immediately');
  await wait(1050);
  await flush();
  assert.equal(calls.length, 2, 'a slow first response should trigger exactly one forced retry');
  assert.equal(calls[1] && calls[1].force, true);
  assert.match(harness.login.textContent, /\$5\.00$/);
  assert.equal(harness.login.classList.contains('is-balance-loading'), false, 'confirmed grant should become ready');
  resolveFirstBalance({ mode: 'server', userId: freshUser.id, balanceCents: 0 });
  await flush();
  assert.match(harness.login.textContent, /\$5\.00$/, 'the superseded first request must not restore a stale zero');
  assert.equal(harness.login.classList.contains('is-balance-loading'), false);
}

{
  let resolveBalance;
  const oldUser = { id: 'user_old', createdAt: new Date(Date.now() - 10 * 60 * 1000) };
  const otherCacheKey = 'omo_nav_balance_v1:' + encodeURIComponent('user_other');
  const harness = makeHarness({
    user: oldUser,
    stored: { [otherCacheKey]: JSON.stringify({ userId: 'user_other', balanceCents: 0, cachedAt: Date.now() }) },
    getBalance() { return new Promise((resolve) => { resolveBalance = resolve; }); },
  });
  await flush();
  assert.equal(harness.login.textContent, '$…', 'an older uncached login must not receive an optimistic grant');
  assert.notEqual(harness.login.textContent, '$0.00', 'another user\'s cached zero must not leak');
  resolveBalance({ mode: 'server', userId: oldUser.id, balanceCents: 325 });
  await flush();
  assert.match(harness.login.textContent, /\$3\.25$/);
}

{
  const harness = makeHarness({ user: null, getBalance: () => Promise.reject(new Error('not called')) });
  await flush();
  assert.equal(harness.login.textContent, 'Log in', 'signed-out first paint must remain immediate');
  assert.equal(harness.login.getAttribute('data-omo-auth-state'), 'signed-out');
}

console.log('PASS nav shows and confirms a fresh $5 grant without leaking cached balances');
