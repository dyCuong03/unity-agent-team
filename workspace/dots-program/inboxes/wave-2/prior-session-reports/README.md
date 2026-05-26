# Prior-session reports — Wave 2

This directory was set aside to hold reports from a prior orchestrator-led attempt at Wave 2 (Reverse Engineer's evidence package, Architect's design briefs, QA Curator's checklist). **Those reports were not persisted to disk** during the prior session; only their downstream synthesis (the 5 orchestrator-written SKILL.md drafts) survives, and that synthesis lives at `workspace/dots-program/scratch/wave-2-orchestrator-drafts/`.

## What the panels should do

Treat this directory as **empty intentionally**. There is no prior subagent text to audit here. The only reference material from the prior attempt is the scratch drafts — which are themselves non-canonical (they were produced by the coordinator in violation of the panel rule).

- **Panel 2 (Reverse Engineer)**: start fresh on the ECS Samples. Your evidence package is the first authoritative artifact for Wave 2.
- **Panel 1 (Architect)**: do NOT skim the scratch drafts before reading the new evidence package. Read evidence first; only consult scratch as a format / scope cross-check.
- **Panel 3 (QA Curator)**: ignore scratch entirely. Your checklist is built against the Architect's specs, not the prior drafts.
- **Panel 4 (Skill Builder)**: do NOT use scratch as your starting body. Anchor on `dots-ecb-orchestration` and `dots-baking-patterns` from Wave 1 for format; pull code examples from the new evidence package's citations.

## Why we kept scratch but not subagent reports

The 5 scratch SKILL.md drafts are visible (~900 lines total) and pre-existed on disk by the time the user enforced the panel rule. Deleting them silently would lose visibility into what was previously done. Preserving them under `scratch/` makes the prior coordinator-synthesis explicit and auditable.

The subagent reports never landed on disk in the prior session, so there is nothing to preserve. Panels start from primary sources — that is the honest baseline.
