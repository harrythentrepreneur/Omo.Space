# Omo workflow offer-card CTA label options

Compiled from `git log -p -- site/workflow.html`, targeted `git log -S` searches, and the August 12 CTA-thinking rollout (`rollout-2026-08-12T01-01-00-019ff233-0ee8-7270-9d7f-6d86cc47c58a.jsonl`). `$X` below stands for the workflow's rendered price.

The two candidate columns in rows 5–10 were brainstormed independently; their placement on the same row does not mean the agent recommended them as pairs.

| # | Download/own door label | Run door label | Microcopy | When used / proposed |
|---:|---|---|---|---|
| 1 | `Buy — $X once` (paid); `Get it — Free` (free) | `Run on our cloud — ≈ $X / run` | None under the buttons. Earlier surrounding offer text: “Powered by Omo · one workflow, two ways to use it.” | First shipped in `14dc165`; the same paid pair remained through `57b860f` (including the two-button rewrite in `dbf0bb1`). This matches the founder’s original preference: “I like the Run on our cloud term.” |
| 2 | `Download & keep — $X once` | `Run it for me — about $X` | Download: “Workflow + prompts. Run them on your computer.” Run: “Per run. Omo handles the setup and sends back the finished result.” | Recommended by the CTA-thinking agent, then shipped in `cf1c7b9`. The agent’s fuller draft was “Workflow and prompts included. Run them on your own computer forever.” / “Omo handles the setup and sends back the finished result.” |
| 3 | `Download Skill.md — $X once` | `Run it for me — about $X` | Same two lines as row 2. | Shipped in `bfaf25e` after the founder said: “Download Skill.md and then below run it for me” and asked to keep the “nice formatting.” |
| 4 | `Download Skill.md — $X once` | `Run it for me — about $X` | Same copy, now in info tooltips rather than always-visible lines. | Current presentation since `75a32e5`; labels unchanged from `bfaf25e`. |
| 5 | `Buy — $X` | `Run on our cloud — ≈ $X` | Candidate microcopy: “yours forever · runs on your machine” / “Omo handles the hosting · result in seconds” | CTA-thinking candidate lists; not selected. |
| 6 | `Buy it — $X` | `Run it — ≈ $X` | Same suggested microcopy direction as row 5. | CTA-thinking candidate lists; not selected. |
| 7 | `Download — $X` | `Run now — ≈ $X` | Same suggested microcopy direction as row 5. | CTA-thinking candidate lists; not selected. |
| 8 | `Own it — $X` | `Try it — ≈ $X` | Same suggested microcopy direction as row 5. | CTA-thinking candidate lists; not selected. |
| 9 | `Get the files — $X` | `Use the API — ≈ $X` | Same suggested microcopy direction as row 5. | CTA-thinking candidate lists; not selected. |
| 10 | `Buy once — $X` | `Run in the cloud` | Same suggested microcopy direction as row 5. | CTA-thinking candidate lists; not selected. |
| 11 | `Get the workflow`; `Own forever` | `Get the result`; `Run it now` | None proposed. | Additional alternatives the CTA sub-agent explicitly rejected. |

Post-click states such as `It’s yours ✓` / `Added to your library ✓` are transaction feedback, not door labels, so they are excluded from the comparison.

## Recommendation

For the founder’s preferred “nice formatting,” preserve the price-bearing form and compare these clearest choices side by side:

- Current: `Download Skill.md — $X once` / `Run it for me — about $X`
- Plain-language ownership: `Download & keep — $X once` / `Run it for me — about $X`
- Original cloud wording: `Download Skill.md — $X once` / `Run on our cloud — ≈ $X / run`

The CTA-thinking agent favored the second pair because it distinguishes “files I keep” from “job done” without exposing infrastructure. The current first pair is more technically specific about the downloaded artifact and directly reflects the founder’s later wording. The founder can choose between specificity (`Skill.md`), possession (`Download & keep`), and the original cloud terminology.
