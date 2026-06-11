---
name: wave5-chunk-did-change-incremental-update
description: Skip processing of unchanged chunks in IJobChunk systems using chunk.DidChange(), enabling incremental updates that recompute only when input data has changed.
tags: [query, performance]
metadata:
  internal-only: true
  tier: 3
---

# Chunk.DidChange — Incremental Update

## Intent
Skip processing of unchanged chunks in IJobChunk systems using chunk.DidChange(), enabling incremental updates that recompute only when input data has changed.

## Use When
- System computes output (LocalToWorld, world-space bounds, derived data) from inputs that change infrequently
- Large static worlds where most entities don't move between frames
- Expensive derived-value computation that should not run for unchanged entities

## Avoid When
- Input changes every frame for all entities — DidChange always true, no benefit
- Output is cheap to compute — optimization overhead exceeds savings

## Senior Pattern
```csharp
[BurstCompile]
public struct ComputeDerivedJob : IJobChunk
{
    [ReadOnly] public ComponentTypeHandle<SourceData> SourceHandle;
    public ComponentTypeHandle<DerivedData> DerivedHandle;
    public uint LastSystemVersion;

    [BurstCompile]
    public void Execute(in ArchetypeChunk chunk, int unfilteredChunkIndex,
        bool useEnableMask, in v128 chunkEnabledMask)
    {
        if (!chunk.DidChange(ref SourceHandle, LastSystemVersion))
            return;  // nothing changed in this chunk since last frame

        var sources = chunk.GetNativeArray(ref SourceHandle);
        var deriveds = chunk.GetNativeArray(ref DerivedHandle);
        var enumerator = new ChunkEntityEnumerator(useEnableMask, chunkEnabledMask, chunk.Count);
        while (enumerator.NextEntityIndex(out var i))
            deriveds[i] = Compute(sources[i]);
    }
}

// In OnUpdate:
var job = new ComputeDerivedJob
{
    SourceHandle = state.GetComponentTypeHandle<SourceData>(isReadOnly: true),
    DerivedHandle = state.GetComponentTypeHandle<DerivedData>(),
    LastSystemVersion = state.LastSystemVersion   // pass per-call, not as a system field
};
state.Dependency = job.ScheduleParallel(myQuery, state.Dependency);

// For hierarchy propagation (children depend on parent LocalToWorld):
bool shouldUpdate = chunk.DidChange(ref ChildTransformHandle, LastSystemVersion)
                 || chunk.DidChange(ref LocalToWorldHandle, LastSystemVersion);
```

## Anti-Patterns
- Using SystemAPI.GetSingleton<T>() with unnecessary writes — marks chunk dirty every frame, defeats change detection.
- Checking DidChange without passing LastSystemVersion — always returns true (always stale).
- Applying DidChange only to leaf inputs but not parent propagation inputs — parent changes fail to propagate to children.
- Storing LastSystemVersion as a system field — it must be read fresh from state.LastSystemVersion in OnUpdate each frame.

## Runtime Risks
- DidChange is chunk-granular: one frequently-written entity in a chunk forces all entities in that chunk to recompute — co-locate static and dynamic entities in separate archetypes to maximize skip rate.
- Structural changes (add/remove component) do not set the dirty bit — entities in new chunks are always processed at least once regardless of DidChange.

## Performance Notes
- DidChange is O(1) per chunk — one integer comparison against LastSystemVersion.
- Large static world (10,000 entities, 128 per chunk = 78 chunks): skipping 70 unchanged chunks saves ~90% of transform work.

## Architecture Guidance
- Store uint LastSystemVersion in the IJobChunk struct; pass from state.LastSystemVersion in OnUpdate (not as a system field — value must be fresh each call).
- The standard Unity LocalToWorldSystem uses this exact pattern — replicate for all custom derived-value systems.
- For multi-input derived values: OR all DidChange checks — skip only when ALL inputs unchanged.

## Related Skills
[[wave4-ijobchunk-full-anatomy]], [[local-to-world-read-only-contract]], [[write-group-custom-transform]], [[post-transform-matrix-non-uniform-scale]]
