# Skill Backlog — Unity DOTS Skill Build Program

**Status:** Phase 0 deliverable. Items are proposals, not approved skills.
**Approval gate:** Each item must pass Phase 4 review questions before `/skill-creator` runs.
**Target:** `unity-agent-team/.claude/skills/unity-dots/<skill-name>/SKILL.md`

---

## Review questions applied to every candidate (Phase 4)

For each candidate to ship, all seven must be YES:

1. Is this **reusable** across DOTS projects? (not BackpackAdventures-specific)
2. Is this **production-worthy** (not a sample shortcut)?
3. Is this **senior-level** (not a tutorial)?
4. Is this **Entities 1.x safe** (no deprecated APIs)?
5. Is this **compile-safe** (no banned patterns)?
6. Is this **routing-worthy** (a known keyword resolves to it)?
7. Would **another DOTS project** benefit from it?

If any answer is NO → reject. No fillers.

---

## Wave 1 — Foundation

### 1. `dots-baking-patterns`
- **Evidence:** `EntitiesSamples/Assets/Baking/{BakingDependencies, BakingTypes, AutoAuthoring}`, `ExampleCode/Baking.cs`
- **Core question it answers:** "When do I use `TransformUsageFlags.Renderable` vs `Dynamic` vs `None`? How do I declare bake-time dependencies without breaking incremental baking?"
- **Critical content:** TransformUsageFlags decision tree; `DependsOn()` vs `GetComponent<T>` in Baker; one Baker per Authoring; no runtime logic in Baker.
- **Anti-patterns to call out:** Reading scene state at bake time without `DependsOn`; multiple Bakers per Authoring; structural authoring side effects.
- **Confidence (pre-review):** 0.92

### 2. `dots-ecb-orchestration`
- **Evidence:** `ExampleCode/Jobs.cs`, multiple HelloCube samples, Kickball/Firefighters
- **Core question:** "Which ECB system do I record into and when does it play back?"
- **Critical content:** BeginInitialization / EndInitialization / BeginSimulation / EndSimulation / BeginFixedStepSimulation / EndFixedStepSimulation — pick by reader/writer phase; ParallelWriter vs serial; ECB.AsParallelWriter() restrictions.
- **Anti-patterns:** Multiple playbacks of same recorder; structural changes outside ECB inside jobs; "spray-and-pray" ECB choice.
- **Overlap check:** `ecs-job-patterns` mentions ECB. Differentiate by focusing on PLAYBACK PHASE selection rather than recording mechanics.
- **Confidence:** 0.90

### 3. `dots-enableable-components`
- **Evidence:** `HelloCube/6.EnableableComponents`, `HelloCube/13.StateChange`
- **Core question:** "When should state be a tag (structural) vs an IEnableableComponent (no structural change)?"
- **Critical content:** decision rule — frequency of toggle vs frequency of presence query; query `.WithAll<T>()` vs `.WithEnabled<T>()`; cost model.
- **Anti-patterns:** Using `AddComponent/RemoveComponent` for hot-path state flips; treating Enableable as boolean field on a component.
- **Confidence:** 0.93

### 4. `dots-entity-lifecycle`
- **Evidence:** `HelloCube/3.Prefabs`, `HelloCube/9.RandomSpawn`, `Streaming/SceneManagement`, ICleanupComponentData usage
- **Core question:** "How do I destroy entities safely and clean up referenced state?"
- **Critical content:** spawn → live → destroy chain; CleanupComponentData (formerly ISystemStateComponentData) for two-phase teardown; SystemState handling; orphan entity prevention.
- **Anti-patterns:** Destroying entity while another entity holds a `Entity` ref to it; cleanup without CleanupComponent → state leak.
- **Confidence:** 0.88

### 5. `dots-spawning-patterns`
- **Evidence:** `HelloCube/3.Prefabs`, `HelloCube/9.RandomSpawn`, prefab baking
- **Core question:** "How do I spawn N entities deterministically without main-thread cost?"
- **Critical content:** ECB.Instantiate from jobs; prefab entity from bake; Random with seeded `CreateFromIndex`; batched instantiate.
- **Anti-patterns:** Per-entity instantiation outside ECB; `UnityEngine.Random` in jobs; spawn during query iteration.
- **Pairs with:** `dots-entity-lifecycle`, `dots-ecb-orchestration`
- **Confidence:** 0.86

