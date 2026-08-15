# OpenSea: how the NFT marketplace grew — and what it teaches Omo

Research date: 2026-08-14. Claims are separated into sourced facts, interpretation, and **UNVERIFIED** items. “Volume” means trading volume/GMV unless stated otherwise; it is not OpenSea revenue.

## Origin

OpenSea began in late 2017, after Devin Finzer and Alex Atallah followed CryptoKitties and the emerging ERC-721 ecosystem. OpenSea’s own 2018 fundraising post says the founders joined early-adopter Discord communities, talked with users, and saw a basic problem: two strangers needed a way to exchange digital collectibles without trusting one another. They built a non-custodial, open marketplace for any Ethereum non-fungible asset, initially centered on games and collectibles but designed to expand to art, software licenses, and other assets.

The founders brought useful pre-existing product and infrastructure experience. Finzer’s own biography says he worked on growth at Google, Flipboard, and Pinterest, founded Claimdog in 2013, and sold it to Credit Karma in 2016. Atallah’s public profiles identify prior work at Palantir and Apple, and his prior startup experience. A contemporaneous a16z profile describes Finzer as a Pinterest growth engineer and Claimdog founder, and Atallah as a Palantir engineer. Their earlier crypto concept, WifiCoin, is reported by secondary sources; the safer primary-source version is that they were already exploring crypto in 2017 and pivoted after CryptoKitties.

The founding insight was broader than “sell CryptoKitties”: blockchain-created items could be scarce, persistent, portable, and interoperable, while an open marketplace could make discovery and exchange possible across projects. In marketplace terms, OpenSea made supply legible and tradable before a large demand pool existed.

OpenSea says its beta launched in December 2017. By its May 2018 seed announcement, more than $500,000 in Ether had passed through its smart contract in its first two months, and the company described itself as supporting more than 700,000 items across 20 categories. Its own current history records YC Winter 2018, a 2021 mainstream breakthrough with more than $10B cumulative volume, and the 2022 Series C at a $13.3B valuation.

## Supply-side launch

The verified bootstrapping pattern was founder-led community seeding, not a conventional paid acquisition launch:

1. Finzer and Atallah went into the early CryptoKitties/crypto Discord communities, talked to users, and shipped a working marketplace quickly.
2. Finzer posted the OpenSea link in an early CryptoKitties-related Discord; OpenSea’s retrospective identifies that collector as its first-ever user. The same user says the product had low volume, and that the two founders personally resolved issues in Discord.
3. The initial supply was broad and permissionless: existing blockchain items could be discovered and traded, rather than requiring OpenSea to manufacture inventory. Early projects such as CryptoCelebrities and game assets gave the marketplace something to browse.
4. OpenSea later reduced creator friction with gas-free/lazy minting. Its December 2020 Collection Manager post says creators could mint and sell without upfront gas because the NFT was not put on-chain until purchase or transfer. In the November beta, 80 creators made more than 1,000 NFTs, producing 506 sales and 58 ETH in revenue.

The often-repeated claim that the founders manually listed NFTs one by one for creators is **UNVERIFIED** from the sources checked for this brief. It is plausible as an early marketplace tactic, but the primary evidence establishes manual community outreach, founder support, and friction reduction—not hand-listing at scale. Omo should copy the verified behavior and treat the hand-listing story as a hypothesis to validate before repeating it.

## Flywheel

The compounding loop looked like this:

`more creators/items → better selection and price discovery → more collectors and traders → sales, creator earnings, and social proof → more creators`

Key mechanics:

