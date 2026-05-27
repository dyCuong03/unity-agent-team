---
name: entity-prefab-reference
description: Store a lazy-loaded prefab handle that defers entity scene loading until explicitly requested, enabling on-demand prefab loading without paying the memory cost at world initialization.
tags: [baking, spawn]
---

# EntityPrefabReference — Deferred Prefab Loading

## Intent
Store a lazy-loaded prefab handle that defers entity scene loading until explicitly requested, enabling on-demand prefab loading without paying the memory cost at world initialization.

## Use When
Prefabs not needed immediately at world load (enemy waves, VFX, dynamically spawned content). Streaming scenarios. Prefabs shared across multiple scenes/worlds.

## Avoid When
The prefab must be available from frame 1 (player character, core HUD entities) — use inline `GetEntity(authoring.Prefab, TransformUsageFlags.Dynamic)` in the Baker for eager loading.

## Senior Pattern
- Baker: `AddComponent(entity, new Config { PrefabRef = new EntityPrefabReference(authoring.Prefab) })`.
- Load system (one-shot): `state.EntityManager.AddComponentData(configEntity, new RequestEntityPrefabLoaded { Prefab = config.PrefabRef })`, then `state.Enabled = false`.
- Wait system: `RequireForUpdate<PrefabLoadResult>`, then `state.EntityManager.HasComponent<PrefabLoadResult>()` guard before accessing.
- Spawn: `state.EntityManager.Instantiate(SystemAPI.GetComponent<PrefabLoadResult>(configEntity).PrefabRoot)`.

## Code Template
```csharp
// Component holding the reference:
public struct EnemySpawnConfig : IComponentData
{
    public EntityPrefabReference EnemyPrefabRef;
    public int SpawnCount;
}

// One-shot load system:
public partial struct RequestEnemyPrefabSystem : ISystem
{
    public void OnCreate(ref SystemState state)
        => state.RequireForUpdate<EnemySpawnConfig>();

    public void OnUpdate(ref SystemState state)
    {
        var configEntity = SystemAPI.GetSingletonEntity<EnemySpawnConfig>();
        var config = SystemAPI.GetSingleton<EnemySpawnConfig>();
        state.EntityManager.AddComponentData(configEntity,
            new RequestEntityPrefabLoaded { Prefab = config.EnemyPrefabRef });
        state.Enabled = false;  // run exactly once
    }
}

// Spawn system — waits for load to complete:
public partial struct SpawnEnemiesSystem : ISystem
{
    public void OnCreate(ref SystemState state)
    {
        state.RequireForUpdate<EnemySpawnConfig>();
        state.RequireForUpdate<PrefabLoadResult>();
    }

    public void OnUpdate(ref SystemState state)
    {
        var configEntity = SystemAPI.GetSingletonEntity<EnemySpawnConfig>();
        if (!SystemAPI.HasComponent<PrefabLoadResult>(configEntity))
            return;

        var result = SystemAPI.GetComponent<PrefabLoadResult>(configEntity);
        var config = SystemAPI.GetSingleton<EnemySpawnConfig>();
        for (int i = 0; i < config.SpawnCount; i++)
            state.EntityManager.Instantiate(result.PrefabRoot);

        state.Enabled = false;
    }
}
```

## Anti-Patterns
- Instantiating from PrefabLoadResult without checking HasComponent — throws if load not yet complete (async load takes at least one frame).
- Not calling `state.Enabled = false` in the load system after adding RequestEntityPrefabLoaded — system runs every frame, adding duplicate load requests.
- Using EntityPrefabReference for a prefab needed on frame 1 — one-frame loading delay causes visible pop-in or missing entity on first frame.

## Runtime Risks
- Accessing PrefabLoadResult before load completes: exception or wrong entity.
- Multiple RequestEntityPrefabLoaded added to same entity: undefined behavior in the streaming system.

## Performance Notes
Deferred load = zero memory footprint until the request is made. PrefabRoot is a live entity in a streamed entity scene — instantiation cost is identical to inline prefab instantiation.

## Architecture Guidance
EntityPrefabReference is the ECS equivalent of an addressable asset reference. Use it as the standard pattern for any content that should load on demand. Pair with a dedicated one-shot load system and a spawn system that waits for the result.

## Related Skills
[[baker-authoring-conversion]], [[singleton-access]]
