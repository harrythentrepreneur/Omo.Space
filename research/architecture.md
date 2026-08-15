# How Omo works

Omo is a marketplace for small AI helpers. Omo calls each helper a **workflow** or a **skill**.

A `SKILL.md` file is the starting description. It says what the helper should do. It is not the live program by itself.

Omo has two main sides:

- The **storefront** is the website people see.
- The **service layer** checks identity, money, inputs, and runs the helper.

There are also two kinds of people:

- A **creator** submits a `SKILL.md`.
- A **buyer** can run the hosted helper or buy the workflow and prompts.

## The short version

```text
Creator -> upload SKILL.md -> review and builder -> generated app -> Modal

Buyer -> Omo website -> Cloudflare Worker -> Modal app -> result
                         |       |      |
                         |       |      +-> Stripe for payments
                         |       +--------> Neon for wallet and records
                         +----------------> Clerk for sign-in
```

The Cloudflare Worker is the front door for every API request. It decides who may do what. It also owns the price and the hosted address. The browser does not get to choose them.

## The two doors

Every active workflow can show two choices.

### Door 1: run it for me

The buyer signs in and fills out a form. Omo runs the helper in the cloud. The buyer pays only for that run.

The browser sends the request to `/api/run`. The Cloudflare Worker checks the person, the workflow, the input, and the wallet. For a generated Modal workflow, the Worker then calls the private Modal app. The browser never receives the Modal credentials.

### Door 2: let me own it

The buyer pays once for the workflow and prompts. The workflow page calls `/api/checkout`. The Worker looks up the license price in its own catalog and creates a Stripe Checkout session.

Stripe later sends a signed payment event to Omo. The Worker records the completed license purchase in Neon.

**Current boundary:** the checkout and purchase record are real. The inspected Worker records a purchase “for later download/ownership fulfillment.” It does not contain the secure file-delivery step. The product UI describes a download link, but the final automatic delivery of the `SKILL.md` bundle should be treated as **coming next** until that delivery path is verified end to end.

The license payment and the run wallet are separate. Buying a workflow does not add run credits. Adding run credits does not buy the downloadable workflow.

## The storefront: the Vercel frontend

The `site/` folder is a static website served by Vercel. “Static” means the pages are HTML, CSS, and JavaScript files. There is no application server inside the Vercel pages.

The main pieces are:

- `index.html` is the public marketplace home.
- `dashboard.html` shows the catalog, wallet, run history, and API key for a signed-in user.
- `workflow.html` is one workflow's sales and detail page. It shows the two doors.
- `run.html` builds the input form, starts a hosted run, polls its status, and renders or downloads the result.
- `catalog.js` is the browser catalog. It contains names, prices, images, descriptions, form hints, and workflow metadata.
- `OMO_VISIBLE_SLUGS` is a reversible storefront whitelist. At the time of this review it exposes 13 workflow slugs. `OMO_VISIBLE_CATALOG` is the full catalog filtered through that list.
- `nav.js` supplies the shared navigation and Clerk sign-in state.
- `menu-workflows.js` adds a signed-in person's workflow shortcuts to the shared menu.

The catalog in the browser is for display. It is not trusted for billing. The Worker keeps its own server catalog and generated hosted registry. That stops a buyer from changing a price or private endpoint in browser tools.

The whitelist controls the main storefront, dashboard, run page, and menu surfaces. It is not a complete access wall for detail pages: `workflow.html` reads the full catalog, so a direct URL can still render a hidden listing's detail page. The Worker registry and server checks decide whether it can really run or charge.

## Identity: Clerk

Clerk handles sign-up and sign-in.

The browser asks Clerk for a session token. A token is a short proof that says who is signed in. The browser sends it to the Worker as a bearer token.

The Worker verifies the token using Clerk's public signing keys. It does not trust a user ID typed by the browser in production mode.

Clerk also sends a signed `user.created` webhook to the Worker. This creates the Omo account and the starter wallet grant. A first call to `/api/me` can create the same record if the webhook has not arrived yet. The database insert is idempotent (safe to repeat), so the $5 grant is not added twice.

## The wallet and money flow

The wallet is the user's balance in the database.

Neon stores the balance as `balance_cents`. Storing cents as a whole number avoids floating-point money mistakes.

The normal flow is:

1. A new account receives 500 cents, or $5.
2. `/api/me` returns the current balance and recent runs.
3. Each catalog workflow has a server-owned price per run.
4. Before Omo spends money on a provider, the Worker reserves that price from the wallet.
5. If the run succeeds, the debit stays in the ledger.
6. If the run fails, the Worker writes a matching refund and restores the wallet.
7. If the balance is too low, the Worker returns `402 insufficient_balance`. It does not call Modal.
8. The buyer can call `/api/topup` to open a separate Stripe Checkout session. A signed Stripe webhook adds those credits exactly once.