- **Low-friction supply.** OpenSea was open and non-custodial; later, lazy minting removed upfront gas. That made “list first, pay when there is a transaction” possible.
- **Broad inventory.** The initial product accepted any Ethereum NFT rather than selecting one narrow category. That increased the chance that a new project would bring its own community.
- **Creator economics.** OpenSea supported creator fees early, before the NFT standard itself included them. In its 2022 report, OpenSea says creators earned $1.1B in creator fees that year and that 80% went to collections outside the top ten. This is OpenSea’s own reported figure, not an independently audited marketplace-wide number.
- **Discovery.** Search, collection pages, categories, activity, offers, rankings, and later drop pages converted a raw token registry into a shopping/discovery surface. OpenSea’s 2023 product update explicitly added category pages for Art, Gaming, Membership, PFP, and Photography; its Studio launch emphasized collection storytelling, featured NFTs, roadmaps, and FAQs.
- **Trust and authenticity.** Verification badges, collection pages, and copymint detection attempted to distinguish authentic supply from plagiarism. OpenSea says its prevention system combined image recognition with human review.
- **Founder/community support.** Early Discord presence and fast issue resolution helped the first users keep using a low-volume product long enough for supply and demand to meet.

This was a two-sided marketplace, but not a perfectly symmetric one: creators and projects often imported their own audiences. OpenSea’s job was to make their items searchable, purchasable, and portable in one place.

## Peak & decline

### Peak

The NFT bull market broke OpenSea into the mainstream in 2021. OpenSea’s own history says it passed $10B cumulative volume during that year. Independent market data commonly puts OpenSea’s monthly trading volume around $3.4B at its August 2021 high; the exact figure varies by dashboard definitions and wash-trading treatment. In January 2022, OpenSea raised $300M at a $13.3B valuation.

The claim that OpenSea had **4.5M users** is **UNVERIFIED** in the sources checked. Contemporary reporting cited about 1.8M active users in late 2021; this is not the same as cumulative registered users. Do not use 4.5M as a fact without a specific dataset and definition.

### Decline and competition

The market contracted sharply in 2022, and OpenSea cut 20% of staff in July 2022 while preparing for a prolonged downturn. This was partly macro/crypto-cycle damage, not solely a product failure. But the downturn exposed a weak moat:

- **Blur attacked the power-trader segment.** Axios described Blur as a wholesale-style venue with faster, trader-oriented mechanics, while OpenSea looked more like a retail store. In 2023 Axios reported OpenSea at about 24% of market volume, versus its earlier dominance.
- **Incentives changed behavior.** Blur used a token and airdrop/points strategy. That attracted volume, including activity that may have been incentive-driven or wash-traded. OpenSea refused to launch a token, so it did not match the subsidy.
- **Royalties became a price war.** OpenSea initially defended creator royalties and, in November 2022, introduced on-chain enforcement for new Ethereum collections. In February 2023 it moved to 0% marketplace fees for a limited time and optional creator earnings for collections without on-chain enforcement; in August 2023 it moved broadly to optional creator fees. This protected trader price competitiveness but weakened a creator-side differentiator.
- **Supply quality and trust were hard to police.** Open permissionlessness brought scale, but also plagiarism, scams, and copymints. Verification and human review helped, but they were costly and imperfect.
- **Regulatory pressure increased uncertainty.** In August 2024, OpenSea disclosed that the SEC had issued a Wells notice, a preliminary notice of likely enforcement—not a finding or final lawsuit. The SEC did not confirm the investigation, and the specific NFTs or conduct at issue were unclear.

The honest diagnosis is not “Blur alone killed OpenSea.” The NFT demand shock shrank the market; Blur then captured the highest-frequency traders with better execution and token incentives; fee and royalty concessions weakened OpenSea’s economic and creator moat; and trust/regulatory problems raised operating costs. A general discovery brand remained, but it was not enough to retain the most economically valuable trading activity.

## Business model

OpenSea’s classic model was a take rate on transactions. The widely cited marketplace fee was 2.5%; OpenSea’s 2023 developer documentation explicitly says its marketplace fee was 2.5% and required on orders through its website/API at that time. Creator earnings/royalties were separate and paid to creators on secondary sales when enforced.

The model evolved in three stages:

