---
name: wave8-ijobchunk-use-enabled-mask-guard
description: Correctly handle the enableable component bitmask in IJobChunk to avoid processing disabled entities or skipping enabled ones.
tags: [jobs, chunks, enableable, antipattern]
---

# IJobChunk useEnabledMask Guard

## Intent
Correctly handle the enableable component bitmask in IJobChunk to avoid processing disabled entities or skipping enabled ones.

## Use When
- An IJobChunk implementation iterates over chunks that contain one or more IEnableableComponent types
- The query includes any component that implements IEnableableComponent

## Avoid When
- The job uses IJobEntity — IJobEntity handles the enableable mask automatically; this guard is only needed in IJobChunk
- No IEnableableComponent types are in the query — useEnabledMask will always be false; the fast path handles all entities

## Senior Pattern
```csharp
[BurstCompile]
public struct ProcessActiveEntitiesJob : IJobChunk
{
    public ComponentTypeHandle<Velocity> VelocityHandle;
    [ReadOnly] public ComponentTypeHandle<ActiveTag> ActiveTagHandle;  // IEnableableComponent
    [ReadOnly] public EntityTypeHandle EntityHandle;

    [BurstCompile]
    public void Execute(in ArchetypeChunk chunk, int unfilteredChunkIndex,
        bool useEnabledMask, in v128 chunkEnabledMask)
    {
        var velocities = chunk.GetNativeArray(ref VelocityHandle);

        if (useEnabledMask)
        {
            // Some entities in chunk may be disabled — iterate only enabled ones:
            var enumerator = new ChunkEntityEnumerator(useEnabledMask, chunkEnabledMask, chunk.Count);
            while (enumerator.NextEntityIndex(out int i))
            {
                velocities[i] = new Velocity { Value = velocities[i].Value * 0.9f };
            }
        }
        else
        {
            // All entities in chunk are enabled — iterate all without mask overhead:
            for (int i = 0; i < chunk.Count; i++)
            {
                velocities[i] = new Velocity { Value = velocities[i].Value * 0.9f };
            }
        }
    }
}

// Schedule — query includes IEnableableComponent type:
EntityQuery query = state.GetEntityQuery(
    ComponentType.ReadWrite<Velocity>(),
    ComponentType.ReadOnly<ActiveTag>());

state.Dependency = new ProcessActiveEntitiesJob
{
    VelocityHandle  = state.GetComponentTypeHandle<Velocity>(),
    ActiveTagHandle = state.GetComponentTypeHandle<ActiveTag>(isReadOnly: true),
    EntityHandle    = state.GetEntityTypeHandle()
}.ScheduleParallel(query, state.Dependency);
```

## Anti-Patterns
- Ignoring `useEnabledMask` and iterating all `chunk.Count` entities — silently processes disabled entities; incorrect simulation results for all state-machine patterns built on IEnableableComponent.
- Using a manual bitmask check instead of ChunkEntityEnumerator — error-prone; re-invents platform-specific SIMD bitmask iteration logic.
- Calling `ArchetypeChunk.GetEnabledMask()` without checking `useEnabledMask` first — unnecessary work when all entities in the chunk are enabled.
- Using IJobChunk when IJobEntity would suffice — IJobEntity handles the mask automatically; prefer it unless chunk-level access is required.

## Runtime Risks
- Skipping the useEnabledMask guard silently processes disabled entities — no exception, no warning.
- For IEnableableComponent-based state machines (dead/alive, sleeping/awake), this means dead or sleeping entities receive updates they should not — correctness bug that manifests as incorrect game behavior.

## Performance Notes
- ChunkEntityEnumerator uses SIMD bitmask iteration internally — faster than a manual branch-per-entity loop.
- The `useEnabledMask == false` fast path skips bitmask overhead entirely for fully-enabled chunks, which is the common case in well-organized archetypes.
- Prefer IJobEntity over IJobChunk for new systems — it eliminates this boilerplate and handles the mask automatically.

## Architecture Guidance
- For new systems, prefer IJobEntity (mask is automatic). Use IJobChunk only when chunk-level access is required (pointer arithmetic, DidChange, per-chunk scratch buffers).
- When using IJobChunk with any IEnableableComponent in the query, the `useEnabledMask` guard + `ChunkEntityEnumerator` pattern is mandatory — treat it as non-negotiable.

## Related Skills
[[wave4-ijobchunk-full-anatomy]], [[enableable-component]], [[wave6-with-disabled-query-filter]], [[wave8-enableable-component-query-mismatch]]