Every real run needs an idempotency key (a retry-safe request name). The Worker claims that key before taking credits. Two copies of the same request cannot both charge the wallet. Reusing the key with different input is rejected.

The current pricing tool uses the cost model in `site/deploy/cost-model.mjs`, a 5× launch markup, and a $0.10 minimum. Unknown or unpriced costs must make a workflow non-chargeable.

## Neon: the system record

Neon is the main PostgreSQL database. PostgreSQL is a structured database made of tables and rows.

The important records are:

- `users`: account ID, wallet balance, and API-key data.
- `credits_ledger`: every signup grant, top-up, run debit, and run refund.
- `run_requests`: the durable state and retry key for each real run.
- `run_progress`: status for longer Modal runs.
- `runs`: older/simple run history.
- `stripe_topups` and `topup_sessions`: wallet payment state.
- `purchases`: one-time workflow license purchases.
- `waitlist`: launch-interest signups.
- `submissions`: creator uploads and every build/release state.
- `stripe_events`: payment-webhook retry protection.

The Worker can use Cloudflare D1 as a fallback. It can also use an in-memory mock for local tests. Production is described and configured around Neon.

## The Cloudflare Worker: the middle of everything

`site/deploy/worker.js` is the `cognition-demos` Cloudflare Worker behind the Omo API.

It is both a router and a guard. Its public routes include:

- `/api/run` and `/api/run/:id` for starting and reading runs.
- `/api/me` for wallet, API key, and run history.
- `/api/checkout` for a one-time workflow license.
- `/api/topup` for wallet credits and Stripe webhook fulfillment.
- `/api/submit` for creator Markdown.
- `/api/submissions` for a creator's build status.
- `/api/waitlist` for public waitlist entries.

It also has protected internal submission routes. The local build worker uses these to claim one queued item and report build, runtime, deployment, and release state.

The Worker imports `hosted-skills.generated.mjs`. That generated file is the server registry. It maps an approved public slug to:

- the input and output rules;
- the price per run;
- the runtime kind;
- the server-owned model or Modal endpoint;
- the names of the private credential settings.

Simple, tightly bounded one-model workflows may run through a reviewed provider call inside the Worker. More complex generated workflows use Modal. Older profiles default to Modal unless they are regenerated with an explicit placement decision. In the current generated registry, 1 listing is Worker-native and 11 are Modal-hosted. The Japanese-style video has a separate pinned Modal branch outside that generated registry.

## What happens in one real hosted run

This is the exact generated Modal path.

1. The buyer opens `run.html` for a visible workflow.
2. The page loads the run manifest. It turns the input schema into a form.
3. Clerk supplies a signed session token.
4. The page sends the slug, input, token, and idempotency key to `POST /api/run`.
5. The Worker finds the slug in `hosted-skills.generated.mjs`.
6. The Worker verifies the Clerk token or an Omo API key.
7. The Worker validates the input against the server-owned JSON Schema (a strict list of allowed fields and types).
8. The Worker loads the account, fixes any stale reservation, and claims the retry key.
9. The Worker reserves the exact run price in Neon. Low balance stops here, before provider spend.
10. The Worker sends the input to the Modal app at `/v1/runs` with `Modal-Key` and `Modal-Secret` proxy headers. Those values stay inside the Worker.
11. Modal returns `202 Accepted` with a call ID and a result path. The Worker returns an Omo run ID and status URL to the browser.
12. `run.html` polls `GET /api/run/:id`.
13. The Worker polls Modal using the saved private result path.
14. When Modal finishes, the Worker checks the output against the server-owned output schema.
15. If it is valid, the Worker marks the run `succeeded`. The reserved debit remains final.
16. The page renders the structured result. It can also make a local download from that result.
17. If dispatch, polling, or output validation fails, the Worker marks the run `refunded` and restores the reserved credits.

The browser talks only to Omo. It never talks directly to Neon and never receives database, Stripe, provider, or Modal secrets.

## How a `SKILL.md` becomes a hosted skill

### 1. Upload

A signed-in creator sends a name and Markdown to `/api/submit`.

The Worker treats the file as hostile data, not as instructions. It checks the size, frontmatter, name, and slug. It stores the source and a SHA-256 fingerprint in the `submissions` table. A fingerprint is a one-way identity for the exact bytes.

The first state is `queued`. Sending the same source twice for the same creator returns the same submission instead of creating two builds.

### 2. Claim and private review

`process-submissions.py` can claim the oldest queued item through a protected internal API. It handles at most one item.

