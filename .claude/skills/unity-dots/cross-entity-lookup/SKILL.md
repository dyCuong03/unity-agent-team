---
name: cross-entity-lookup
description: Read component data from entities not in the current iteration — either via a snapshot copy (ToComponentDataArray) for simple read-only cases, or via ComponentLookup for random access by entity ID.
tags: [core, query]
---

# Cross-Entity Lookup

## Intent
Read component data from entities not in the current iteration — either via a snapshot copy (ToComponentDataArray) for simple read-only cases, or via ComponentLookup for random access by entity ID.

## Use When
Spatial queries, targeting, nearest-neighbour, graph traversal, or any system where entity A needs to read data from entity B that is not co-iterated.

## Avoid When
The relationship is static and can be expressed as a component reference (Entity field) — use ComponentLookup with a pre-stored entity handle. Avoid ToComponentDataArray for entity counts above ~10k per frame due to copy cost.

## Senior Pattern
- Snapshot approach: `var data = query.ToComponentDataArray<T>(Allocator.Temp)` — simple, read-only, disposed at end of OnUpdate.
- Job-accessible snapshot: `query.ToArchetypeChunkArray(state.WorldUpdateAllocator)` — passes chunk array to job without per-element copy.
- Random access in job: `ComponentLookup<T> lookup = SystemAPI.GetComponentLookup<T>(true)` — pass to job, access via `lookup[entity]`.
- Always mark ComponentLookup `[ReadOnly]` in the job if not writing — prevents false write dependencies.
- Use `state.WorldUpdateAllocator` (not `Allocator.Temp`) for data passed to jobs.

## Code Template
```csharp
// Snapshot read (simple, main-thread):
var enemyPositions = m_EnemyQuery
    .ToComponentDataArray<LocalTransform>(Allocator.Temp);
// ... use enemyPositions ...
enemyPositions.Dispose();

// ComponentLookup in a job:
[BurstCompile]
partial struct TargetingJob : IJobEntity
{
    [ReadOnly] public ComponentLookup<Health> HealthLookup;

    void Execute(ref TargetSelector selector, in PotentialTargets targets)
    {
        for (int i = 0; i < targets.Count; i++)
        {
            var h = HealthLookup[targets[i]];
            if (h.Current > 0) { selector.Best = targets[i]; break; }
        }
    }
}

// In OnUpdate:
state.Dependency = new TargetingJob
{
    HealthLookup = SystemAPI.GetComponentLookup<Health>(true)
}.ScheduleParallel(state.Dependency);
```

## Anti-Patterns
- Using Allocator.Temp for data passed to a job — Allocator.Temp is scoped to the main thread frame; jobs may outlive it.
- Not marking ComponentLookup [ReadOnly] when only reading — serialises parallel jobs unnecessarily.
- Calling EntityManager.GetComponentData<T>(entity) inside a per-entity loop — one managed call per entity, defeats ECS performance model.
- ToComponentDataArray on a very large query every frame — O(n) copy cost.

## Runtime Risks
- Allocator.Temp data in a job: dangling pointer, memory corruption, or safety exception.
- Non-readonly ComponentLookup in parallel job: safety system reports write conflict.

## Performance Notes
- Allocator.Temp: cheapest for data created, used, and discarded within one main-thread frame.
- WorldUpdateAllocator: lives one frame, job-accessible, cheaper than Persistent.
- ComponentLookup has cache-miss penalty vs sequential iteration — acceptable for sparse lookups, costly for dense O(n²) patterns.

## Architecture Guidance
Cross-entity reads are a common performance hotspot. For dense many-to-many relationships, consider spatial partitioning (NativeMultiHashMap by cell) rather than O(n²) ComponentLookup.
