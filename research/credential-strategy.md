# Credential Strategy for the Omo Builder

Status: REBUILT 2026-08-16 from the coordinator's verified records (the original file was lost in a git stash operation before its first commit; the strategy content below is the verified verdict from the design agent, unchanged in substance).

## 1. The goal

The builder must be able to grow its capabilities without ever touching a human credential. Every key follows one repeatable pattern: founder approves with one sentence, the key is provisioned process-only, and the builder resolves it only for a typed capability.

## 2. The role email

Use `builder@omospace.co` — a forwarding alias to the founder's inbox. The builder gets NO mailbox login, recovery code, or 2FA. Identity stays founder-bound forever.

## 3. The three capability unlocks (hard-holds)

### Search (issue #59)
- Provider: Brave Search API (bounded raw results, predictable pricing).
- Key: `OMO_BRAVE_SEARCH_API_KEY`.
- Unlocks: verdict-sweep, deep-research, literature-review, fact-checking.

### Images (issue #61)
- Provider: public OpenAI Images API, pinned to `gpt-image-2-2026-04-21`.
- Dedicated Omo project. Auto-recharge OFF. Key restricted to Images endpoints.
- Do NOT use the subscription OAuth for production.
- Unlocks: logo-design, cover generation, the flagship book's illustrations.

### Safe execution (issue #60)
- No key at all: a fresh, secret-free Modal Sandbox per run. Network blocked. Strict process/file/CPU/memory/time limits.
- v1 stays unavailable until the limits and cleanup are adversarially verified.

## 4. The provisioning protocol (every future credential)

1. Founder says the approval sentence.
2. The key lands in a non-repo dotenv (mode 0600), never in chat, never in argv.
3. The builder imports it process-only (never prints).
4. The capability resolver binds it to a typed capability.
5. A bounded proof run verifies the capability.
6. Rotation at 90 days, or immediately if the value ever appears in chat.

## 5. Risk notes (honest)

- Provider drift: prices and limits change. Pin versions; review quarterly.
- Brave storage rights: check the plan before preserving result data.
- Safe-exec residual risk: a sandbox is not proof of safety.
- Account recovery concentration: the role address concentrates recovery at the domain + founder inbox. Protect the registrar, mail forwarding, password manager, 2FA.
- Can wait: Replicate/fal/Runware fallbacks, transactional email, SMS, autonomous account creation, provider key-management automation, production safe-exec. Add them only when a typed skill contract proves the need.

## 6. The approval sentences (copy-ready, in order)

1. Role address: "Approve the Omo role email builder@omospace.co as a forwarding alias to the founder inbox, with no mailbox login for the builder."
2. Search: "Approve a bounded public-query search backend and process-only loading of its API key."
3. Images: "Approve a bounded image-generation provider and process-only loading of its API key."
4. Safe exec: "Approve the isolated ephemeral safe-execution design with allowlisted runtimes, bounded filesystem/process/CPU/memory/time, and network off by default."
