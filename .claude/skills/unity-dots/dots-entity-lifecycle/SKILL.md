---
name: dots-entity-lifecycle
description: Senior-level entity lifecycle — safe destruction, structural-change-during-iteration rules, ICleanupComponentData two-phase teardown, dangling Entity refs, and subscene load/unload. Use when destroying entities, designing cleanup that needs to run after destruction, or debugging "entity already destroyed" / orphan-reference bugs.
metadata:
  internal-only: true
  tier: 3
---

# Entity Lifecycle — Senior Patterns

Entities are not GameObjects. There is no `OnDestroy` callback to do cleanup. Destruction is structural, can invalidate active queries, and any other entity holding the `Entity` value still has it — it's a generation-tagged handle, not a managed reference. Two-phase teardown via `ICleanupComponentData` is the senior tool for "run cleanup before this entity actually disappears."

## Intent

Make entity creation and destruction explicit, deferred, and survivable across the systems that read the same state.

## The three lifecycle rules

1. **Never make a structural change inside the query you're iterating.** Use an ECB to record `DestroyEntity` / `AddComponent` / `RemoveComponent`, then let the ECB system play it back.
2. **An `Entity` value outlives the entity.** Validate with `EntityManager.Exists(entity)` (or `SystemAPI.HasComponent<T>(entity)`) before dereferencing.
3. **Cleanup needs explicit components.** `ICleanupComponentData` keeps the entity alive after `DestroyEntity` is called, until **you** remove the cleanup component.

## Senior pattern — destroy via ECB during iteration

```csharp
public partial struct FallAndDestroySystem : ISystem
{
    [BurstCompile]
    public void OnCreate(ref SystemState state) {
        state.RequireForUpdate<BeginSimulationEntityCommandBufferSystem.Singleton>();
    }

    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var ecbSingleton = SystemAPI.GetSingleton<BeginSimulationEntityCommandBufferSystem.Singleton>();
        var ecb = ecbSingleton.CreateCommandBuffer(state.WorldUnmanaged);

        var dropPerFrame = new float3(0, -SystemAPI.Time.DeltaTime * 5f, 0);

        foreach (var (transform, entity) in
                 SystemAPI.Query<RefRW<LocalTransform>>().WithEntityAccess())
        {
            transform.ValueRW.Position += dropPerFrame;
            if (transform.ValueRO.Position.y < 0)
            {
                // Structural change during iteration would invalidate the query.
                // Record the intent; playback happens AFTER OnUpdate.
                ecb.DestroyEntity(entity);
            }
        }
    }
}
```

## Senior pattern — two-phase teardown with ICleanupComponentData

Use case: when an entity is destroyed, release a `NativeArray` or notify another system **before** the entity actually disappears.

```csharp
// Cleanup component. Adding this to an entity makes DestroyEntity defer
// the actual destruction until the cleanup component is removed.
public struct SoundHandleCleanup : ICleanupComponentData
{
    public int AudioSourceId;
}

// Phase 1: regular destruction request — ECB.DestroyEntity recorded.
// Result: entity keeps the SoundHandleCleanup component but loses everything else.

// Phase 2: a dedicated system finds the "tombstone" and finalizes.
public partial struct ReleaseAudioOnDeathSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var ecb = SystemAPI.GetSingleton<EndSimulationEntityCommandBufferSystem.Singleton>()
                           .CreateCommandBuffer(state.WorldUnmanaged);

        // Tombstones: have the cleanup component but no live data.
        foreach (var (handle, entity) in
                 SystemAPI.Query<RefRO<SoundHandleCleanup>>().WithEntityAccess())
        {
            // Do the cleanup work (release audio source, log, etc.)
            AudioManager.Release(handle.ValueRO.AudioSourceId);

            // Remove the cleanup component — only NOW does the entity truly vanish.
            ecb.RemoveComponent<SoundHandleCleanup>(entity);
        }
    }
}
```

## Validating an Entity ref

```csharp
if (state.EntityManager.Exists(targetEntity) &&
    SystemAPI.HasComponent<EnemyTag>(targetEntity))
{
    var enemyTransform = SystemAPI.GetComponent<LocalTransform>(targetEntity);
    // ... safe to use
}
```

`Entity` is `(Index, Version)`. When an entity at `Index` is destroyed and that slot is reused, the new entity has a higher `Version`. A stale ref has the old `Version` and `Exists` returns false.

## Anti-patterns

- ❌ Calling `state.EntityManager.DestroyEntity(entity)` inside a `SystemAPI.Query` foreach. Mutates the query you're walking.
- ❌ Storing entity references in a managed `List<Entity>` and assuming they're valid next frame. Always re-validate.
- ❌ Adding a regular `IComponentData` and expecting it to "hold the entity alive". Only `ICleanupComponentData` does that.
- ❌ Forgetting to remove the cleanup component in phase 2. The entity becomes immortal — a slow leak.
- ❌ Multiple systems calling `DestroyEntity` on the same target in the same frame without coordination. ECB swallows the second call but the intent is unclear.
- ❌ Putting cleanup work in a Baker. Bakers run at conversion, not at runtime destruction.

## Failure modes

| Symptom | Likely cause |
|---|---|
| `InvalidOperationException: This entity has been destroyed` | Holding a stale Entity ref; missing `Exists` check |
| Entities "won't die" — count never drops | A cleanup component is attached but no system removes it |
| Cleanup runs on the wrong frame | Cleanup system in a phase BEFORE the destroy-recording system; reverse the order or move to End* ECB |
| Memory leak — native containers tied to entities | Cleanup component missing; container never released on destroy |
| Subscene unload leaves orphan entities | Subscene-spawned entities holding refs to subscene-owned entities; refs become invalid on unload |

## Runtime verification

- **Static:** every `ICleanupComponentData` declaration must be paired with a system that removes it. Grep for `: ICleanupComponentData` → confirm each has a matching `RemoveComponent<X>` in a cleanup system.
- **Runtime:** spawn N, destroy N, assert chunk capacity returns to baseline; assert no entity remains in `World.EntityManager.UniversalQuery` matching the cleanup component's archetype after one full frame.

## Performance notes

- `DestroyEntity` is a structural change. Batched via ECB it's cheap; per-entity in a hot loop it isn't.
- A subscene unload destroys all its entities atomically. Cheaper than destroying them one by one.
- Cleanup components keep an entity in an "almost dead" archetype. Many of these accumulate → archetype fragmentation. Keep the time between phase 1 and phase 2 short (ideally one frame).

## Compile / editor safety

- `ICleanupComponentData` (renamed from `ISystemStateComponentData` in Entities 1.x). Refuse old name in reviews.
- Cleanup systems must run **after** the system that records the destroy. Use `[UpdateAfter]` or place them in End* ECB phases.

## Entities version notes (1.4.x)

- `ICleanupComponentData` is current. `ISystemStateComponentData` is the deprecated 0.x name — same semantics, do not use.
- `EntityManager.Exists` and `SystemAPI.HasComponent<T>` are the supported existence checks. `entity != Entity.Null` is not a validity check — `Entity.Null` is just `(0,0)`, a destroyed entity has `(realIndex, oldVersion)`.

## See also
- `dots-ecb-orchestration` — the playback-phase choice for destruction
- `dots-enableable-components` — often "destroy then recreate" is really "disable then re-enable"
- `dots-spawning-patterns` — the create side of the same coin
