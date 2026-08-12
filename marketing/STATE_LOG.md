# STATE_LOG (append-only)

Format: ISO timestamp | run | action | result | lesson
The tail (last lines) is the most recent state. Append; never rewrite history.

---
2026-08-13T00:20+06:00 | tick-001 | audited payment loop vs spec | loop is ~80% built: idempotency, billing state machine, auto-refund, $5 grant, server Stripe checkout all present; gap = 3 live secrets + Worker route + canary + magic-link grant | audit first, don't rebuild code; blockers are deployment + one feature
2026-08-13T01:05+06:00 | signup-grant-speed | traced and fixed slow $5 pill appearance | fresh Clerk accounts now show the guaranteed $5 immediately while /api/me confirms it, retry once after 1s, and ignore stale first responses; demo auth-to-$5 measured 1.8ms and billing matched | webhook was not the gate; slow /api/me enrichment must not block visible grant feedback
2026-08-13T01:19+06:00 | checkout-live-canary | deployed Worker, traced live checkout, fixed cross-request Neon I/O, added live canary and orphan-session expiry, audited 24 listings | Stripe/routing proven and unpaid canary expired; checkout now fails closed at 503 because production lacks purchases (42P01); local 22/117/11/17 and live 10/10 green | apply the full additive schema before any paid canary; session creation is not fulfillment
