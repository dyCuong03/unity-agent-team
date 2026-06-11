---
name: toentityarray-snapshot-pattern
description: Safely combine entity iteration with per-entity structural changes by snapshotting entity IDs and component data into NativeArrays before performing structural changes, avoiding iterator invalidation.
tags: [query, structural-change]
metadata:
  internal-only: true
  tier: 3
---

# ToEntityArray Snapshot Pattern

## Intent
Safely combine entity iteration with per-entity structural changes by snapshotting entity IDs and component data into NativeArrays before performing structural changes, avoiding iterator invalidation.

## Use When
A system must both iterate entity data AND perform structural changes that depend on per-entity conditions — where query-level batch operations are insufficient because the condition varies per entity.

## Avoid When
All matching entities receive the same structural change — use the query-level batch overload instead (cheaper, no copy). Avoid for very large entity counts (>10k) where copy cost is significant — redesign using ECB.ParallelWriter in a job instead.

## Senior Pattern
1. Build the query.
2. `var entities = query.ToEntityArray(Allocator.Temp)` — snapshot entity IDs.
3. `var data = query.ToComponentDataArray<T>(Allocator.Temp)` — snapshot component values.
4. Perform the batch structural change on the query (e.g., `state.EntityManager.AddComponent<T>(query)` or `RemoveComponent`).
5. Iterate the snapshot arrays with a for loop — access per-entity data safely, call `SetComponentData` for per-entity initialisation.
6. Allocator.Temp arrays dispose automatically — no explicit Dispose needed.

## Code Template
```csharp
public void OnUpdate(ref SystemState state)
{
    var query = SystemAPI.QueryBuilder()
        .WithAll<RequiresSetup>().WithNone<SetupDone>().Build();

    if (query.IsEmpty) return;

    // Snapshot before structural change
    var entities = query.ToEntityArray(Allocator.Temp);
    var setupData = query.ToComponentDataArray<RequiresSetup>(Allocator.Temp);

    // Batch structural change on the query (one archetype operation)
    state.EntityManager.AddComponent<SetupDone>(query);
    state.EntityManager.RemoveComponent<RequiresSetup>(query);

    // Per-entity init using the snapshot (no iterator invalidation risk)
    for (int i = 0; i < entities.Length; i++)
    {
        state.EntityManager.SetComponentData(entities[i], new SetupDone
        {
            InitialPosition = setupData[i].SpawnPosition,
            InitializedAt = (float)SystemAPI.Time.ElapsedTime
        });
    }
    // Allocator.Temp — no dispose needed
}
```

## Anti-Patterns
- Calling structural changes inside a SystemAPI.Query foreach — iterator invalidation, exception.
- Using Allocator.TempJob for snapshot arrays used only on the main thread — unnecessary overhead, requires Dispose.
- Taking snapshots then iterating them with another SystemAPI.Query — redundant; the snapshot is the iteration.
- ToEntityArray on a large query every frame — O(N) copy cost every frame is a performance issue; redesign if this is on a hot path.

## Runtime Risks
- Structural change inside foreach: safety exception or data corruption.
- Using stale snapshot data after a structural change that moves entities between archetypes — ToComponentDataArray snapshots values at call time; subsequent structural changes don't affect the copy.

## Performance Notes
ToEntityArray + ToComponentDataArray = O(N) memory allocation and copy. For N < ~1000, cost is negligible. For N > 10,000, prefer redesigning the system to use ECB.ParallelWriter in a job (avoids the main-thread copy).

## Architecture Guidance
Snapshot pattern is the canonical "iterate + structurally change" solution on the main thread. For parallel equivalents, use IJobEntity with ECB.ParallelWriter — records the conditional structural change without requiring a snapshot.

## Related Skills
[[batch-structural-change-on-query]], [[ecb-parallel-writer]]
