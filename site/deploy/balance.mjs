// Omo — credits core (pure, testable, zero runtime dependencies).
//
// Every Omo account starts with $5 of free credits (granted on first signup
// via the Clerk webhook, or lazily by /api/me). API runs debit the balance at
// the cost-model run price (5x markup, $0.10 floor); top-ups add credits via
// Stripe Checkout. API keys are deterministic per user: 'omo_' + a hash of
// (userId, secret) — no database of keys needed, the same user always gets
// the same key for the same secret.
//
// This module is imported by site/deploy/worker.js and exercised directly by
// site/deploy/test-balance.mjs. It must stay dependency-free so the worker
// bundles it and the vm-based router tests can concatenate it.

export const SIGNUP_GRANT_USD = 5; // $5 free credits on first signup
export const TOPUP_AMOUNTS_USD = [20, 50, 100, 200]; // suggested dashboard chips
export const MIN_TOPUP_USD = 5; // custom top-ups may be any cent amount at/above this
export const API_KEY_PREFIX = 'omo_';
export const API_KEY_HEX_CHARS = 32; // 16 + 16 from two hash passes

// The signup grant: { amountUsd } for the Clerk user.created webhook.
export function grantSignupCredits() {
  return { amountUsd: SIGNUP_GRANT_USD };
}

// Debit costUsd from a balance. Returns:
//   { ok: true, balance, debitedUsd }            — enough credits
//   { ok: false, insufficient: true, balance, costUsd, shortfallUsd } — not enough
// Balances are dollars; rounding to cents keeps floats honest.
export function debitForRun(balanceUsd, costUsd) {
  const balance = Math.round((Number(balanceUsd) || 0) * 100) / 100;
  const cost = Math.round((Number(costUsd) || 0) * 100) / 100;
  if (balance < cost) {
    return {
      ok: false,
      insufficient: true,
      balance,
      costUsd: cost,
      shortfallUsd: Math.round((cost - balance) * 100) / 100,
    };
  }
  return {
    ok: true,
    balance: Math.round((balance - cost) * 100) / 100,
    debitedUsd: cost,
  };
}

// The dashboard's top-up presets (Stripe amounts in USD).
export function topupAmounts() {
  return TOPUP_AMOUNTS_USD.slice(); // defensive copy
}

// ── Deterministic API key ─────────────────────────────────────────────────
// FNV-1a (32-bit) — deterministic, dependency-free, fine for demo keys.
// Swap for crypto.subtle HMAC if keys ever need to be unguessable.
function fnv1a(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

// 16 hex chars from two FNV passes over the input.
export function hashHex(str) {
  const s = String(str == null ? '' : str);
  const a = fnv1a(s).toString(16).padStart(8, '0');
  const b = fnv1a('\u0001' + s + '\u0002').toString(16).padStart(8, '0');
  return a + b;
}

// Deterministic per (userId, secret): the same user always gets the same key.
// The secret is read from env (BALANCE_KEY_SECRET, else LLM_API_KEY, else a
// dev fallback) — never hardcoded here.
export function apiKeyFor(userId, secret) {
  const u = String(userId || '');
  const s = String(secret || '');
  return API_KEY_PREFIX + hashHex(u + '|' + s) + hashHex(s + '|' + u);
}
