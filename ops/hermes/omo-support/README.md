# Omo Support Hermes beta operations

This release is **diagnosis-only**. It deliberately contains no maintainer action path. Browser users cannot reach shell, files, GitHub, deployment, billing, messaging, or destructive tools.

## Boundary

`Omo browser → Clerk-authenticated Worker → HMAC broker → tool-free omo-support profile`

- Worker derives the Clerk subject and signs the exact broker payload.
- Broker durably rejects nonce replay and hard-pins the `omo-support` profile.
- The profile's `api_server` platform resolves to zero tools (`context_engine` is an empty toolset).
- Maintainer/action fields are rejected with `403 support_actions_disabled`.
- Remediation will be a separate server-controlled workflow and profile; it must never reuse customer-chat sessions or credentials.

## Required secrets

Create `/etc/omo-support-broker/env` mode `0600`, owned by root, containing only:

```text
OMO_SUPPORT_SHARED_SECRET=...
API_SERVER_KEY=...
```

Do not source `/root/.hermes/.env`. The API credential must be scoped to the profile-safe API route before production activation. Until Hermes supports a scoped API token or a dedicated support-only API server is provisioned, keep the service disabled.

Set the same HMAC value as the Worker secret:

```bash
npx wrangler secret put OMO_SUPPORT_SHARED_SECRET --config site/deploy/wrangler.toml
```

Never place either value in Git, browser JavaScript, issue text, logs, or this README.

## Install after merge

```bash
sudo install -d -o root -g root -m 0755 /opt/omo-support-broker
sudo install -o root -g root -m 0755 services/omo-support-broker/app.py /opt/omo-support-broker/app.py
sudo install -o root -g root -m 0644 ops/hermes/omo-support/omo-support-broker.service /etc/systemd/system/omo-support-broker.service
# Add nginx-location.conf to the existing HTTPS server block.
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable --now omo-support-broker
```

## Release gates

1. Broker unit and Nginx configuration validate.
2. Invalid, stale and replayed signatures are rejected.
3. Signed-out Worker call returns `401` before broker dispatch.
4. Authenticated chat returns `profile=omo-support`, `mode=support`.
5. Captured outbound Hermes agent has zero resolved tools.
6. Attempts to supply `maintainer`, `action`, `profile`, model or endpoint cannot expand authority.
7. No raw customer message, Clerk ID, session ID, secret, exception or internal path appears in logs.

## Remediation policy

Issue-to-PR remediation is not part of this diagnosis-only service. Its separate controller must require an existing Omo.Space issue, create a fresh isolated worktree and `fix/issue-<number>-<slug>` branch, record required tests, and allow PR creation only. It must have no merge, deploy, billing, refund, migration, force-push or destructive capability.
