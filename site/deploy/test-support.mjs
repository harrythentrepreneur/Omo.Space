import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const site = path.resolve(here, '..');
const worker = fs.readFileSync(path.join(here, 'worker.js'), 'utf8');
const html = fs.readFileSync(path.join(site, 'support.html'), 'utf8');
const client = fs.readFileSync(path.join(site, 'support.js'), 'utf8');
const broker = fs.readFileSync(path.resolve(site, '..', 'services', 'omo-support-broker', 'app.py'), 'utf8');

assert.match(worker, /'\/api\/support\/chat': \{ handler: handleSupportChat \}/);
assert.match(worker, /authenticateAccount\(request, env, false\)/);
assert.doesNotMatch(worker, /OMO_SUPPORT_MAINTAINER_IDS|maintainers\.includes\('\*'\)/);
assert.match(worker, /X-Omo-Signature/);
assert.match(worker, /result\.profile !== 'omo-support'/);
assert.match(worker, /result\.mode !== 'support'/);
assert.match(worker, /new TextEncoder\(\)\.encode\(rawResponse\)\.length > 16384/);
assert.match(worker, /message\.length > 8000/);
assert.match(html, /id="support-chat-app"/);
assert.match(html, /src="support\.js"/);
assert.match(client, /Clerk\.session\.getToken/);
assert.match(client, /textContent = text/);
assert.match(client, /body\.profile !== 'omo-support'/);
assert.doesNotMatch(client, /OMO_SUPPORT_SHARED_SECRET|API_SERVER_KEY/);
assert.match(broker, /PROFILE = "omo-support"/);
assert.match(broker, /\/p\/\{PROFILE\}\/v1\/chat\/completions/);
assert.match(broker, /hmac\.compare_digest/);
assert.match(broker, /CREATE TABLE IF NOT EXISTS broker_nonces/);
assert.match(broker, /POLICY_VERSION = "support-safe-v2"/);
assert.match(broker, /support_actions_disabled/);
assert.doesNotMatch(broker, /payload\.get\(["']profile/);

console.log('19 support chat contract checks passed');
