# Wave 1 — Architect Specs

**Author:** dots-architect (Panel 1)
**Date:** 2026-05-26
**Wave scope:** HelloCube + Basic ECS Lifecycle (Entities 1.x)
**Evidence source:** `outboxes/reverse-engineer/wave-1-evidence.md` (14 sources, 4 skills)
**Format anchors:** `dots-ecb-orchestration/SKILL.md`, `dots-baking-patterns/SKILL.md`
**Verification contract:** `.claude/skills/qa-validation/verification-contract.md`

**Wave decisions up-front (apply to all 4 specs):**
- `SystemBase` is OUT of scope for Wave 1 — `ISystem`-only. `SystemBase` deferred to Wave 7 (Hybrid bridge) where the managed `EntityCommandBufferSystem` base and reactive patterns belong.
- `WorldSystemFilter` (Netcode client/server splits) is OUT of scope for Wave 1 — deferred to Wave 7.
- `WithChangeFilter<T>` is OUT of scope for Wave 1 — deferred to Wave 4 (Jobs + Burst) where change-version semantics matter most.
- The `ExecuteFoo` sample-only tag pattern is documented as a sample shortcut inside `singleton-patterns`, not promoted to a production pattern, and not its own micro-skill.
- "Runtime-created singleton" (system creates its own singleton entity in `OnCreate`) is mentioned as an explicit deferral in `singleton-patterns`, full treatment in Wave 6 (State Flow).
- All four specs share a common banned-API list (0.x deprecations); each spec re-lists only the items most likely to be re-introduced in that skill's surface.

---

## ecs-fundamentals

### Spec status
**DRAFT** — confidence 0.92

### Intent (1 sentence)
The substrate every other DOTS skill assumes: how to declare a system, declare a component, run lifecycle code, and access entity data inside `ISystem` using Entities 1.x.

### Use when
- Writing a new runtime ECS system (`partial struct ... : ISystem`).
- Declaring a new `IComponentData` or zero-size tag.
- Reviewing any system file to confirm it uses the current Entities 1.x shell (`SystemAPI`, `RefRW`/`RefRO`, `[BurstCompile]`).

### Avoid when
- Designing baking, ECB orchestration, jobs, enableable components, or singleton consumption — those have their own skills; this is the substrate, not the application.
- Building authoring `MonoBehaviour` code (no overlap — different stack).

### Senior pattern (no code)
Every runtime system is declared `public partial struct <Name>System : ISystem`. The `partial` keyword is non-negotiable — the source generator emits the `ISystem` glue into a sibling partial; remove it and the system silently fails to register. Lifecycle methods (`OnCreate`, `OnUpdate`, `OnDestroy`) are all individually marked `[BurstCompile]` — Burst is the default, never the exception. `OnCreate` declares prerequisites with `state.RequireForUpdate<T>()` to defer `OnUpdate` until the gating data exists; multiple `RequireForUpdate` calls chain with AND. Hot-path data access goes through `SystemAPI.*` exclusively (`SystemAPI.Time`, `SystemAPI.Query<RefRW<T>, RefRO<T>>()`, `SystemAPI.GetSingleton<T>()`, `SystemAPI.GetComponentLookup<T>()`). Direct `state.EntityManager.GetComponentData<T>` is reserved for cold paths and Burst-incompatible scenarios. `RefRW<T>` grants write access; `RefRO<T>` grants read-only access — using `RefRW` where `RefRO` would suffice unnecessarily widens the dependency footprint and blocks parallel scheduling later. Components are blittable structs implementing `IComponentData` (or `IBufferElementData` for buffers); they hold data only, no methods that touch other entities. Per-frame allocations use `Allocator.Temp` (auto-freed at frame end) or `state.WorldUpdateAllocator` (auto-freed at end of world update). `Allocator.TempJob` and `Allocator.Persistent` require explicit disposal — `OnDestroy` is the disposal site for anything allocated in `OnCreate`.

### Anti-patterns
- **Missing `partial`** — `struct MySystem : ISystem` (no `partial`) → source generator emits nothing, system never runs, no compile error. The single most common silent failure.
- **Non-Burst lifecycle** — omitting `[BurstCompile]` on `OnUpdate` to "make debugging easier" → ships to production at 5–20× cost; Burst should be default and only suppressed via `BurstCompiler.Options.EnableBurstCompilation = false` for local debug sessions.
- **`RefRW` for read-only access** — using `RefRW<T>.ValueRO` instead of `RefRO<T>.ValueRO` — compiles, but widens the system's component write set and prevents the scheduler from running it in parallel with any other system reading `T`.
- **`SystemAPI` outside an `ISystem`/`SystemBase`/`IJobEntity` body** — calling `SystemAPI.Time.DeltaTime` from a static helper → source generator cannot rewrite the call, compile error or null reference at runtime.
- **`Allocator.TempJob` allocated in `OnUpdate` without disposal** — even if a job is scheduled, the safety system logs a "deallocated without disposing" warning every frame; correct default is `Allocator.Temp` for main-thread per-frame, `state.WorldUpdateAllocator` for cross-job per-frame.

### Failure modes

