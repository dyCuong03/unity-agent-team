---
name: singleton-patterns-config-and-access
description: Senior-level pattern for expressing world-unique data (game config, controls, frame input snapshot, prefab tables) as singleton entities with O(1) `SystemAPI.GetSingleton<T>()` / `GetSingletonRW<T>()` access, gated by `state.RequireForUpdate<T>()`. Covers the >1-instance throw, write-from-parallel safety, scene-merge collision modes, and when "this looks like a static" is actually still a singleton. Use whenever designing config, registries, input state, prefab references, or any data that should exist exactly once per world.
metadata:
  internal-only: true
  tier: 3
---

# Singleton Patterns — Senior Patterns

A singleton in DOTS is just an entity with a component that exists exactly once in the world. `SystemAPI.GetSingleton<T>()` is the O(1) accessor. `state.RequireForUpdate<T>()` is the gate that keeps the system from firing before the singleton is baked. Together they are the senior idiom for config, registries, frame-scoped input snapshots, and any data that should not be modeled per-entity.

## Intent

Model world-unique data as a single entity + component, accessed in O(1) from any system that depends on it, with a hard prerequisite contract that prevents first-frame races against scene baking.

## Use when

- A component is conceptually unique per world: game config, controls registry, frame input snapshot, prefab collection, world bounds, debug settings.
- A system needs guaranteed access to that data and must not run until it exists.
- You'd otherwise write `GetEntityQuery(...)` and `.GetSingleEntity()` to fetch it — the Singleton API is faster (no query iteration) and clearer.
- One system writes the value (e.g. an input system snapshots controller state into `InputState`) and many systems read it; you want a read-only contract on the consumers.

## Avoid when

- The data is per-entity (per-character config, per-faction tuning, per-region settings). Model as regular components on the relevant entities — a "singleton" of per-entity data is a misuse.
- Multiple instances are legitimately possible (e.g. multiple `PlayerInput` for split-screen). The singleton API throws on more than one — model it as a regular component and query for the matching entity explicitly.
- The "singleton" is a thin wrapper for true global mutable state that would be clearer as a static field. Rare — usually the singleton entity is still right because it survives world disposal and is visible to ECS systems; but be honest if the answer is actually a static.

## Senior pattern — read-only consumer

```csharp
using Unity.Burst;
using Unity.Entities;

public struct GameConfig : IComponentData
{
    public float Gravity;
    public Entity ProjectilePrefab;
}

[BurstCompile]
public partial struct ConfigConsumerSystem : ISystem
{
    [BurstCompile]
    public void OnCreate(ref SystemState state)
    {
        // The prerequisite contract — see entity-query-patterns-requireforupdate-gating.
        state.RequireForUpdate<GameConfig>();
    }

    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var config = SystemAPI.GetSingleton<GameConfig>();
        // ... use config.Gravity, config.ProjectilePrefab
    }
}
```

## Senior pattern — producer/consumer split with `GetSingletonRW`

When one system writes and others read (the canonical pattern for input state):

```csharp
public struct InputState : IComponentData
{
    public float2 Move;
    public bool Fire;
}

// Producer: snapshots controller state into the singleton once per frame.
[BurstCompile]
public partial struct InputSnapshotSystem : ISystem
{
    public void OnCreate(ref SystemState state) => state.RequireForUpdate<InputState>();

    public void OnUpdate(ref SystemState state)
    {
        // GetSingletonRW gives a writable reference — main-thread / scheduled-write context only.
        var rw = SystemAPI.GetSingletonRW<InputState>();
        rw.ValueRW.Move = ReadStickRaw();
        rw.ValueRW.Fire = ReadFireRaw();
    }

    // ReadStickRaw / ReadFireRaw are placeholders; if they touch managed APIs,
    // see ecs-fundamentals-isystem-default for the bridge pattern.
    static float2 ReadStickRaw() => default;
    static bool ReadFireRaw() => default;
}

// Consumer: read-only access, gated on the same singleton.
[BurstCompile]
public partial struct PlayerControllerSystem : ISystem
{
    public void OnCreate(ref SystemState state) => state.RequireForUpdate<InputState>();
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var input = SystemAPI.GetSingleton<InputState>();
        // ... apply input to player entities
    }
}
```

Order the producer before the consumer (`[UpdateBefore(typeof(PlayerControllerSystem))]` on the producer, or place the producer in `InitializationSystemGroup`). The singleton is the contract; system ordering decides when each side runs.

## Senior pattern — baking the singleton

Singletons are produced by a Baker, exactly like any other entity:

```csharp
public class GameConfigAuthoring : MonoBehaviour
{
    public float Gravity;
    public GameObject ProjectilePrefab;

    class Baker : Baker<GameConfigAuthoring>
    {
        public override void Bake(GameConfigAuthoring a)
        {
            // Singleton: no transform needed. See ecs-fundamentals-transformusageflags.
            var e = GetEntity(TransformUsageFlags.None);
            AddComponent(e, new GameConfig
            {
                Gravity = a.Gravity,
                ProjectilePrefab = GetEntity(a.ProjectilePrefab, TransformUsageFlags.Dynamic)
            });
        }
    }
}
```

Place exactly one `GameConfigAuthoring` in the subscene. Two will throw at scene merge with a "more than one singleton" error.

## Anti-patterns

