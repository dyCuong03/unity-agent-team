---
name: entity-query-patterns-systemapi-query
description: Senior-level guide to `SystemAPI.Query<RefRW<T>, RefRO<U>, ...>()` as the default main-thread per-entity iteration inside `ISystem.OnUpdate`. Covers the RefRO/RefRW intent discipline, when to refine with `.WithAll` / `.WithNone` / `.WithEntityAccess`, the structural-change-in-iteration trap, when to promote to `IJobEntity`, and the silent-no-op of writing through a `RefRO`. Use when iterating entities on the main thread, deciding between SystemAPI.Query and IJobEntity, or debugging "my system runs but nothing changes".
metadata:
  internal-only: true
  tier: 3
---

# SystemAPI.Query Patterns — Senior Patterns

`SystemAPI.Query<...>()` with `foreach` is the senior default for main-thread iteration in `ISystem`. It's source-generated into a tight archetype-chunk loop, expresses read/write intent at the type level, and composes cleanly with `.WithAll` / `.WithNone` / `.WithAny` / `.WithEntityAccess`. It is *not* a substitute for `IJobEntity` at scale — but for the bulk of gameplay systems it's the right tool, and the discipline it enforces around access intent pays off across the rest of the codebase.

## Intent

Iterate entities on the main thread with explicit read/write intent, archetype-chunk-aware iteration, and zero allocation — so the system is fast, readable, and gives the scheduler the information it needs to parallelize adjacent jobs.

## Use when

