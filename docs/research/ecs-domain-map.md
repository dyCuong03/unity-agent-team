# ECS Domain Map — Target skill taxonomy

**Status:** Phase 0 deliverable. No skill content yet — taxonomy only.
**Target folder:** `unity-agent-team/.claude/skills/unity-dots/`
**Skill format:** must match the SKILL.md format used by all existing publish-package skills (front-matter `name` + `description`, body Markdown). Generation MUST be done via `/skill-creator` per Rule 1.

---

## 20 candidate domains (from team prompt) → high-value mapping

Mapping each candidate domain to the ECS-Samples evidence base. A domain is **viable** only if the samples expose patterns concrete enough to teach reasoning from. A domain is **questionable** when patterns are thin or already covered by an existing publish-package skill.

| # | Domain | Evidence base in ECS Samples | Existing skill overlap | Wave priority |
|---|---|---|---|---|
| 1 | `ecs-architecture` | ExampleCode/ComponentsSystems.cs, Kickball steps | `unity-dots-best-practices` (general), `architect` (role) | W3 — needs differentiation |
| 2 | `system-design` | HelloCube/1.MainThread, ExampleCode/ComponentsSystems.cs | `architect` role brief overlap | W3 |
| 3 | `update-groups` | HelloCube/11.FixedTimestep, FixedStepSimulationSystemGroup usage | None | **W2** — clean win |
| 4 | `entity-lifecycle` | HelloCube/3.Prefabs, 9.RandomSpawn; Streaming/SceneManagement | None | **W1** — foundational |
| 5 | `baking` | EntitiesSamples/Baking/* (7 subfolders!) | None | **W1** — highest density |
| 6 | `ecb-patterns` | ExampleCode/Jobs.cs, multiple HelloCube samples | `ecs-job-patterns` (mentions ECB) | **W1** — focused skill warranted |
| 7 | `singleton-patterns` | Spread across samples (SystemAPI.GetSingleton<T>) | None directly | W2 |
| 8 | `enableable-components` | HelloCube/6.EnableableComponents, 13.StateChange | None | **W1** — clean isolated pattern |
| 9 | `event-driven-ecs` | HelloCube/13.StateChange, request/response patterns | None | W2 |
| 10 | `spawning` | HelloCube/3.Prefabs, 9.RandomSpawn; Kickball | None | **W1** — pairs with entity-lifecycle |
| 11 | `pooling` | Not directly in samples — samples use ECB spawn/despawn | None | **REJECT** — sample evidence too thin; ECB IS the pool in DOTS |
| 12 | `transform-patterns` | HelloCube/5.Reparenting, 12.CustomTransforms | None | W2 |
| 13 | `hybrid-bridge` | HelloCube/7.GameObjectSync, 15.UnityObjectRef, UI Toolkit | None directly | **W2** — high pain area |
| 14 | `jobs-and-burst` | HelloCube/2.IJobEntity, 4.IJobChunk, ExampleCode/Jobs.cs, Boids | `ecs-job-patterns`, `burst-safety` exist | W3 — needs to extend not duplicate |
| 15 | `physics` | PhysicsSamples (out of Wave 1) | None | Defer to later program |
| 16 | `performance` | Boids (scale), Tornado (parallel write) | `unity-dots-best-practices` general | W3 |
| 17 | `memory-safety` | NativeContainer usage throughout | `memory-safety` exists | **REJECT** — already covered; would duplicate |
| 18 | `testing` | Samples have no formal test patterns | None | **REJECT for this program** — covered by `qa-validation` + `verification-contract` already shipped; ECS samples don't teach it |
| 19 | `debugging` | EntitiesJournaling references, no concentrated samples | `investigation` skill exists | W3 — only if differentiated |
| 20 | `anti-patterns` | Implicit in Kickball/Firefighters step refactors | None | W2 — cross-cutting |
| 21 | `versioning` | Entities 1.4.x detection, deprecated API map | None | W3 — meta-skill |

**Counts:** 18 viable, 3 rejected (`pooling`, `memory-safety`, `testing`). Quality > quantity per the spec.

---

## Wave plan (small, composable skills)

Per team prompt: **MAX 5 skills per wave**. Confidence ≥ 0.70 to ship. Reject anything that duplicates an existing publish-package skill.

### Wave 1 — Foundation (5 skills)
Pattern density is highest, blast radius from misuse is largest. Skills here unlock the others.
- `dots-baking-patterns` (TransformUsageFlags, BakingDependencies, IBaker contracts)
- `dots-ecb-orchestration` (BeginInitialization vs EndSimulation ECB, when each is safe)
- `dots-enableable-components` (vs structural change, query filtering rules)
- `dots-entity-lifecycle` (spawn → live → cleanup → cleanup component pattern)
- `dots-spawning-patterns` (prefab + ECB.Instantiate, RandomSpawn determinism)

### Wave 2 — Architecture & Hybrid (5 skills)
- `dots-update-groups` (Initialization/Simulation/Presentation; FixedStep)
- `dots-singleton-patterns` (RequireForUpdate, SystemAPI.GetSingleton<T>, ownership)
- `dots-transform-patterns` (LocalTransform, Parent, hierarchy traversal)
- `dots-hybrid-bridge` (Baker authoring, UnityObjectRef, GameObjectSync, one-way data flow)
- `dots-event-driven-ecs` (request tags, IEnableableComponent commands)

### Wave 3 — Performance & Meta (3–5 skills, only those that differ from existing)
- `dots-chunk-iteration` (IJobChunk patterns from Boids; only if not covered by ecs-job-patterns)
- `dots-versioning-1x` (Entities 1.x API surface, what was deprecated)
- `dots-anti-patterns` (cargo-cult patterns from Kickball Step 1, sample shortcuts to avoid)
- `dots-debugging-flow` (EntitiesJournaling, Entities Hierarchy window) — only if differentiated
- *(reject if any falls below 0.70 confidence at QA gate)*

**Total target:** 13–15 elite skills across 3 waves. Below the 20-cap. Above the 3-floor. Quality bar enforced by the QA & Skill Curator role gate.

---

## What this map is NOT

- Not a list of files to produce. The QA gate (Phase 4) may reject any candidate.
- Not final. Reverse-engineer findings (Phase 2) may add or kill candidates.
- Not a substitute for `/skill-creator`. Per Rule 1, no skill file is written outside that workflow.
