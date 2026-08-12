# Payment-loop spec + canary checklist (Omo pilot, week 1)

**Owner:** Kaviru + AI agents (built) / Harry (approves, sends email)
**Goal:** make ONE first-party workflow — the Phonics book maker — trustworthy enough
that a real teacher can pay, receive the result, be refunded automatically on failure,
and come back to pay again.

Scope is deliberately ONE workflow. Do not generalize to the marketplace yet.

## Build items (each with acceptance criteria)

### 1. Stripe production + credit packs
- [ ] Turn ON Stripe production keys for the pilot path.
- [ ] Sell prepaid credit packs. Minimum top-up $5. Do NOT process individual
      $0.99 card charges (fees eat them).
- [ ] Replace blanket "$5 signup credit" with a single "one free book" grant.
      No open-ended promotional credit — it is an abuse vector on a tight budget.

### 2. Immutable credit ledger
- [ ] Every grant, debit, credit, and refund is an append-only ledger row.
- [ ] A failed validation costs $0 and records nothing billable.
- [ ] Ledger and Stripe reconcile to the cent every night.

### 3. One-click magic link (the funnel)
- [ ] Email contains a signed, single-use, time-boxed magic link.
- [ ] Link lands the user AUTHENTICATED and directly in the book builder —
      NOT the homepage, NOT a signup form, NOT a four-field registration.
- [ ] Deep-link carries the "free book" grant so the first run is already paid for.

### 4. Automatic refund on failure
- [ ] Any run that fails validation, times out, errors on a provider call, or
      returns no usable output → full automatic credit refund, zero manual steps.
- [ ] Refund event is written to the ledger and emailed to the user within minutes.

### 5. Idempotency (no double charges)
- [ ] One request id = exactly one charge. Double-click / resubmit / retry
      must not create a second charge.

### 6. Support discipline
- [ ] One inbox: support@phonicsmaker.com.
- [ ] Two fixed support windows per day; every ticket answered <4h, resolved <24h.
- [ ] Refund macro: "Refunded in full — you should see the credit immediately.
      Sorry for the trouble. What went wrong so I can fix it?"
- [ ] Failure macro: "Your book didn't generate — I've refunded it automatically.
      Try once more with the link, or reply and I'll build it for you."

### 7. Hide unrunnable listings
- [ ] On omo.space, hide or label "not yet available" every listing that cannot
      currently be bought and successfully delivered. A "proven workflows"
      storefront cannot open with ambiguous proof.

## Canary checklist (run all 20 before any email)

| # | Scenario | Expected |
|---|---|---|
| 1-5 | Valid input, happy path | correct output, correct single charge, receipt, delivered |
| 6 | Empty input | clean error, $0 charged |
| 7 | Malformed input | clean error, $0 charged |
| 8 | Run timeout | auto-refund, error surfaced |
| 9 | Provider failure (image gen / LLM down) | auto-refund, error surfaced |
| 10 | Duplicate submit (double-click) | ONE charge only |
| 11 | Retry after failure | works, no stale charge |
| 12 | Refund path | credit returned, ledger correct |
| 13 | Magic link reuse (second click) | rejected or re-auths cleanly, no double grant |
| 14 | Magic link after expiry | clean expiry, no grant |
| 15 | Two concurrent runs | both succeed, charges distinct and correct |
| 16 | Large / unusual input | bounded, no runaway cost, clean result or error |
| 17 | Free-book grant consumed once | second run correctly priced |
| 18 | Credit balance insufficient | clear top-up prompt, no partial charge |
| 19 | Receipt email | arrives, correct amount |
| 20 | Full end-to-end: email → magic link → free book → pay $0.99 → second book | completes with correct ledger |

## Acceptance gates (all must pass before the 200-email goes out)

- [ ] >=95% valid-output success across the 20 canaries
- [ ] 0 duplicate charges
- [ ] 100% automatic refund on failed runs
- [ ] Delivered COGS measured and reconciled (actual model + image + PDF cost)
- [ ] <5% refund / serious-complaint rate
- [ ] Support responded <4h and resolved <24h on every canary ticket
