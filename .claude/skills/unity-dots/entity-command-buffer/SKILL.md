---
name: entity-command-buffer
description: Record structural changes (AddComponent, RemoveComponent, Instantiate, DestroyEntity) during job execution or entity iteration, then play them back safely on the main thread after the frame boundary.
---

# Entity Command Buffer

## Intent
Record structural changes (AddComponent, RemoveComponent, Instantiate, DestroyEntity) during job execution or entity iteration, then play them back safely on the main thread after the frame boundary.

## Use When
Any structural change needed inside a job or while iterating entities. Use BeginSimulationEntityCommandBufferSystem for standard playback timing. Use Allocator.Temp ECB only for immediate same-frame playback on the main thread.

## Avoid When
The change is a component value mutation, not a structural change — write directly via RefRW. Avoid creating per-system manual ECBs when BeginSimulationEntityCommandBufferSystem covers the timing.

## Senior Pattern
- Get ECB singleton from the appropriate ECB system: `SystemAPI.GetSingleton<BeginSimulationEntityCommandBufferSystem.Singleton>().CreateCommandBuffer(state.WorldUnmanaged)`.
- For parallel jobs: use `ecb.AsParallelWriter()` and pass `[ChunkIndexInQuery] int chunkIndex` as the sort key to Execute.
- For main-thread same-frame use: `new EntityCommandBuffer(Allocator.Temp)`, call Playback, then Dispose.
- Commands are replayed in sort-key order — deterministic across parallel workers.

## Code Template
```csharp
// From a parallel job:
[BurstCompile]
partial struct SpawnJob : IJobEntity
{
    public EntityCommandBuffer.ParallelWriter Ecb;
    public Entity Prefab;

    void Execute([ChunkIndexInQuery] int chunkIndex, in SpawnRequest request)
    {
        var e = Ecb.Instantiate(chunkIndex, Prefab);
        Ecb.SetComponent(chunkIndex, e, new LocalTransform
        {
            Position = request.Position,
            Rotation = quaternion.identity,
            Scale = 1f
        });
    }
}

[BurstCompile]
public void OnUpdate(ref SystemState state)
{
    var ecbSingleton = SystemAPI.GetSingleton<BeginSimulationEntityCommandBufferSystem.Singleton>();
    var ecb = ecbSingleton.CreateCommandBuffer(state.WorldUnmanaged);

    state.Dependency = new SpawnJob
    {
        Ecb = ecb.AsParallelWriter(),
        Prefab = SystemAPI.GetSingleton<SpawnConfig>().Prefab
    }.ScheduleParallel(state.Dependency);
}
```

## Anti-Patterns
- Using a non-parallel ECB inside ScheduleParallel — safety exception.
- Forgetting to pass sort key to ECB.ParallelWriter — non-deterministic replay, potential exception.
- Creating a manual Allocator.Temp ECB and forgetting to Dispose — memory leak.
- Playing back an ECB while iterating entities from the same query — iterator invalidation.

## Runtime Risks
- ECB.ParallelWriter without sort key: command order is undefined, entity creation may produce wrong results.
- Playback during active iteration: crashes or silently wrong entity state.
- Missing Dispose on manual ECB: leak persists until world destruction.

## Performance Notes
- ECB recording is cheap (unmanaged buffer append). Playback is batched and amortized.
- BeginSimulationEntityCommandBufferSystem avoids per-system allocator overhead.
- Avoid creating structural changes every frame on many entities — use enableable components for toggle-frequency changes.

## Architecture Guidance
Define a small number of ECB playback points (begin/end simulation, begin/end initialization). Systems write to the nearest appropriate playback point. Never add ad-hoc Playback calls mid-frame outside defined points.

## Related Skills (Wave 3 deepenings)
- [[ecb-system-timing]] — Begin vs End simulation boundary selection, RequireForUpdate guard
- [[ecb-parallel-writer]] — ChunkIndexInQuery sort key mechanics, deterministic replay
- [[ecb-manual-immediate]] — Allocator.Temp inline playback, one-shot init pattern
- [[ecb-multiplayback]] — PlaybackPolicy.MultiPlayback for streaming/subscene reload
- [[structural-change-cost-model]] — when to use ECB vs enableable vs value mutation
- [[batch-structural-change-on-query]] — EntityManager query-level batch operations
- [[toentityarray-snapshot-pattern]] — safe iterate + structurally change pattern
- [[icleanupcomponentdata-runtime]] — on-destroy resource release pattern
