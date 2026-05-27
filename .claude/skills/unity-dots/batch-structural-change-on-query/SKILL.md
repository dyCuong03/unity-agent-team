---
name: batch-structural-change-on-query
description: Perform a structural change on all entities matching a query in a single pass by passing the EntityQuery directly to EntityManager, rather than iterating entities individually.
tags: [ecb, structural-change, performance]
---

# Batch Structural Change on Query

## Intent
Perform a structural change on all entities matching a query in a single pass by passing the EntityQuery directly to EntityManager, rather than iterating entities individually.

## Use When
Destroying, adding, or removing components from all entities that match a condition — and the condition is uniform (same operation for all matching entities). The query IS the condition.

## Avoid When
The operation is conditional per-entity (some entities in the query should be changed, others should not) — use ECB with per-entity conditional recording instead. Avoid inside a SystemAPI.Query foreach on the same query type — iterator invalidation.

## Senior Pattern
- `state.EntityManager.DestroyEntity(query)` — destroys all matching entities in one pass.
- `state.EntityManager.AddComponent<T>(query)` — adds T to all matching entities in one pass.
- `state.EntityManager.RemoveComponent<T>(query)` — removes T from all matching in one pass.
- `state.EntityManager.SetComponentEnabled<T>(query, bool)` — toggles enabled state for all matching.
- Build the query with EntityQueryBuilder and reuse it — don't rebuild the query every OnUpdate.

## Code Template
```csharp
[BurstCompile]
public partial struct WaveCleanupSystem : ISystem
{
    private EntityQuery m_DeadEnemyQuery;
    private EntityQuery m_WaveCompleteQuery;

    public void OnCreate(ref SystemState state)
    {
        m_DeadEnemyQuery = SystemAPI.QueryBuilder()
            .WithAll<EnemyData, Dead>().Build();
        m_WaveCompleteQuery = SystemAPI.QueryBuilder()
            .WithAll<WaveComplete>().Build();
        state.RequireForUpdate(m_WaveCompleteQuery);
    }

    public void OnUpdate(ref SystemState state)
    {
        // Destroy all dead enemies in one pass
        state.EntityManager.DestroyEntity(m_DeadEnemyQuery);

        // Remove WaveComplete from all entities (flag consumed)
        state.EntityManager.RemoveComponent<WaveComplete>(m_WaveCompleteQuery);
    }
}
```

## Anti-Patterns
- Calling the per-entity overload in a foreach loop: `foreach var e in query.ToEntityArray() { EntityManager.AddComponent<T>(e); }` — N archetype operations instead of 1.
- Calling query-overload structural changes inside a SystemAPI.Query foreach — invalidates the active iterator.
- Using the query overload when you need per-entity conditional logic — all matching entities are affected, no per-entity filtering possible.

## Runtime Risks
- Query-level structural change inside active foreach: access exception.
- Unintended over-matching: query selects more entities than intended, destroys or modifies wrong entities.

## Performance Notes
- Single archetype operation for all matching entities — O(1) archetype overhead regardless of entity count.
- For mass spawning: `EntityManager.Instantiate(prefab, count, Alloc)` is the batch equivalent.
- Query-level DestroyEntity is the correct pattern for despawning all entities of a type (e.g., on scene transition).

## Architecture Guidance
Query-level structural changes are the highest-performance main-thread batch API. Use them for phase transitions, mass cleanup, and scene management operations where all matching entities should be uniformly affected.

## Related Skills
[[direct-entity-manager-structural-changes]], [[entity-command-buffer]]