The file is copied only to a locked private review folder when that folder is configured. The processor checks the hash again. It never runs commands from the uploaded Markdown.

A new skill normally stops at `needs_review/reviewed_profile_required`. This is intentional. A human or the Hermes builder must create a reviewed profile before executable code can be generated.

### 3. The Hermes builder

The `omo-builder` Hermes profile is a smart agent that reads the approved `SKILL.md` and builds the backend for it.

Its one-shot loop is:

1. Verify the exact source and promise.
2. Research required providers, limits, prices, and rights.
3. Write the smallest reviewed runtime profile.
4. Compile the generated app.
5. Test schemas, happy paths, bad inputs, semantics, costs, and failure behavior.
6. Fix shared compiler or runtime problems, then regenerate.
7. Calculate a chargeable price only when costs are known.
8. Return either a release candidate or a typed blocker with evidence and a resume point.

The builder cannot create accounts, accept terms, read secrets, spend money, message customers, merge, deploy, or move production traffic by itself.

### 4. Compile

`packages/skill-to-modal/compiler.py` combines two things:

- the creator's reviewed `SKILL.md`;
- a trusted JSON profile that defines strict inputs, outputs, prompt, provider, limits, readiness, fixtures, and pricing inputs.

It generates `containers/<slug>/`, including:

- `modal_app.py`: the runnable Modal/FastAPI backend;
- input and output JSON Schemas;
- a vendored copy of the source `SKILL.md`;
- prompts and approved assets;
- a manifest and capability report;
- contract tests and test cases;
- a pricing report.

The generated Modal app exposes proxy-protected `/v1/runs` and result routes. It rejects invalid input before starting provider work. A blocked profile returns unavailable instead of pretending to run.

### 5. Test and price

`tools/host-skill/host.py` runs the compiler and then runs:

- compiler and host-tool tests;
- the generated container contract test;
- pricing verification.

It checks that the manifest and pricing report agree. The output is either ready for the next gate or blocked.

### 6. Register

With `--register`, the hosting tool generates four public/server contracts:

- `containers/<slug>/hosted-profile.json`;
- `site/run-manifests/<slug>.json` for the browser form;
- the catalog entry in `site/catalog.js`;
- the runtime row in `site/deploy/hosted-skills.generated.mjs`.

Registration does not make the workflow live by itself.

### 7. Deploy and list

The release processor can, with explicit production approval, deploy the generated app to Modal, run a direct canary, register it, run the Worker suites, and deploy the Worker registry.

A listing is truly live only after all of these are true:

- Modal deployment succeeded.
- The direct Modal canary returned a valid result.
- The generated registry contains the slug.
- The Cloudflare Worker was deployed with that registry.
- A live `/api/run` smoke check resolves the slug.
- The storefront whitelist includes the slug when public visibility is wanted.

Production promotion remains a human gate.

## What is real, and what is coming next

### Real in this repository

- The Vercel storefront pages and shared navigation.
- The full catalog and 13-slug visibility whitelist.
- Clerk sign-in and Worker-side token verification.
- The $5 idempotent signup grant.
- Neon wallet, ledger, run, payment, waitlist, and creator-submission tables.
- Separate Stripe license checkout and wallet top-up flows.
- Retry-safe credit reservation, success settlement, and automatic failure refund.
- Creator upload, queue state, protected build-worker API, runtime choices, and typed blockers.
- The compiler, generated containers, contract tests, pricing checks, and registration generator.
- Generated Worker-native and Modal-hosted registry support.
- Modal proxy authentication held by the Worker.

### Coming next or still human-gated

- The repository contains dispatcher service/timer templates, but the builder's own rules say they must not be assumed installed. The queue-to-Hermes wake-up bridge is **coming next until installed and verified**.
- New skills still need a reviewed profile. The builder may prepare it, but uploaded Markdown never approves itself.
- PR, merge, Modal deployment, Worker deployment, catalog publication, billing canary, and traffic promotion require explicit approval.
- The one-time license checkout records ownership, but the secure automatic `SKILL.md` bundle delivery is **coming next until verified**.
- The larger “mega-agent/autopilot” control plane is a plan. Today's working path is the smaller agent-assisted compiler, test, pricing, and release path described above.

## The simplest mental model

- **Vercel is the shop window.**
- **Clerk is the ID desk.**
- **The Cloudflare Worker is the front door and cashier.**
- **Neon is the wallet and record book.**
- **Stripe moves payment money.**
- **The builder turns an approved description into a tested backend.**
- **Modal is the workshop where hosted skills run.**
- **The generated registry is the Worker’s trusted address book.**

No single piece does everything. The Worker ties them together and keeps identity, price, wallet rules, private addresses, and secrets out of the browser.
