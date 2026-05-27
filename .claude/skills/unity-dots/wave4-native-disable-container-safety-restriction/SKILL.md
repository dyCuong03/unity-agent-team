---
name: wave4-native-disable-container-safety-restriction
description: Allow each parallel worker in IJobChunk to hold its own per-thread scratch NativeContainer by opting out of the safety system''s shared-container restriction.
---

# NativeDisableContainerSafetyRestriction — Per-Thread Scratch

## Intent
Allow each parallel worker in IJobChunk to hold its own per-thread scratch NativeContainer by opting out of the safety system's shared-container restriction.

## Use When
- IJobChunk needs per-chunk working memory (scratch buffer, priority queue, temporary list).
- Each chunk's `Execute()` call receives a copy of the job struct, guaranteeing no sharing between workers.

## Avoid When
- Container is truly shared across workers — use `NativeParallelMultiHashMap.AsParallelWriter()` instead.
- Using IJobParallelFor — job struct copy semantics differ; IJobChunk is safer for this pattern.

## Senior Pattern
```csharp
[BurstCompile]
public struct NearestNeighborJob : IJobChunk
{
    // Per-thread ownership guaranteed by IJobChunk copy-per-chunk semantics.
    // Safety restriction disabled because each worker has its own copy.
    [NativeDisableContainerSafetyRestriction]
    public NativePriorityHeap<float> Scratch;

    [BurstCompile]
    public void Execute(in ArchetypeChunk chunk, int unfilteredChunkIndex,
        bool useEnableMask, in v128 chunkEnabledMask)
    {
        // Lazy init — Scratch is uninitialized on first Execute per chunk
        if (!Scratch.IsCreated)
            Scratch = new NativePriorityHeap<float>(16, Allocator.Temp);

        var enumerator = new ChunkEntityEnumerator(useEnableMask, chunkEnabledMask, chunk.Count);
        while (enumerator.NextEntityIndex(out var i))
        {
            Scratch.Push(/* distance for entity i */);
        }
        // Allocator.Temp — auto-disposed when job completes on this worker
    }
}
```

## Anti-Patterns
- Using `[NativeDisableContainerSafetyRestriction]` on a container that IS shared between workers — silent race, impossible to detect in Burst release builds.
- Forgetting `IsCreated` check — Burst-compiled null-ref crashes worker thread.
- Using `Allocator.Persistent` for scratch — leaks if job is abandoned; use `Allocator.Temp`.

## Runtime Risks
- Safety system cannot protect after opt-out — correctness depends entirely on developer's guarantee of per-thread ownership.
- IJobChunk guarantees one copy of job struct per chunk dispatch; IJobParallelFor does NOT give the same guarantee in all Unity versions.

## Performance Notes
- `Allocator.Temp` inside Burst job = thread-local storage, essentially free allocation.
- Enables O(n) algorithms (nearest-neighbor, convex hull) without pre-allocated global arrays.

## Architecture Guidance
IJobChunk guarantees per-chunk copy semantics — each worker thread receives its own copy of the job struct, so each worker has its own `Scratch` instance. This is why the opt-out is safe here specifically. Always document the per-thread ownership guarantee at the field declaration.

## Related Skills
[[ijobchunk-full-anatomy]], [[ijobchunk-chunk-job]]