| Symptom | Cause |
|---|---|
| System exists in code but `OnUpdate` never fires | Missing `partial` keyword on the struct; source generator did not emit registration |
| Compile error `SystemAPI cannot be resolved` outside system body | `SystemAPI` called from static method, extension, or non-`ISystem` type |
| Compile error `ref T` foreach incompatible | Copying an Entities 0.x `Entities.ForEach((ref T a, in T b) =>)` pattern — 1.x requires `SystemAPI.Query<RefRW<T>, RefRO<T>>()` with `.ValueRW`/`.ValueRO` access |
| Frame-rate cliff after a refactor | `[BurstCompile]` was dropped from `OnUpdate` during the refactor; system silently fell back to managed IL |
| "Deallocated without disposing" warning each frame | `NativeArray<T>(Allocator.TempJob)` or `(Allocator.Persistent)` allocated in `OnUpdate` without a corresponding `Dispose()` call |

### Required code-example sources
Builder draws snippets from (evidence package, file:line):
- `Dots101/Entities101/Assets/HelloCube/1. MainThread/RotationSystem.cs:7-33` — canonical `partial struct ISystem` shell with `OnCreate` / `OnUpdate`, `[BurstCompile]` on both, `RequireForUpdate<T>`, `SystemAPI.Time.DeltaTime`, `SystemAPI.Query<RefRW<T>, RefRO<T>>()` foreach.
- `Dots101/Entities101/Assets/HelloCube/8. CrossQuery/VelocityAuthoring.cs:25-29` — minimal `IComponentData` struct shape (plain blittable fields, no methods).
- `EntitiesSamples/Assets/ExampleCode/ComponentsSystems.cs:31-55` — full three-method lifecycle template (`OnCreate` / `OnDestroy` / `OnUpdate`) showing all three are individually `[BurstCompile]`-annotated and each is optional when empty.
- `Dots101/Entities101/Assets/HelloCube/14. ClosestTarget/TargetingSystem.cs:35-38` — the rare-but-required `OnDestroy` pattern for systems that allocate persistent native containers in `OnCreate`.

### Verification (per qa-validation/verification-contract.md)
- **Static (2–3):**
  1. Grep for `struct \w+System\s*:\s*ISystem` and assert every match has the `partial` keyword on the same line.
  2. For every `ISystem`-implementing struct, assert `OnCreate`, `OnUpdate`, and `OnDestroy` (when present) each carry `[BurstCompile]`.
  3. Grep for `SystemAPI\.` outside `ISystem` / `SystemBase` / `IJobEntity` bodies — must return zero hits.
- **Runtime (2–3):**
  1. **EditMode ECS Test World** — create a world, instantiate the system, advance one frame, assert `OnCreate` ran exactly once and `OnUpdate` ran exactly once when its `RequireForUpdate` precondition is satisfied; remove the precondition entity and assert `OnUpdate` is skipped.
  2. **Deterministic Runtime Checklist** — for any system that allocates in `OnCreate`, assert the corresponding native container is disposed in `OnDestroy` (use `mcp__ai-game-developer__console-get-logs` to assert no "deallocated without disposing" warnings after a world tear-down).
  3. **Determinism** — re-run the same OnUpdate over the same entity set twice; component values must match bit-for-bit.

### Performance notes
- `[BurstCompile]` is mandatory on all `ISystem` lifecycle methods in hot paths; removal is a high-blast performance change and a BLOCK trigger per escalation policy.
- `RefRO<T>` over `RefRW<T>` widens the system's parallel-scheduling opportunities at zero runtime cost.
- `Allocator.Temp` and `state.WorldUpdateAllocator` are the two correct per-frame allocator choices; `TempJob`/`Persistent` require explicit `Dispose()` and an `OnDestroy` site for `OnCreate` allocations.

### Banned API list for this skill (Entities 1.x)
- `Entities.ForEach((ref T a, in T b) => {...})` — 0.x lambda iteration; 1.x replacement is `SystemAPI.Query<RefRW<T>, RefRO<T>>()` foreach.
- `Translation`, `Rotation`, `NonUniformScale` — 0.x transform components; 1.x replacement is `LocalTransform`.
- `IConvertGameObjectToEntity` — 0.x conversion interface; 1.x replacement is `Baker<T>` (covered by `dots-baking-patterns`).
- `ISystemStateComponentData` — 0.x cleanup component; 1.x replacement is `ICleanupComponentData`.
- `BurstCompiler.CompileSynchronously` as a runtime call — never; use `[BurstCompile(CompileSynchronously = true)]` only on `OnCreate` when bake-time consistency is required.

### Overlap declaration
- vs Wave 1-legacy shipped skills:
  - `dots-entity-lifecycle` — **weak overlap, distinct domain.** That skill owns entity create/destroy patterns; this spec owns the system shell itself. Cross-link: `ecs-fundamentals` → "see `dots-entity-lifecycle` for entity create/destroy patterns" (no content duplication).
  - `dots-baking-patterns`, `dots-ecb-orchestration`, `dots-enableable-components`, `dots-spawning-patterns` — distinct domains.
- vs other Wave 1 specs:
  - `singleton-patterns` references the `RequireForUpdate<T>` mechanism — `ecs-fundamentals` owns it as a lifecycle gate; `singleton-patterns` references it as a safe-singleton-read precondition. No duplication.
  - `entity-query-patterns` references `SystemAPI.Query<...>()` — `ecs-fundamentals` owns the SystemAPI surface broadly; `entity-query-patterns` owns the query construction grammar specifically.

### Pre-QA confidence
**0.92** — substrate skill, evidence is dense and unambiguous, three sibling specs all cross-link cleanly. Confidence not at 1.0 because the `SystemBase` deferral creates a known-but-named gap (Wave 7 will close it).

---

## dots-update-groups

### Spec status
**DRAFT** — confidence 0.88

