# Wave 1 — Reverse-Engineer Evidence

**Author:** dots-reverse-engineer (Panel 2)
**Date:** 2026-05-26
**Scope:** HelloCube + Basic ECS Lifecycle
**Files read (14, all under EntitiesSamples on disk):**

1. `Dots101/Entities101/Assets/HelloCube/1. MainThread/RotationSystem.cs`
2. `Dots101/Entities101/Assets/HelloCube/2. IJobEntity/RotationSystem.cs`
3. `Dots101/Entities101/Assets/HelloCube/4. IJobChunk/RotationSystem.cs`
4. `Dots101/Entities101/Assets/HelloCube/8. CrossQuery/CollisionSystem.cs`
5. `Dots101/Entities101/Assets/HelloCube/8. CrossQuery/MoveSystem.cs`
6. `Dots101/Entities101/Assets/HelloCube/8. CrossQuery/SpawnSystem.cs`
7. `Dots101/Entities101/Assets/HelloCube/8. CrossQuery/VelocityAuthoring.cs`
8. `Dots101/Entities101/Assets/HelloCube/8. CrossQuery/PrefabCollectionAuthoring.cs`
9. `Dots101/Entities101/Assets/HelloCube/8. CrossQuery/DefaultColorAuthoring.cs`
10. `Dots101/Entities101/Assets/HelloCube/11. FixedTimestep/DefaultRateSpawnerSystem.cs`
11. `Dots101/Entities101/Assets/HelloCube/11. FixedTimestep/FixedRateSpawnerSystem.cs`
12. `Dots101/Entities101/Assets/HelloCube/11. FixedTimestep/MoveProjectilesSystem.cs`
13. `Dots101/Entities101/Assets/HelloCube/14. ClosestTarget/{InitializationSystem,TargetingSystem,MovementSystem,SettingsAuthoring,TargetAuthoring}.cs`
14. `Dots101/Entities101/Assets/HelloCube/_Common/ExecuteAuthoring.cs` + `EntitiesSamples/Assets/ExampleCode/ComponentsSystems.cs`

All paths verified Entities 1.x. No `Entities.ForEach`, no `Translation`/`Rotation`/`NonUniformScale`, no `IConvertGameObjectToEntity`, no `ISystemStateComponentData`. `SystemBase` only appears once in `ComponentsSystems.cs` as `EntityCommandBufferSystem` (its valid managed base), not as a runtime system.

---

## ecs-fundamentals

### Sources cited
- `Dots101/.../HelloCube/1. MainThread/RotationSystem.cs:7-33` — canonical `partial struct ISystem` with `[BurstCompile]` on every entry point (`OnCreate`, `OnUpdate`), `state.RequireForUpdate<T>()` gating, `SystemAPI.Time.DeltaTime`, and `SystemAPI.Query<RefRW<T>, RefRO<T>>()` foreach iteration.
- `Dots101/.../HelloCube/8. CrossQuery/VelocityAuthoring.cs:25-29` — minimal `IComponentData` struct: plain blittable fields, no methods, no `[Serializable]` needed for ECS.
- `Dots101/.../HelloCube/2. IJobEntity/RotationSystem.cs:8-25` — `ISystem` that schedules a job: `OnUpdate` constructs the job struct, captures only blittable inputs, calls `.Schedule()`. Job lives outside the system struct.
- `EntitiesSamples/Assets/ExampleCode/ComponentsSystems.cs:31-55` — full lifecycle template: `OnCreate` / `OnDestroy` / `OnUpdate`, all three `[BurstCompile]`, all three optional when empty.
- `Dots101/.../HelloCube/14. ClosestTarget/TargetAuthoring.cs:18-21` — zero-field tag component pattern (`AddComponent<Target>` with `public struct Target : IComponentData { public Entity Value; }` — almost-tag with one entity ref).

### Reusable pattern
Every runtime system is `public partial struct <Name>System : ISystem`, `[BurstCompile]` on each lifecycle method, and uses `SystemAPI.*` exclusively for time, queries, singletons, and component access — never `state.EntityManager.GetComponentData<T>` in hot paths. `RefRW<T>` / `RefRO<T>` in `SystemAPI.Query` is mandatory in Entities 1.x — the old `ref T, in T` foreach is gone. Components are blittable structs implementing `IComponentData` (or `IBufferElementData`); they hold data only, never methods that touch other entities.

