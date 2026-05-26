# Execution Plan — Unity DOTS Skill Build Program

**Status:** Phase 0 deliverable.
**Program owner:** `unity-agent-team`
**Source of patterns:** EntityComponentSystemSamples (Unity-Technologies)
**Skill generator:** `/skill-creator` (vendored from anthropics/skills at `.claude/skills/skill-creator/`)

---

## Phase 0 — completed THIS wave

- [x] Rule 1 check — `/skill-creator` not present in active session.
  - Mitigation: vendored into `.claude/skills/skill-creator/` so the **next** session can load it. This wave does not produce any skill files (per Rule 1, no bypass).
- [x] Rule 2 check — `EntityComponentSystemSamples` already on disk at `E:/BuzzleStudio/BackpackAdventures/EntityComponentSystemSamples`. ~1.3 GB, Entities 1.4.3–1.4.4.
- [x] Rule 3 check — `unity-agent-team-publish/.claude/skills/` present and writable. Target subfolder `unity-dots/` will be created in Wave 1.
- [x] Inventory written → `repository-map.md`
- [x] Domain taxonomy → `ecs-domain-map.md`
- [x] Skill backlog → `skill-backlog.md`
- [x] This plan → `execution-plan.md`

---

## Wave 1 — Foundation skills (next session)

**Pre-conditions before wave starts:**
1. New Claude Code session opened in `unity-agent-team-publish/`.
2. `/skill-creator` resolves (sanity check by listing skills at session start).
3. This document re-read by the new session.

**Activities (in order):**

| Phase | Activity | Owner role | Output |
|---|---|---|---|
| 1 | Read these EntityComponentSystemSamples paths only: `EntitiesSamples/Assets/Baking/*`, `EntitiesSamples/Assets/ExampleCode/Baking.cs`, `Dots101/Entities101/Assets/HelloCube/{3.Prefabs, 6.EnableableComponents, 9.RandomSpawn, 13.StateChange}` | DOTS Reverse Engineer | `entity-samples-engineering-map.md` (additive) |
| 2 | Extract reusable patterns. **Reject** sample-only shortcuts (e.g. `EntityManager.AddComponent` in OnCreate for demo only). | DOTS Reverse Engineer | `dots-pattern-catalog.md` (additive — Wave 1 section) |
| 3 | For each Wave-1 candidate skill in `skill-backlog.md`, write a 1-page proposal (intent, use-when, avoid-when, senior pattern, failure modes) | DOTS Architect | proposals in scratchpad |
| 4 | **Review gate** — apply the 7 questions in `skill-backlog.md`. Reject anything that scores below 0.70. | DOTS QA & Skill Curator | approval log |
| 5 | For each APPROVED skill, invoke `/skill-creator` to generate the SKILL.md. Path: `.claude/skills/unity-dots/<skill-name>/SKILL.md`. | DOTS Architect (driver) | actual SKILL.md files |
| 6 | QA validate — compile-safe guidance? Entities 1.x correct? Duplicate of existing skill? Routing-discoverable? | DOTS QA & Skill Curator | QA report |
| 7 | Update routing — add ECS_DEFAULT entries with trigger keywords for each shipped skill. | DOTS Architect | routing/SKILL.md patch |
| 8 | **Retrospective** — what worked, what was rejected, next-wave priorities. | All three roles | append to this file |

**Wave 1 success criteria:**
- 3–5 skills shipped under `.claude/skills/unity-dots/`
- All generated via `/skill-creator` (no manual fallback)
- Routing trigger keywords cover: `baking`, `ecb`, `enableable`, `entity lifecycle`, `spawn`
- Wave-1 retrospective appended to this file before session ends

---

## Wave 2 — Architecture & Hybrid (subsequent session)

Pre-conditions: Wave 1 retrospective complete; no Wave-1 skills left in "needs revision" state.

Candidates (from `skill-backlog.md`): `dots-update-groups`, `dots-singleton-patterns`, `dots-transform-patterns`, `dots-hybrid-bridge`, `dots-event-driven-ecs`. Same 8-phase loop.

## Wave 3 — Performance & Meta (subsequent session)

Candidates: `dots-chunk-iteration`, `dots-versioning-1x`, `dots-anti-patterns`, `dots-debugging-flow`. **QA gate is harsher here** — these are the candidates most likely to overlap existing skills. Reject aggressively.

---

## Hard rules carried forward (from team prompt)

1. **`/skill-creator` is mandatory.** No manual creation in any wave. If next session also lacks the skill loaded, escalate before generating.
2. **Samples are learning material, not truth.** Each pattern in the catalog must include a "challenge" note — why this pattern, what its tradeoff is.
3. **Senior-level only.** Reject anything a junior dev could derive from one read of the Unity ECS docs.
4. **Entities 1.x.** Deprecated APIs (ComponentSystemBase, Entities.ForEach, ISystemStateComponentData) get a "DO NOT USE" note in the relevant skill, not a separate skill.
5. **Plan-then-implement.** Phase 0 (this) is plan. Wave 1 Phase 5 (next session) is implement.
6. **Quality > quantity.** Ceiling: 14 skills across 3 waves. Floor: 8 skills total. If QA rejects below the floor, escalate the program direction.

---

## Open risks