### Intent (1 sentence)
Choose the correct system group and ordering for a system so it ticks at the right rate, in the right phase, with the right ordering relative to siblings — and know which group choices change execution semantics, not just sequence.

### Use when
- Adding `[UpdateInGroup]`, `[UpdateBefore]`, or `[UpdateAfter]` to a new or existing system.
- Diagnosing "system runs at the wrong rate" / "system runs at the wrong phase" symptoms.
- Implementing a one-shot initialization system that should run exactly once after world boot.
- Implementing physics-coupled accumulation that must use a constant `DeltaTime`.

### Avoid when
- The system is intentionally default-group, default-order (no attribute needed — the default `SimulationSystemGroup` is correct for almost all gameplay).
- Cross-world execution control (covered by Wave 7 `WorldSystemFilter` deferral).

### Senior pattern (no code)
Group selection drives execution **semantics**, not just ordering. There are exactly four built-in groups every Wave 1 system needs to understand. `InitializationSystemGroup` ticks once per frame, very early — the only valid place for one-shot bootstrap systems that disable themselves after first `OnUpdate` (`state.Enabled = false`). `SimulationSystemGroup` is the default group when no attribute is present — it ticks once per render frame with variable `SystemAPI.Time.DeltaTime`, and is the home of all gameplay logic. `FixedStepSimulationSystemGroup` ticks zero-to-many times per render frame at a constant `DeltaTime` — it is the **only** correct home for physics-like accumulation, integration steps, and any logic whose correctness depends on a fixed timestep; placing a spawner here causes bursty 0-to-N spawn batches per frame. `PresentationSystemGroup` ticks last, after simulation — it is read-only relative to simulation state; any structural change here happens after rendering has been submitted and produces undefined visual behavior. `[UpdateBefore(typeof(X))]` and `[UpdateAfter(typeof(X))]` express ordering **within a single group only** — both systems must share the same `[UpdateInGroup]` for the constraint to apply; cross-group ordering attributes are silently ignored. The `OrderFirst = true` / `OrderLast = true` properties on `[UpdateInGroup]` constrain only the immediate parent group, not transitively into ancestor or descendant groups. A custom `EntityCommandBufferSystem` subclass must be placed via `[UpdateInGroup]` + `[UpdateBefore]` — the relationship between custom ECB systems and update groups is the only place a Wave 1 system creates a managed type.

### Anti-patterns
- **Spawner in `FixedStepSimulationSystemGroup`** — placed there "just because" → causes 0-to-many spawn batches per render frame, visible as bursty entity population; only physics-like accumulation belongs in the fixed group.
- **Missing `state.Enabled = false` in a one-shot init system** — re-spawns / re-initializes every frame; exponential entity growth within seconds. Always disable after first successful `OnUpdate`.
- **`OrderFirst = true` for cross-group "guarantee"** — only orders within the immediate parent group, not transitively; cross-group ordering must be expressed by choosing the correct `[UpdateInGroup]`.
- **`[UpdateBefore(typeof(X))]` where X is in a different group** — silently ignored by the group sorter, no warning. Both systems must share `[UpdateInGroup]`.
- **Mutating simulation state from `PresentationSystemGroup`** — structural change happens after the frame's rendering has been submitted; produces undefined visual behavior and breaks the "presentation reads, never writes" invariant.

### Failure modes

| Symptom | Cause |
|---|---|
| System ticks at variable rate but logic assumes constant `DeltaTime` (e.g. integration explodes) | System is in default `SimulationSystemGroup` instead of `FixedStepSimulationSystemGroup` |
| One-shot initialization re-runs every frame, entity count explodes | Init system in `InitializationSystemGroup` but missing `state.Enabled = false` at end of `OnUpdate` |
| `[UpdateBefore(typeof(OtherSystem))]` has no effect, ordering wrong | `OtherSystem` is in a different update group than this system |
| Spawner produces bursty 0/0/0/3/0/0/2 entity creation per render frame | Spawner is in `FixedStepSimulationSystemGroup` which ticks 0–N times per render frame |
| Visual glitches that only appear in build, not in editor | Mutation in `PresentationSystemGroup` (post-render structural change) |

### Required code-example sources
Builder draws snippets from (evidence package, file:line):
- `Dots101/Entities101/Assets/HelloCube/11. FixedTimestep/FixedRateSpawnerSystem.cs:8-15` — `[UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]` on an `ISystem`; the in-file comment makes the "only difference is the group" decision explicit.
- `Dots101/Entities101/Assets/HelloCube/11. FixedTimestep/DefaultRateSpawnerSystem.cs:8-32` — same logic without `[UpdateInGroup]` → defaults to `SimulationSystemGroup` at variable rate. The two side-by-side teach the group selection decision.
- `Dots101/Entities101/Assets/HelloCube/8. CrossQuery/SpawnSystem.cs:10-25` — `[UpdateInGroup(typeof(InitializationSystemGroup))]` + `state.Enabled = false;` at end of first `OnUpdate` — canonical "run once at init" pattern.
- `EntitiesSamples/Assets/ExampleCode/ComponentsSystems.cs:154-167` — custom `EntityCommandBufferSystem` subclass placed via `[UpdateInGroup(typeof(InitializationSystemGroup))] [UpdateBefore(typeof(FooSystem))]` — the one valid pattern for a custom ECB system.

