---
name: wave4-entity-index-in-query-scatter-pattern
description: Write each entity''s computed result to a pre-allocated NativeArray using a stable per-entity index, enabling lock-free parallel scatter for inter-job data passing.
tags: [jobs, query]
metadata:
  internal-only: true
  tier: 3
---

# EntityIndexInQuery Scatter Pattern

## Intent
Write each entity's computed result to a pre-allocated NativeArray using a stable per-entity index, enabling lock-free parallel scatter for inter-job data passing.

## Use When
- A parallel IJobEntity needs to write one result per entity into a NativeArray for a downstream job.
- Each entity's result is independent (no two entities write the same index).
- Entity count is known before scheduling via `query.CalculateEntityCount()`.

## Avoid When
- Multiple entities could map to the same index — use `NativeParallelMultiHashMap`.
- Entity count changes between `CalculateEntityCount()` and job execution — indices become stale.

## Senior Pattern
```csharp
int count = myQuery.CalculateEntityCount();
var positions = CollectionHelper.CreateNativeArray<float3, RewindableAllocator>(
    count, ref state.WorldUpdateAllocator);

var scatterHandle = new ScatterJob { Positions = positions }
    .ScheduleParallel(myQuery, state.Dependency);
state.Dependency = new GatherJob { Positions = positions }
    .Schedule(scatterHandle);

[BurstCompile]
public partial struct ScatterJob : IJobEntity
{
    // [NativeDisableParallelForRestriction] required: safety system sees parallel writes
    // to one array; developer guarantees uniqueness via [EntityIndexInQuery]
    [NativeDisableParallelForRestriction]
    public NativeArray<float3> Positions;

    [BurstCompile]
    public void Execute([EntityIndexInQuery] int entityIndex, in LocalTransform t)
    {
        Positions[entityIndex] = t.Position;
    }
}
```

## Anti-Patterns
- Using `[ChunkIndexInQuery]` as NativeArray write index — chunk-level, not entity-level; multiple entities per chunk write the same slot.
- Not calling `CalculateEntityCount()` and guessing capacity — out-of-bounds write in Burst release builds.
- Reusing the NativeArray across frames — `[EntityIndexInQuery]` order may change if query entity set changes.

## Runtime Risks
- Structural change between `CalculateEntityCount()` and job execution invalidates indices — schedule before any ECB playback affecting the query.

## Performance Notes
- Direct array indexing = cache-optimal scatter; N entities write N distinct cache lines in parallel.
- `CalculateEntityCount()` is O(archetypes in query), not O(entities) — safe to call per-frame.

## Architecture Guidance
Two-phase: scatter (parallel write per entity) → gather (sequential or parallel read). Combine with `[ChunkIndexInQuery]` + ECB.ParallelWriter in the same job when both scatter and structural changes are needed.

## Related Skills
[[ijobentity-advanced-patterns]], [[native-parallel-multihashmap-parallel-writer]], [[world-update-allocator-per-frame-native]]
