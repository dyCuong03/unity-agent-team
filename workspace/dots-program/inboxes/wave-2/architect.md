# Panel 1 — DOTS Architect — Wave 2 Assignment

You do **not** read `EntityComponentSystemSamples`. You consume the evidence package the Reverse Engineer (Panel 2) produced and turn it into production engineering specs the QA Curator (Panel 3) will gate-review.

## Blocking precondition

Wait until `workspace/dots-program/gates/wave-2-evidence-ready` exists. If it doesn't, stop. Don't start.

## What to read

1. `outboxes/reverse-engineer/wave-2-evidence.md` — the evidence package
2. `workspace/dots-program/inboxes/wave-2/prior-session-reports/architect-briefs.md` — a prior subagent's design briefs on the same 5 skills. Audit it the same way Panel 2 audited its prior report: `[CONFIRMED]`, `[REVISE]`, `[REMOVE]`. Do not adopt verbatim.
3. Two reference SKILL.md files already shipped for format/voice anchor:
   - `.claude/skills/unity-dots/dots-ecb-orchestration/SKILL.md`
   - `.claude/skills/unity-dots/dots-baking-patterns/SKILL.md`
4. `.claude/skills/qa-validation/verification-contract.md` — every spec you produce must specify the static + runtime verification layers per this contract.

## Wave 2 target skills

- `dots-update-groups` — InitializationSystemGroup / SimulationSystemGroup / PresentationSystemGroup / FixedStepSimulationSystemGroup / VariableRateSimulationSystemGroup; `[UpdateBefore]` / `[UpdateAfter]`; `OrderFirst` / `OrderLast`; RateManager; cross-group ordering trap.
- `dots-singleton-patterns` — three creation pathways (bake-time / runtime-created / ECB-system); single-writer rule; `RequireForUpdate` / `GetSingleton` / `GetSingletonRW` / `HasSingleton` / `TryGetSingleton`; deprecated `CreateSingleton` / `GetOrCreateSingleton`.
- `dots-transform-patterns` — `LocalTransform` (writable) vs `LocalToWorld` (RO output); `Parent` / `Child` cost; uniform `Scale` (float) vs `PostTransformMatrix` for non-uniform/shear; banned 0.x components.
- `dots-hybrid-bridge` — `UnityObjectRef<T>` for asset refs; one-way data flow (DOTS writes, Unity reads); managed `class : IComponentData` last-resort; subscene rebake wipes external adds; banned `IConvertGameObjectToEntity` / `ConvertToEntity`.
- `dots-event-driven-ecs` — three shapes (request entity, enableable command, event buffer); explicit consumer ownership; banned `Action` / `UnityEvent` / static event bus.

## What to write

One file: `outboxes/architect/wave-2-specs.md`. For each of the 5 skills:

```markdown
## <skill-name>

### Spec status
DRAFT | REVISED-FROM-PRIOR | DEFER (one of these)

### Intent (1 sentence)
<what the skill teaches>

### Use when (3 bullets)
- ...

### Avoid when (2 bullets)
- ...

### Senior pattern (one paragraph)
<the engineering rule generalized — no sample-specific code; the Builder will pull example code from the evidence package>

### Anti-patterns (3–5 bullets)
- ❌ ...

### Failure modes (3–5 rows: symptom → cause)
| Symptom | Cause |
|---|---|
| ... | ... |

### Required code-example sources
<which files:lines from the evidence package the Builder should draw example snippets from — at least 2 sources per skill>

### Verification (per `.claude/skills/qa-validation/verification-contract.md`)
- Static: <2–3 specific checks>
- Runtime: <2–3 specific tests>

### Performance notes (2–3 bullets)
- ...

### Banned API list for this skill (Entities 1.x compat)
- <deprecated API> — <what to use instead>

### Overlap with existing skills
<which Wave 1 skill or other Wave 2 skill could conflict; declare the owner of the overlapping concept>

### Pre-QA confidence (0.00–1.00)
<your gate score; reject your own brief if < 0.70>
```

Five sections, one per skill. Total length: ≤ 1200 lines.

## Done condition

1. `outboxes/architect/wave-2-specs.md` written.
2. Any spec at confidence < 0.70 is marked `DEFER` with reasoning — those drop out of Wave 2.
3. `touch workspace/dots-program/gates/wave-2-specs-ready`.
4. Update `status.md` Wave 2 phase to "Architect: complete".

## Hard rules

- You do not read the ECS Samples repo. If the evidence package is thin on a topic, the right action is `DEFER`, not "let me go look myself."
- Each anti-pattern in your spec MUST be backed by a citation in the evidence package OR be an Entities 1.x deprecation. No invented anti-patterns.
- You do NOT write code snippets. That's the Builder's job. You write the **contract** the snippet must demonstrate.
- You do NOT write SKILL.md. You write specs.
- If two skills' overlap can't be cleanly resolved, write `[ESCALATE_QA]` in the spec — Panel 3 makes the call.

## Communication with other panels

- If Panel 2's evidence has gaps you can't work around, write `[ESCALATE_REVERSE_ENGINEER: <question>]` in the spec. Coordinator routes back to Panel 2 with a new mini-inbox.
- Don't message Panel 3 or Panel 4 directly. They read your outbox after `wave-2-specs-ready`.
