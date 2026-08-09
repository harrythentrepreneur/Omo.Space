// Omo — credits core unit tests (no network, no keys)
// Usage: node test-balance.mjs
import {
  SIGNUP_GRANT_USD,
  grantSignupCredits,
  debitForRun,
  apiKeyFor,
  hashHex,
  topupAmounts,
  API_KEY_PREFIX,
} from './balance.mjs';

let pass = 0, fail = 0;
const check = (name, cond) => { if (cond) { pass++; console.log(`PASS  ${name}`); } else { fail++; console.log(`FAIL  ${name}`); } };

// 1. Signup grant = $10
check('grant: signup grant is $10', SIGNUP_GRANT_USD === 10);
check('grant: grantSignupCredits returns $10', grantSignupCredits().amountUsd === 10);

// 2. debitForRun — happy path
const d1 = debitForRun(10, 0.10);
check('debit: $10 - $0.10 → ok, balance $9.90', d1.ok === true && d1.balance === 9.9);
check('debit: reports debited amount', d1.debitedUsd === 0.1);
const d2 = debitForRun(0.10, 0.10);
check('debit: exact-balance spend leaves $0.00', d2.ok === true && d2.balance === 0);
const d3 = debitForRun(10, 0);
check('debit: $0 cost debits nothing', d3.ok === true && d3.balance === 10);

// 3. debitForRun — insufficient (the 402 semantics the worker maps)
const i1 = debitForRun(0.05, 0.10);
check('debit: $0.05 vs $0.10 → insufficient', i1.ok === false && i1.insufficient === true);
check('debit: insufficient reports shortfall', i1.shortfallUsd === 0.05);
check('debit: insufficient balance untouched', i1.balance === 0.05);
const i2 = debitForRun(0, 0.10);
check('debit: zero balance is insufficient', i2.ok === false && i2.insufficient === true);
const i3 = debitForRun(10, 10.01);
check('debit: $10 vs $10.01 → insufficient (cents-rounded)', i3.ok === false && i3.shortfallUsd === 0.01);

// 4. apiKeyFor — deterministic, prefixed, stable per (user, secret)
const k1 = apiKeyFor('user_123', 's3cret');
check('key: prefix is omo_', k1.startsWith(API_KEY_PREFIX) && API_KEY_PREFIX === 'omo_');
check('key: deterministic for same user+secret', k1 === apiKeyFor('user_123', 's3cret'));
check('key: different user → different key', k1 !== apiKeyFor('user_456', 's3cret'));
check('key: different secret → different key', k1 !== apiKeyFor('user_123', 'other-secret'));
check('key: stable length (prefix + 32 hex from two passes)', k1.length === API_KEY_PREFIX.length + 32 && /^omo_[0-9a-f]{32}$/.test(k1));
const k2 = apiKeyFor('demo-abc123', '');
check('key: works with empty secret (dev fallback)', /^omo_[0-9a-f]{32}$/.test(k2));

// 5. hashHex helper
check('hash: hex, 16 chars, lowercase', /^[0-9a-f]{16}$/.test(hashHex('anything')));
check('hash: deterministic', hashHex('a') === hashHex('a'));
check('hash: differs across inputs', hashHex('a') !== hashHex('b'));

// 6. topup amounts
const t = topupAmounts();
check('topup: presets are [5,10,25,50]', JSON.stringify(t) === JSON.stringify([5, 10, 25, 50]));
t.push(999);
check('topup: returns a copy (caller cannot mutate presets)', topupAmounts().length === 4);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
