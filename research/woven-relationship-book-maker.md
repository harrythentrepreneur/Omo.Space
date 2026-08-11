# Woven Relationship Book Maker — server-catalog follow-up

The browser catalog loads `site/ig-more.js` automatically in both `index.html`
and `dashboard.html`. The Worker does not: `site/deploy/worker.js` owns a static
`CATALOG_ROWS` snapshot and ignores client-supplied workflow, prompt, and price
values in real mode.

Per the concurrent-edit boundary, this launch does **not** edit `worker.js`.
Until a separate server-catalog change adds `woven-relationship-book-maker`,
local/mock dashboard runs and simulated purchases work, but authenticated
real-mode `/api/run` and configured-Stripe `/api/checkout` calls will reject the
slug as unknown. The future row must pin these server-owned values:

- name: `Woven Relationship Book Maker`
- one-time license: `$29`
- run price: `$0.10`
- model: `deepseek-v4-flash`
- output contract: `{ "book": "Markdown story", "page_plan": ["page note"] }`
- safety: use only supplied relationship facts; never invent names, dates,
  events, or quotations

This is a normal generic `/api/run` text workflow, not a dedicated Modal
container. Its honest hosted deliverable is a Markdown relationship-book draft
plus a PDF-ready page plan; it does not claim to render or return a finished PDF.

The server follow-up should add router coverage proving that the slug ignores
client prompt/price overrides, debits exactly 10 cents, honors the 402 flow, and
pins checkout to $29 before production traffic is enabled.