- Main-thread per-entity work in `OnUpdate` that doesn't justify the cost of scheduling a job. Scheduling a job has overhead; for a few hundred entities with a simple body, `SystemAPI.Query` is faster end-to-end.
- The work touches managed objects (so a Burst job can't be used) but you still want chunk-iteration efficiency.
- The body is small and obvious — the kind of thing where reading the foreach is faster than reading an `IJobEntity` declaration.
- The system also does main-thread setup work (singleton read, ECB acquisition) — folding the iteration into the same method keeps the system file short.

## Avoid when

- Entity counts are large (thousands+) and the body is non-trivial. Promote to `IJobEntity.ScheduleParallel` — the main-thread ceiling here is real and shows up as a frame-time anchor.
- The body needs to mutate archetypes (`AddComponent`, `RemoveComponent`, `DestroyEntity`, structural moves). You cannot call `EntityManager` mutators inside the foreach — the enumerator becomes invalid. Use an ECB (see `dots-ecb-orchestration`).
- You need chunk-level optimizations: `DidChange` on the chunk, raw pointer iteration, version-filtered chunks. Drop to `IJobChunk` for that.
- The body is so trivial that even main-thread iteration is wasted — consider whether a singleton or an enableable component flip would solve it without per-entity work at all.

## Senior pattern

```csharp
using Unity.Burst;
using Unity.Entities;
using Unity.Transforms;

[BurstCompile]
public partial struct RotationSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        float dt = SystemAPI.Time.DeltaTime;

        // RefRW<LocalTransform>  — writing position/rotation
        // RefRO<RotationSpeed>   — reading speed
        // Source-gen turns this into archetype-chunk iteration. Zero alloc.
        foreach (var (transform, speed) in
                 SystemAPI.Query<RefRW<LocalTransform>, RefRO<RotationSpeed>>())
        {
            transform.ValueRW = transform.ValueRO.RotateY(speed.ValueRO.Radians * dt);
        }
    }
}
```

The `RefRO` / `RefRW` choice is the contract: it tells the source generator (and any reader of the code) which components are read and which are written. Adjacent systems can run in parallel against the same component if their access intents don't conflict — using `RefRW` "to be safe" forfeits that.

## Refining the implicit query

`SystemAPI.Query` derives an `EntityQuery` from the tuple. Add filters with the `.With*` methods:

```csharp
// Only entities that ALSO have BossTag (without including it in the tuple).
foreach (var transform in SystemAPI.Query<RefRW<LocalTransform>>()
                                   .WithAll<BossTag>())
{ /* ... */ }

// Exclude entities tagged Disabled.
foreach (var transform in SystemAPI.Query<RefRW<LocalTransform>>()
                                   .WithNone<Disabled>())
{ /* ... */ }

// At least one of A or B.
foreach (var transform in SystemAPI.Query<RefRW<LocalTransform>>()
                                   .WithAny<EngagedTag, AlertedTag>())
{ /* ... */ }

// Bring the Entity into the tuple — needed for ECB.DestroyEntity / structural ops.
foreach (var (transform, entity) in
         SystemAPI.Query<RefRW<LocalTransform>>().WithEntityAccess())
{
    if (transform.ValueRO.Position.y < 0)
        ecb.DestroyEntity(entity);
}

// Iterate enabled AND disabled instances of an IEnableableComponent.
foreach (var spinEnabled in
         SystemAPI.Query<EnabledRefRW<Spin>>()
                  .WithOptions(EntityQueryOptions.IgnoreComponentEnabledState))
{ /* ... */ }
```

The `.With*` builders compose without allocating — they return a query builder struct, not a managed collection.

## Anti-patterns

- Writing to `.ValueRW` on a `RefRO<T>`. The compiler rejects it, which is fine — but the worse failure mode is using `RefRW` everywhere "to be safe". Source-gen then treats every iteration as a writer, and the scheduler must serialize any adjacent job that reads the same component. The intent contract pays off only when you're disciplined about RefRO.
- Calling `state.EntityManager.AddComponent / RemoveComponent / DestroyEntity` inside the foreach. The mutation may invalidate the chunk you're iterating; you may corrupt the enumerator, skip entities, or process them twice. Record into an ECB and let it play back at a known phase.
- Capturing an enumerated `RefRW`/`RefRO` across a function boundary. The refs are valid only for the current iteration of the loop; passing one into a method that holds it across the next iteration is undefined behavior. If a helper needs the data, pass the *value* (`spin.ValueRO`) not the ref.
- Writing through `var x = …ValueRO; x.Field = …;` and expecting it to write back. `ValueRO` returns a copy of the value — assignments to that copy never reach the component. Use `ValueRW = newValue;` with `RefRW`.
- Using `SystemAPI.Query` on a thousand entities with a heavy per-entity math body, then wondering why the main thread is the bottleneck. Promote to `IJobEntity.ScheduleParallel` — the main-thread ceiling is what `SystemAPI.Query` is bounded by.

## Failure modes

| Symptom | Likely cause |
|---|---|
| System runs but the world state never changes | Used `RefRO` and wrote through `.ValueRW` (won't compile) OR wrote through a `ValueRO`-derived local copy that never reaches the component |
| `InvalidOperationException: This iterator is invalid` mid-frame | Called `EntityManager.AddComponent` / `DestroyEntity` inside the foreach — the underlying chunk array changed mid-iteration |
| System processes some entities twice or skips others | Same root cause — structural change during iteration. Use ECB |
| Adjacent jobs that "should" run in parallel are serialized | Over-declaring `RefRW` on read-only iterations; the scheduler conservatively assumes a write conflict |
| Performance is fine in editor but bad in player | Main-thread iteration over a count that grew at runtime; the job-promotion threshold was crossed. Move to `IJobEntity.ScheduleParallel` |
| `foreach` never enters the body | Implicit query has no matches — usually a missing tag, a `WithNone` that excludes everything, or `IEnableableComponent` with all instances disabled (see `dots-enableable-components`) |

## Runtime verification

- **Static:** grep `SystemAPI.Query<` and check each tuple type carries `RefRO` for read-only access and `RefRW` only where the body writes. If you see `RefRW` on a parameter whose only use is `.ValueRO`, downgrade it. This is the single highest-leverage code review item for ISystem performance.
- **Static:** any `SystemAPI.Query<...>` followed by `EntityManager.AddComponent` / `RemoveComponent` / `DestroyEntity` inside the foreach is a structural-change-in-iteration bug. Rewrite to use ECB.
- **Runtime:** in playmode, capture a Profiler sample of the system. If main-thread time is the bottleneck and entity count is high, the promotion to `IJobEntity` is overdue.

## Performance notes

- `SystemAPI.Query` is source-generated into archetype-chunk iteration — comparable throughput to `IJobEntity.Run()` (i.e. the same job structure executed on the main thread without scheduling). The overhead vs. raw `IJobEntity.Run` is negligible.
- The main-thread ceiling is the real limit. For a few hundred entities or low-cost bodies, scheduling overhead exceeds iteration cost — main-thread wins. For thousands of entities with non-trivial bodies, `IJobEntity.ScheduleParallel` wins by spreading across worker threads.
- `RefRO` / `RefRW` are intent declarations *and* alias hints — Burst can reorder reads of `RefRO` data more aggressively than reads of `RefRW`. Wrong intent doesn't just cost scheduling — it costs in-loop performance too.

## Compile / editor safety

- `SystemAPI.Query` requires `partial struct` (or `partial class` for `SystemBase`) for source generation. Forgetting `partial` produces obscure source-gen errors.
- Inside a `[BurstCompile]` `OnUpdate`, the body of the foreach must be Burst-clean — managed allocations, `Debug.Log` with interpolation, or `string` construction will fail compilation. See `ecs-fundamentals-isystem-default` for the bridge-system pattern when managed work is unavoidable.

## Entities version notes (1.4.x)

- `SystemAPI.Query<RefRW<T>, RefRO<U>, ...>()` is the current surface. The 0.x `Entities.ForEach` API is the predecessor — different ergonomics (lambda capture rules), `SystemBase`-only — refuse old patterns in reviews of new code.
- `RefRW<T>` / `RefRO<T>` / `EnabledRefRW<T>` / `EnabledRefRO<T>` are the current ref types. The 0.x `ref T` / `in T` parameter syntax inside `Entities.ForEach` is gone.
- `.WithEntityAccess()` replaces the 0.x `Entity entity` parameter capture from `Entities.ForEach`.

## See also

- [`ecs-fundamentals-isystem-default`](../ecs-fundamentals-isystem-default/SKILL.md) — the host system type for this iteration pattern
- [`entity-query-patterns-requireforupdate-gating`](../entity-query-patterns-requireforupdate-gating/SKILL.md) — every system that runs this loop should gate on its prerequisites
- [`dots-ecb-orchestration`](../dots-ecb-orchestration/SKILL.md) — the right tool for structural changes the foreach can't make safely
- [`dots-enableable-components`](../dots-enableable-components/SKILL.md) — `EnabledRefRW`/`EnabledRefRO` and `IgnoreComponentEnabledState` query options
