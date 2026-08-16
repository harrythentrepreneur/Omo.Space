#!/usr/bin/env node

import { signPilotToken } from './pilot-magic.mjs';

const [email, cohort = 'pilot-200', ttlValue = '86400'] = process.argv.slice(2);
const secret = process.env.PILOT_MAGIC_LINK_SECRET || '';
const ttlSeconds = Number(ttlValue);

if (!email || !Number.isInteger(ttlSeconds) || ttlSeconds < 60 || ttlSeconds > 14 * 24 * 60 * 60) {
  console.error('Usage: PILOT_MAGIC_LINK_SECRET=... node generate-pilot-link.mjs EMAIL [COHORT] [TTL_SECONDS]');
  process.exit(2);
}

try {
  const token = await signPilotToken({
    email,
    cohort,
    grant_cents: 99,
    exp: Math.floor(Date.now() / 1000) + ttlSeconds,
  }, secret);
  console.log(`https://omo.space/pilot-claim.html?token=${encodeURIComponent(token)}`);
} catch (error) {
  console.error(`Could not generate pilot link: ${error && error.code ? error.code : 'pilot_token_invalid_payload'}`);
  process.exit(1);
}
