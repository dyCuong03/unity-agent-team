# Panel 4 — DOTS Skill Builder — Wave 1 Assignment

**Wave 1 scope:** HelloCube + Basic ECS Lifecycle.
**Target skills:** `ecs-fundamentals`, `dots-update-groups`, `singleton-patterns`, `entity-query-patterns` (only those QA approves).

You are the only panel allowed to write into `.claude/skills/unity-dots/`. You invoke `/skill-creator` — mandatory; no manual file authoring.

## Blocking precondition

Wait until `workspace/dots-program/gates/wave-1-qa-approved` exists. If `wave-1-qa-rejected` exists instead, stop.

## What to read

1. `workspace/dots-program/outboxes/qa-curator/wave-1-approvals.md` — authoritative list of what to build. Build only `APPROVED`. Skip `DEFER` / `REJECT_DUPLICATE`.
2. `workspace/dots-program/outboxes/architect/wave-1-specs.md` — the contract per skill
3. `workspace/dots-program/outboxes/reverse-engineer/wave-1-evidence.md` — pull example snippets from the cited file:line ranges. Quote real code; do not invent.
4. Format anchors: `.claude/skills/unity-dots/dots-ecb-orchestration/SKILL.md` and `.claude/skills/unity-dots/dots-baking-patterns/SKILL.md`
5. `.claude/skills/skill-creator/SKILL.md` — the vendored `/skill-creator` workflow

## `/skill-creator` invocation

Verify `skill-creator` is loaded in your Claude session's available-skills list at session start. If absent:
1. Halt.
2. Write `workspace/dots-program/outboxes/skill-builder/wave-1-blocker.md` explaining the block.
3. `touch workspace/dots-program/gates/wave-1-builder-blocked`.
4. SendMessage coordinator. Wait.

When loaded, invoke `/skill-creator` once per approved skill. Per skill:
- Target path: `.claude/skills/unity-dots/<skill-name>/SKILL.md`
- Front-matter `description`: derived from the Architect's Intent + Use-when keywords (one sentence + comma-separated triggers).
- Body sections (per Architect spec): Intent / Use when / Avoid when / Senior pattern / Code example (verbatim from evidence with attribution comment) / Anti-patterns / Failure modes / Runtime verification / Static verification / Performance notes / Compile safety / Entities version notes / See also.
- The eval/iterate loop in `/skill-creator` may not be runnable here (needs API access). If not, document and ship description-tuning as a follow-up; do NOT block on it.

## What else to write

`workspace/dots-program/outboxes/skill-builder/wave-1-build-log.md`:

```markdown
## Wave 1 build log

### Built
- <skill-name> — .claude/skills/unity-dots/<skill-name>/SKILL.md (N lines)
  - description: <quote>
  - code source: <evidence file:lines>
  - eval loop: yes/no/why

### Skipped (per QA)
- <skill-name> — reason: <quote>

### Blockers
- <list or "none">

### Self-review (per skill)
For each: verified Use-when / Avoid-when / anti-patterns / failure-modes from spec all appear in SKILL.md; static+runtime verification block present; no banned APIs in example code.
```

## Done condition

1. Each APPROVED skill has a SKILL.md at `.claude/skills/unity-dots/<skill-name>/SKILL.md`.
2. Build log written.
3. `touch workspace/dots-program/gates/wave-1-skills-shipped`.
4. Update `status.md`.
5. SendMessage coordinator — coordinator routes through the routing/SKILL.md keyword table update and pushes to the remote.

## Hard rules

- You do NOT invent new skills.
- You do NOT modify the Architect's spec mid-build. If wrong, write `[ESCALATE_ARCHITECT]` and stop on that skill.
- You do NOT touch shipped Wave 1-legacy SKILL.md files.
- You do NOT commit or push. Coordinator does that after all gates flip.
- Do NOT adopt scratch drafts at `workspace/dots-program/scratch/wave-2-orchestrator-drafts/` as your starting body — those were coordinator-synthesized and explicitly non-canonical.