---

## Wave 2 — Architecture & Hybrid

### 6. `dots-update-groups`
- **Evidence:** Default world groups, `HelloCube/11.FixedTimestep`
- **Why:** Update-order bugs are the single most expensive ECS class of bug.
- **Critical content:** Initialization / Simulation / Presentation default groups; FixedStepSimulationSystemGroup determinism; `[UpdateBefore/After]` vs custom groups; per-frame vs per-fixed-step.
- **Confidence:** 0.85

### 7. `dots-singleton-patterns`
- **Evidence:** Spread across samples
- **Critical content:** `RequireForUpdate<T>()`; `SystemAPI.GetSingleton<T>()` vs lookup; single-writer rule; singleton ownership in baking vs runtime.
- **Confidence:** 0.83

### 8. `dots-transform-patterns`
- **Evidence:** `HelloCube/5.Reparenting`, `HelloCube/12.CustomTransforms`
- **Critical content:** LocalTransform / Parent / PreviousParent / LinkedEntityGroup; reparenting cost; custom transform hierarchies; world-space vs local-space.
- **Confidence:** 0.84

### 9. `dots-hybrid-bridge`
- **Evidence:** `HelloCube/7.GameObjectSync`, `HelloCube/10.FirstPersonController`, `HelloCube/15.UnityObjectRef`, UI Toolkit examples
- **Critical content:** UnityObjectRef for managed asset refs; CompanionComponent caveats; one-way data flow rule (DOTS writes state, Unity reads); when to use Baker vs runtime sync; input → request pattern.
- **Confidence:** 0.87

### 10. `dots-event-driven-ecs`
- **Evidence:** Request/response patterns in StateChange and Kickball
- **Critical content:** Request tag pattern; enableable command components; one-frame events vs persistent state; explicit consumer system.
- **Confidence:** 0.80

---

## Wave 3 — Performance & Meta (ship only those that clear 0.70)

### 11. `dots-chunk-iteration`
- **Evidence:** `HelloCube/4.IJobChunk`, Boids
- **Overlap risk:** `ecs-job-patterns` covers job basics. Differentiate by focusing on CHUNK-level iteration cost model and EntityQuery filtering.
- **Confidence (pre-review):** 0.78

### 12. `dots-versioning-1x`
- **Why:** Old DOTS code online still uses 0.x APIs (ComponentSystemBase patterns, Entities.ForEach).
- **Critical content:** Entities 1.x API map; what was deprecated; ISystem over SystemBase; SystemAPI replacement of EntityManager.
- **Confidence:** 0.82

### 13. `dots-anti-patterns`
- **Evidence:** Kickball Step 1 → Step 5 refactor trail; Firefighters early steps
- **Critical content:** Manager objects disguised as ECS; structural changes in hot loops; sample shortcuts that fail at scale; main-thread fallback in OnUpdate.
- **Confidence:** 0.83

### 14. `dots-debugging-flow`
- **Evidence:** EntitiesJournaling (mentioned in samples), Entities Hierarchy & Systems window
- **Overlap risk:** `investigation` skill exists. Reject if differentiation is weak.
- **Confidence:** 0.72 — borderline; QA gate decides

---

## Rejected candidates (with reason)

| Domain | Reason |
|---|---|
| `pooling` | DOTS doesn't pool objects the way OOP does. ECB spawn/despawn IS the pool. Teaching a `pooling` skill encourages anti-pattern OOP thinking. |
| `memory-safety` | `memory-safety/SKILL.md` already exists in the publish package. Would duplicate. |
| `testing` | Already covered by `qa-validation/SKILL.md` + the verification-contract shipped earlier. ECS Samples don't teach testing patterns. |
| `physics` | Out of Wave 1–3 scope. PhysicsSamples is its own deep project. Defer. |

---

## What this backlog is NOT

- Not a commitment to write all 14 skills. The QA gate may reject any.
- Not ordered by user value — ordered by **dependency** (foundation first, meta last).
- Not a substitute for the wave-end retrospective. After each wave, this file is updated with what shipped, what was rejected, and what new candidates emerged.