1. **Early growth:** low-friction listing/minting and a platform take rate, with creator royalties as an additional creator-side economic layer.
2. **Royalty differentiation:** OpenSea supported creator fees early and later tried contract-level enforcement. Its own 2022 report framed royalties as a durable creator business model.
3. **Competitive compression:** Blur’s zero-fee/low-fee trading and token rewards pressured OpenSea. OpenSea temporarily cut its marketplace fee to 0% and made creator earnings optional in 2023. The move could defend volume, but it also taught users that fees and royalties were negotiable and weakened the supply-side promise.

Token incentives were the sharpest contrast: Blur could subsidize traders with a speculative asset and use airdrops to bootstrap liquidity; OpenSea chose not to issue a token. That avoided token liabilities and incentive farming, but left it vulnerable in a market where traders optimized for immediate rewards.

## Lessons for Omo

### What is the same

Omo is also a two-sided marketplace: workflow creators/suppliers need distribution, while buyers need confidence that a listed item produces a useful result. Manual or agent-assisted supply seeding, curation, trust signals, discovery, and a transaction fee all transfer well.

### What is fundamentally different

OpenSea’s core supply was mostly speculative or collectible: the item’s price and resale liquidity were central to demand. Omo’s supply is functional: a workflow should save time or produce a result that a buyer can inspect and use. That difference is an opportunity, but only if Omo makes quality and outcomes measurable.

The moat Omo needs is therefore not “the largest catalog.” It should be a compounding evidence layer:

`verified workflow → successful result evidence → buyer trust and repeat use → creator earnings/feedback → better workflows and ranking data → more successful results`

If Omo only aggregates prompt files with attractive thumbnails, Blur’s lesson applies directly: a better-funded marketplace can copy listings, undercut fees, and buy activity. Omo’s defensible assets must be workflow provenance, structured input/output contracts, result-quality data, creator reputation, category-specific evaluation, and repeat buyer history. Those are harder to copy than a listing page and become more valuable with every completed run.

### Copy these tactics

1. **Seed supply manually, but operationalize it.** Recruit a small set of proven creators/workflows, import or help author the first listings, run sample jobs, and document the exact promise and failure modes. Track activation and repeat usage, not catalog count.
2. **Make trust visible.** Use curation badges tied to evidence: tested output, named reviewer, success rate, last verified date, input requirements, and refund behavior. A badge should be earned and revocable.
3. **Give creators durable economics.** Omo’s 85/15 split can play the role creator royalties played for OpenSea: creators should have a reason to improve and keep their workflow on Omo. Make payout, attribution, and version history legible.
4. **Build collection/creator pages for discovery.** Create indexable pages around creator, job-to-be-done, category, input type, and output type. Add examples and comparison pages only where the underlying workflows are actually active and tested.
5. **Turn every run into marketplace data.** Capture structured success/failure, edits, reruns, refunds, time-to-result, and buyer rating. Use this to rank workflows by outcome quality—not by clicks or raw volume.
6. **Use try-before-buy as a controlled demand bridge.** Let a buyer see a bounded sample or receive a free/low-cost first result, then charge for the useful completed result. This is the functional equivalent of OpenSea’s low-friction listing: reduce the first transaction’s risk without making the entire market free.

### Do not copy these tactics

- **Do not enter a token-incentive war.** Token rewards can manufacture volume, invite farming, and attract users who leave when subsidies stop. Reward verified outcomes, referrals that convert, or repeat value in ordinary currency instead.
- **Do not chase speculative demand.** Omo should not optimize for viral catalog growth, vanity signups, or workflows that look impressive but fail in production. A result that saves a buyer 30 minutes is more valuable than a collectible listing that merely attracts a click.
- **Do not race to zero fees.** Omo’s fee funds QA, refunds, hosting, creator payouts, and support. Compete on trustworthy results and repeat-use economics; use temporary, bounded pilots only when the learning goal is explicit.

### Top three lessons

