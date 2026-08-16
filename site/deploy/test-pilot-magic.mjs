import assert from 'node:assert/strict';
import { signPilotToken, verifyPilotToken } from './pilot-magic.mjs';

const secret = 'fixture-only-pilot-secret-32-bytes-minimum';
const payload = {
  email: 'Teacher@example.com',
  cohort: 'Pilot-200',
  grant_cents: 99,
  exp: 2_000_000_000,
};

const token = await signPilotToken(payload, secret);
const verified = await verifyPilotToken(token, secret, 1_999_999_000);
assert.deepEqual(verified, {
  email: 'teacher@example.com',
  cohort: 'pilot-200',
  grant_cents: 99,
  exp: 2_000_000_000,
});

await assert.rejects(
  verifyPilotToken(token, secret, 2_000_000_000),
  (error) => error && error.code === 'pilot_token_expired',
);

const tampered = `${token.slice(0, -1)}${token.endsWith('a') ? 'b' : 'a'}`;
await assert.rejects(
  verifyPilotToken(tampered, secret, 1_999_999_000),
  (error) => error && error.code === 'pilot_token_invalid',
);

await assert.rejects(
  signPilotToken({ ...payload, grant_cents: 0 }, secret),
  (error) => error && error.code === 'pilot_token_invalid_payload',
);

console.log('4 passed, 0 failed');