### Verification (per qa-validation/verification-contract.md)
- **Static (2–3):**
  1. For every `ISystem`-implementing struct with `[UpdateBefore(typeof(X))]` or `[UpdateAfter(typeof(X))]`, assert that struct and `X` share the same `[UpdateInGroup]` (or both default to `SimulationSystemGroup` when no attribute is present).
  2. For every system with `[UpdateInGroup(typeof(InitializationSystemGroup))]`, assert the `OnUpdate` body contains either `state.Enabled = false;` or a documented justification comment for re-running each frame.
  3. For every system with `[UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]`, assert it does not call `Instantiate` (spawn) without the architect's explicit acknowledgement — bursty-spawn is the most common misuse.
- **Runtime (2–3):**
  1. **EditMode ECS Test World** — schedule a frame at 120 FPS and at 30 FPS; assert systems in `FixedStepSimulationSystemGroup` accumulate to the same total `DeltaTime` over the same wall-clock window, while `SimulationSystemGroup` systems tick exactly the render-frame count.
  2. **Deterministic Runtime Checklist** — for a one-shot init system, advance 10 frames and assert `OnUpdate` ran exactly once (instrument via a counter field or log assertion).
  3. **Ordering test** — for any two systems with explicit `[UpdateBefore]`/`[UpdateAfter]` constraint, instrument both with frame-counter sentinel writes and assert the read order matches the constraint over 100 frames.

### Performance notes
- `FixedStepSimulationSystemGroup` may tick 0 times in a fast render frame and 4+ times in a slow render frame — your `OnUpdate` cost is multiplied by the per-frame tick count. Budget accordingly.
- Adding a system to `PresentationSystemGroup` introduces a sync point if it reads simulation data — measure before committing.
- `OrderFirst = true` / `OrderLast = true` are O(1) flags; `[UpdateBefore]`/`[UpdateAfter]` chains are O(N log N) in the group's topological sort — both are fine, but a long chain of `[UpdateBefore]` constraints is harder to reason about than `OrderFirst`/`OrderLast` for the rare "must be at edge of group" case.

### Banned API list for this skill (Entities 1.x)
- `[UpdateInGroup(typeof(ClientSimulationSystemGroup))]`, `[UpdateInGroup(typeof(ServerSimulationSystemGroup))]` — Netcode groups, deferred to Wave 7; if encountered in Wave 1 code, escalate to architect.
- `[AlwaysUpdateSystem]` — 0.x attribute; 1.x replacement is *absence* of `RequireForUpdate`, or explicit `state.Enabled = true` management.
- `ComponentSystemBase.LastSystemVersion` direct access — superseded by query change-version filters (`WithChangeFilter`), itself deferred to Wave 4.

### Overlap declaration
- vs Wave 1-legacy shipped skills:
  - `dots-ecb-orchestration` — **complementary, distinct.** That skill owns "which ECB singleton to consume in which group"; this spec owns "which groups exist and when they tick." Cross-link from this spec → `dots-ecb-orchestration` for the ECB phase decision; cross-link from `dots-ecb-orchestration` → here for the underlying group semantics.
  - Others: distinct.
- vs other Wave 1 specs:
  - `ecs-fundamentals` references `[BurstCompile]` and `RequireForUpdate<T>`; this spec references `[UpdateInGroup]` and group ordering — distinct mechanisms, no duplication.

### Pre-QA confidence
**0.88** — group selection is finite (4 groups in scope, plus the attribute family), evidence is direct, side-by-side fixed/default sample is uniquely strong. Confidence not at 0.95 because `RateManager` runtime tuning, custom-group definition, and `WorldSystemFilter` are real production needs deferred to a later wave — Wave 1 ships the substrate only.

---

## singleton-patterns

### Spec status
**DRAFT** — confidence 0.90

### Intent (1 sentence)
Three production singleton patterns in Entities 1.x — bake-time data, execution-toggle tag, framework-provided ECB singleton — and the single-writer rule that keeps them safe.

### Use when
- Defining a configuration / settings component that exactly one entity will carry (settings, prefab collections, scene-scope flags).
- Reading a settings component from a system via `SystemAPI.GetSingleton<T>()`.
- Consuming an `EntityCommandBufferSystem.Singleton` (`BeginSimulation*`, `EndSimulation*`, etc.) inside `OnUpdate`.
- Gating an `OnUpdate` on the presence of a singleton via `state.RequireForUpdate<T>()`.

### Avoid when
- A system needs to broadcast data to many entities — that's not a singleton, that's a `DynamicBuffer` or a per-entity component.
- Runtime gating that flips per-frame — use `IEnableableComponent` (covered by `dots-enableable-components`), not an add/remove of a singleton tag (avoid structural churn).

