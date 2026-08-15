# Nous Research: how it came into reality

Research date: 2026-08-14. Claims below distinguish primary material from reporting and mark gaps as `UNVERIFIED`.

## Origin

The best-supported origin story is not “ex-OpenAI researchers founded a startup.” It is an online, open-weights collaboration that became a company. In a 2025 Fortune interview, cofounder Karan Malhotra said Nous was created in 2022 by volunteers who met through Discord, GitHub, and Twitter. The group experimented with existing open models, including Llama and Mistral, and released model variants under the Hermes name. [Fortune, Apr. 25, 2025](https://fortune.com/crypto/2025/04/25/paradigm-nous-research-crypto-ai-venture-capital-deepseek-openai-blockchain/)

The founding team most consistently identified in public sources is Jeffrey Quesnelle, Karan Malhotra, Ryan “Teknium” (pseudonymous surname not established here), and Shivani Mitra. Teknium’s own biography says he helped found Nous as an AI research community on Discord and later formalized it with three cofounders. [Teknium](https://teknium.io/). A technical report confirms Teknium, Jeffrey Quesnelle, and Chen Guang as Nous researchers, but it is not itself a founding-team roster. [Hermes 3 report](https://nousresearch.com/wp-content/uploads/2024/08/Hermes-3-Technical-Report.pdf)

Their prior context appears to have been the open-source/open-weights community, not employment at OpenAI. Malhotra’s prior Open Assistant/LAION connection is reported by a third-party profile, while Fortune describes the early group as AI researchers and “crypto native.” Diederik P. Kingma’s later collaboration with Nous does not make him a founder or imply that the founders were ex-OpenAI. `UNVERIFIED: a complete founder-by-founder employment history before Nous.`

The original insight was practical and ideological: a small, distributed group could improve open base models through data curation, fine-tuning, evaluation, and public releases, while preserving user control and unrestricted access. Nous’s current mission states that it advances human rights and freedoms by creating and proliferating open-source language models and supporting their unrestricted use. [Nous Research](https://nousresearch.com/)

## Name

“Nous” is Ancient Greek and is commonly translated as “mind” or “intellect,” with philosophical associations reaching back to Plato, Aristotle, and Plotinus. [Routledge Encyclopedia of Philosophy](https://www.rep.routledge.com/articles/thematic/nous). This meaning fits the lab’s intellectual/research identity.

`UNVERIFIED: I did not find a Nous primary-source statement explaining the founders’ exact naming decision. “They chose it because it means mind/intellect” is a reasonable interpretation, not a confirmed quote from the lab.`

## Key moments

1. **Hermes 1 and the first recognizable identity (2023).** The early Hermes fine-tunes turned the group’s work into a named, repeatable line of open models. Fortune says the Hermes series gained popularity in the open-source community. Exact Hermes 1 launch date and team list: `UNVERIFIED` in the sources reviewed.

2. **OpenHermes and Hermes 2.** The `teknium/OpenHermes-2.5` dataset card says OpenHermes 2/2.5 and Nous Hermes 2 were built from a curated mixture of open datasets and custom synthetic data, reaching roughly one million instruction/chat samples; it calls OpenHermes 2.5 a continuation of OpenHermes 1. [OpenHermes-2.5 dataset card](https://huggingface.co/datasets/teknium/OpenHermes-2.5). Nous’s Hermes-2 models then made the data-to-model pipeline legible to the community: release the dataset, fine-tune multiple base models, publish weights, and show evaluations.

3. **Benchmarks and leaderboard visibility.** Nous-Hermes-13B’s model discussion recorded Open LLM Leaderboard results and a #1 position on several reported tasks in late 2023. [Model-card evaluation record](https://huggingface.co/NousResearch/Nous-Hermes-13b/discussions/12/files). The community also used a “Nous benchmark” suite in third-party evaluation tooling. `UNVERIFIED: I found no primary evidence that Nous operated a standalone official leaderboard; this may refer to benchmark scripts/suites or community usage rather than a Nous-owned leaderboard.`

4. **Hermes 3 (2024).** Hermes 3 made the research program more explicit: instruction following, tool use, long-context conversation, structured output, reasoning, and creative/role-play data. Its report says weights for all versions were publicly available and describes 8B, 70B, and 405B Llama 3.1 fine-tunes. [Hermes 3 Technical Report](https://nousresearch.com/wp-content/uploads/2024/08/Hermes-3-Technical-Report.pdf). This was a major credibility moment because the release paired a strong artifact with a technical report and reproducible evaluation story.

5. **DisTrO and distributed training (2024–25).** Nous’s DisTrO repository describes “Distributed Training Over-The-Internet,” a family of low-latency optimizers reducing inter-GPU communication requirements by three to four orders of magnitude. The repository records an August 2024 preliminary report, a December 2024 15B training result, and the later Psyche Network/Consilience milestones. [DisTrO GitHub repository](https://github.com/NousResearch/DisTrO). This connected the earlier open-model work to a bigger thesis: open models plus globally distributed compute.

6. **Hermes 4 (2025).** The Hermes 4 report describes a family of hybrid reasoning models and publicly released weights. [Hermes 4 paper](https://arxiv.org/abs/2508.18255). By this stage Hermes had become a durable product/research brand rather than a one-off fine-tune.

Overall, the moments that made Nous known were not one press launch. They were a sequence of useful public artifacts: models people could download, datasets people could train on, benchmark results people could compare, and research papers that explained a distinct technical direction.

## Growth mechanics

**Community as the initial distribution channel.** The origin community formed on Discord, GitHub, and Twitter/X; the DisTrO repository still directs interested contributors to Discord. [DisTrO](https://github.com/NousResearch/DisTrO). The open-weights audience supplied users, testers, quantizers, deployers, critics, and word-of-mouth distribution.

**Dataset releases as marketing and infrastructure.** OpenHermes was not merely a paper appendix: its dataset card made the recipe visible and reusable. The dataset itself became a durable discovery surface on Hugging Face, while derivative models spread the Nous/Hermes name through the ecosystem.

**Models as proof, papers as credibility.** Hermes releases created immediate utility; technical reports explained why the models were worth attention. The current Nous site summarizes this strategy as open-source models plus infrastructure for distributed, unbiased training, with focus areas including architecture, data synthesis, fine-tuning, and reasoning. [Nous Research](https://nousresearch.com/)

**Open-weights ecosystem position.** Nous built on Meta Llama, Mistral, and other open foundations, then returned weights, datasets, code, and evaluations to the ecosystem. That made the lab legible to a community that values artifacts over corporate promises. The available Hugging Face catalog shows the continuing model-release pattern. [NousResearch on Hugging Face](https://huggingface.co/NousResearch/models)

**Funding and scale-up.** Fortune reported approximately $20M in earlier seed rounds from Distributed Global, North Island Ventures, and Delphi Ventures, followed by a $50M Series A financed almost entirely by Paradigm in April 2025; it reported a roughly 20-person team at that time. [Fortune](https://fortune.com/crypto/2025/04/25/paradigm-nous-research-crypto-ai-venture-capital-deepseek-openai-blockchain/). `UNVERIFIED: the exact legal round structure, cap table, and current team size.` I found no evidence that a16z led Nous funding; the documented major investor in the cited reporting is Paradigm, not a16z crypto.

**Business model.** The public record describes a research organization that later added decentralized-training infrastructure, Psyche, hosted/model-access surfaces, and agent products. It is not best described as only an academic lab or only a SaaS company. `UNVERIFIED: a complete current revenue breakdown.`

The growth mechanism, in compact form:

`community -> useful open artifact -> public evaluation -> derivatives/adoption -> credibility -> larger research ambition and funding`

## Lessons for Omo

1. **Ship a proof artifact that travels without you.** OpenHermes worked as a dataset, a model ingredient, and a community reference point. For Omo, every workflow should produce a small, inspectable proof: input contract, output example, quality rubric, and honest limitations.

2. **Make the brand stand for a specific thesis.** “Open models and distributed training” gave Nous a coherent identity across datasets, models, papers, and community. Omo should make “proven AI workflows, bought per successful result” equally concrete across listing copy, receipts, demos, and public artifacts.

3. **Turn evaluation into distribution.** Nous’s benchmark evidence made releases comparable and discussable. Omo can publish workflow-level success rates, failure/refund rates, latency bands, and representative outputs—without exposing customer data.

4. **Release reusable building blocks, not only finished products.** Datasets, code, reports, and model cards let other people extend Nous’s work. Omo can open-source workflow contracts, validators, renderers, and example inputs while keeping paid execution, hosted reliability, and premium bundles as the business boundary.

5. **Let community feedback improve the artifact.** The Discord/GitHub model gave Nous a testing and recruiting surface. Omo should create a narrow practitioner feedback loop around a few workflows first, then publish the changes and measured gains.

What Omo should not copy:

- **Do not copy research-lab scope before product proof.** Nous’s distributed-training and crypto direction required enormous technical and capital ambition. Omo should first prove repeat purchase, valid-output rate, and margin on a small workflow set.
- **Do not copy benchmark theater or ideological overreach.** A leaderboard position is not customer value, and “open” does not excuse unreliable outputs, unclear licensing, or weak support. Omo should publish only reproducible, decision-relevant metrics and keep the paid promise tightly bounded.

## Sources

- [Nous Research official site](https://nousresearch.com/)
- [Nous Research GitHub organization](https://github.com/NousResearch)
- [Nous Research DisTrO repository](https://github.com/NousResearch/DisTrO)
- [Hermes 3 Technical Report](https://nousresearch.com/wp-content/uploads/2024/08/Hermes-3-Technical-Report.pdf)
- [Hermes 4 Technical Report / arXiv](https://arxiv.org/abs/2508.18255)
- [OpenHermes-2.5 dataset card](https://huggingface.co/datasets/teknium/OpenHermes-2.5)
- [Nous-Hermes-13B evaluation record](https://huggingface.co/NousResearch/Nous-Hermes-13b/discussions/12/files)
- [NousResearch model catalog on Hugging Face](https://huggingface.co/NousResearch/models)
- [Fortune: Paradigm investment and Nous origin/funding/team reporting](https://fortune.com/crypto/2025/04/25/paradigm-nous-research-crypto-ai-venture-capital-deepseek-openai-blockchain/)
- [Teknium biography](https://teknium.io/)
- [Routledge Encyclopedia of Philosophy: Nous](https://www.rep.routledge.com/articles/thematic/nous)

