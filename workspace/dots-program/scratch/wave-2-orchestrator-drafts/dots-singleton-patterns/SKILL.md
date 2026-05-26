---
name: dots-singleton-patterns
description: Model cross-system shared configuration and game state as a single-entity component with a strict single-writer contract. Covers RequireForUpdate gating, SystemAPI.GetSingleton / GetSingletonRW / HasSingleton / TryGetSingleton, bake-time vs runtime-created vs ECB-system singletons, the "exactly one entity" runtime invariant, and the single-writer rule. Use when designing frame-stable global config, shared mutable state, or any component intended to exist on exactly one entity.
---

# Singleton Patterns — Senior Patterns

A "singleton" in DOTS is a component on **exactly one entity**, accessed through a uniform API. It is not a static field, not a `World.GetOrCreate<T>`, and not a service locator. Misuse is silent until the day a second entity gets the component and the system throws on `GetSingleton`.

## Intent

Share a single piece of state across many systems with one declared writer, one well-defined creation point, and a runtime invariant (one and only one).

## Three creation pathways (pick one per singleton, document it)

| Pathway | When | Mutability |
|---|---|---|
| **Bake-time** (Authoring + Baker writes one entity in the subscene) | Frame-stable config: game settings, level parameters, level-load seed | Immutable at runtime (treat as `readonly`) |
| **Runtime-created** (`state.EntityManager.CreateEntity` + `AddComponent` in `OnCreate` of an owner system) | Mutable game state: current input snapshot, level-loaded flag, frame stats | One owner writes; others read |
| **ECB-system singleton** (`EndSimulationEntityCommandBufferSystem.Singleton` etc.) | Built-in: ECB recorder handles | Read-only handle, never written by user code |

## Senior pattern

```csharp
// Component carries data; nothing on it forces uniqueness — the contract is enforced
// by your code paths, NOT by a type-system marker.
public struct LevelConfig : IComponentData
{
    public int   LevelIndex;
    public float Gravity;
    public uint  Seed;
}

public partial struct GravitySystem : ISystem
{
    [BurstCompile]
    public void OnCreate(ref SystemState state)
    {
        // Declares "we need this singleton" — system idles cleanly until it exists.
        // Without this, GetSingleton<LevelConfig>() throws if the singleton is missing.
        state.RequireForUpdate<LevelConfig>();
    }

    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        // Read path — safe because RequireForUpdate guarantees existence.
        var cfg = SystemAPI.GetSingleton<LevelConfig>();

        // Hot path: capture into job, don't call SystemAPI from inside the job.
        new ApplyGravityJob { Gravity = cfg.Gravity, Dt = SystemAPI.Time.DeltaTime }
            .ScheduleParallel();
    }
}

// Mutation: ONE owner system writes via GetSingletonRW. Mark single-writer in code review.
public partial struct LevelClockSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var cfgRef = SystemAPI.GetSingletonRW<LevelConfig>();
        cfgRef.ValueRW.Seed = cfgRef.ValueRO.Seed + 1u;
    }
}
```

## Optional / nullable singletons

When the singleton may not exist (level not loaded yet, ECB system not available):

```csharp
if (SystemAPI.HasSingleton<LevelConfig>())
{
    var cfg = SystemAPI.GetSingleton<LevelConfig>();
    // ...
}

// Or:
if (SystemAPI.TryGetSingleton<LevelConfig>(out var cfg)) { /* ... */ }
```

Prefer `RequireForUpdate<T>` over runtime `HasSingleton` checks — it gates the whole `OnUpdate`, saves the dispatch when not present, and documents intent.

## Anti-patterns

- ❌ Two systems calling `GetSingletonRW<T>` on the same component. Single-writer contract violation. Code review must reject — even if both writers happen to write the same value, the dependency graph becomes a race.
- ❌ Iterating an `EntityQuery` to find "the one entity" instead of `SystemAPI.GetSingletonEntity<T>()`. Slower and breaks if a second entity ever appears.
- ❌ Putting hot per-frame per-entity data on a singleton just to share it. Defeats chunk locality — N readers do N pointer chases instead of one chunk scan.
- ❌ Calling `SystemAPI.GetSingleton<T>` *inside* a parallel job. Singletons aren't job-safe. Capture into the job struct as a value on the main thread before scheduling.
- ❌ A "singleton" component that exists on more than one entity in production data. Add a baking validator that fails the build if `query.CalculateEntityCount() != 1`.

## Failure modes

| Symptom | Cause |
|---|---|
| `InvalidOperationException: GetSingleton<T> requires exactly one matching entity but found N` | Two entities now carry the component (often a duplicated Baker), or zero (missed `RequireForUpdate` or scene not loaded) |
| Config visibly stale | Reader runs before the writer in the same group with no `[UpdateAfter]` — see `dots-update-groups` |
| Burst-time exception inside parallel job | `SystemAPI.GetSingleton` called from inside the job — must be hoisted to `OnUpdate` and passed via job field |
| Singleton "resets" every frame | Writer in OnUpdate overwriting a bake-time value — bake-time singletons should be treated immutable |
| Singleton missing after subscene unload | Bake-time singletons live in the subscene — unloading destroys them; readers must `RequireForUpdate` or `HasSingleton`-guard |

## Runtime verification (Tester Verification Contract)

- **Static:** grep every `GetSingleton<T>` / `GetSingletonRW<T>`. Each must be paired with a `RequireForUpdate<T>` in the same system's `OnCreate`, OR wrapped in `HasSingleton<T>` / `TryGetSingleton<T>`. Anything else is a latent throw.
- **Runtime:** at frame N (post-load), assert `world.EntityManager.CreateEntityQuery(ComponentType.ReadOnly<T>()).CalculateEntityCount() == 1` for every component intended as a singleton. Add as a one-shot validation system in builds.

## Performance notes

- `GetSingleton<T>` is cheap (cached query lookup). Repeated calls in `OnUpdate` are fine but capture into a local for clarity.
- `GetSingletonRW<T>` marks the component as written and adds to the dependency graph. Don't sprinkle it where read access suffices.
- Singletons read by jobs should be passed *by value* into the job struct. Passing a `ComponentLookup<T>` for a single read is wasted indirection.

## Compile / editor safety

- `[InternalBufferCapacity]` doesn't apply to singletons (they're scalar). Buffer-singletons are a separate consideration (often a `DynamicBuffer<T>` on a known entity).
- Singleton component types should still be `[BurstCompile]`-friendly (blittable, no managed refs) unless explicitly part of the hybrid bridge.

## Entities version notes (1.4.x)

- `SystemAPI.GetSingleton<T>()` / `GetSingletonRW<T>()` / `HasSingleton<T>()` / `TryGetSingleton<T>()` — current.
- `state.EntityManager.CreateSingleton<T>()` — **does not exist**. Refuse old code that uses it. Create an entity, add the component, that's the singleton.
- `World.GetOrCreateSingleton<T>` — 0.x, gone. Use `RequireForUpdate` + `GetSingleton`.
- For ECB systems, the canonical handle is `EndSimulationEntityCommandBufferSystem.Singleton` (nested type) — not `World.GetExistingSystemManaged<...>()`.

## See also
- `dots-update-groups` — writer-before-reader ordering for mutable singletons
- `dots-spawning-patterns` — Spawner singletons are covered there; this skill is about cross-system shared state
- `dots-ecb-orchestration` — ECB-system singletons are the canonical example of "read-only handle singleton"
