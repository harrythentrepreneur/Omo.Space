# Changelog

This file records the public history of Omo.Space. The first stable release covers the project from its initial commit on 9 August 2026 through `v0.1.0` on 22 August 2026.

The phase summaries are curated for readability. The collapsed appendix is generated from GitHub's merged pull-request records, filtered to commits contained in the release tag.

## [v0.1.0] - 2026-08-22

This first stable release includes the full project history from the initial commit on 9 August 2026 through `v0.1.0` on 22 August 2026: **397 commits and 126 merged pull requests**.

### Phase 1: storefront, accounts and deterministic hosting

- Built the original marketplace and account experience, including Clerk navigation and recoverable sign-out.
- Added the deterministic `SKILL.md` to Modal compiler and the first reviewed runtime candidates.
- Introduced runtime placement decisions so approved workflows can run Worker-native or on Modal.
- Added cached billing state and server-owned execution paths.

### Phase 2: creator intake and Git-backed releases

- Replaced mock creator uploads with a durable submission queue and fixed schema migration gate.
- Added authenticated creator review, collision handling, safe retry and state restoration after refresh.
- Bound approved submissions to Git issues, branches, pull requests, CI and merge evidence.
- Released the Woven Storybook and Customer Feedback Theme Finder workflows through the reviewed path.

### Phase 3: isolated builders and support

- Added isolated Hermes builders on Modal and direct Cloudflare-to-Modal build dispatch.
- Added bounded leases, stale-claim recovery and safe builder failure stages.
- Separated Modal execution from GitHub release authority and reverted unsafe approval bypasses.
- Added the in-product Omo Support agent with contextual guest support.

### Phase 4: compiler hardening and deterministic canaries

- Added image-style and rendering foundations, rooted compiler resources and chart prerequisites.
- Pinned builder dependencies and made Worker contracts portable to the trusted Node runtime.
- Added the deterministic label-normalizer executor and cross-container polling.
- Made compile gates baseline-aware, precise and revision-bound.
- Added safe merged-release recovery and stale creator-claim recovery.

### Phase 5: marketplace expansion and product hardening

- Published reviewed Meta Ads and UGC workflows from skills.sh sources.
- Hardened authentication against stale session credentials.
- Added production-facing workflow cards and supporting research while reverting unready hero experiments.

### Phase 6: trusted staging and production finalization

- Built the finalizer state machine, credential-free trigger and controlled provider transport.
- Added fixed staging environments, durable canary state and protected release paths.
- Added production provider adapters, canonical deployment receipts, schema migrations and typed HTTP diagnostics.
- Added exact production canary seeding, schedule reconciliation and scoped builder inference.
- Released the label-normalizer canary through the real Git-backed submission lifecycle.

### Phase 7: stable-release hardening

- Added squash-merge provenance recovery and exact Git history checks.
- Made Modal and Cloudflare deployment adoption idempotent.
- Added provider readback, receipt reconciliation and append-only recovery history.
- Stabilized production canary authentication and accepted the live `completed` terminal contract.
- Verified the canonical `/run` publication route and completed authoritative production promotion.

### Changes from RC1 to stable

