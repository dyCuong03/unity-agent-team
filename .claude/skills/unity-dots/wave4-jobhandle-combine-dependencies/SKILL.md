---
name: wave4-jobhandle-combine-dependencies
description: Create a fan-in barrier that forces a downstream job to wait for multiple independent upstream jobs without introducing a sync point.
tags: [jobs, performance]
---

# JobHandle.CombineDependencies — Fan-In Barrier

## Intent
Create a fan-in barrier that forces a downstream job to wait for multiple independent upstream jobs without introducing a sync point.

## Use When
- A downstream job reads data produced by two or more independent parallel jobs.
- Multiple job pipelines must converge before a merge/reduce step.
- Building multi-stage simulation pipelines (spatial hash → accumulate → steer).

## Avoid When
- Jobs are sequential (A → B → C) — chain `state.Dependency` directly, no `CombineDependencies` needed.
- Only one upstream job — pass its handle directly.

## Senior Pattern
```csharp
// Two independent upstream jobs, one downstream consumer:
var handleSpatial  = spatialHashJob.ScheduleParallel(entityQuery, state.Dependency);
var handleTargets  = targetCopyJob.ScheduleParallel(targetQuery, state.Dependency);
var mergeBarrier   = JobHandle.CombineDependencies(handleSpatial, handleTargets);
state.Dependency   = mergeJob.Schedule(hashMap.Buckets.Length, 64, mergeBarrier);

// For > 3 handles:
using var handles = new NativeArray<JobHandle>(
    new[] { h1, h2, h3, h4, h5 }, Allocator.Temp);
var barrier = JobHandle.CombineDependencies(handles);
state.Dependency = downstreamJob.ScheduleParallel(query, barrier);
```

## Anti-Patterns
- Omitting one handle from `CombineDependencies` when the downstream job reads that job's output — silent race condition.
- Using 3-argument overload with > 3 handles — compile error or silent truncation; use `NativeArray<JobHandle>` overload.
- Creating a fake barrier for sequential jobs — unnecessary complexity, adds no correctness guarantee.

## Runtime Risks
- Missing a handle from the combine = race condition between predecessor and downstream job on shared NativeArrays or component data.
- In Burst release builds, safety checks are stripped — missing dependency is a silent data race.

## Performance Notes
- `CombineDependencies` has zero runtime cost — constructs a dependency struct; no worker threads involved.
- Downstream job starts as soon as all combined predecessors complete, with no main-thread involvement.

## Architecture Guidance
Design job DAG explicitly: nodes = jobs, edges = data dependencies. Map each edge to either a direct handle pass or a `CombineDependencies` barrier. Assign the final leaf handle to `state.Dependency`.

## Related Skills
[[job-dependency-chain]], [[state-dependency-job-chaining]], [[ijobentity-parallel-job]]
