---
name: wave4-ijobentity-advanced-patterns
description: Extend IJobEntity with query filters, sort key parameters, and implicit-query scheduling for production ECS systems.
---

# IJobEntity — Advanced Patterns

## Intent
Extend IJobEntity with query filters, sort key parameters, and implicit-query scheduling for production ECS systems.

## Use When
- Structural component filters needed: `[WithAll]`, `[WithNone]`, `[WithAny]`, `[WithDisabled]`, `[WithPresent]`.
- ECB.ParallelWriter used and deterministic sort key required (`[ChunkIndexInQuery]`).
- Per-entity NativeArray writes need a stable index (`[EntityIndexInQuery]`).

## Avoid When
Per-chunk metadata (`unfilteredChunkIndex`, `DidChange`, SharedComponent values) required — use IJobChunk.

## Senior Pattern
```csharp
[WithAll(typeof(ActiveTag))]
[WithNone(typeof(DeadTag))]
[WithDisabled(typeof(FrozenTag))]
[BurstCompile]
public partial struct MoveJob : IJobEntity
{
    public EntityCommandBuffer.ParallelWriter Ecb;
    public float DeltaTime;

    [BurstCompile]
    public void Execute(
        [ChunkIndexInQuery] int chunkIndex,
        Entity entity,
        ref LocalTransform transform,
        in Velocity velocity)
    {
        transform.Position += velocity.Value * DeltaTime;
        if (transform.Position.y < -100f)
            Ecb.DestroyEntity(chunkIndex, entity);
    }
}

state.Dependency = new MoveJob
{
    Ecb = ecbSys.CreateCommandBuffer().AsParallelWriter(),
    DeltaTime = SystemAPI.Time.DeltaTime
}.ScheduleParallel(state.Dependency);
```

## Parameter Semantics
- `ref T` — read/write (RW type handle).
- `in T` — read-only (RO type handle; allows parallel reads with other RO jobs).
- `[ChunkIndexInQuery] int` — chunk-level sort key for ECB.ParallelWriter; unique per chunk, deterministic.
- `[EntityIndexInQuery] int` — entity-level index within query; use as NativeArray write index for scatter patterns.
- `Entity entity` — required when using ECB commands on the current entity.

## Anti-Patterns
- Using `[ChunkIndexInQuery]` as NativeArray write index — chunk-level, not entity-level; multiple entities in same chunk write same slot.
- Using `[EntityIndexInQuery]` as ECB.ParallelWriter sort key — not chunk-stable; use `[ChunkIndexInQuery]` instead.
- Forgetting `partial` on the struct — source generation silently fails.
- Not assigning result to `state.Dependency` when work should persist across system boundaries.

## Runtime Risks
- Wrong sort key for ECB.ParallelWriter = non-deterministic structural change order across frames.
- Missing `[WithNone]` for intended exclusion filters — queries silently match more entities than expected.

## Architecture Guidance
Default job type for ECS simulation work. Use `[WithAll]`/`[WithNone]` attributes on the struct to keep query intent co-located with the job. Reserve IJobChunk for cases where per-chunk metadata is genuinely required.

## Related Skills
[[ijobentity-parallel-job]], [[ijobchunk-full-anatomy]], [[ecb-parallel-writer]], [[entity-index-in-query-scatter-pattern]]
