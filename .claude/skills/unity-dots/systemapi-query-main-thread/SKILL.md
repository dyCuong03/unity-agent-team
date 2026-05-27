---
name: systemapi-query-main-thread
description: Iterate matching entities on the main thread using a concise, source-generated foreach that declares read/write intent and eliminates manual type handle boilerplate.
tags: [core, query]
---

# SystemAPI Query — Main Thread Iteration

## Intent
Iterate matching entities on the main thread using a concise, source-generated foreach that declares read/write intent and eliminates manual type handle boilerplate.

## Use When
Per-entity logic that must run on the main thread, is not parallelizable, or needs to interleave with other main-thread operations. One query, straightforward per-entity work.

## Avoid When
The work is parallelizable and entity count is large — use IJobEntity.ScheduleParallel instead. Avoid when cross-entity lookup is needed (use ComponentLookup). Avoid for chunk-level control (use IJobChunk).

## Senior Pattern
- `SystemAPI.Query<RefRW<A>, RefRO<B>>()` — source-generated, cached query.
- RefRW for components you write; RefRO for components you only read.
- Chain .WithAll<T>() / .WithNone<T>() / .WithAny<T>() for query filtering.
- Do not mutate archetypes (AddComponent, RemoveComponent) inside the loop — use ECB.

## Code Template
```csharp
[BurstCompile]
public void OnUpdate(ref SystemState state)
{
    float dt = SystemAPI.Time.DeltaTime;
    foreach (var (transform, speed) in
        SystemAPI.Query<RefRW<LocalTransform>, RefRO<MoveSpeed>>()
            .WithAll<IsActive>())
    {
        transform.ValueRW.Position +=
            math.forward(transform.ValueRO.Rotation) * speed.ValueRO.Value * dt;
    }
}
```

## Anti-Patterns
- Using RefRW on a component you only read — creates a false write dependency that serialises parallel jobs.
- Calling EntityManager.AddComponent / RemoveComponent inside the foreach — invalidates the iterator.
- Rebuilding the query inside OnUpdate without caching — minor overhead but unnecessary.
- Using SystemAPI.Query when you need the Entity itself — add `Entity` as the first query parameter.

## Runtime Risks
- Archetype mutation inside loop: iterator invalidation, undefined behavior.
- RefRW misuse on read-only data: job safety system reports false conflicts.

## Performance Notes
Source-generated query is cached after first use. Equivalent to manual IJobChunk iteration in throughput. Main-thread bound — does not utilize worker threads.

## Architecture Guidance
Main-thread iteration is appropriate for low-entity-count logic, initialization, and single-system orchestration. For simulation with >1000 entities, prefer jobs.
