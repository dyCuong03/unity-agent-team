---
name: ecb-parallel-writer
description: Enable structural changes from ScheduleParallel jobs by converting an ECB to a thread-safe parallel writer keyed by chunk index for deterministic command replay.
---

# ECB Parallel Writer

## Intent
Enable structural changes from ScheduleParallel jobs by converting an ECB to a thread-safe parallel writer keyed by chunk index for deterministic command replay.

## Use When
Any IJobEntity or IJobChunk scheduled with ScheduleParallel that needs to record structural changes (AddComponent, RemoveComponent, Instantiate, DestroyEntity, SetComponent on new entities).

## Avoid When
The job is scheduled with Schedule (single-threaded) — a regular ECB works fine without AsParallelWriter. Avoid for jobs that only mutate existing component values — use RefRW directly, no ECB needed.

## Senior Pattern
- `ecb.AsParallelWriter()` converts the ECB to a ParallelWriter — pass this as a job field.
- In IJobEntity Execute: add `[ChunkIndexInQuery] int chunkIndex` as a special parameter (source-generated, not a component).
- Use `chunkIndex` as the sort key on every ECB.ParallelWriter call: `ecb.DestroyEntity(chunkIndex, entity)`.
- Sort key guarantees deterministic playback order across parallel workers — commands with lower sort keys execute first.
- Commands within the same chunk (same sort key) execute in recording order.

## Code Template
```csharp
[BurstCompile]
partial struct DestroyOutOfBoundsJob : IJobEntity
{
    public EntityCommandBuffer.ParallelWriter Ecb;
    public float BoundaryY;

    void Execute([ChunkIndexInQuery] int chunkIndex, Entity entity,
        in LocalTransform transform)
    {
        if (transform.Position.y < BoundaryY)
            Ecb.DestroyEntity(chunkIndex, entity);
    }
}

[BurstCompile]
public void OnUpdate(ref SystemState state)
{
    var ecb = SystemAPI
        .GetSingleton<EndSimulationEntityCommandBufferSystem.Singleton>()
        .CreateCommandBuffer(state.WorldUnmanaged)
        .AsParallelWriter();

    state.Dependency = new DestroyOutOfBoundsJob
    {
        Ecb = ecb,
        BoundaryY = -10f
    }.ScheduleParallel(state.Dependency);
}
```

## Anti-Patterns
- Passing a non-parallel ECB (regular `CreateCommandBuffer`) to a ScheduleParallel job — safety system throws at schedule time or at Playback.
- Using a hard-coded constant sort key (e.g., always `0`) — all commands land in bucket 0, replay is non-deterministic for commands from different chunks.
- Using `[EntityIndexInQuery] int entityIndex` as sort key when `[ChunkIndexInQuery]` is sufficient — EntityIndexInQuery is a global sequential index, more expensive to compute. Use only when per-entity order within a chunk matters.
- Forgetting the sort key parameter entirely — ECB.ParallelWriter methods require it; compiler error or safety exception.

## Runtime Risks
- Non-parallel ECB in parallel job: race condition on the command buffer, detected by safety system.
- Wrong sort key: non-deterministic structural changes, subtle replay ordering bugs.

## Performance Notes
- Parallel command recording scales with worker thread count. Playback sort is O(commands × log(chunks)) — negligible relative to entity processing.
- ChunkIndexInQuery sort key is free to generate (source-generated from chunk metadata). Prefer it over EntityIndexInQuery.

## Architecture Guidance
ParallelWriter is the correct and only pattern for structural changes from parallel jobs. Design systems to record commands in parallel and let the ECBSystem batch-sort and replay them on the main thread.

## Related Skills
[[entity-command-buffer]], [[ijobentity-parallel-job]], [[job-dependency-chain]]
