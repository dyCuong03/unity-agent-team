---
name: baking-type-component
description: Mark a component as existing only in the baking world so it can carry intermediate data from Bakers to baking systems without appearing in the runtime world.
tags: [baking]
metadata:
  internal-only: true
  tier: 3
---

# BakingType Component

## Intent
Mark a component as existing only in the baking world so it can carry intermediate data from Bakers to baking systems without appearing in the runtime world.

## Use When
A Baker needs to pass data to a baking system (WorldSystemFilterFlags.BakingSystem) that cannot be expressed in the final runtime component. Multi-stage baking pipelines, cross-entity aggregation, blob asset staging.

## Avoid When
The data belongs in the runtime world — use a normal IComponentData. Avoid when the data only needs to survive within a single baking pass — use [TemporaryBakingType] instead.

## Senior Pattern
- `[BakingType]` attribute on IComponentData or IBufferElementData struct.
- Baker adds the [BakingType] component as a staging area for the baking system to read.
- Baking system reads the [BakingType] component, computes the final result, and adds the runtime component.
- [BakingType] is automatically stripped from the destination runtime world after all baking systems complete.
- Can also be applied to managed class components (`[BakingType] public class MeshArrayBakingType : IComponentData`).

## Code Template
```csharp
// Staging component — exists only during baking
[BakingType]
public struct RawMeshData : IComponentData
{
    public float MeshScale;
    public Hash128 SourceHash;
}

// Staging buffer — Baker populates, baking system reads
[BakingType]
public struct RawVertex : IBufferElementData
{
    public float3 Position;
}

// Baker stages the data:
class Baker : Baker<MeshAuthoring>
{
    public override void Bake(MeshAuthoring authoring)
    {
        DependsOn(authoring.Mesh);
        var entity = GetEntity(TransformUsageFlags.None);
        AddComponent(entity, new RawMeshData
        {
            MeshScale = authoring.Scale,
            SourceHash = ComputeHash(authoring.Mesh)
        });
        // Baking system will read RawMeshData and produce BlobAssetReference<MeshBlobAsset>
    }
}
```

## Anti-Patterns
- Forgetting [BakingType] on an intermediate component — it leaks into the runtime world, pollutes archetypes, wastes memory.
- Reading a [BakingType] component from a runtime system — it doesn't exist, silent no-op or exception.
- Using [BakingType] when [TemporaryBakingType] would suffice — choose based on whether data must survive across multiple baking system passes.

## Runtime Risks
No runtime errors from correct use — wrong use leaks baking data into the runtime world, causing archetype pollution and potential system misfires.

## Performance Notes
[BakingType] components exist only during baking. Zero runtime memory or CPU cost. Stripped automatically — no cleanup code required.

## Architecture Guidance
Think of [BakingType] as a typed message channel from Baker to baking system. Baker writes the staging data; baking system reads, transforms, and produces the runtime component. This split keeps Bakers simple and baking systems reusable.

## Related Skills
[[baker-authoring-conversion]], [[baking-system]]
