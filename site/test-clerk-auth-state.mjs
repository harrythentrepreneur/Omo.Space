import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('./clerk.js', import.meta.url), 'utf8');
let clerkListener;
let resolveSignOut;
let signOutCalls = 0;
const removedStorageKeys = [];
const signedInUser = {
  id: 'user_123',
  firstName: 'Kaviru',
  lastName: 'Hapuarachchi',
  fullName: 'Kaviru Hapuarachchi',
  username: 'kaviru',
  primaryEmailAddress: { emailAddress: 'kaviru@example.com' },
};
const switchedUser = {
  id: 'user_456',
  firstName: 'Ada',
  lastName: 'Lovelace',
  fullName: 'Ada Lovelace',
  username: 'ada',
  primaryEmailAddress: { emailAddress: 'ada@example.com' },
};

const fakeClerk = {
  // Reproduces the observed timing: Clerk's listener payload has the new user
  // before the singleton's `user` property is updated.
  user: null,
  load: async () => {},
  addListener(callback) { clerkListener = callback; },
  openSignIn() {},
  openSignUp() {},
  signOut() {
    signOutCalls += 1;
    return new Promise((resolve) => { resolveSignOut = resolve; });
  },
};

const keyPayload = Buffer.from('clerk.example.com$').toString('base64url');
const scripts = new Map();
function scriptNode() {
  const listeners = {};
  return {
    parentNode: null,
    setAttribute() {},
    addEventListener(type, callback) { listeners[type] = callback; },
    removeEventListener(type) { delete listeners[type]; },
    trigger(type) { if (listeners[type]) listeners[type](); },
  };
}

const document = {
  head: {
    appendChild(script) {
      script.parentNode = this;
      scripts.set(script.id, script);
      if (script.id === 'clerk-ui') {
        context.window.__internal_ClerkUICtor = function ClerkUI() {};
      } else if (script.id === 'clerk-js') {
        context.window.Clerk = fakeClerk;
      }
      queueMicrotask(() => script.trigger('load'));
    },
    removeChild() {},
  },
  createElement: scriptNode,
  getElementById(id) { return scripts.get(id) || null; },
};

const context = vm.createContext({
  console,
  document,
  localStorage: {
    getItem() { return null; },
    setItem() {},
    removeItem(key) { removedStorageKeys.push(key); },
  },
  URL,
  URLSearchParams,
  Promise,
  queueMicrotask,
  setTimeout,
  clearTimeout,
  window: {
    CLERK_PUBLISHABLE_KEY: `pk_test_${keyPayload}`,
    location: { protocol: 'https:', href: 'https://omo.best/', search: '', assign() {} },
    atob(value) { return Buffer.from(value, 'base64').toString('binary'); },
    setTimeout,
    clearTimeout,
  },
});
context.window.window = context.window;
context.window.document = document;
context.window.localStorage = context.localStorage;
context.window.URL = URL;
context.window.URLSearchParams = URLSearchParams;

vm.runInContext(source, context, { filename: 'clerk.js' });
await new Promise((resolve) => setTimeout(resolve, 0));
assert.equal(typeof clerkListener, 'function', 'Clerk listener should be registered');
assert.equal(context.window.ClerkAuth.isSignedIn(), false);

clerkListener({ user: signedInUser, session: { id: 'sess_123' } });

assert.equal(
  context.window.ClerkAuth.isSignedIn(),
  true,
  'listener payload should update auth state even before Clerk.user catches up',
);
assert.equal(context.window.ClerkAuth.getUser().id, 'user_123');

clerkListener({ user: switchedUser, session: { id: 'sess_456' } });
assert.equal(context.window.ClerkAuth.getUser().id, 'user_456');
assert.deepEqual(
  [...removedStorageKeys].sort(),
  ['cognition_user', 'omo_apikey_v1', 'omo_balance_v1', 'omo_usage_v1'].sort(),
  'switching directly between Clerk accounts should clear the previous user’s browser state',
);
removedStorageKeys.length = 0;

const signOutPromise = context.window.ClerkAuth.signOut();
assert.equal(signOutCalls, 1);
assert.equal(
  context.window.ClerkAuth.isSignedIn(),
  true,
  'auth state must remain signed in until Clerk confirms sign-out',
);
resolveSignOut();
await signOutPromise;
assert.equal(context.window.ClerkAuth.isSignedIn(), false);
assert.deepEqual(
  [...removedStorageKeys].sort(),
  ['cognition_user', 'omo_apikey_v1', 'omo_balance_v1', 'omo_usage_v1'].sort(),
  'successful sign-out should clear user-bound browser state',
);

removedStorageKeys.length = 0;
clerkListener({ user: signedInUser, session: { id: 'sess_456' } });
clerkListener({ user: null, session: null });
assert.deepEqual(
  [...removedStorageKeys].sort(),
  ['cognition_user', 'omo_apikey_v1', 'omo_balance_v1', 'omo_usage_v1'].sort(),
  'Clerk-driven sign-out should clear user-bound browser state',
);
assert.equal(
  context.window.ClerkAuth.isSignedIn(),
  false,
  'listener payload should clear auth state on sign-out',
);
assert.equal(context.window.ClerkAuth.getUser(), null);
console.log('PASS Clerk listener payload updates storefront auth state');
