---
name: ijobchunk-chunk-job
description: Process entities at the chunk level for maximum control — chunk-level change filtering, enable mask handling, direct pointer access, and explicit sort key management.
tags: [core, jobs, chunks]
---

# IJobChunk — Chunk-Level Job

## Intent
Process entities at the chunk level for maximum control — chunk-level change filtering, enable mask handling, direct pointer access, and explicit sort key management.

## Use When
Change filtering via chunk.DidChange() is required. Enable mask must be processed explicitly. Direct unsafe pointer access is needed for maximum throughput. Chunk index is required for ECB.ParallelWriter.

## Avoid When
IJobEntity provides sufficient control — IJobChunk adds significant boilerplate. Use IJobEntity for the common case; reserve IJobChunk for performance-critical or control-critical paths.

## Senior Pattern
- Implement `IJobChunk` on an unmanaged struct.
- Acquire type handles in OnCreate or OnUpdate via `SystemAPI.GetComponentTypeHandle<T>`.
- Update type handles each frame (they are version-stamped; stale handles cause wrong data).
- Pass the query explicitly to `job.ScheduleParallel(query, state.Dependency)`.
- Use `chunk.DidChange(ref typeHandle, lastSystemVersion)` for change-filtered paths.
- Chain result into `state.Dependency`.

## Code Template
```csharp
[BurstCompile]
struct TransformUpdateJob : IJobChunk
{
    public ComponentTypeHandle<LocalTransform> TransformHandle;
    [ReadOnly] public ComponentTypeHandle<Velocity> VelocityHandle;
    public uint LastSystemVersion;
    public float DeltaTime;

    public void Execute(in ArchetypeChunk chunk, int unfilteredChunkIndex,
        bool useEnabledMask, in v128 chunkEnabledMask)
    {
        if (!chunk.DidChange(ref VelocityHandle, LastSystemVersion))
            return;

        var transforms = chunk.GetNativeArray(ref TransformHandle);
        var velocities = chunk.GetNativeArray(ref VelocityHandle);
        for (int i = 0; i < chunk.Count; i++)
        {
            var t = transforms[i];
            t.Position += velocities[i].Value * DeltaTime;
            transforms[i] = t;
        }
    }
}

[BurstCompile]
public void OnUpdate(ref SystemState state)
{
    state.Dependency = new TransformUpdateJob
    {
        TransformHandle = SystemAPI.GetComponentTypeHandle<LocalTransform>(),
        VelocityHandle  = SystemAPI.GetComponentTypeHandle<Velocity>(true),
        LastSystemVersion = state.LastSystemVersion,
        DeltaTime = SystemAPI.Time.DeltaTime
    }.ScheduleParallel(m_Query, state.Dependency);
}
```

## Anti-Patterns
- Caching type handles across frames without refreshing — handle version mismatch, reads wrong chunk data.
- Not passing state.Dependency to Schedule — race condition.
- Using IJobChunk where IJobEntity would suffice — unnecessary boilerplate.
- Accessing chunk data without checking useEnabledMask when entities may be disabled.

## Runtime Risks
- Stale type handle: silent wrong data or access violation.
- Missing dependency chain: data race.
- Ignoring chunkEnabledMask when IEnableableComponent is in use: processing disabled entities.

## Performance Notes
- Direct pointer via `chunk.GetRequiredComponentDataPtrRO/RW` is the fastest possible access — avoids NativeArray bounds checks.
- chunk.DidChange() enables skipping unchanged chunks entirely — major win for sparse-update scenarios.
- Pair with chunk.Count for manual SIMD if needed.

## Architecture Guidance
IJobChunk is the performance ceiling. Use it deliberately for transform pipelines, rendering integration, and high-throughput physics. Document why IJobEntity was insufficient.
