# Automated Omo builder dispatch

This is a private, outbound-only bridge from Cloudflare's authoritative submission queue to an ephemeral, isolated `omo-builder` Hermes job on Modal.

## Behaviour

1. The systemd timer runs the dispatcher every 30 seconds with jitter.
2. A nonblocking file lock prevents overlapping claims.
3. `process-submissions.py` uses the protected Cloudflare build-worker API and claims at most one queued item.
4. An empty queue exits silently and starts no model.
5. A genuinely new valid source is stored beneath `OMO_BUILD_REVIEW_ROOT` as a mode-0600 `SKILL.md` inside a mode-0700 submission directory.
6. Only `needs_review/reviewed_profile_required` launches Modal. The launch payload contains only validated submission ID, slug, source SHA-256 and a deterministic dispatch ID; it never contains source bytes or a host path.
7. The Modal job re-claims that exact reviewed submission through the protected API, persists the source in its own mode-0600 temporary file, verifies SHA-256, and starts a fresh Hermes home with messaging, memory and cron disabled.
8. The trusted root parent keeps the permanent Gemini key and exposes only a random per-run bearer through a loopback-only inference boundary. The unprivileged Hermes child receives `http://127.0.0.1:<random>/v1`, uses the fixed `gemini-2.5-flash` model, and has only `file,skills` tools. The boundary accepts only bounded `POST /v1/chat/completions` calls, fixes Google's OpenAI-compatible upstream and model, rejects redirects and host overrides, enforces a request budget, strips headers/errors, buffers bounded responses before success, and shuts down immediately after Hermes. The trusted parent—not Hermes—may open a verified PR; neither phase may merge, deploy, or publish.

## Installation

Create the private root with owner `root` and mode `0700`. Install the service and timer files into `/etc/systemd/system/`, run `systemctl daemon-reload`, and enable the timer. The host environment file needs Modal CLI authentication plus the protected build-worker base URL/token used by the claim processor; never duplicate credentials into unit files.

Deploy `tools/host-skill/modal_hermes_builder.py` as `omo-hermes-builder`. Its dedicated Modal secret must be named `omo-hermes-builder-gemini` and contain exactly the runtime credentials it needs: `GEMINI_API_KEY`, `BUILD_WORKER_BASE_URL`, `BUILD_WORKER_TOKEN`, and `GH_TOKEN`. Keep the previous secret intact for rollback; do not reuse conversational Hermes auth, messaging credentials, Stripe keys or broad Cloudflare credentials.

Run the credential-free image smoke with:

```bash
python3 -m modal run tools/host-skill/modal_hermes_smoke.py
```

## Verification

- `systemctl status omo-builder-dispatch.timer`
- `systemctl list-timers omo-builder-dispatch.timer`
- `journalctl -u omo-builder-dispatch.service`
- With an empty queue, the service exits 0 without a log line, Modal call or Hermes session.
- For a controlled test submission, verify Cloudflare moves `queued -> processing -> needs_review`, exactly one Modal call is recorded for the deterministic dispatch ID, and the conversational Hermes profile is untouched.
- Verify the Modal job reports only safe identifiers/status, never source, credentials, private paths or subprocess output.

## Recovery

A nonzero dispatcher result is visible in the journal and retried on the next timer tick. A claimed submission is never silently reclaimed as queued. Review its Cloudflare status and failure code before any operator retry. Do not delete review artifacts until the related release is resolved.