### Senior pattern (no code)
A "singleton" in Entities 1.x is simply *a component type that exactly one entity has* — there is no special declaration, no special interface, no `ISingletonComponent`. Three production patterns cover virtually every Wave 1 use case. **(a) Bake-time data singleton** — a single authoring `MonoBehaviour` bakes a struct holding configuration, prefab references, or scene-scoped settings; consumed read-only via `SystemAPI.GetSingleton<T>()`. Ownership rule: exactly one baker writes the component type. **(b) Execution-toggle tag singleton** — a zero-size `IComponentData` baked from a scene's authoring object, paired with `state.RequireForUpdate<T>()` to gate systems on the presence of the scene/feature. This is a **sample-only** convenience for scene execution toggles in the HelloCube samples (the `ExecuteFoo` family); production code should use `IEnableableComponent` for runtime gating, never add/remove tags per frame. **(c) Framework-provided singleton** — the `Singleton` nested struct on each `EntityCommandBufferSystem` (`BeginSimulationEntityCommandBufferSystem.Singleton`, etc.); consumed by `SystemAPI.GetSingleton<...>()` + `.CreateCommandBuffer(state.WorldUnmanaged)`. ECB singletons are the *only* documented exception to single-writer — multiple systems record commands into the same ECB per frame, and the framework arbitrates at playback. The safe-read contract is identical for all three: pair `RequireForUpdate<T>()` in `OnCreate` with `SystemAPI.GetSingleton<T>()` in `OnUpdate`. Reading a singleton in `OnCreate` directly is unsafe because baked singletons are not guaranteed to exist until baking has completed (after world boot). For optional singletons that may legitimately not exist, use `SystemAPI.TryGetSingleton<T>(out var x)` or `SystemAPI.HasSingleton<T>()` and do not gate with `RequireForUpdate`. For Burst-compatible mutation of singleton data, use `SystemAPI.GetSingletonRW<T>().ValueRW`; reserve `state.EntityManager.SetComponentData<T>` for cold paths. Runtime-created singletons (system creates its own singleton entity in `OnCreate`) are a real pattern but out of scope for Wave 1 — see Wave 6 (State Flow) for that treatment.

### Anti-patterns
- **Two bakers writing the same singleton type** — silent at bake time, runtime exception on first `SystemAPI.GetSingleton<Settings>()` with confusing "multiple entities have component" message. Ownership rule: each singleton type bakes from exactly one authoring source.
- **Reading a singleton in `OnCreate`** — baked singletons exist only after baking completes; `SystemAPI.GetSingleton<T>()` in `OnCreate` throws on world boot. Always defer to `OnUpdate` + `RequireForUpdate<T>()`.
- **Add/remove `ExecuteFoo`-style tags per frame for runtime gating** — every flip is a structural change → archetype churn. Use `IEnableableComponent` for runtime gating (covered by `dots-enableable-components`); reserve add/remove for bake-time-only configuration.
- **Mutating a singleton via `state.EntityManager.SetComponentData<T>` in a Burst-compiled `ISystem`** — not Burst-safe in all cases and unnecessarily expensive; use `SystemAPI.GetSingletonRW<T>().ValueRW = ...` for the writable accessor.
- **`SystemAPI.GetSingleton<T>()` without `RequireForUpdate<T>()` or `TryGetSingleton<T>()`** — throws on zero or multiple entities; "the singleton exists because the scene loaded it" is not a runtime guarantee.

### Failure modes

| Symptom | Cause |
|---|---|
| First-frame `InvalidOperationException: GetSingleton requires a single entity matching the query` | Baked singleton not yet present (race) — missing `RequireForUpdate<T>()` |
| Same exception, but only after a particular scene loads | Two authoring sources baked the same component type; multiple entities now match |
| Per-frame archetype churn warning, performance cliff over time | `ExecuteFoo` (or similar) tags added/removed per frame for runtime gating instead of using `IEnableableComponent` |
| `OnUpdate` runs even though prerequisite settings entity was never created | `RequireForUpdate<T>()` declared on the wrong type, or singleton consumed via `TryGetSingleton` but ignored |
| Burst job throws on singleton write | `EntityManager.SetComponentData` in a Burst-compiled path instead of `GetSingletonRW<T>().ValueRW` |

### Required code-example sources
Builder draws snippets from (evidence package, file:line):
- `Dots101/Entities101/Assets/HelloCube/14. ClosestTarget/SettingsAuthoring.cs:16-42` — bake-time data singleton (`Settings` struct holding prefab refs, counts, an enum).
- `Dots101/Entities101/Assets/HelloCube/14. ClosestTarget/InitializationSystem.cs:11-17` — `state.RequireForUpdate<Settings>() + state.RequireForUpdate<ExecuteClosestTarget>()` showing two `RequireForUpdate` calls chain with AND.
- `Dots101/Entities101/Assets/HelloCube/11. FixedTimestep/MoveProjectilesSystem.cs:12,19,24` — framework-provided runtime singleton: `state.RequireForUpdate<EndSimulationEntityCommandBufferSystem.Singleton>()` + `SystemAPI.GetSingleton<...>()` + `.CreateCommandBuffer(state.WorldUnmanaged)`.
- `Dots101/Entities101/Assets/HelloCube/_Common/ExecuteAuthoring.cs:6-69` — execution-toggle tag pattern (must be presented as a *sample shortcut* with explicit "do not use for runtime gating" guidance).
- `Dots101/Entities101/Assets/HelloCube/8. CrossQuery/SpawnSystem.cs:17-25` — `RequireForUpdate<PrefabCollection>()` + `state.Enabled = false` after one-shot consumption.

### Verification (per qa-validation/verification-contract.md)
- **Static (2–3):**
  1. For every `SystemAPI.GetSingleton<T>()` call, assert either the enclosing `ISystem` has a matching `state.RequireForUpdate<T>()` in `OnCreate`, or the call is `TryGetSingleton<T>(out _)`/`HasSingleton<T>()` instead.
  2. For every `IComponentData` type T used in a `GetSingleton<T>()` call, assert there is exactly one `Baker<TAuthoring>` (or one `AddComponent<T>` site) that produces it — grep all `AddComponent<T>` and `SetComponentData<T>` sites.
  3. For every Burst-compiled system that writes to a singleton, assert it uses `GetSingletonRW<T>().ValueRW = ...` and not `EntityManager.SetComponentData<T>`.
