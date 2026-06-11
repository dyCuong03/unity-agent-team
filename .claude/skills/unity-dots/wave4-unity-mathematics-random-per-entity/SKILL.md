---
name: wave4-unity-mathematics-random-per-entity
description: Generate statistically independent, deterministic random streams per entity in parallel jobs using `Unity.Mathematics.Random.CreateFromIndex()`.
tags: [jobs, math]
metadata:
  internal-only: true
  tier: 3
---

# Unity.Mathematics.Random — Per-Entity Parallel RNG

## Intent
Generate statistically independent, deterministic random streams per entity in parallel jobs using `Unity.Mathematics.Random.CreateFromIndex()`.

## Use When
- Per-entity randomness needed in parallel IJobEntity or IJobChunk.
- Reproducibility is important (deterministic seeds per entity index).
- Burst-safe RNG with no shared state between workers is required.

## Avoid When
- Single non-deterministic random value needed on the main thread — `new System.Random()` is sufficient.
- Cross-frame persistent RNG state needed — store `Random` as an `IComponentData` component and pass `ref Random rng` to `Execute`.

## Senior Pattern
```csharp
[BurstCompile]
public partial struct SpawnVariationJob : IJobEntity
{
    public uint FrameSeed;

    [BurstCompile]
    public void Execute([EntityIndexInQuery] int entityIndex, ref SpawnVariation variation)
    {
        var rng = Unity.Mathematics.Random.CreateFromIndex((uint)entityIndex + FrameSeed);
        variation.Offset = rng.NextFloat3(new float3(-1f), new float3(1f));
        variation.Scale  = rng.NextFloat(0.8f, 1.2f);
    }
}

// Persistent per-entity RNG (AI behaviors, procedural animation):
public struct AgentRng : IComponentData
{
    public Random Rng;
}
// Pass as: ref Random rng in Execute — state preserved across frames
```

## Anti-Patterns
- Using `new Unity.Mathematics.Random((uint)index)` instead of `CreateFromIndex` — sequential seeds produce visually correlated outputs; `CreateFromIndex` hashes the index first.
- Sharing a single `Random` instance as a job field across parallel workers — race condition; each worker advances the state unpredictably.
- Storing RNG as a static field — Burst-unsafe, shared state across calls.
- `new Random(0)` throws — seed 0 is invalid; `CreateFromIndex(0)` is safe.

## Runtime Risks
- Re-using the same `(entityIndex + frameSeed)` combination across consecutive frames produces identical streams — vary `FrameSeed` if true frame-to-frame variation is needed.

## Performance Notes
- `CreateFromIndex` is a single hash operation — O(1), suitable for per-entity use in tight loops.
- `Random` is a 4-byte struct; zero allocation, entirely register-resident in Burst.
- `NextFloat3Direction()`, `NextFloat()`, `NextFloat2()` etc. are all Burst-safe.

## Architecture Guidance
- One-shot spawn variation: create `Random` in `Execute` using entity index + stable seed.
- Persistent per-entity RNG (AI behaviors, procedural animation): store `Random` as `IComponentData` and pass `ref Random rng` to `Execute` — state preserved across frames.
- Deterministic replay: store initial seed as a component, re-seed each logical tick from it.

## Related Skills
[[ijobentity-advanced-patterns]], [[entity-index-in-query-scatter-pattern]], [[burst-compilation-contract]]
