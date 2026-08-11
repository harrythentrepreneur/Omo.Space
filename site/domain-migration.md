# `omo.space` marketplace domain migration

Migration performed on 2026-08-11 for Vercel team `harrys-projects-fdb7b42f`.

## Live domain move

Before the move, both `omo.space` and `www.omo.space` resolved to production deployment `omo-87867pgax-harrys-projects-fdb7b42f.vercel.app` (`omo-mc`). The separate `omo-minecraft` project existed, but neither hostname resolved to its deployment when inspected.

The target was the ready production deployment `cognition-2qh8zb2un-harrys-projects-fdb7b42f.vercel.app`, already serving `omo.best`. The following commands completed successfully and non-interactively:

```sh
npx vercel domains ls --scope harrys-projects-fdb7b42f
npx vercel alias ls --scope harrys-projects-fdb7b42f
npx vercel inspect https://omo.space --scope harrys-projects-fdb7b42f
npx vercel inspect https://www.omo.space --scope harrys-projects-fdb7b42f
npx vercel project inspect omo-mc --scope harrys-projects-fdb7b42f
npx vercel project inspect omo-minecraft --scope harrys-projects-fdb7b42f
npx vercel inspect cognition-2qh8zb2un-harrys-projects-fdb7b42f.vercel.app --scope harrys-projects-fdb7b42f
npx vercel alias rm omo.space --yes --scope harrys-projects-fdb7b42f
npx vercel alias set cognition-2qh8zb2un-harrys-projects-fdb7b42f.vercel.app omo.space --scope harrys-projects-fdb7b42f
npx vercel alias rm www.omo.space --yes --scope harrys-projects-fdb7b42f
npx vercel alias set cognition-2qh8zb2un-harrys-projects-fdb7b42f.vercel.app www.omo.space --scope harrys-projects-fdb7b42f
npx vercel domains add omo.space cognition --force --scope harrys-projects-fdb7b42f
npx vercel domains add www.omo.space cognition --force --scope harrys-projects-fdb7b42f
npx vercel domains verify omo.space --scope harrys-projects-fdb7b42f
npx vercel domains verify www.omo.space --scope harrys-projects-fdb7b42f
```

The two `domains add --force` calls removed the stale `omo-mc` project association and attached both hostnames persistently to `cognition`. Vercel reports both domains verified and `configured-correctly`, with no conflicts or verification challenges. No dashboard click or DNS edit was required.

## DNS and compatibility

DNS is externally hosted on `dns1.registrar-servers.com` and `dns2.registrar-servers.com`, not on Vercel nameservers. Existing records already target Vercel: the apex resolves to `216.150.1.1`, and `www` is a CNAME to `77d19481d9ba0cdf.vercel-dns-016.com`. Vercel accepted both as valid for `cognition`.

`omo.best` remains attached to the same `cognition` deployment and continues to return the marketplace with HTTP 200. This is the simplest non-interactive compatibility option; it is not yet a redirect. A strict redirect can be configured later without risking the old URL today.

Neither `api.omo.best` nor `api.omo.space` currently has a public DNS record. The owned API documentation was renamed to `api.omo.space` as requested, but that hostname must be provisioned before those absolute examples can resolve (or the examples should be changed to the same-origin `https://omo.space/api/*` routes).

## Repository changes

Updated hardcoded production references in the owned files:

- `site/key-config.js`
- `site/api.html`
- `site/index.html`
- `site/creators.html`
- `site/host.html`

`site/signup.html` had no `omo.best` reference. Relative links were left unchanged, and placeholder key values were untouched.

## Deferred concurrent-file patch

Apply `site/domain-worker-patch.md` after the sibling agent lands. Its exact changes are:

- `site/deploy/worker.js`: use `https://omo.space` for both purchase and credit-top-up Stripe success/cancel URLs; allow `https://omo.space` in production CORS while temporarily retaining `https://omo.best` for compatibility.
- `site/dashboard.html`: change the OG URL to `https://omo.space/dashboard.html`; replace both `https://cognition-demo.pages.dev` API fallbacks with `https://omo.space`.

## Other remaining legacy references

These files were outside this migration's write ownership and still need a follow-up replacement or explicit decision:

- `site/deploy/mcp-server.mjs`: top-up/dashboard URLs, API-key help URLs and text, checkout URL, MCP instructions, and the test request URL.
- `site/deploy/test-router.mjs`: Clerk `azp` and test request `Origin`.
- `site/deploy/MCP-INTEGRATION.md`: Worker route, `OMO_SITE_ORIGIN`, discovery/curl URLs, and dashboard URL.
- `site/deploy/wrangler.toml`: commented production route.
- `site/.well-known/mcp.json`: MCP server URL.
- `site/mcp.html`: OG URL, MCP endpoint/setup copy, and API-page display text.
- `site/SETUP.md`: documented production CORS origin.
- `site/clerk.js`: mock `demo@omo.best` addresses; these are example identities rather than network endpoints.