- **Runtime (2–3):**
  1. **EditMode ECS Test World** — create a world *without* the singleton entity; advance one frame; assert `OnUpdate` did not run (gating works). Then create the singleton entity; advance one frame; assert `OnUpdate` ran exactly once.
  2. **Failure-mode reproduction** — bake two entities with the same `Settings` component type; advance one frame; assert `SystemAPI.GetSingleton<Settings>()` throws with the multiple-entities exception (proves the failure mode is detectable in test).
  3. **Determinism** — read the same singleton from two systems in the same frame; assert both reads return bit-identical values (no torn reads).

### Performance notes
- `SystemAPI.GetSingleton<T>()` and `GetSingletonRW<T>()` are O(1) lookups via cached query — no per-call overhead beyond a query check.
- The `ExecuteFoo` execution-toggle tag pattern is **bake-time-only** by design; the moment it becomes a per-frame add/remove pattern, it's archetype churn — replace with `IEnableableComponent`.
- Singleton entity creation is one-time at bake; runtime cost of *consuming* a singleton is the lookup cost only.

### Banned API list for this skill (Entities 1.x)
- `World.GetExistingSystemManaged<BeginSimulationEntityCommandBufferSystem>().CreateCommandBuffer()` — 0.x access pattern; 1.x replacement is `SystemAPI.GetSingleton<BeginSimulationEntityCommandBufferSystem.Singleton>().CreateCommandBuffer(state.WorldUnmanaged)`.
- `SetSingleton<T>(value)` as a free-standing method on `SystemBase` — superseded by `GetSingletonRW<T>().ValueRW = value` in `ISystem`.
- `World.EntityManager.GetAllUniqueSharedComponentData<T>` for "is the singleton present?" — use `SystemAPI.HasSingleton<T>()` or `TryGetSingleton<T>()`.
- `ISingletonComponent`, `ISharedSingleton` — these are not Entities 1.x interfaces; any code referencing them is invented or copied from a non-Entities framework.

### Overlap declaration
- vs Wave 1-legacy shipped skills:
  - `dots-baking-patterns` — **complementary, distinct.** That skill owns the *baker side* ("how to write the Baker that produces a `Settings` singleton"). This spec owns the *runtime contract* ("how to consume one safely, gate it, mutate it, and validate it"). Cross-link both directions.
  - `dots-ecb-orchestration` — **complementary.** That skill owns the ECB orchestration; this spec owns the ECB singleton's *consumption pattern* (`RequireForUpdate` + `GetSingleton` + `CreateCommandBuffer`). Mention the ECB singleton as the canonical framework-provided example; defer all orchestration detail to `dots-ecb-orchestration`.
  - `dots-enableable-components` — referenced as the correct replacement for the `ExecuteFoo` per-frame-add-remove anti-pattern.
- vs other Wave 1 specs:
  - `ecs-fundamentals` defines `RequireForUpdate<T>()` as a lifecycle gate; this spec uses it as the safe-singleton-read precondition. Distinct uses, cross-link.
  - `entity-query-patterns` shares the underlying query mechanism (singletons are queries that match exactly one entity); cross-link for the `RequireForUpdate(EntityQuery)` overload comparison.

### Pre-QA confidence
**0.90** — three pattern types are finite, evidence is dense, the `ExecuteFoo` "do not promote to production" callout is explicit and well-evidenced. Confidence not at 1.0 because the runtime-created-singleton pattern is intentionally deferred to Wave 6 and the QA reviewer may push for inclusion — if so, accept the revision.

---

## entity-query-patterns

### Spec status
**DRAFT** — confidence 0.88

### Intent (1 sentence)
Construct and iterate entity queries safely across the three Entities 1.x iteration paths (`SystemAPI.Query`, `IJobEntity`, `IJobChunk`) with the correct filter grammar (`WithAll`, `WithNone`, `WithAny`, `WithEntityAccess`) and the right snapshot allocator.

### Use when
- Adding a new `SystemAPI.Query<...>()` foreach in `OnUpdate`.
- Building an `EntityQuery` for an `IJobChunk` Schedule.
- Snapshotting matching entities to a `NativeArray<T>` for cross-entity logic.
- Reviewing a query with `WithAll`/`WithNone`/`WithAny` to ensure the filter expresses the intent.

### Avoid when
- Change-version filtering (`WithChangeFilter<T>`) — deferred to Wave 4.
- Shared-component filtering (`SetSharedComponentFilter`) and `EntityQueryOptions.IgnoreComponentEnabledState` — deferred to a "advanced query filters" follow-up; cross-reference `dots-enableable-components` only.
- Job-internal query construction — queries must be built on the main thread and passed in; covered as an anti-pattern here.

### Senior pattern (no code)
There are exactly three production paths to iterate matching entities in a system: **(a) `SystemAPI.Query<...>()`** foreach — main-thread, source-generated, the most ergonomic for small N or rare iteration; **(b) `IJobEntity`** — same semantics jobified, the query is inferred from the `Execute(...)` signature plus any `[WithAll]`/`[WithNone]`/`[WithAny]` attributes on the job struct; **(c) `IJobChunk`** with an explicit `EntityQuery` — chunk-level iteration for cross-entity work and SIMD opportunities. The filter grammar is shared across all three: `WithAll<T>` requires presence, `WithNone<T>` requires absence, `WithAny<T>` requires at-least-one-of, `WithEntityAccess()` adds the `Entity` ID to the iteration. For snapshots, the standard idiom is `query.ToEntityArray(Allocator.Temp)` and `query.ToComponentDataArray<T>(Allocator.Temp)`; `Allocator.Temp` auto-frees at frame end and never needs explicit disposal. Long-lived queries (used in `IJobChunk.Schedule` or stored across `OnUpdate` calls) are cached in `OnCreate` via `state.GetEntityQuery(...)`; one-shot per-frame queries via `SystemAPI.QueryBuilder()...Build()` are equally efficient because the source generator memoizes the builder chain by textual identity (helper-method-constructed queries miss this memoization — cache them in `OnCreate` instead). Queries are built on the main thread only — building a query inside a job throws. Iterating one query inside another's foreach with overlapping component access trips the safety system ("container already in use") — snapshot the inner query to a `NativeArray<Entity>` first and iterate the snapshot. The query-based overload of `state.RequireForUpdate(EntityQuery)` is the correct gate when the precondition is "at least one entity matches this query" rather than "this singleton exists" — both overloads exist and serve different purposes.