- Accessing the singleton in `OnUpdate` without `state.RequireForUpdate<T>()` in `OnCreate`. The first frame can fire before subscene baking completes — `GetSingleton<T>()` throws "singleton does not exist". The gate is the only correct guard; an `if (!HasSingleton<T>()) return;` inside `OnUpdate` runs the system-scheduler bookkeeping every frame for nothing.
- Two unrelated Bakers each producing the same singleton type. At runtime there are now two; `GetSingleton<T>()` throws "more than one singleton". Bake-time merging is unforgiving here.
- Using `SystemAPI.GetSingletonRW<T>` from a parallel-scheduled job context. `GetSingletonRW` is for main-thread / scheduled-write — to mutate a singleton from a parallel job, capture the writable reference outside the job and write through it in a single-threaded section, or use an ECB.
- A "singleton entity" holding a `NativeList<T>` that grows every frame. That's fine *if* you document the owning writer system and treat it as global mutable state — but a `NativeList` inside a singleton component is `unsafe`-territory: lifetime must be tied to the singleton entity (disposed in `OnDestroy` of the writer, or via `Allocator.Persistent` with explicit cleanup). Don't roll this without an explicit contract.
- Treating "singleton" as a synonym for "static class on a system". Don't put a static field on the system and call it a singleton — the whole point is that it lives in ECS, survives world recreation correctly, and is visible to all systems.

## Failure modes

| Symptom | Likely cause |
|---|---|
| `InvalidOperationException: GetSingleton<T>() requires that exactly one T exist` (count: 0) | Missing `RequireForUpdate<T>()` and the system fired before bake completed; or the Baker that should produce the singleton isn't attached to any GameObject in a loaded subscene |
| Same exception, count: 2 (or more) | Two Bakers produce the singleton, or the authoring GameObject was duplicated in the subscene |
| Singleton value reads as default the first time, "real" later | A consumer system ran before the producer this frame. Add `[UpdateBefore]` on the producer or `[UpdateAfter]` on the consumer |
| Random NRE or data-race smell on a singleton's `NativeList`/`NativeHashMap` field | Singleton entity carrying a managed-lifetime container without an explicit owner system disposing it |
| Singleton "disappears" on subscene unload | Subscene-owned singleton entity was destroyed with the subscene; reload the subscene or move the singleton into a persistent world entity |
| Two scenes baking conflicting singletons of the same type | Throw at scene merge — split the data, or designate one scene as the singleton owner |

## Runtime verification

- **Static:** every system calling `SystemAPI.GetSingleton<T>()` / `GetSingletonRW<T>()` must declare `state.RequireForUpdate<T>()` in `OnCreate`. Grep for `GetSingleton<` and confirm each match has a matching `RequireForUpdate` for the same type in the same system file.
- **Static:** every `IComponentData` used as a singleton should be produced by exactly one Baker. Grep for `AddComponent(e, new <Singleton>` and confirm one Baker writes it.
- **Runtime:** in playmode, open the Entities Hierarchy and confirm exactly one entity carries the singleton component. For producer/consumer singletons, sample the singleton's value at frame boundaries and confirm the producer's writes are visible to all consumers in the same frame.

## Performance notes

- `SystemAPI.GetSingleton<T>()` is O(1) — implemented as a direct chunk lookup against the singleton archetype, not a query iteration. Cheap enough to call once at the top of every `OnUpdate`.
- Each distinct singleton component type tends to land in its own archetype (because it's the only entity with that component). Many singletons → many tiny archetypes — usually fine, but if you have hundreds of singletons it's worth grouping related fields into one `GameConfig`-style aggregate.
- `GetSingletonRW` is slightly more expensive than `GetSingleton` (writable reference + change-version bump). Use `GetSingleton` on consumers; reserve `GetSingletonRW` for the producer.

## Compile / editor safety

- `SystemAPI.GetSingleton<T>` and `GetSingletonRW<T>` are source-generated and Burst-compatible. They work identically in `ISystem` and `SystemBase`.
- The singleton API throws fast in the editor; the same call can manifest as a native crash in a Burst-compiled player build if the gate is missing. The `RequireForUpdate` gate is your only line of defense.

## Entities version notes (1.4.x)

- `SystemAPI.GetSingleton<T>()` is the current accessor. The old `GetSingletonEntity<T>` still exists for the rare "I need the entity reference, not the value" case (e.g. attaching a child entity to the config entity).
- `state.RequireForUpdate<T>()` is the current generic gate. The 0.x `RequireSingletonForUpdate<T>` is removed.
- For singletons with reactive/changed-only behavior, use `state.RequireForUpdate(state.GetEntityQuery(ComponentType.ReadOnly<T>()))` and combine with change filtering rather than the older `RequireSingletonForUpdate` overloads.

## See also

- [`entity-query-patterns-requireforupdate-gating`](../entity-query-patterns-requireforupdate-gating/SKILL.md) — the gating side of this pattern, generalized beyond singletons
- [`dots-baking-patterns`](../dots-baking-patterns/SKILL.md) — how the singleton component gets produced at bake time
- [`ecs-fundamentals-transformusageflags`](../ecs-fundamentals-transformusageflags/SKILL.md) — `None` is the right flag for almost every singleton
- [`dots-ecb-orchestration`](../dots-ecb-orchestration/SKILL.md) — when a singleton mutation needs to be deferred across the frame boundary
- [`ecs-fundamentals-isystem-default`](../ecs-fundamentals-isystem-default/SKILL.md) — bridge pattern when the producer must touch managed APIs