1. Seed the first high-quality supply yourself and support creators directly until buyers can discover real value.
2. Make trust and outcome evidence the network effect; a catalog alone is not a moat.
3. Keep the take rate and creator split sustainable. A fee war can buy volume while destroying the incentives that make supply worth having.

## Sources

Primary and first-party sources:

- OpenSea, “OpenSea raises $2 million to make true digital ownership more accessible” (May 10, 2018): https://opensea.io/blog/articles/opensea-raises-2-million
- OpenSea, “About OpenSea / Our Journey”: https://opensea.io/about-opensea
- OpenSea, “A chat with OpenSea’s first-ever user” (Sept. 30, 2021): https://opensea.io/blog/articles/a-chat-with-openseas-first-ever-user
- OpenSea, “Create NFTs for Free on OpenSea” (Dec. 29, 2020): https://opensea.io/blog/articles/introducing-the-collection-manager
- OpenSea, “Improving Authenticity on OpenSea: Updates to Verification and Copymint Prevention”: https://opensea.io/blog/articles/improving-authenticity-on-opensea
- OpenSea, “Creators Using OpenSea Earned Over $1 Billion from Creator Fees in 2022”: https://opensea.io/blog/articles/1-billion-from-creator-fees-in-2022
- OpenSea, “January 2023 Product Updates”: https://opensea.io/blog/articles/product-updates-january-2023
- OpenSea, “This Week in Web3 and NFTs: The OpenSea Digest, August 18, 2023” (optional creator fees): https://opensea.io/blog/articles/opensea-digest-aug-18-2023
- OpenSea, February 2023 fee/creator-earnings announcement: https://x.com/opensea/status/1626682043655507969
- OpenSea developer docs, “OpenSea Fees” (2.5% fee as documented Sept. 2023): https://docs.opensea.io/changelog/opensea-fees
- OpenSea, “Introducing OpenSea Studio” (Oct. 3, 2023): https://opensea.io/blog/articles/introducing-opensea-studio
- Devin Finzer, biography: https://devinfinzer.com/
- Y Combinator, OpenSea company profile: https://www.ycombinator.com/companies/opensea

Independent reporting/data context:

- a16z, “Investing in OpenSea” (April 2021; founder backgrounds and Dune chart): https://a16z.com/announcement/investing-in-opensea/
- Thought Economics, “Devin Finzer on NFTs & OpenSea’s Future” (founder account of 2017 context): https://thoughteconomics.com/devin-finzer/
- Axios, “OpenSea lays off 20%, braces for ‘prolonged downturn’” (July 14, 2022): https://www.axios.com/2022/07/14/opensea-lays-off-20-braces-for-prolonged-downturn
- Axios, “Blur, OpenSea, other marketplaces fight over a shrinking NFT market” (Sept. 1, 2023): https://www.axios.com/2023/09/01/nft-opensea-blur
- Axios, “OpenSea aims win NFT market by bringing more people in” (Jan. 22, 2024): https://www.axios.com/2024/01/22/nft-opensea-market-blur
- Axios, “SEC notifies NFT marketplace, OpenSea, of likely lawsuit” (Aug. 28, 2024): https://www.axios.com/2024/08/28/sec-nft-opensea-lawsuit-wells-notice
- Forbes, “The First NFT Billionaires: OpenSea Founders Each Worth Billions After New Fundraising” (Jan. 5, 2022): https://www.forbes.com/sites/elizahaverstock/2022/01/05/nft-billionaires-opensea-founders-each-worth-billions-following-latest-funding-round/
- OpenSea co-founder Alex Atallah, early metrics and collections (personal post): https://paragraph.com/@alexatallah/FGuImihdcBEnUZ5EBt0s

**UNVERIFIED / not used as fact:** the claim that OpenSea founders manually listed NFTs one-by-one for creators; the “4.5M users” figure; and any exact OpenSea peak number that does not specify whether it is monthly volume, cumulative volume, Ethereum-only volume, all-chain volume, or wash-trade-adjusted volume.