### Anti-patterns
- **Building a query inside a job** — `SystemAPI.QueryBuilder()...Build()` called in `Execute()` → throws (or, worse, compiles in some cases and uses the wrong world). Always build queries on the main thread in `OnUpdate` or `OnCreate` and pass the `EntityQuery` into the job constructor.
- **`WithAll<T>` and `WithNone<T>` on the same type T** — query is permanently empty, no warning. Static-check this in code review.
- **`ToComponentDataArray<T>(Allocator.Persistent)` per frame** — every frame leaks the array; same applies to `Allocator.TempJob` without an explicit `Dispose()` call. The default per-frame allocator is `Allocator.Temp` (auto-freed at frame end).
- **Nested foreach over overlapping component sets** — `SystemAPI.Query<RefRW<A>>()` outer, `SystemAPI.Query<RefRO<A>>()` inner → safety system throws "container already in use." Snapshot the inner query (`ToEntityArray(Allocator.Temp)`) and iterate the snapshot.
- **Cached `EntityQuery` field used after a structural change that adds new matching entities** — live queries re-evaluate on access, but `ToEntityArray` snapshots are frozen; re-snapshot after any structural change mid-`OnUpdate`.
- **`SystemAPI.QueryBuilder()` constructed inside a helper method called from multiple sites** — source generator's textual memoization keys on the call site, not the produced query; helper-constructed queries miss the cache. Cache in `OnCreate` via `state.GetEntityQuery(...)` instead.

### Failure modes

| Symptom | Cause |
|---|---|
| Query foreach returns zero entities even though matching entities clearly exist | Same type used in both `WithAll<T>` and `WithNone<T>` — query is permanently empty |
| Safety-system exception "container already in use" mid-`OnUpdate` | Nested foreach with overlapping component access; snapshot the inner query first |
| `ArgumentException: query not built on main thread` | `SystemAPI.QueryBuilder()...Build()` called from inside a `IJobEntity` or `IJobChunk` body |
| Per-frame memory leak warning, performance degrades over time | `ToEntityArray(Allocator.Persistent)` or `Allocator.TempJob` without explicit `Dispose()` — use `Allocator.Temp` for per-frame snapshots |
| Newly-created entities missed by a snapshot iterated later in the same `OnUpdate` | Snapshotted with `ToEntityArray` *before* the structural change; re-snapshot or use the live query |

### Required code-example sources
Builder draws snippets from (evidence package, file:line):
- `Dots101/Entities101/Assets/HelloCube/4. IJobChunk/RotationSystem.cs:21-25` — `SystemAPI.QueryBuilder().WithAll<RotationSpeed, LocalTransform>().Build()` passed to `IJobChunk.Schedule(query, dependency)`; `SystemAPI.GetComponentTypeHandle<T>(true)` for read-only handle.
- `Dots101/Entities101/Assets/HelloCube/14. ClosestTarget/TargetingSystem.cs:42-43` — `WithAll<LocalTransform>().WithNone<Target, Settings>()` (exclude both a tag and the singleton entity) and `WithAll<LocalTransform, Target>()`.
- `Dots101/Entities101/Assets/HelloCube/8. CrossQuery/CollisionSystem.cs:22-23` — multi-component query against URP material property — shows queries spanning rendering + simulation components.
- `EntitiesSamples/Assets/ExampleCode/ComponentsSystems.cs:72-89` — `myQuery.ToComponentDataArray<T>(Allocator.Temp)` + `ToEntityArray(Allocator.Temp)` snapshot patterns.
- `EntitiesSamples/Assets/ExampleCode/ComponentsSystems.cs:137-145` — canonical `SystemAPI.Query<RefRW<Foo>, RefRO<Bar>>().WithAll<Apple>().WithNone<Banana>().WithEntityAccess()` foreach with entity ID access.

### Verification (per qa-validation/verification-contract.md)
- **Static (2–3):**
  1. Grep every `SystemAPI.QueryBuilder()` or `state.GetEntityQuery(` call site and assert it is inside an `ISystem` method body, not inside an `Execute(` body or inside a static helper.
  2. For every `WithAll<T>` chain, assert no type T appears in both `WithAll` and `WithNone` of the same query — flag matches as compile-time bugs.
  3. Grep every `.ToEntityArray(` / `.ToComponentDataArray(` / `.ToComponentDataArray<` call and assert the allocator argument is `Allocator.Temp` or `state.WorldUpdateAllocator`; flag `Allocator.Persistent` and `Allocator.TempJob` without an explicit nearby `Dispose()`.
