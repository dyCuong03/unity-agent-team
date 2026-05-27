---
name: ijobentity-parallel-job
description: Execute per-entity computation in parallel across worker threads using a source-generated job whose query is inferred from the Execute method signature.
---

# IJobEntity — Parallel Job

## Intent
Execute per-entity computation in parallel across worker threads using a source-generated job whose query is inferred from the Execute method signature.

## Use When
Per-entity work that is parallelizable, Burst-friendly, and does not require chunk-level control. The primary pattern for simulation logic in production DOTS.

## Avoid When
You need chunk-level early-exit, direct chunk pointer access, or change filtering via chunk.DidChange() — use IJobChunk. Avoid when the job needs ECB.ParallelWriter without [ChunkIndexInQuery] — add the parameter first.

## Senior Pattern
- `partial struct MyJob : IJobEntity` with [BurstCompile].
- Execute signature declares read/write intent: `ref` = write, `in` = read.
- Schedule with `state.Dependency = new MyJob { ... }.ScheduleParallel(state.Dependency)`.
- Use [WithAll], [WithNone], [WithAny] attributes on the struct for query filtering.
- Add `[ChunkIndexInQuery] int chunkIndex` to Execute when ECB.ParallelWriter is needed.

## Code Template
```csharp
[BurstCompile]
partial struct ApplyVelocityJob : IJobEntity
{
    public float DeltaTime;

    void Execute(ref LocalTransform transform, in Velocity velocity)
    {
        transform.Position += velocity.Value * DeltaTime;
    }
}

[BurstCompile]
public void OnUpdate(ref SystemState state)
{
    state.Dependency = new ApplyVelocityJob
    {
        DeltaTime = SystemAPI.Time.DeltaTime
    }.ScheduleParallel(state.Dependency);
}
```

## Anti-Patterns
- Forgetting to assign the return of Schedule to state.Dependency — next system races against this job.
- Using ScheduleParallel with a non-parallel ECB — safety exception at runtime.
- Capturing a NativeContainer without [ReadOnly] when it is read-only — false write dependency.
- Using Schedule (single-threaded) when ScheduleParallel is safe — wastes parallel budget.

## Runtime Risks
- Missing state.Dependency chain: data race between this job and subsequent systems.
- ECB.ParallelWriter without sort key: non-deterministic command order, potential exception.

## Performance Notes
- ScheduleParallel splits chunks across worker threads. Use for any entity count above ~500 with non-trivial per-entity work.
- Schedule runs single-threaded. Use only when ordering within entities is required.
- Job struct fields are copied to each worker — keep them small (entity handles, primitive params, NativeArray refs).

## Architecture Guidance
IJobEntity is the default parallel work unit. Design systems around one IJobEntity per concern. Use state.Dependency as the explicit contract between systems.
