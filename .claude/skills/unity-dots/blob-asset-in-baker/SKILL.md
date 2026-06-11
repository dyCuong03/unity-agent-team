---
name: blob-asset-in-baker
description: Build immutable, Burst-safe, shareable constant data blobs at bake time using BlobBuilder, register them with BlobAssetStore for lifetime management, and store BlobAssetReference<T> in a runtime co...
tags: [baking]
metadata:
  internal-only: true
  tier: 3
---

# Blob Asset in Baker

## Intent
Build immutable, Burst-safe, shareable constant data blobs at bake time using BlobBuilder, register them with BlobAssetStore for lifetime management, and store BlobAssetReference<T> in a runtime component.

## Use When
Large constant data shared by multiple entities or per-entity (animation curves, config tables, mesh bounds, spell data, nav tables). Any read-only data that does not change at runtime and benefits from shared memory or Burst-safe access.

## Avoid When
The data changes at runtime — blobs are immutable. Avoid for small scalar constants — just put them in the component directly. Avoid storing BlobArray by value outside of a BlobAssetReference.

## Senior Pattern
- Define a struct with BlobArray<T>, BlobString, or nested BlobPtr<T> fields for the blob shape.
- In Baker: `using var blobBuilder = new BlobBuilder(Allocator.Temp)` — dispose scope ensures cleanup.
- `ref var root = ref blobBuilder.ConstructRoot<MyBlobData>()` — root allocation.
- `var array = blobBuilder.Allocate(ref root.MyArray, count)` — allocate BlobArray.
- `blobBuilder.CreateBlobAssetReference<MyBlobData>(Allocator.Persistent)` — create the reference.
- `AddBlobAsset(ref blobRef, out _)` — registers with BlobAssetStore, enables deduplication and lifetime management.
- Store `BlobAssetReference<MyBlobData>` in a component field.

## Code Template
```csharp
public struct AnimationBlobData
{
    public BlobArray<float> Keyframes;
    public float Duration;
    public int FrameCount;
}

class Baker : Baker<AnimationAuthoring>
{
    public override void Bake(AnimationAuthoring authoring)
    {
        DependsOn(authoring.AnimationCurve);  // register dependency first

        var entity = GetEntity(TransformUsageFlags.Dynamic);

        using var builder = new BlobBuilder(Allocator.Temp);
        ref var root = ref builder.ConstructRoot<AnimationBlobData>();
        root.Duration = authoring.AnimationCurve.length > 0
            ? authoring.AnimationCurve.keys[^1].time : 0f;
        root.FrameCount = authoring.AnimationCurve.length;

        var keyframes = builder.Allocate(ref root.Keyframes, root.FrameCount);
        for (int i = 0; i < root.FrameCount; i++)
            keyframes[i] = authoring.AnimationCurve.keys[i].value;

        var blobRef = builder.CreateBlobAssetReference<AnimationBlobData>(Allocator.Persistent);
        AddBlobAsset(ref blobRef, out _);

        AddComponent(entity, new AnimationData { Blob = blobRef });
    }
}
```

## Anti-Patterns
- Using `Allocator.TempJob` for CreateBlobAssetReference — blob is freed before runtime use.
- Not calling `AddBlobAsset` in the Baker — BlobAssetStore doesn't manage lifetime, blob leaks on rebake.
- Disposing BlobBuilder before `CreateBlobAssetReference` — builder data freed, reference is invalid.
- Storing a BlobArray field by value (not through BlobAssetReference) — interior pointer becomes dangling immediately.
- Not registering DependsOn for the source asset — Baker won't rerun when source data changes, blob is stale.

## Runtime Risks
- Allocator.TempJob blob: use-after-free at runtime, hard to diagnose crash.
- Missing AddBlobAsset: memory leak accumulates on every incremental rebake.
- Dangling BlobArray copy: immediate undefined behavior in Burst jobs.

## Performance Notes
- BlobAssets are read-only so they can be accessed simultaneously from multiple Burst jobs with no safety restrictions.
- Shared blobs (via AddBlobAsset deduplication) eliminate redundant memory for identical data.
- BlobBuilder is a managed allocation — dispose scope is required.

## Architecture Guidance
BlobAsset = the ECS equivalent of a read-only const table. Use for any data that is "authored once, read many times by many entities." Structure the blob type to match read access patterns (flat arrays are faster to traverse than nested BlobPtr chains).

## Related Skills
[[baker-authoring-conversion]], [[baker-depends-on]]
