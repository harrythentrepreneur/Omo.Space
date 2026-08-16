const TOKEN_VERSION = 'v1';
const TOKEN_KEYS = ['cohort', 'email', 'exp', 'grant_cents'];
const COHORT_RE = /^[a-z0-9][a-z0-9._-]{0,63}$/;

export class PilotTokenError extends Error {
  constructor(code) {
    super(code);
    this.name = 'PilotTokenError';
    this.code = code;
  }
}

export function normalizePilotEmail(value) {
  const email = String(value || '').trim().toLowerCase();
  if (!email || email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    throw new PilotTokenError('pilot_token_invalid_payload');
  }
  return email;
}

export function validatePilotPayload(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new PilotTokenError('pilot_token_invalid_payload');
  }
  const keys = Object.keys(value).sort();
  if (keys.length !== TOKEN_KEYS.length || keys.some((key, index) => key !== TOKEN_KEYS[index])) {
    throw new PilotTokenError('pilot_token_invalid_payload');
  }
  const email = normalizePilotEmail(value.email);
  const cohort = String(value.cohort || '').trim().toLowerCase();
  const grantCents = Number(value.grant_cents);
  const exp = Number(value.exp);
  if (!COHORT_RE.test(cohort) || !Number.isInteger(grantCents) || grantCents < 1 || grantCents > 10000 ||
      !Number.isSafeInteger(exp) || exp < 1) {
    throw new PilotTokenError('pilot_token_invalid_payload');
  }
  return { email, cohort, grant_cents: grantCents, exp };
}

export async function signPilotToken(payload, secret) {
  const normalized = validatePilotPayload(payload);
  const key = await importHmacKey(secret, ['sign']);
  const encodedPayload = base64UrlEncode(new TextEncoder().encode(JSON.stringify(normalized)));
  const signingInput = `${TOKEN_VERSION}.${encodedPayload}`;
  const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(signingInput));
  return `${signingInput}.${base64UrlEncode(new Uint8Array(signature))}`;
}

export async function verifyPilotToken(token, secret, nowSeconds = Math.floor(Date.now() / 1000)) {
  const value = String(token || '').trim();
  if (!value || value.length > 4096) throw new PilotTokenError('pilot_token_invalid');
  const parts = value.split('.');
  if (parts.length !== 3 || parts[0] !== TOKEN_VERSION || !parts[1] || !parts[2]) {
    throw new PilotTokenError('pilot_token_invalid');
  }
  let signature;
  let rawPayload;
  try {
    signature = base64UrlDecode(parts[2]);
    rawPayload = new TextDecoder().decode(base64UrlDecode(parts[1]));
  } catch {
    throw new PilotTokenError('pilot_token_invalid');
  }
  const key = await importHmacKey(secret, ['verify']);
  const verified = await crypto.subtle.verify(
    'HMAC', key, signature, new TextEncoder().encode(`${parts[0]}.${parts[1]}`),
  );
  if (!verified) throw new PilotTokenError('pilot_token_invalid');
  let parsed;
  try { parsed = JSON.parse(rawPayload); } catch { throw new PilotTokenError('pilot_token_invalid_payload'); }
  const payload = validatePilotPayload(parsed);
  const canonical = base64UrlEncode(new TextEncoder().encode(JSON.stringify(payload)));
  if (canonical !== parts[1]) throw new PilotTokenError('pilot_token_invalid_payload');
  if (!Number.isSafeInteger(nowSeconds) || nowSeconds >= payload.exp) {
    throw new PilotTokenError('pilot_token_expired');
  }
  return payload;
}

async function importHmacKey(secret, usages) {
  const bytes = new TextEncoder().encode(String(secret || ''));
  if (bytes.length < 32) throw new PilotTokenError('pilot_secret_not_configured');
  return crypto.subtle.importKey('raw', bytes, { name: 'HMAC', hash: 'SHA-256' }, false, usages);
}

function base64UrlEncode(bytes) {
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function base64UrlDecode(value) {
  if (!/^[A-Za-z0-9_-]+$/.test(value)) throw new Error('invalid base64url');
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  const binary = atob(normalized + '='.repeat((4 - normalized.length % 4) % 4));
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}
