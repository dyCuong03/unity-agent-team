# Panel 1 — DOTS Architect — Wave 1 Assignment

**Wave 1 scope:** HelloCube + Basic ECS Lifecycle.

**Target skills:** `ecs-fundamentals`, `dots-update-groups`, `singleton-patterns`, `entity-query-patterns`.

You do NOT read the ECS Samples repo. You consume the Reverse Engineer's evidence package and produce production engineering specs the QA Curator will gate-review.

## Blocking precondition

Wait until `workspace/dots-program/gates/wave-1-evidence-ready` exists. If absent, stop and wait.

## What to read

1. `workspace/dots-program/outboxes/reverse-engineer/wave-1-evidence.md` — primary input
2. Two format anchors from already-shipped skills:
   - `.claude/skills/unity-dots/dots-ecb-orchestration/SKILL.md`
   - `.claude/skills/unity-dots/dots-baking-patterns/SKILL.md`
3. `.claude/skills/qa-validation/verification-contract.md` — every spec must specify static + runtime verification per this contract.
4. **Reference (do NOT adopt)** — orchestrator drafts under `workspace/dots-program/scratch/wave-2-orchestrator-drafts/`:
   - `dots-update-groups/SKILL.md` and `dots-singleton-patterns/SKILL.md` were drafted by a coordinator earlier (rule violation); the user explicitly required panel re-authoring. Consult only for format/scope cross-check — do not copy content.

## Already-shipped skills (do not duplicate)

These ship and must NOT be redone:
- `dots-baking-patterns`, `dots-ecb-orchestration`, `dots-enableable-components`, `dots-entity-lifecycle`, `dots-spawning-patterns`

If a new spec overlaps any of these >30%, declare REJECT_DUPLICATE in the spec and replace with a cross-link recommendation.

## What to write

One file: `workspace/dots-program/outboxes/architect/wave-1-specs.md`. For each of the 4 target skills:

```markdown
## <skill-name>

### Spec status
DRAFT | DEFER (with reason)

### Intent (1 sentence)

### Use when (3 bullets)

### Avoid when (2 bullets)

### Senior pattern (paragraph — the engineering rule, generalized; no code)

### Anti-patterns (3–5 bullets)

### Failure modes (table: symptom → cause, 3–5 rows)

### Required code-example sources
<file:lines from the evidence package the Builder draws snippets from; ≥2 per skill>

### Verification (per qa-validation/verification-contract.md)
- Static: <2–3 specific checks>
- Runtime: <2–3 specific tests>

### Performance notes (2–3 bullets)

### Banned API list for this skill (Entities 1.x)

### Overlap declaration
- vs Wave 1-legacy shipped skills: <none | links to> ...
- vs other Wave 1 specs: <none | links to> ...

### Pre-QA confidence (0.00–1.00)
Reject your own spec if < 0.70.
```

## Done condition

1. Specs written.
2. Any spec at confidence < 0.70 marked `DEFER` with reason.
3. `touch workspace/dots-program/gates/wave-1-specs-ready`.
4. Update `status.md` Wave 1 phase.
5. SendMessage coordinator with summary.

## Hard rules

- You do not read the ECS Samples repo. If evidence is thin, write `DEFER` not "let me look myself."
- Every anti-pattern in your spec MUST trace to a citation in the evidence package OR be an Entities 1.x deprecation.
- You do NOT write code snippets. You write the contract the snippet must demonstrate.
- You do NOT write SKILL.md.
- If two specs collide, write `[ESCALATE_QA]` and let Panel 3 decide.