### Where the sample is a shortcut
`HelloCube/1. MainThread` deliberately omits jobs to show the "naive" baseline — production should never iterate transforms on the main thread at this scale. The samples also assume Burst always succeeds; real code needs a non-Burst fallback path or compile-time guards (`[BurstCompile(CompileSynchronously = true)]` is appropriate for OnCreate but not the default in samples). Finally, none of the samples define `OnDestroy` — production systems that allocate `NativeArray`/`NativeHashMap` at `OnCreate` must dispose in `OnDestroy` (see `TargetingSystem.OnDestroy` lines 35-38 for the one exception).

### Failure modes observed or implied
- Forgetting `partial` on the struct → source generator silent failure, system never registers ← `partial` is required so the SG can emit the `ISystem` glue.
- Missing `RefRW`/`RefRO` wrappers in `SystemAPI.Query` → compile error in Entities 1.x; copying the example from 0.x docs is the most common mistake ← API moved from `ref T, in T` to `RefRW<T>, RefRO<T>` plus `.ValueRW`/`.ValueRO`.
- Reading `.ValueRW` when you only need read access → unnecessary safety-system writability flag → blocks parallel scheduling later ← always use `.ValueRO` for reads.
- Calling `SystemAPI.*` from a `static` method or outside an `ISystem` method body → source generator cannot resolve `state` ← `SystemAPI` is rewritten by SG and only legal inside `ISystem`/`SystemBase`/`IJobEntity` bodies.
- Allocating in `OnUpdate` without disposing (e.g., `NativeArray<T>(Allocator.TempJob)` not freed) → leak warning every frame ← prefer `Allocator.Temp` or `state.WorldUpdateAllocator` (auto-freed at frame end).

### Overlap with shipped skills
Overlaps weakly with `dots-entity-lifecycle` (which covers entity create/destroy). This skill is broader: it covers the system shell itself (struct layout, lifecycle methods, SystemAPI surface) — the substrate every other skill assumes. Suggested cross-link: `ecs-fundamentals` → "see `dots-entity-lifecycle` for entity create/destroy patterns" rather than re-covering.

### Reusability score: 0.95
Justification: This is the substrate. Every DOTS skill, every existing project file, and every Wave 2+ skill (baking, ECB, jobs) builds on this exact `partial struct ISystem + [BurstCompile] + SystemAPI` template. Score lowered from 1.0 because the "managed SystemBase" path (still valid for `EntityCommandBufferSystem` and reactive `SystemBase` patterns) is intentionally out of scope here and needs a separate Wave 7 (Hybrid) treatment.

