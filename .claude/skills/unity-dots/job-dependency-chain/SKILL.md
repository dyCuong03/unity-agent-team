---
name: job-dependency-chain
description: Wire every scheduled job into the system''s dependency chain via state.Dependency so the ECS scheduler can automatically enforce read/write ordering between systems without explicit sync points.
tags: [core, jobs, performance]
metadata:
  internal-only: true
  tier: 3
---

# Job Dependency Chain

## Intent
Wire every scheduled job into the system's dependency chain via state.Dependency so the ECS scheduler can automatically enforce read/write ordering between systems without explicit sync points.

## Use When
Every IJobEntity.Schedule / ScheduleParallel and IJobChunk.Schedule / ScheduleParallel call, without exception.

## Avoid When
There is no "avoid when" — this is non-negotiable for every job schedule call.

## Senior Pattern
- Pass current `state.Dependency` as the dependency parameter to Schedule/ScheduleParallel.
- Assign the returned JobHandle back to `state.Dependency`.
- The ECS scheduler reads `state.Dependency` after OnUpdate and wires it into the next system's input automatically.
- Only call `state.Dependency.Complete()` when main-thread access to job results is required in the same frame — this is an explicit sync point.

## Code Template
```csharp
[BurstCompile]
public void OnUpdate(ref SystemState state)
{
    // Chain: pass in, assign out — always.
    state.Dependency = new PrepareJob { ... }
        .ScheduleParallel(state.Dependency);

    state.Dependency = new ConsumeJob { ... }
        .Schedule(state.Dependency);  // sequential after PrepareJob

    // Only call Complete() when you MUST read results on main thread this frame:
    // state.Dependency.Complete();  // explicit sync point — document why
}
```

## Anti-Patterns
- Forgetting to assign `state.Dependency = job.Schedule(...)` — silent data race, intermittent wrong results.
- Calling `.Complete()` at the end of every OnUpdate as "safety" — introduces a full sync point every frame, stalls all worker threads.
- Scheduling two jobs in the same OnUpdate without chaining the first result into the second's dependency — jobs may race.
- Using a local JobHandle variable and never assigning it to state.Dependency — the dependency is lost.

## Runtime Risks
- Missing chain: data race between systems — non-deterministic, hardware-dependent, extremely hard to debug.
- Unnecessary Complete(): worker thread stall every frame, frame time spike, CPU underutilization.

## Performance Notes
Correct chaining allows the scheduler to run jobs from different systems in parallel when their read/write domains do not conflict. Breaking the chain forces serialisation. Never call Complete() without profiling evidence that the stall is acceptable.

## Architecture Guidance
Treat state.Dependency as the system's contract with the scheduler. In = work I depend on completing. Out = work I have scheduled. Never break the contract silently.
