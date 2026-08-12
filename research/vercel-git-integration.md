# Vercel Git integration

## Current configuration

The storefront repository is `harrythentrepreneur/Omo.Space` (renamed from
`harrythentrepreneur/cognition-marketplace`). It is connected to the existing
Vercel project rather than a replacement project:

- Team: `harrys-projects-fdb7b42f`
- Project: `cognition`
- Project ID: `prj_WKUlbr3EpyPzn4BuVfEmEy3QAHlF`
- Production branch: `main`
- Production domains: `omo.best`, `omo.space`, and `www.omo.space`

## What was wrong

The Vercel project was linked to `harrythentrepreneur/cognition`, not the
storefront repository. Storefront pull requests therefore received no Vercel
preview builds or checks, merges did not trigger production deployments, and
Vercel's repository link opened the wrong repository.

## What changed

On 2026-08-12, the storefront repository was renamed to `Omo.Space`, the local
Git remote was updated to the renamed HTTPS URL, and the existing Vercel
project's Git integration was connected to `harrythentrepreneur/Omo.Space`.
The project ID, environment configuration, deployment history, and production
domain aliases were preserved.

## How to verify the integration

For future pull requests:

1. Open a pull request against `main` in `harrythentrepreneur/Omo.Space`.
2. Confirm GitHub reports the `Vercel` check (and, when enabled, Vercel Preview
   Comments).
3. Open the preview URL from the check and confirm the proposed revision is
   running.
4. After merging, confirm Vercel creates a production deployment from the merge
   commit and keeps `omo.best` and `omo.space` assigned to project
   `prj_WKUlbr3EpyPzn4BuVfEmEy3QAHlF`.

Useful commands:

```bash
gh pr checks <PR_NUMBER> --repo harrythentrepreneur/Omo.Space
npx vercel project inspect cognition --scope harrys-projects-fdb7b42f
npx vercel alias ls --scope harrys-projects-fdb7b42f
```

Manual deployments at
`https://cognition-fh8t18gii-harrys-projects-fdb7b42f.vercel.app` continue to
work as before, but the repaired Git integration is the normal path for pull
request previews and `main` production deployments.