### Open questions for the Architect (3)
1. Should this skill cover `SystemBase` at all, or is it strictly `ISystem`-only and `SystemBase` is deferred to Wave 7?
2. Do we ship a "lifecycle anti-patterns" appendix (e.g., do-not-do `state.EntityManager.CreateEntity()` in a struct OnUpdate hot path), or keep the skill positive-only?
3. Where does the `partial` requirement live — in `ecs-fundamentals` (because it's a syntactic property of every ISystem) or in a separate "source-generator gotchas" advisory?

---

## dots-update-groups

### Sources cited
- `Dots101/.../HelloCube/11. FixedTimestep/FixedRateSpawnerSystem.cs:8-15` — `[UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]` on an `ISystem`; the in-file comment explicitly states the only difference from `DefaultRateSpawnerSystem` is the group → this **is** the canonical "how to put a system on fixed timestep" pattern.
- `Dots101/.../HelloCube/11. FixedTimestep/DefaultRateSpawnerSystem.cs:8-32` — same logic with **no** `[UpdateInGroup]` → defaults to `SimulationSystemGroup` at variable rate. Comparing the two side-by-side teaches the group selection decision.
- `Dots101/.../HelloCube/11. FixedTimestep/MoveProjectilesSystem.cs:7-26` — system that pairs `EndSimulationEntityCommandBufferSystem.Singleton` with a default-group system, showing ECB-singleton + group interaction.
- `Dots101/.../HelloCube/8. CrossQuery/SpawnSystem.cs:10-25` — `[UpdateInGroup(typeof(InitializationSystemGroup))]` + `state.Enabled = false;` at end of first OnUpdate → canonical "run once at init" pattern.
- `EntitiesSamples/Assets/ExampleCode/ComponentsSystems.cs:154-167` — custom `EntityCommandBufferSystem` subclass placed via `[UpdateInGroup(typeof(InitializationSystemGroup))] [UpdateBefore(typeof(FooSystem))]` → the only valid pattern for a custom ECB system.

### Reusable pattern
Group selection drives execution semantics, not just ordering. `SimulationSystemGroup` (default) runs once per render frame with variable `DeltaTime`; `FixedStepSimulationSystemGroup` runs zero-to-many times per frame with a constant `DeltaTime` and is the only correct place for physics-like accumulation. `InitializationSystemGroup` + `state.Enabled = false` is the canonical "run once after world boot" pattern — preferable to `OnCreate`-side spawning because `SystemAPI.GetSingleton<T>()` for bake-time singletons is only safe after baking has completed. `[UpdateBefore]` / `[UpdateAfter]` express ordering **within** a single group; cross-group ordering is by `[UpdateInGroup]` choice only.

### Where the sample is a shortcut
The sample never demonstrates `[UpdateInGroup(typeof(PresentationSystemGroup))]`, `[CreateAfter]`/`[CreateBefore]`, or `OrderFirst`/`OrderLast` — important production controls. It also doesn't show `WorldSystemFilter` (server-only / client-only systems for Netcode) — likely deliberate (Wave 7 territory). The `FixedTimestep` sample doesn't touch `RateManager.Timestep` (the public knob for tuning fixed step from 1/60s to a different rate); that's hidden behind `SliderHandler.cs` (managed code, not shown).

### Failure modes observed or implied
- Putting a spawner in `FixedStepSimulationSystemGroup` "just because" → causes 0-to-many spawn batches per frame, visible as bursty population ← only physics-like accumulation belongs there.
- Forgetting `state.Enabled = false` in a one-shot init system → re-spawns every frame, exponential entity growth ← always disable after first successful OnUpdate.
- Using `OrderFirst = true` to "guarantee" running before another group's first system → only orders within the immediate parent group, not transitively ← use `[UpdateInGroup]` + `[UpdateBefore]` for precise control.
- `[UpdateBefore(typeof(X))]` where X lives in a different group → silently ignored by the group sorter, no warning ← both systems must share `[UpdateInGroup]`.
- Adding work to `PresentationSystemGroup` that mutates simulation state → structural change after rendering submitted, undefined visual behavior ← Presentation is read-only relative to simulation.

### Overlap with shipped skills
No direct overlap. `dots-ecb-orchestration` references `BeginSimulationEntityCommandBufferSystem.Singleton` / `EndSimulationEntityCommandBufferSystem.Singleton` — the names of those singletons **are** an update-group fact (they're the ECB systems registered in `SimulationSystemGroup`). Suggested cross-link: `dots-update-groups` owns "which groups exist and when they tick"; `dots-ecb-orchestration` owns "which ECB singleton to consume in which group."

### Reusability score: 0.90
Justification: Every system needs a group decision. The skill is short, finite (5 standard groups + a handful of attributes), and high-leverage. Score lowered from 1.0 because RateManager tuning, `WorldSystemFilter`, and custom group definition are real production needs that the HelloCube samples skip — they'll need a follow-up sub-skill in Wave 7 or as a "production" appendix.

### Open questions for the Architect (3)
1. Do we cover `WorldSystemFilter.LocalSimulation` / `ServerSimulation` / `ClientSimulation` here, or defer to a Netcode-specific skill in Wave 7?
2. Should "custom ComponentSystemGroup" (the `MySystemGroup` pattern in `ComponentsSystems.cs:58-62`) ship in Wave 1, or wait until a real use case appears?
3. RateManager tuning — runtime-set via `SystemAPI.GetSingleton<...>` or compile-time via `[UpdateInGroup]` attributes — which is the documented production knob?

---

## singleton-patterns

### Sources cited
- `Dots101/.../HelloCube/_Common/ExecuteAuthoring.cs:6-69` — the canonical "execution-toggle singleton" pattern: one authoring MonoBehaviour bakes one or more zero-size tag components onto a single entity; every system in the sample sets `state.RequireForUpdate<ExecuteFoo>()` to gate its OnUpdate on a baked tag.
- `Dots101/.../HelloCube/14. ClosestTarget/SettingsAuthoring.cs:16-42` — bake-time singleton with real data (`Settings` struct holding prefab refs, counts, an enum). Consumed by `SystemAPI.GetSingleton<Settings>()` at line `InitializationSystem.cs:23` and `TargetingSystem.cs:45`.
- `Dots101/.../HelloCube/14. ClosestTarget/InitializationSystem.cs:11-17` — `state.RequireForUpdate<Settings>() + state.RequireForUpdate<ExecuteClosestTarget>()` → two `RequireForUpdate` calls **chain with AND**, both singletons must exist before OnUpdate runs.
- `Dots101/.../HelloCube/11. FixedTimestep/MoveProjectilesSystem.cs:12,19,24` — runtime ECB-system singleton: `state.RequireForUpdate<EndSimulationEntityCommandBufferSystem.Singleton>()` + `SystemAPI.GetSingleton<...>()` + `.CreateCommandBuffer(state.WorldUnmanaged)`. Demonstrates the "framework-provided" singleton consumed across many systems per frame.
- `Dots101/.../HelloCube/8. CrossQuery/SpawnSystem.cs:17-25` — `state.RequireForUpdate<PrefabCollection>()` paired with `state.Enabled = false` after consumption — a singleton used **once** at boot then never again.

### Reusable pattern
A "singleton" in Entities 1.x is **a component type that exactly one entity has** — there is no special declaration. Three production patterns: (a) bake-time data singleton (baked from a single authoring MonoBehaviour, holds config / prefab refs / settings — consumed read-only via `GetSingleton<T>()`); (b) execution-toggle tag singleton (zero-size component used only with `RequireForUpdate<T>()` to gate scenes/levels — the `ExecuteFoo` family); (c) framework-provided singleton (the ECB-system `Singleton` struct, owned by an `EntityCommandBufferSystem`, consumed read-write across many writers per frame via `CreateCommandBuffer`). The single-writer rule applies to bake-time and execution-toggle singletons — never `SetSingleton<T>` from multiple systems without explicit ordering. ECB singletons are the documented exception (multiple writers, framework arbitrates at playback).

### Where the sample is a shortcut
The samples bake every "singleton" from a unique authoring component — they never demonstrate `TryGetSingleton<T>` or `HasSingleton<T>` for the case where the singleton may legitimately not exist (e.g., conditional features). They also never show `GetSingletonRW<T>` for in-place mutation, only `GetSingleton<T>` read + `EntityManager.SetComponentData` write — which is the wrong pattern in Burst-able code. Finally, no sample shows the failure case where two authoring components bake the same component type onto two entities → `GetSingleton<T>` throws at runtime with a confusing "multiple entities" message.

### Failure modes observed or implied
- `SystemAPI.GetSingleton<T>()` throws if zero or multiple entities have `T` ← always pair with `RequireForUpdate<T>()` or `TryGetSingleton<T>` for optional cases.
- Two different baker scripts both `AddComponent<Settings>` → silent at bake time, runtime exception on first `GetSingleton<Settings>` call ← ownership rule: each singleton type bakes from exactly one authoring source.
- Mutating a singleton via `EntityManager.SetComponentData` from a Burst-compiled `ISystem` → not Burst-safe in all cases; prefer `GetSingletonRW<T>().ValueRW = ...` ← samples skip this entirely, production should use RW accessor.
- Using `ExecuteFoo`-style tags from runtime code (adding/removing them per frame) → structural change every frame, archetype churn ← these tags are bake-time only by design; runtime gating should use `IEnableableComponent`.
- Consuming a bake-time singleton in `OnCreate` directly → singleton entity may not exist yet (baking happens after `OnCreate`) ← always defer first read to `OnUpdate` and gate with `RequireForUpdate<T>()`.

### Overlap with shipped skills
Weak overlap with `dots-baking-patterns` (which owns the "how to write a Baker"). This skill owns the **runtime contract**: how to gate, read, mutate, and validate singletons. Suggested split: `dots-baking-patterns` → "how to bake a Settings singleton"; `singleton-patterns` → "how to consume one safely from a system, including `RequireForUpdate` and single-writer rules."

### Reusability score: 0.92
Justification: Singletons are how every DOTS system gets its world-config inputs and how every project bridges level-load → simulation. The `RequireForUpdate<T>` + `GetSingleton<T>` idiom is in literally every system file we read. Score lowered from 1.0 because the runtime-created singleton case (system itself creates the singleton entity, common for stateful systems like score / global cooldown / pause flag) is not exercised by HelloCube — Architect may want to add a Wave 6 cross-link when state-flow patterns ship.

### Open questions for the Architect (3)
1. Do we ship guidance for runtime-created singletons (system creates its own singleton entity in OnCreate) now, or wait for the state-flow skill in Wave 6?
2. Should the `ExecuteFoo` tag pattern be its own micro-skill ("scene execution toggles") or stay as a worked example inside `singleton-patterns`?
3. `GetSingletonRW<T>` vs `EntityManager.SetComponentData<T>` for write — which do we recommend as the production default in Burst-able code?

---

## entity-query-patterns

### Sources cited
- `Dots101/.../HelloCube/4. IJobChunk/RotationSystem.cs:21-25` — `SystemAPI.QueryBuilder().WithAll<RotationSpeed, LocalTransform>().Build()` cached only inline; passed to `IJobChunk.Schedule(query, dependency)`. `SystemAPI.GetComponentTypeHandle<T>(true)` for read-only, no `true` for read-write.
- `Dots101/.../HelloCube/14. ClosestTarget/TargetingSystem.cs:42-43` — two queries built each OnUpdate: `WithAll<LocalTransform>().WithNone<Target, Settings>()` (find targets-without-target-tag, excluding the settings singleton entity) and `WithAll<LocalTransform, Target>()`. Demonstrates `WithNone` to exclude both a tag and the singleton entity from the same query.
- `Dots101/.../HelloCube/8. CrossQuery/CollisionSystem.cs:22-23` — multi-component query against URP material property — shows queries that span rendering + simulation components.
- `EntitiesSamples/Assets/ExampleCode/ComponentsSystems.cs:72-89` — `myQuery.ToComponentDataArray<T>(Allocator.Temp)` + `ToEntityArray(Allocator.Temp)` patterns for snapshotting; `Allocator.Temp` requires no manual dispose.
- `EntitiesSamples/Assets/ExampleCode/ComponentsSystems.cs:137-145` — `SystemAPI.Query<RefRW<Foo>, RefRO<Bar>>().WithAll<Apple>().WithNone<Banana>().WithEntityAccess()` → the canonical SG-foreach with entity ID access.

### Reusable pattern
There are exactly three ways to iterate matching entities in a system: (a) `SystemAPI.Query<...>()` foreach — most ergonomic, main thread, source-generated; (b) `IJobEntity` — same semantics but jobified, query inferred from `Execute` signature; (c) `IJobChunk` with an explicit `EntityQuery` — chunk-level iteration for cross-entity logic and SIMD opportunities. `WithAll<T>` filters by presence, `WithNone<T>` by absence, `WithAny<T>` by at-least-one-of, `WithEntityAccess()` adds the `Entity` ID. For optional read-only snapshots, `query.ToEntityArray(Allocator.Temp)` + `query.ToComponentDataArray<T>(Allocator.Temp)` is the standard idiom — both auto-freed at frame end. For long-lived queries (used across multiple OnUpdate calls or stored as a field), cache in `OnCreate` with `state.GetEntityQuery(...)`; for one-shot per-frame queries, `SystemAPI.QueryBuilder().WithAll<T>().Build()` is fine because the SG caches it for you.

### Where the sample is a shortcut
The samples never use `state.GetEntityQuery(...)` field caching — every query is built inline in `OnUpdate`. This is fine because Entities 1.x SG memoizes `QueryBuilder` chains by their textual identity, but a project where queries are constructed in helper methods will silently miss the cache. The samples also don't demonstrate `EntityQueryOptions.IgnoreComponentEnabledState` (referenced in `ComponentsSystems.cs:318` but not used in the HelloCube path), or shared-component filters (`SetSharedComponentFilter`), which are critical for grouping entities by render layer or team. No sample uses `RequireForUpdate(query)` — the query-based overload of `RequireForUpdate` that gates OnUpdate by query non-empty (vs the singleton-type overload).

### Failure modes observed or implied
- Calling `SystemAPI.QueryBuilder()...Build()` inside a job → not allowed; queries must be built on the main thread and passed in ← build in OnUpdate, pass into job constructor.
- `WithAll<T>` + `WithNone<T>` for the same type T → query is permanently empty, no warning ← static check this in code review.
- Using `ToComponentDataArray<T>(Allocator.Persistent)` and forgetting to dispose → leak every frame ← always `Allocator.Temp` (auto-freed) or `state.WorldUpdateAllocator` (auto-freed at frame end) for per-frame snapshots.
- Iterating one query inside another query's foreach with overlapping component access → safety system throws "container already in use" ← snapshot the inner query to a temp array first (the CrossQuery sample explicitly does this at lines 38-39).
- Forgetting to refresh a cached `EntityQuery` field after a structural change → query result may exclude newly-added entities until next frame ← Entities 1.x queries are live (re-evaluated on access), but `ToEntityArray` snapshot is not — re-snapshot if you make structural changes mid-OnUpdate.

### Overlap with shipped skills
No direct overlap with shipped skills. `dots-enableable-components` may cross-reference `EntityQueryOptions.IgnoreComponentEnabledState` (the only query option that interacts with enableable state). Suggested cross-link: `entity-query-patterns` owns the query construction grammar; `dots-enableable-components` owns the "how disabled components affect query results" detail.

### Reusability score: 0.93
Justification: Queries are the second-most-universal API after `ISystem` itself. Three iteration paths (`SystemAPI.Query`, `IJobEntity`, `IJobChunk`) cover essentially every gameplay system. Score lowered from 1.0 because `SetSharedComponentFilter`, `EntityQueryOptions`, and `WithChangeFilter` are production-grade query patterns that HelloCube doesn't exercise — Architect may want a "advanced query filters" follow-up sub-skill.

### Open questions for the Architect (3)
1. Do we cover `WithChangeFilter<T>` here (change-version filtering) or defer to a Wave 4 jobs/dependency skill where change-version actually matters most?
2. Cached-in-`OnCreate` queries vs inline `SystemAPI.QueryBuilder` — which do we recommend as the production default, and does the answer change for hot vs cold OnUpdate?
3. `RequireForUpdate(EntityQuery)` (query-based gating) is a real Entities 1.x API but absent from HelloCube — do we ship a worked example or document its existence and defer to a real-use Wave?

---

## Cross-skill notes (architect digest)

- **`partial struct ISystem`** is the universal shell. Every Wave 1 skill spec should open with this single fact.
- **`SystemAPI.*` over `state.EntityManager.*`** is the universal preference for hot-path code in Entities 1.x — call this out in `ecs-fundamentals` and reinforce in `singleton-patterns` + `entity-query-patterns`.
- **`Allocator.Temp` is the default** for per-frame native allocations in samples — no sample uses `Allocator.TempJob` outside of an explicit job that disposes it. Make this the default recommendation across all four skills.
- **`RequireForUpdate<T>` is the gate** — used by every system in the sample to defer OnUpdate until prerequisites exist. It belongs in `ecs-fundamentals` (as a lifecycle gate) AND `singleton-patterns` (as the safe pattern for reading singletons).
- **The `ExecuteFoo` tag pattern** is a deliberate sample-only convenience for toggling scenes — production should NOT copy it for runtime gating. Call this out explicitly in `singleton-patterns` "shortcuts" section.
- **No overlap with shipped skills is heavy enough to warrant a split or merge.** All four Wave 1 skills are complementary to the shipped 5 (`dots-baking-patterns`, `dots-ecb-orchestration`, `dots-enableable-components`, `dots-entity-lifecycle`, `dots-spawning-patterns`) and slot in cleanly below them as the substrate.

---

**End of Wave 1 evidence.**
