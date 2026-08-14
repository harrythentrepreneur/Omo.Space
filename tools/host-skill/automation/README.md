# Automated Omo builder dispatch

This is a private, outbound-only bridge from Cloudflare's authoritative submission queue to the isolated `omo-builder` Hermes profile.

## Behaviour

1. The systemd timer runs the dispatcher every 30 seconds with jitter.
2. A nonblocking file lock prevents overlapping claims.
3. `process-submissions.py` uses the protected Cloudflare build-worker API and claims at most one queued item.
4. An empty queue exits silently and starts no model.
5. A genuinely new valid source is stored beneath `OMO_BUILD_REVIEW_ROOT` as a mode-0600 `SKILL.md` inside a mode-0700 submission directory.
6. Only `needs_review/reviewed_profile_required` wakes `omo-builder`. Uploaded source is never placed in arguments, prompts or logs; only the verified private path and source hash are supplied.
7. The first automation phase may open a verified PR but cannot merge, deploy or publish.

## Installation

Create the private root with owner `root` and mode `0700`. Install the service and timer files into `/etc/systemd/system/`, run `systemctl daemon-reload`, and enable the timer. The environment file must contain the protected build-worker base URL and token; never duplicate them into unit files.

## Verification

- `systemctl status omo-builder-dispatch.timer`
- `systemctl list-timers omo-builder-dispatch.timer`
- `journalctl -u omo-builder-dispatch.service`
- With an empty queue, the service exits 0 without a log line or Hermes session.
- For a test submission, verify Cloudflare moves `queued -> processing -> needs_review` and a new `omo-builder` session starts exactly once.

## Recovery

A nonzero dispatcher result is visible in the journal and retried on the next timer tick. A claimed submission is never silently reclaimed as queued. Review its Cloudflare status and failure code before any operator retry. Do not delete review artifacts until the related release is resolved.
