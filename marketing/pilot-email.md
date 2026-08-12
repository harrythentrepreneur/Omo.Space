# Pilot email — 200-user cohort (finalized) + follow-ups

**Sends from the PhonicsMaker identity, not "Omo."** Harry signs as himself.
The list is moved under the PhonicsMaker brand (UK "soft opt-in" rules restrict
jumping to a differently-branded product). Get privacy counsel to sign off before
sending if you cross borders.

## Segmentation (who gets the email)

Include: recently active, opted-in, non-paying or recently-churned PhonicsMaker users.
Exclude: unsubscribes, bounces, and current paying subscribers (protect the $5k MRR).

## Main email (send Thursday, after the 20 canaries pass)

Subject: PhonicsMaker without a subscription — one book for $0.99

Body:

> Hi [First name],
>
> You used PhonicsMaker before. We're testing a simpler way to use it:
> make one printable phonics book when you need it, pay $0.99, and keep it.
> No subscription.
>
> I've added one free book to your account so you can try it:
> [Make my book]
>
> If anything goes wrong, reply directly and I'll personally fix it.
>
> — Harry

## Follow-up 1 — non-openers (48h)

Subject: Your free book is waiting

> Hi [First name] — quick one. I put a free book in your PhonicsMaker account.
> One click, make a printable phonics book, keep it. No subscription, no card.
>
> [Make my book]
>
> — Harry

## Follow-up 2 — opened but didn't make a book (day 5)

Subject: One teacher made this in 30 seconds

> Hi [First name] — a teacher made this decodable book in about 30 seconds
> and used it the same morning. Yours is still sitting there, free:
>
> [Make my book]
>
> Make one book, pay $0.99 only if you want more. No subscription.
>
> — Harry

## Follow-up 3 — made the free book but didn't pay (day 10)

Subject: Want another book? It's $0.99

> Hi [First name] — glad you made your book. If it was useful, the next one is
> $0.99, and you only ever pay when you make one. No subscription.
>
> [Make another book]
>
> If something about it wasn't right, tell me — I'll fix it for you.
>
> — Harry

## Sending rules

- Plain text, one link, personal sign-off. No HTML, no images, no "Omo" branding.
- The link is a signed magic link straight into the book builder (see
  payment-loop-spec.md), carrying the free-book grant.
- Send from the PhonicsMaker domain; monitor replies personally and answer <24h.
- Log opens, clicks, free books made, and paid second books per recipient.

## The metric (decides everything)

Primary: >=25% of users who successfully make the free book must fund and complete
a second, paid book within 14 days.

Minimum useful signal from the 200:
- >=20 successful first books
- >=5 paid second books within 14 days
- >=95% valid-output success
- 0 double-charges, auto-refund on failure
- <5% refund/complaint rate

If fewer than 3 users complete a paid second book: STOP, do not email the rest of
the list, interview 10 users, fix the job/output/price/onboarding, re-run a smaller
cohort.