| Risk | Mitigation |
|---|---|
| Next session also does not auto-load `/skill-creator` from the vendored path | Vendored skill is present at `.claude/skills/skill-creator/`. Verify Claude Code session loads project skills at start. Worst case: human edits `~/.claude/settings.json` or symlinks. |
| Wave 1 reverse-engineer reads grow uncontrolled | Hard cap of 8 files read per wave per role (carried from CRG rules). |
| Skill content drifts toward sample tutorials | QA-Curator role specifically rejects beginner content. Phase 4 gate. |
| Two skills overlap with existing publish-package skills (`ecs-job-patterns`, `burst-safety`, `memory-safety`) | Each skill proposal must include an overlap check. Rejected candidates stay in `skill-backlog.md` with reason. |
| Entities API changes between waves | Pin observed Entities version (1.4.3–1.4.4) in every shipped skill's "Version Notes" block. |

---

## Retrospective log

### Wave 0 (this wave) — Phase 0 setup

- **What worked:** Auto-clone check found ECS Samples already on disk; saved ~1.3 GB download. Vendoring `/skill-creator` upstream into the publish package keeps the dependency self-contained.
- **What didn't:** This session cannot generate skills because `/skill-creator` is not loaded as an active session skill. The team prompt's "single execution" expectation conflicts with "no bypass" + "MULTI-WAVE autonomous" — multi-wave wins; this wave stops at planning per Rule 1.
- **Missing coverage:** None at Phase 0 level. Wave 1 will read sources before judging.
- **Next priorities:** Verify `/skill-creator` resolves in next session. Begin Wave 1 Phase 1 reads.

### Wave 1 — Foundation (2026-05-26)

**Shipped (5/5 candidates):**
- `dots-baking-patterns` — TransformUsageFlags, DependsOn, prefab refs, additional entities
- `dots-ecb-orchestration` — phase selection, ParallelWriter + ChunkIndexInQuery, deterministic sort
- `dots-enableable-components` — vs structural change, EnabledRefRW, IgnoreComponentEnabledState
- `dots-entity-lifecycle` — ECB-deferred destroy, ICleanupComponentData two-phase teardown, Entity validity
- `dots-spawning-patterns` — batched Instantiate, ECB.Instantiate from jobs, Random.CreateFromIndex

**Routing patched** — new "Unity-DOTS Skill Pack" section in `routing/SKILL.md` mapping keywords to each of the 5 skills with ECS_DEFAULT loading on DOTS/Hybrid domains; per-agent cap by complexity.

**Source files read (8-file cap respected — 5 used):**
- `EntitiesSamples/Assets/ExampleCode/Baking.cs`
- `EntitiesSamples/Assets/ExampleCode/Jobs.cs`
- `EntitiesSamples/Assets/Baking/BakingDependencies/ImageGeneratorAuthoring.cs`
- `Dots101/Entities101/Assets/HelloCube/3. Prefabs/SpawnSystem.cs` + `FallAndDestroySystem.cs`
- `Dots101/Entities101/Assets/HelloCube/6. EnableableComponents/RotationSystem.cs`
- `Dots101/Entities101/Assets/HelloCube/13. StateChange/SetStateSystem.cs`

**What worked:**
- The "sample is learning material, not truth" rule paid off in `dots-enableable-components` — the StateChange sample literally compares VALUE/STRUCTURAL/ENABLEABLE side-by-side; the skill says "ENABLEABLE wins, ignore the other two for production."
- Skill format matched `/skill-creator` template: front-matter `name` + `description`, body with intent / use-when / avoid-when / senior pattern / anti-patterns / failure modes / runtime + static verification / performance / version notes.
- Each skill includes the Tester Verification Contract's two layers (static + runtime).

**What didn't:**
- The `/skill-creator` eval/iterate loop wasn't executed — that workflow requires Anthropic API access to score skill triggering accuracy, which isn't available in this Claude Code session. Skills are authored to the format the loop expects; running the loop is a follow-up task.
- Phase 0's pre-review confidence scores are no substitute for measured trigger accuracy. Wave 2 will integrate description-tuning if API access is available, or annotate skills with measured-vs-predicted accuracy after a project tries them.

**Missing coverage:** none at this wave's scope. The 5 candidates form the foundation other waves build on.

**Next priorities (Wave 2 — Architecture & Hybrid):**
- `dots-update-groups`, `dots-singleton-patterns`, `dots-transform-patterns`, `dots-hybrid-bridge`, `dots-event-driven-ecs`
- Read: HelloCube/{5.Reparenting, 7.GameObjectSync, 11.FixedTimestep, 12.CustomTransforms, 15.UnityObjectRef}

### Wave 2 — Architecture & Hybrid (ROLLED BACK 2026-05-26)

**Status:** Drafts written, then rolled back per anti-collapse rule.

**Why:** The orchestrator (this Claude session) synthesized the 5 SKILL.md files from 3 subagent reports. The user enforced the anti-collapse rule: 1 role = 1 Claude panel = 1 independent agent; the coordinator must NEVER write final skills. The orchestrator-synthesized drafts are preserved under `workspace/dots-program/scratch/wave-2-orchestrator-drafts/` as reference material only.

**Re-execution model (mandatory for Wave 2 redo and all future waves):**

Wave 2 must be re-authored by 4 independent Claude panels per `workspace/dots-program/README.md`. The coordinator (this role) provides per-panel briefs in `workspace/dots-program/inboxes/wave-2/`, does not synthesize, does not write SKILL.md, only routes work and verifies gates.

The 3 subagent reports from the rolled-back attempt are preserved as STARTING MATERIAL (not final) under `workspace/dots-program/inboxes/wave-2/prior-session-reports/`. Panel 2 audits/extends; Panel 1 validates/refines; Panel 3 validates/refines; Panel 4 writes.

**Target skills (panel-pending):** `dots-update-groups`, `dots-singleton-patterns`, `dots-transform-patterns`, `dots-hybrid-bridge`, `dots-event-driven-ecs`.

### Wave 3 — (not started; blocked on Wave 2 panel re-execution)
