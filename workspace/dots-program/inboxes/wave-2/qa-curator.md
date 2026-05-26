# Panel 3 — DOTS QA Curator — Wave 2 Assignment

You hold the rejection gate. Nothing reaches the Skill Builder without your approval. Your job is to reject weak specs, not to fix them.

## Blocking precondition

Wait until `workspace/dots-program/gates/wave-2-specs-ready` exists.

## What to read

1. `outboxes/architect/wave-2-specs.md` — the specs to gate
2. `outboxes/reverse-engineer/wave-2-evidence.md` — to verify each spec's claims trace back to evidence
3. `workspace/dots-program/inboxes/wave-2/prior-session-reports/qa-checklist.md` — prior subagent's checklist on the same scope. Audit it. Use only the parts your own review confirms.
4. `.claude/skills/qa-validation/verification-contract.md` — the static + runtime verification contract every approved spec must satisfy
5. The 5 Wave 1 shipped skills under `.claude/skills/unity-dots/` — to check overlap

## What to write

One file: `outboxes/qa-curator/wave-2-approvals.md`. For each of the 5 specs:

```markdown
## <skill-name>

### Decision
APPROVED | REVISIONS_REQUIRED | REJECT_DUPLICATE | DEFER

### Per-skill must-pass items (the specific checks you applied)
| # | Check | Pass? | Notes |
|---|---|---|---|
| 1 | MUST teach <specific thing> | ✅/❌ | ... |
| 2 | MUST NOT recommend <deprecated API> | ✅/❌ | ... |
| ... | ... | ... | ... |

(6–10 specific must-pass items per skill — not generic "is it good"; cite Entities 1.x APIs by name)

### Citation trace
For each anti-pattern and failure mode the spec claims, is it backed by a line in the evidence package? List unbacked claims here. Any spec with > 0 unbacked claims is REVISIONS_REQUIRED.

### Overlap verdict
Cross-check this spec vs each Wave 1 skill and each other Wave 2 spec. If any > 30% concept overlap, declare the owner skill and require the loser to cross-link instead of duplicate.

### Verification contract compliance
- Static layer present and specific? <yes/no — list what's missing>
- Runtime layer present and specific? <yes/no>

### Final reason for decision
<one paragraph>
```

Then at the bottom:

```markdown
## Cross-cutting overlap matrix

(only fill out pairs with any overlap risk)

| Skill A | Skill B | Overlap | Owner |
|---|---|---|---|
| ... | ... | ... | ... |

## Reject thresholds I applied

- ≥ 2 must-pass items failing → REVISIONS_REQUIRED
- > 30% content overlap with existing skill → REJECT_DUPLICATE or merge proposal
- Any banned API recommended → REJECT
- Verification contract layer missing → REVISIONS_REQUIRED
```

## Done condition

Two possible end states:

### A. All 5 specs APPROVED (or some DEFER, none REJECT/REVISIONS)
1. `touch workspace/dots-program/gates/wave-2-qa-approved`
2. Update `status.md` Wave 2 phase to "QA: approved; awaiting Skill Builder"
3. Builder reads your approvals file plus the architect specs to build.

### B. Any spec REVISIONS_REQUIRED or REJECT_DUPLICATE
1. Do NOT touch `wave-2-qa-approved`.
2. `touch workspace/dots-program/gates/wave-2-qa-rejected`
3. Update `status.md` Wave 2 phase to "QA: rejected; sent back to Architect"
4. Coordinator notices the rejection gate and re-issues a focused mini-inbox to Architect with your reasoning. The loop continues until APPROVED.

Three rounds of REVISIONS_REQUIRED on the same spec → DEFER it. Coordinator escalates.

## Hard rules

- You do not rewrite specs. You write decisions and reasons. The Architect rewrites.
- You do not write SKILL.md. Builder writes SKILL.md (and only after your approval).
- Every must-pass check must be specific. "Is it senior-level?" is not a check. "MUST teach `RequireForUpdate<T>` before `GetSingleton<T>`" is a check.
- You may NOT recommend approval if the spec lacks a citation trace to evidence. That's the anti-cargo-cult rule.
