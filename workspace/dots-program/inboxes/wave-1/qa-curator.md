# Panel 3 — DOTS QA Curator — Wave 1 Assignment

**Wave 1 scope:** HelloCube + Basic ECS Lifecycle.
**Target skills:** `ecs-fundamentals`, `dots-update-groups`, `singleton-patterns`, `entity-query-patterns`.

You hold the rejection gate. Nothing reaches the Skill Builder without your approval.

## Blocking precondition

Wait until `workspace/dots-program/gates/wave-1-specs-ready` exists.

## What to read

1. `workspace/dots-program/outboxes/architect/wave-1-specs.md` — the specs you gate
2. `workspace/dots-program/outboxes/reverse-engineer/wave-1-evidence.md` — to verify each claim traces to evidence
3. `.claude/skills/qa-validation/verification-contract.md` — verification contract every approved spec must satisfy
4. The 5 shipped Wave 1-legacy skills under `.claude/skills/unity-dots/` — to enforce no duplication

## What to write

`workspace/dots-program/outboxes/qa-curator/wave-1-approvals.md`. Per skill:

```markdown
## <skill-name>

### Decision
APPROVED | REVISIONS_REQUIRED | REJECT_DUPLICATE | DEFER

### Per-skill must-pass items (6–10 specific checks; cite Entities 1.x APIs by name)
| # | Check | Pass? | Notes |
|---|---|---|---|
| 1 | MUST teach <specific API/concept> | ✅/❌ | ... |
| ... | ... | ... | ... |

### Citation trace
Every anti-pattern + failure mode in the spec — backed by a line in the evidence package? List unbacked claims. >0 unbacked → REVISIONS_REQUIRED.

### Overlap verdict
vs each shipped Wave 1-legacy skill, vs each other Wave 1 spec. If >30% concept overlap, declare the owner and require the loser to cross-link instead of duplicate.

### Verification contract compliance
- Static layer present + specific? <yes/no — list gaps>
- Runtime layer present + specific? <yes/no — list gaps>

### Final reason
<paragraph>
```

Bottom of file:

```markdown
## Cross-cutting overlap matrix
(only pairs with overlap risk)

| Skill A | Skill B | Overlap | Owner |

## Reject thresholds I applied
- ≥ 2 must-pass items failing → REVISIONS_REQUIRED
- >30% content overlap with shipped skill → REJECT_DUPLICATE or merge proposal
- Any banned Entities 1.x API recommended → REJECT
- Verification contract layer missing → REVISIONS_REQUIRED
```

## Done condition

### A. All target specs APPROVED (or DEFER, none REJECT/REVISIONS)
1. `touch workspace/dots-program/gates/wave-1-qa-approved`
2. Update `status.md`
3. SendMessage coordinator with summary

### B. Any spec REVISIONS_REQUIRED or REJECT_DUPLICATE
1. Do NOT touch the approval gate.
2. `touch workspace/dots-program/gates/wave-1-qa-rejected`
3. Update `status.md`
4. SendMessage coordinator with rejection reasons — coordinator routes back to Architect.
5. 3 rounds of REVISIONS on the same spec → DEFER it.

## Hard rules

- You do not rewrite specs. You write decisions and reasons. Architect rewrites.
- You do not write SKILL.md.
- Every must-pass check must be specific. "Is it senior-level?" is not a check. "MUST teach `RequireForUpdate<T>` before `GetSingleton<T>`" is.
- You may NOT approve a spec lacking citation trace to evidence.
