---
name: direct-entity-manager-structural-changes
description: Use EntityManager directly for structural changes outside of any active query iteration — appropriate for one-shot initialisation, infrequent config-driven respawns, and batch operations on the mai...
tags: [structural-change]
---

# Direct EntityManager Structural Changes

## Intent
Use EntityManager directly for structural changes outside of any active query iteration — appropriate for one-shot initialisation, infrequent config-driven respawns, and batch operations on the main thread.

## Use When
One-shot init systems (state.Enabled = false after first run). Mass respawn triggered by config change. Any structural change that happens once at startup or once on a significant event, not per-frame.

## Avoid When
Inside a SystemAPI.Query foreach — iterator is invalidated. Inside a scheduled job — EntityManager is not accessible from jobs. In per-frame simulation hot paths — use ECB for deferred execution.

## Senior Pattern
- Disable the system after first run: `state.Enabled = false;` at the start of OnUpdate (set before any work so even exceptions during work don't leave the system enabled for next frame).
- Use batch overloads exclusively:
  - `state.EntityManager.Instantiate(prefab, count, Allocator.Temp)` — spawns N entities in one archetype operation.
  - `state.EntityManager.AddComponent<T>(query)` — adds T to all matching entities in one pass.
  - `state.EntityManager.RemoveComponent<T>(query)` — removes T from all matching in one pass.
  - `state.EntityManager.DestroyEntity(query)` — destroys all matching in one pass.
- Use `state.EntityManager.AddBuffer<T>(entity)` for per-entity buffer initialisation after batch spawn.

## Code Template
```csharp
[BurstCompile]
public partial struct WorldSetupSystem : ISystem
{
    public void OnCreate(ref SystemState state)
        => state.RequireForUpdate<WorldConfig>();

    public void OnUpdate(ref SystemState state)
    {
        state.Enabled = false;  // one-shot — set before work begins

        var config = SystemAPI.GetSingleton<WorldConfig>();

        // Batch spawn — single archetype operation for all N entities
        var enemies = state.EntityManager.Instantiate(
            config.EnemyPrefab, config.EnemyCount, Allocator.Temp);

        // Per-entity init using the spawned array
        for (int i = 0; i < enemies.Length; i++)
        {
            state.EntityManager.SetComponentData(enemies[i],
                LocalTransform.FromPosition(new float3(i * 2f, 0, 0)));
        }

        // Batch tag all spawned enemies
        var enemyQuery = SystemAPI.QueryBuilder()
            .WithAll<EnemyData>().WithNone<EnemyReady>().Build();
        state.EntityManager.AddComponent<EnemyReady>(enemyQuery);
    }
}
```

## Anti-Patterns
- Calling `state.EntityManager.Instantiate(prefab)` (single-entity overload) in a loop — N archetype operations instead of 1.
- Calling structural changes inside SystemAPI.Query foreach — iterator invalidation, safety exception.
- Forgetting `state.Enabled = false` on a one-shot init system — repeated spawning every frame.
- Calling `state.EntityManager.CompleteAllTrackedJobs()` to "enable" structural changes instead of properly scheduling them — blocks all worker threads.

## Runtime Risks
- Structural change inside foreach: access exception or silent data corruption.
- Missing state.Enabled = false: duplicate entity spawning every frame.
- Loop of single Instantiate: O(N) archetype operations cause visible frame spikes at large N.

## Performance Notes
- `Instantiate(prefab, count, Alloc)`: O(1) archetype operations + O(count) data copies. Dominates single-entity loop by orders of magnitude at count > 100.
- `AddComponent(query)`: single structural change pass over all matching chunks. Same cost regardless of entity count.
- `DestroyEntity(query)`: single pass, optimal for mass destruction.

## Architecture Guidance
Direct EntityManager = privileged main-thread batch API. Reserve for world setup and explicit event-driven mass operations. For all simulation-phase structural changes, ECB is the correct tool.

## Related Skills
[[entity-command-buffer]], [[batch-structural-change-on-query]]