- **Runtime (2–3):**
  1. **EditMode ECS Test World** — create N entities, run a `SystemAPI.Query<RefRW<T>>().WithEntityAccess()` foreach, assert the visited entity set matches the created set bit-for-bit (no missed, no extra).
  2. **Filter correctness** — create entities with components A and A+B; run a query with `WithAll<A>().WithNone<B>()`; assert only the A-only entities are visited.
  3. **Snapshot vs live behavior** — snapshot with `ToEntityArray(Allocator.Temp)`, perform an ECB-deferred structural change, then iterate the snapshot — assert the snapshot reflects pre-change state (proves the snapshot is frozen, not live).

### Performance notes
- `SystemAPI.Query<...>()` is main-thread, source-generated, and zero-overhead vs hand-rolled iteration; prefer for non-jobified per-frame work.
- `IJobChunk` is the right tool for cross-entity logic and SIMD-friendly tight loops; the per-chunk overhead amortizes over chunk capacity (~128 entities by default for small archetypes).
- `Allocator.Temp` per-frame snapshots are essentially free (rewind allocator); `Allocator.Persistent` per-frame is a memory leak; `Allocator.TempJob` per-frame requires explicit `Dispose()`.
- The source generator memoizes `SystemAPI.QueryBuilder()...Build()` chains by textual identity — inline construction is fine, helper-method construction silently misses the cache.

### Banned API list for this skill (Entities 1.x)
- `EntityManager.CreateEntityQuery(...)` as the primary query-construction call in `OnUpdate` — superseded by `SystemAPI.QueryBuilder()` and `state.GetEntityQuery()`.
- `Entities.ForEach((...) => {...}).WithAll<T>()` lambda chains — 0.x; replaced by `SystemAPI.Query<...>()` or `IJobEntity`.
- `EntityQueryDesc` struct-based query construction — superseded by the `QueryBuilder` fluent API.
- `Allocator.TempJob` without an explicit `Dispose()` call in the same `OnUpdate` body — leak vector; use `Allocator.Temp` or `state.WorldUpdateAllocator` for per-frame snapshots.

### Overlap declaration
- vs Wave 1-legacy shipped skills:
  - `dots-enableable-components` — **complementary, distinct.** That skill owns "how enableable components affect query results"; this spec owns the query construction grammar itself. Cross-link from this spec → `dots-enableable-components` for the `EntityQueryOptions.IgnoreComponentEnabledState` interaction.
  - `dots-spawning-patterns`, `dots-baking-patterns`, `dots-ecb-orchestration`, `dots-entity-lifecycle` — distinct domains.
- vs other Wave 1 specs:
  - `ecs-fundamentals` covers `SystemAPI.Query<RefRW<T>, RefRO<T>>()` as part of the substrate; this spec covers the full query grammar (`WithAll`/`WithNone`/`WithAny`/`WithEntityAccess`) and the three iteration paths. Cross-link without duplication — the substrate establishes "queries exist as `SystemAPI.Query`," this spec teaches "how to construct and filter them."
  - `singleton-patterns` shares `RequireForUpdate` mechanism (singleton-type overload there, query-based overload here); cross-link the two `RequireForUpdate` overloads for completeness.

### Pre-QA confidence
**0.88** — query construction is finite (5 filter clauses, 3 iteration paths, 2 long-vs-short-lived caching strategies), evidence is dense. Confidence not at 0.95 because shared-component filters, `EntityQueryOptions`, and `WithChangeFilter` are intentionally deferred — the QA reviewer may push to include `RequireForUpdate(EntityQuery)` as a worked example, which is reasonable to accept.

---

## Cross-spec architecture digest (for QA Curator)

1. **All four specs are DRAFT, none DEFER.** Evidence is sufficient for all four. No `[ESCALATE_QA]` collisions detected.
2. **Wave-level deferrals (intentional, documented in each spec's "Avoid when" and "Banned API"):**
   - `SystemBase` → Wave 7 (Hybrid)
   - `WorldSystemFilter` → Wave 7 (Netcode)
   - `WithChangeFilter<T>` → Wave 4 (Jobs + Burst)
   - Runtime-created singletons → Wave 6 (State Flow)
   - Shared-component filters / `EntityQueryOptions` → "advanced query filters" follow-up
3. **No >30% overlap with shipped skills.** All cross-references are complementary; no `REJECT_DUPLICATE` issued.
4. **Common substrate facts** (each spec references but does not own):
   - `partial struct ISystem` shell — owned by `ecs-fundamentals`
   - `[BurstCompile]` mandate — owned by `ecs-fundamentals`
   - `RequireForUpdate<T>()` mechanism — owned by `ecs-fundamentals`, used as a precondition by `singleton-patterns` and `entity-query-patterns`
   - `SystemAPI.*` surface — owned by `ecs-fundamentals`, specific calls owned by the relevant skill (`GetSingleton<T>` → `singleton-patterns`, `Query<...>` → `entity-query-patterns`, `GetSingleton<...Singleton>().CreateCommandBuffer` → `dots-ecb-orchestration` for orchestration, `singleton-patterns` for the consumption-as-singleton angle)
5. **Verification contract compliance:** every spec has both Static (2–3 grep-able checks) and Runtime (2–3 EditMode/Deterministic checks) per `qa-validation/verification-contract.md`. No `STATIC ONLY` or `RUNTIME ONLY` specs.
6. **Banned API discipline:** each spec lists Entities 0.x → 1.x replacements that are most likely to be re-introduced in that skill's surface area; no overlap with shipped-skill banned lists.

---

**End of Wave 1 specs.**
