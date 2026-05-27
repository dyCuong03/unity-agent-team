---
name: wave5-post-transform-matrix-non-uniform-scale
description: Apply non-uniform scale to entities using PostTransformMatrix, which is multiplied into LocalToWorld after the standard TRS computation.
---

# PostTransformMatrix — Non-Uniform Scale

## Intent
Apply non-uniform scale to entities using PostTransformMatrix, which is multiplied into LocalToWorld after the standard TRS computation.

## Use When
- Non-uniform scale needed (e.g., (1, 2, 1) — taller but same width)
- Squash-and-stretch animation, terrain tile variations, procedurally scaled geometry

## Avoid When
- Uniform scale is sufficient — use LocalTransform.Scale
- Non-uniform scale is baked and static — bake into mesh vertices or baked matrix directly

## Senior Pattern
```csharp
// In a custom LocalToWorld system (IJobChunk):
[BurstCompile]
public struct ApplyPostTransformJob : IJobChunk
{
    [ReadOnly]  public ComponentTypeHandle<LocalTransform> LocalTransformHandle;
    public ComponentTypeHandle<LocalToWorld> LocalToWorldHandle;
    // Optional — null when absent from chunk
    [ReadOnly]  public ComponentTypeHandle<PostTransformMatrix> PostTransformMatrixHandle;

    [BurstCompile]
    public void Execute(in ArchetypeChunk chunk, int unfilteredChunkIndex,
        bool useEnableMask, in v128 chunkEnabledMask)
    {
        var transforms = chunk.GetNativeArray(ref LocalTransformHandle);
        var localToWorlds = chunk.GetNativeArray(ref LocalToWorldHandle);

        // One null check per chunk, not per entity:
        bool hasPost = chunk.Has(ref PostTransformMatrixHandle);
        NativeArray<PostTransformMatrix> postArr = hasPost
            ? chunk.GetNativeArray(ref PostTransformMatrixHandle)
            : default;

        var enumerator = new ChunkEntityEnumerator(useEnableMask, chunkEnabledMask, chunk.Count);
        while (enumerator.NextEntityIndex(out var i))
        {
            float4x4 trs = transforms[i].ToMatrix();
            localToWorlds[i] = new LocalToWorld
            {
                Value = hasPost ? math.mul(trs, postArr[i].Value) : trs
            };
        }
    }
}

// Add PostTransformMatrix in Baker for authoring-time non-uniform scale:
public override void Bake(MyAuthoring authoring)
{
    var entity = GetEntity(TransformUsageFlags.Dynamic);
    AddComponent(entity, new PostTransformMatrix
    {
        Value = float4x4.Scale(authoring.NonUniformScale)
    });
}
```

## Anti-Patterns
- Storing non-uniform scale in LocalTransform.Scale — it is a single float; non-uniform values silently truncated to uniform.
- Ignoring PostTransformMatrix in a custom LocalToWorld system — non-uniform scale silently discarded.
- Checking HasComponent<PostTransformMatrix> per-entity in hot path — use chunk.Has() which is one check per chunk, not per entity.
- Wrong multiplication order: `math.mul(postTransform, trs)` — correct order is `math.mul(trs, postTransform)`.

## Runtime Risks
- GetNativeArray returns default when component absent from chunk — always null-check before indexing.
- Writing PostTransformMatrix from a parallel job that also writes LocalTransform on same entities — both type handles must be correctly marked (ref vs ReadOnly).

## Performance Notes
- Optional component check via chunk.Has(): one boolean per chunk, not per entity.
- Avoids storing full 4x4 matrix in LocalTransform for all entities when only a minority need non-uniform scale.

## Architecture Guidance
- Correct multiplication order: LocalToWorld.Value = math.mul(standardTRS, postTransform[i].Value).
- Standard Unity transform system already handles PostTransformMatrix — only custom transform systems need to implement this manually.
- Prefer PostTransformMatrix over modifying mesh vertices at runtime for dynamic non-uniform scale.

## Related Skills
[[local-transform-write-pattern]], [[local-to-world-read-only-contract]], [[write-group-custom-transform]], [[wave4-ijobchunk-full-anatomy]]
