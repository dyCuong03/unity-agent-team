---
name: wave4-ijobparallelfor-array-transform
description: Process large non-entity NativeArrays in parallel by distributing index ranges across worker threads.
---

# IJobParallelFor — Array Transform

## Intent
Process large non-entity NativeArrays in parallel by distributing index ranges across worker threads.

## Use When
- Data is a raw NativeArray (not ECS entities/components) and each index is independent.
- Large element counts (> ~1000) where parallel speedup exceeds scheduling overhead.
- Math-heavy transforms where Burst + SIMD provide significant gains.

## Avoid When
- Data is ECS entities/components — use IJobEntity or IJobChunk.
- Elements have cross-index dependencies.

## Senior Pattern
```csharp
[BurstCompile]
public struct ScaleJob : IJobParallelFor
{
    public NativeArray<float> Values;
    public float Scale;

    public void Execute(int index)
    {
        Values[index] *= Scale;
    }
}

// batchSize=64 is a common starting point; profile for your data size
state.Dependency = job.Schedule(myArray.Length, 64, state.Dependency);
```

## Anti-Patterns
- Writing to `Values[index ± k]` without `[NativeDisableParallelForRestriction]` — safety error.
- Using `[NativeDisableParallelForRestriction]` to write arbitrary indices without proving no two workers write the same index — silent race.
- `batchSize` of 1 for small arrays — thread dispatch overhead dominates.
- `batchSize` equal to total length — equivalent to IJob, parallel overhead wasted.

## Runtime Risks
- Cross-index writes without the attribute produce incorrect results in Burst release builds (no bounds check).
- `batchSize` too small causes excessive work-item overhead.

## Performance Notes
- `batchSize` 64 works well for float32 arrays; tune based on Profiler results.
- SIMD auto-vectorization works best for simple arithmetic loops.
- For entity data, prefer IJobEntity — IJobParallelFor is for non-entity NativeArrays only.

## Architecture Guidance
Use for non-entity bulk array transforms: physics response buffers, audio sample processing, procedural mesh generation. For ECS entity data, always prefer IJobEntity or IJobChunk.

## Related Skills
[[ijobentity-parallel-job]], [[job-dependency-chain]], [[burst-compilation-contract]]