GitHub generated 17 merged changes between `v0.1.0-rc.1` and `v0.1.0`, covering PRs [#181](https://github.com/harrythentrepreneur/Omo.Space/pull/181) through [#197](https://github.com/harrythentrepreneur/Omo.Space/pull/197).

- [RC1 to stable comparison](https://github.com/harrythentrepreneur/Omo.Space/compare/v0.1.0-rc.1...v0.1.0)
- [Initial commit to v0.1.0 comparison](https://github.com/harrythentrepreneur/Omo.Space/compare/d68364d0b57a21185f55f8eebae8ce153bcd4cd4...v0.1.0)
- [Complete commit history for v0.1.0](https://github.com/harrythentrepreneur/Omo.Space/commits/v0.1.0)

<details>
<summary>Complete automatically generated merged PR list (126)</summary>

- [#3](https://github.com/harrythentrepreneur/Omo.Space/pull/3) fix(auth): update navigation after Clerk login by @harrythentrepreneur
- [#5](https://github.com/harrythentrepreneur/Omo.Space/pull/5) Document repaired Vercel Git integration by @harrythentrepreneur
- [#7](https://github.com/harrythentrepreneur/Omo.Space/pull/7) fix(auth): make sign-out complete and recoverable by @harrythentrepreneur
- [#9](https://github.com/harrythentrepreneur/Omo.Space/pull/9) Compile supported SKILL.md workflows to Modal by @harrythentrepreneur
- [#11](https://github.com/harrythentrepreneur/Omo.Space/pull/11) Add media-sequential compiler proof by @harrythentrepreneur
- [#12](https://github.com/harrythentrepreneur/Omo.Space/pull/12) Revert media-sequential proof pending review fixes by @harrythentrepreneur
- [#17](https://github.com/harrythentrepreneur/Omo.Space/pull/17) Route Facebook Ads Worker calls to OMOSpace Modal by @harrythentrepreneur
- [#19](https://github.com/harrythentrepreneur/Omo.Space/pull/19) feat: let Hermes classify workflow runtime placement by @harrythentrepreneur
- [#20](https://github.com/harrythentrepreneur/Omo.Space/pull/20) perf: show cached billing data while refreshing by @harrythentrepreneur
- [#21](https://github.com/harrythentrepreneur/Omo.Space/pull/21) feat: execute reviewed workflows in selected runtime by @harrythentrepreneur
- [#22](https://github.com/harrythentrepreneur/Omo.Space/pull/22) feat: add executable audio animation fixture runtime by @harrythentrepreneur
- [#23](https://github.com/harrythentrepreneur/Omo.Space/pull/23) feat: add private submission build bridge by @harrythentrepreneur
- [#24](https://github.com/harrythentrepreneur/Omo.Space/pull/24) feat: add fixed submission schema migration gate by @harrythentrepreneur
- [#26](https://github.com/harrythentrepreneur/Omo.Space/pull/26) fix: bootstrap production submissions schema by @harrythentrepreneur
- [#27](https://github.com/harrythentrepreneur/Omo.Space/pull/27) fix: restore creator submissions after refresh by @harrythentrepreneur
- [#28](https://github.com/harrythentrepreneur/Omo.Space/pull/28) fix: identify private build worker HTTP client by @harrythentrepreneur
- [#29](https://github.com/harrythentrepreneur/Omo.Space/pull/29) feat: add secure creator web approval flow by @harrythentrepreneur
- [#30](https://github.com/harrythentrepreneur/Omo.Space/pull/30) fix: inherit reviewed runtime and retry gated builds by @harrythentrepreneur
- [#32](https://github.com/harrythentrepreneur/Omo.Space/pull/32) Gate creator workflows through verified Git releases by @harrythentrepreneur
- [#34](https://github.com/harrythentrepreneur/Omo.Space/pull/34) Allow retry after approved canary-gate failure by @harrythentrepreneur
- [#36](https://github.com/harrythentrepreneur/Omo.Space/pull/36) Release woven-storybook-pipeline submission sub_08b017bc6b22fca3112dead68f19f4a2 by @harrythentrepreneur
- [#38](https://github.com/harrythentrepreneur/Omo.Space/pull/38) Support protected release-record reads by @harrythentrepreneur
- [#40](https://github.com/harrythentrepreneur/Omo.Space/pull/40) Install locked Worker dependencies before release deploy by @harrythentrepreneur
- [#42](https://github.com/harrythentrepreneur/Omo.Space/pull/42) Fix submission progress restoration after refresh by @harrythentrepreneur
- [#43](https://github.com/harrythentrepreneur/Omo.Space/pull/43) Automate isolated Omo builder dispatch by @harrythentrepreneur
- [#46](https://github.com/harrythentrepreneur/Omo.Space/pull/46) Allow reviewed submissions to retry gated builds by @harrythentrepreneur
- [#45](https://github.com/harrythentrepreneur/Omo.Space/pull/45) Release customer-feedback-theme-finder submission sub_6166d8f473593cc2c565e77574f5d7f9 by @harrythentrepreneur
- [#47](https://github.com/harrythentrepreneur/Omo.Space/pull/47) Fix customer feedback canary schema compliance by @harrythentrepreneur
- [#48](https://github.com/harrythentrepreneur/Omo.Space/pull/48) Give customer feedback workflow an explicit output shape by @harrythentrepreneur
- [#49](https://github.com/harrythentrepreneur/Omo.Space/pull/49) Publish customer feedback workflow in storefront catalog by @harrythentrepreneur
- [#50](https://github.com/harrythentrepreneur/Omo.Space/pull/50) Make feedback arrays a normal multiline input by @harrythentrepreneur
- [#53](https://github.com/harrythentrepreneur/Omo.Space/pull/53) feat: run isolated Hermes builders on Modal by @harrythentrepreneur
- [#55](https://github.com/harrythentrepreneur/Omo.Space/pull/55) Add isolated in-product Omo Support Hermes chat by @harrythentrepreneur
- [#56](https://github.com/harrythentrepreneur/Omo.Space/pull/56) fix(support): use production broker route by @harrythentrepreneur
- [#57](https://github.com/harrythentrepreneur/Omo.Space/pull/57) Allow contextual guest support chat by @harrythentrepreneur
- [#64](https://github.com/harrythentrepreneur/Omo.Space/pull/64) Dispatch creator builds from Cloudflare directly to Modal by @harrythentrepreneur
- [#66](https://github.com/harrythentrepreneur/Omo.Space/pull/66) Recover stale Modal builder dispatch leases by @harrythentrepreneur
- [#68](https://github.com/harrythentrepreneur/Omo.Space/pull/68) Expose safe creator builder failure stages by @harrythentrepreneur
- [#70](https://github.com/harrythentrepreneur/Omo.Space/pull/70) Load Modal processor sibling modules safely by @harrythentrepreneur
- [#72](https://github.com/harrythentrepreneur/Omo.Space/pull/72) Enable bounded non-interactive Modal builds by @harrythentrepreneur
- [#73](https://github.com/harrythentrepreneur/Omo.Space/pull/73) Revert unsafe Modal builder approval bypass by @harrythentrepreneur
- [#74](https://github.com/harrythentrepreneur/Omo.Space/pull/74) Isolate Modal Hermes from GitHub release authority by @harrythentrepreneur
- [#76](https://github.com/harrythentrepreneur/Omo.Space/pull/76) Expose owner retry for pre-runtime canary failures by @harrythentrepreneur
- [#78](https://github.com/harrythentrepreneur/Omo.Space/pull/78) Fix Modal Hermes startup dependency by @harrythentrepreneur
- [#80](https://github.com/harrythentrepreneur/Omo.Space/pull/80) Allow retry after pre-runtime builder failure by @harrythentrepreneur
- [#82](https://github.com/harrythentrepreneur/Omo.Space/pull/82) Expose and harden trusted builder failures by @harrythentrepreneur
- [#83](https://github.com/harrythentrepreneur/Omo.Space/pull/83) Align Worker builder revision pin by @harrythentrepreneur
- [#85](https://github.com/harrythentrepreneur/Omo.Space/pull/85) Image style system (issue #84) by @harrythentrepreneur
- [#89](https://github.com/harrythentrepreneur/Omo.Space/pull/89) Install pytest in trusted builder image by @harrythentrepreneur
- [#91](https://github.com/harrythentrepreneur/Omo.Space/pull/91) Reddit research: SEO playbook + skill sourcing (issue #90) by @harrythentrepreneur
- [#93](https://github.com/harrythentrepreneur/Omo.Space/pull/93) Restore credential strategy doc by @harrythentrepreneur
- [#94](https://github.com/harrythentrepreneur/Omo.Space/pull/94) Add deterministic label-normalizer canary executor by @harrythentrepreneur
- [#95](https://github.com/harrythentrepreneur/Omo.Space/pull/95) Align trusted builder revision with merged canary fix by @harrythentrepreneur
- [#96](https://github.com/harrythentrepreneur/Omo.Space/pull/96) Make deterministic canary polling cross-container safe by @harrythentrepreneur
- [#97](https://github.com/harrythentrepreneur/Omo.Space/pull/97) Align trusted builder with cross-container canary fix by @harrythentrepreneur
- [#98](https://github.com/harrythentrepreneur/Omo.Space/pull/98) Make trusted compile gate baseline-aware by @harrythentrepreneur
- [#99](https://github.com/harrythentrepreneur/Omo.Space/pull/99) Align trusted builder with compile gate fix by @harrythentrepreneur
- [#100](https://github.com/harrythentrepreneur/Omo.Space/pull/100) Make compile-gate exclusions precise by @harrythentrepreneur
- [#101](https://github.com/harrythentrepreneur/Omo.Space/pull/101) Align trusted builder with precise compile gate by @harrythentrepreneur
- [#102](https://github.com/harrythentrepreneur/Omo.Space/pull/102) Root compiler resources and chart prerequisites by @harrythentrepreneur
- [#103](https://github.com/harrythentrepreneur/Omo.Space/pull/103) Align trusted builder with rooted chart gate by @harrythentrepreneur
- [#104](https://github.com/harrythentrepreneur/Omo.Space/pull/104) Include trusted compiler test dependencies by @harrythentrepreneur
- [#105](https://github.com/harrythentrepreneur/Omo.Space/pull/105) Align trusted builder with dependency fix by @harrythentrepreneur
- [#106](https://github.com/harrythentrepreneur/Omo.Space/pull/106) fix: make trusted Worker contracts pass on Node 18 by @harrythentrepreneur
- [#107](https://github.com/harrythentrepreneur/Omo.Space/pull/107) fix: align trusted revision with Node 18 contract fix by @harrythentrepreneur
- [#109](https://github.com/harrythentrepreneur/Omo.Space/pull/109) fix: scope identity for trusted release commits by @harrythentrepreneur
- [#110](https://github.com/harrythentrepreneur/Omo.Space/pull/110) fix: align trusted pin with release commit fix by @harrythentrepreneur
- [#111](https://github.com/harrythentrepreneur/Omo.Space/pull/111) Release label-normalizer-canary submission sub_0c34a83ec6b12cc24826d97ad083057f by @harrythentrepreneur
- [#113](https://github.com/harrythentrepreneur/Omo.Space/pull/113) fix: resume verified merged releases safely by @harrythentrepreneur
- [#122](https://github.com/harrythentrepreneur/Omo.Space/pull/122) fix(auth): prevent stale session credentials by @harrythentrepreneur
- [#124](https://github.com/harrythentrepreneur/Omo.Space/pull/124) fix: reclaim stale creator submission claims by @harrythentrepreneur
- [#131](https://github.com/harrythentrepreneur/Omo.Space/pull/131) Add Hermes Profiles and Bots to hero rotation by @harrythentrepreneur
- [#133](https://github.com/harrythentrepreneur/Omo.Space/pull/133) Revert Hermes Profiles and Bots hero rotation by @harrythentrepreneur
- [#128](https://github.com/harrythentrepreneur/Omo.Space/pull/128) feat: publish skills.sh Meta Ads and UGC workflows by @harrythentrepreneur
- [#143](https://github.com/harrythentrepreneur/Omo.Space/pull/143) feat: add trusted release finalization foundation by @harrythentrepreneur
- [#144](https://github.com/harrythentrepreneur/Omo.Space/pull/144) feat: add deterministic trusted release finalizer by @harrythentrepreneur
- [#145](https://github.com/harrythentrepreneur/Omo.Space/pull/145) ci: add credential-free trusted release trigger by @harrythentrepreneur
- [#146](https://github.com/harrythentrepreneur/Omo.Space/pull/146) feat(release): add staging deployment contracts by @harrythentrepreneur
- [#147](https://github.com/harrythentrepreneur/Omo.Space/pull/147) feat(release): add controlled staging transport by @harrythentrepreneur
- [#148](https://github.com/harrythentrepreneur/Omo.Space/pull/148) feat(release): add staging environment bootstrap by @harrythentrepreneur
- [#149](https://github.com/harrythentrepreneur/Omo.Space/pull/149) fix(release): allow exact Worker bootstrap by @harrythentrepreneur
- [#150](https://github.com/harrythentrepreneur/Omo.Space/pull/150) fix(release): route staging canary exactly by @harrythentrepreneur
- [#151](https://github.com/harrythentrepreneur/Omo.Space/pull/151) feat(release): add durable staging canary state by @harrythentrepreneur
- [#152](https://github.com/harrythentrepreneur/Omo.Space/pull/152) fix(release): accept Cloudflare D1 system table by @harrythentrepreneur
- [#153](https://github.com/harrythentrepreneur/Omo.Space/pull/153) security: protect trusted release paths by @harrythentrepreneur
- [#155](https://github.com/harrythentrepreneur/Omo.Space/pull/155) feat(release): add production finalizer foundation by @harrythentrepreneur
- [#156](https://github.com/harrythentrepreneur/Omo.Space/pull/156) feat(release): add protected production controller by @harrythentrepreneur
- [#157](https://github.com/harrythentrepreneur/Omo.Space/pull/157) fix(release): add finalizer receipt migration by @harrythentrepreneur
- [#158](https://github.com/harrythentrepreneur/Omo.Space/pull/158) fix(release): use canonical finalizer origin by @harrythentrepreneur
- [#159](https://github.com/harrythentrepreneur/Omo.Space/pull/159) fix(ci): pin resolvable setup-node action by @harrythentrepreneur
- [#160](https://github.com/harrythentrepreneur/Omo.Space/pull/160) fix(release): add typed HTTP stage diagnostics by @harrythentrepreneur
- [#161](https://github.com/harrythentrepreneur/Omo.Space/pull/161) fix(release): preserve sanitized HTTP status by @harrythentrepreneur
- [#162](https://github.com/harrythentrepreneur/Omo.Space/pull/162) fix(release): preserve finalizer claim status by @harrythentrepreneur
- [#163](https://github.com/harrythentrepreneur/Omo.Space/pull/163) fix(release): add finalizer schema readback by @harrythentrepreneur
- [#164](https://github.com/harrythentrepreneur/Omo.Space/pull/164) fix(release): add complete finalization schema migration by @harrythentrepreneur
- [#165](https://github.com/harrythentrepreneur/Omo.Space/pull/165) fix(release): preserve finalizer resume status by @harrythentrepreneur
- [#166](https://github.com/harrythentrepreneur/Omo.Space/pull/166) fix(release): add safe resume query probe by @harrythentrepreneur
- [#167](https://github.com/harrythentrepreneur/Omo.Space/pull/167) fix(release): use request-bound resume query by @harrythentrepreneur
- [#168](https://github.com/harrythentrepreneur/Omo.Space/pull/168) fix(release): treat empty resume result as idle by @harrythentrepreneur
- [#169](https://github.com/harrythentrepreneur/Omo.Space/pull/169) fix(release): scope production canary submission by @harrythentrepreneur
- [#170](https://github.com/harrythentrepreneur/Omo.Space/pull/170) fix(release): seed trusted production canary by @harrythentrepreneur
- [#171](https://github.com/harrythentrepreneur/Omo.Space/pull/171) fix(release): reconcile production builder schedule by @harrythentrepreneur
- [#172](https://github.com/harrythentrepreneur/Omo.Space/pull/172) fix(release): use Cloudflare schedule API by @harrythentrepreneur
- [#173](https://github.com/harrythentrepreneur/Omo.Space/pull/173) fix(release): parse Cloudflare schedule readback by @harrythentrepreneur
- [#174](https://github.com/harrythentrepreneur/Omo.Space/pull/174) fix(release): retry exact production canary by @harrythentrepreneur
- [#175](https://github.com/harrythentrepreneur/Omo.Space/pull/175) fix(builder): classify Hermes failures safely by @harrythentrepreneur
- [#176](https://github.com/harrythentrepreneur/Omo.Space/pull/176) fix(builder): scope private source handoff by @harrythentrepreneur
- [#177](https://github.com/harrythentrepreneur/Omo.Space/pull/177) fix(builder): use scoped Nous inference credits by @harrythentrepreneur
- [#178](https://github.com/harrythentrepreneur/Omo.Space/pull/178) fix(builder): accept scoped Nous invoke JWTs by @harrythentrepreneur
- [#180](https://github.com/harrythentrepreneur/Omo.Space/pull/180) Release label-normalizer-canary submission sub_2ef7768c339891996c61ba3d291c1612 by @harrythentrepreneur
- [#181](https://github.com/harrythentrepreneur/Omo.Space/pull/181) fix(release): recover failed squash-merge finalizations by @harrythentrepreneur
- [#182](https://github.com/harrythentrepreneur/Omo.Space/pull/182) fix(release): fetch provenance history in finalizer by @harrythentrepreneur
- [#183](https://github.com/harrythentrepreneur/Omo.Space/pull/183) fix(release): type production preflight failures by @harrythentrepreneur
- [#184](https://github.com/harrythentrepreneur/Omo.Space/pull/184) fix(release): install pinned Modal CLI by @harrythentrepreneur
- [#185](https://github.com/harrythentrepreneur/Omo.Space/pull/185) fix(release): make Modal deployment idempotent by @harrythentrepreneur
- [#186](https://github.com/harrythentrepreneur/Omo.Space/pull/186) fix(release): reach Worker in production smoke by @harrythentrepreneur
- [#187](https://github.com/harrythentrepreneur/Omo.Space/pull/187) fix(release): recover verified rolled-back generations by @harrythentrepreneur
- [#189](https://github.com/harrythentrepreneur/Omo.Space/pull/189) fix(release): wire rollback provider readback by @harrythentrepreneur
- [#190](https://github.com/harrythentrepreneur/Omo.Space/pull/190) fix(release): align finalizer with provider contracts by @harrythentrepreneur
- [#191](https://github.com/harrythentrepreneur/Omo.Space/pull/191) fix(release): recover receipt-bearing internal failures by @harrythentrepreneur
- [#192](https://github.com/harrythentrepreneur/Omo.Space/pull/192) fix(release): preserve append-only recovery history by @harrythentrepreneur
- [#193](https://github.com/harrythentrepreneur/Omo.Space/pull/193) fix(release): reconcile exact Worker effects by @harrythentrepreneur
- [#194](https://github.com/harrythentrepreneur/Omo.Space/pull/194) fix(release): stabilize production canary auth by @harrythentrepreneur
- [#195](https://github.com/harrythentrepreneur/Omo.Space/pull/195) fix(release): accept completed canary status by @harrythentrepreneur
- [#196](https://github.com/harrythentrepreneur/Omo.Space/pull/196) fix(release): recover verified public failures by @harrythentrepreneur
- [#197](https://github.com/harrythentrepreneur/Omo.Space/pull/197) fix(release): verify canonical publication route by @harrythentrepreneur

</details>


[v0.1.0]: https://github.com/harrythentrepreneur/Omo.Space/releases/tag/v0.1.0
