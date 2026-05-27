---
name: wave4-ijobchunk-full-anatomy
description: Low-level parallel chunk iteration with explicit enableable-component mask handling, type handle management, and per-chunk metadata access.
tags: [jobs, chunks]
---

# IJobChunk — Full Anatomy with Enableable Mask

## Intent
Low-level parallel chunk iteration with explicit enableable-component mask handling, type handle management, and per-chunk metadata access.

## Use When
- Per-chunk metadata needed: `unfilteredChunkIndex`, `DidChange`, SharedComponent values, `ChunkHeader`.
- Fine-grained enableable-component masking required.
- ECB.ParallelWriter sort key must be `unfilteredChunkIndex` for deterministic parallel playback.
- IJobEntity source generation is insufficient.

## Avoid When
Standard entity iteration without per-chunk metadata — use IJobEntity (less boilerplate, identical performance).

## Senior Pattern
```csharp
[BurstCompile]
public struct MyChunkJob : IJobChunk
{
    public ComponentTypeHandle<Velocity> VelocityHandle;
    [ReadOnly] public ComponentTypeHandle<Speed> SpeedHandle;
    public EntityTypeHandle EntityHandle;
    public EntityCommandBuffer.ParallelWriter Ecb;
    public float DeltaTime;

    [BurstCompile]
    public void Execute(in ArchetypeChunk chunk, int unfilteredChunkIndex,
        bool useEnableMask, in v128 chunkEnabledMask)
    {
        var velocities = chunk.GetNativeArray(ref VelocityHandle);
        var speeds     = chunk.GetNativeArray(ref SpeedHandle);
        var entities   = chunk.GetNativeArray(EntityHandle);

        var enumerator = new ChunkEntityEnumerator(useEnableMask, chunkEnabledMask, chunk.Count);
        while (enumerator.NextEntityIndex(out var i))
        {
            velocities[i] = new Velocity { Value = velocities[i].Value + speeds[i].Value * DeltaTime };
            if (speeds[i].Value > 100f)
                Ecb.RemoveComponent<Speed>(unfilteredChunkIndex, entities[i]);
        }
    }
}

// In OnUpdate:
var job = new MyChunkJob
{
    VelocityHandle = state.GetComponentTypeHandle<Velocity>(),
    SpeedHandle    = state.GetComponentTypeHandle<Speed>(true),
    EntityHandle   = state.GetEntityTypeHandle(),
    Ecb            = ecbSystem.CreateCommandBuffer().AsParallelWriter(),
    DeltaTime      = SystemAPI.Time.DeltaTime
};
state.Dependency = job.ScheduleParallel(myQuery, state.Dependency);
```

## Anti-Patterns
- Not passing `useEnableMask`/`chunkEnabledMask` to `ChunkEntityEnumerator` — silently processes disabled entities.
- Caching `ComponentTypeHandle<T>` across frames — stale after structural changes; always call `state.GetComponentTypeHandle<T>()` in OnUpdate.
- Using `chunk.Count` directly when query has enableable components — iterates disabled entities.

## Runtime Risks
- Stale type handles throw safety errors in development builds; silently corrupt data in release builds.
- Wrong ECB.ParallelWriter sort key (not `unfilteredChunkIndex`) = non-deterministic command playback order.

## Performance Notes
- Direct NativeArray access via type handles = maximum cache locality (chunk memory is contiguous).
- `ScheduleParallel` distributes whole chunks across workers.
- Per-chunk scheduling overhead is lower than per-entity scheduling.

## Architecture Guidance
Always use `unfilteredChunkIndex` as ECB.ParallelWriter sort key. Reserve IJobChunk for systems where per-chunk information genuinely changes behavior — otherwise use IJobEntity.

## Related Skills
[[ijobchunk-chunk-job]], [[enableable-component]], [[ecb-parallel-writer]], [[job-dependency-chain]]
