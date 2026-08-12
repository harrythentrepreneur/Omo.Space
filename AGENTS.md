# Omo Growth Loop — Operating Rules (canonical)

These rules bind every agent working on Omo: the omo-space-marketing mentor
profile, the omo-growth-loop cron profile, and any delegated subagent.

## Hard safety rules — irreversible actions require Harry's explicit approval first

Never do any of the following without Harry's explicit, specific permission.
When unsure whether an action is irreversible or destructive, STOP and ask.

1. Spending money — payments, refunds, billing changes, ad spend, purchasing
   services, or anything that moves money.
2. External messages — email, DM, SMS, social posts, publishing content, or any
   communication that reaches a real person outside this workspace.
3. Deploying or changing production — pushing to a remote, deploying, running
   migrations, modifying live infrastructure or live configuration.
4. Destructive changes to files or history — deleting, overwriting, or moving
   data; `git reset --hard`, `git push --force`, destructive `rm`. Work
   additively; commit before large changes; prefer a branch.
5. Secrets — never read, print, copy, move, or otherwise expose .env files,
   API keys, tokens, passwords, or credential files.
6. System state — installing services/daemons, or modifying another profile's
   config, skills, memory, or SOUL.md without approval.

## The loop (how every run works)

- READ first: marketing/GOAL.md and the tail of marketing/STATE_LOG.md.
- Do ONE concrete next action. Delegate heavy reasoning to Codex sol
  (read-only) and verify its output yourself.
- WRITE last: append one structured line to STATE_LOG.md, update GOAL.md,
  and commit both. The state log is append-only; git is memory.
- If the next step needs Harry, write a PROPOSAL block in GOAL.md and stop.
  Never churn, never repeat an action, never invent work.

## If you break a rule

Stop immediately. Do not try to fix or hide it silently. Surface it to Harry
and explain exactly what happened and what you did to contain it.
