---
name: temporary-baking-type
description: Mark a component as a single-pass baking signal — present during Baker execution and baking system processing within one baking pass, then automatically removed before the next pass.
tags: [baking]
---

# TemporaryBakingType

## Intent
Mark a component as a single-pass baking signal — present during Baker execution and baking system processing within one baking pass, then automatically removed before the next pass.

## Use When
Change-detection markers ("this entity was modified in this pass"), processing flags, or any intermediate state that must NOT persist across incremental baking passes.

## Avoid When
The data must survive across multiple baking system updates within a multi-pass pipeline — use [BakingType] instead.

## Senior Pattern
- `[TemporaryBakingType]` attribute on IComponentData struct.
- Baker adds the component to signal "this entity changed this pass."
- Baking system reads the component to identify entities requiring reprocessing.
- Component is automatically removed at the end of the baking pass — no explicit cleanup.
- Combine with [BakingType] ICleanupComponentData for multi-pass incremental detection.

## Code Template
```csharp
// Change signal — automatically removed after each baking pass
[TemporaryBakingType]
public struct EntityModifiedThisPass : IComponentData { }

// Baker adds it to flag changed entities:
class Baker : Baker<SomeAuthoring>
{
    public override void Bake(SomeAuthoring authoring)
    {
        var entity = GetEntity(TransformUsageFlags.None);
        AddComponent(entity, new SomeComponent { Value = authoring.Value });
        AddComponent<EntityModifiedThisPass>(entity);  // signals "reprocess me"
    }
}

// Baking system reads only changed entities:
[WorldSystemFilter(WorldSystemFilterFlags.BakingSystem)]
public partial struct IncrementalProcessSystem : ISystem
{
    public void OnUpdate(ref SystemState state)
    {
        foreach (var data in
            SystemAPI.Query<RefRO<SomeComponent>>()
                .WithAll<EntityModifiedThisPass>())
        {
            // Only processes entities modified in this pass
        }
    }
}
```

## Anti-Patterns
- Using [TemporaryBakingType] for data a baking system needs to persist across passes — it gets stripped, causing data loss and incorrect incremental results.
- Assuming [TemporaryBakingType] components are present in subsequent baking system OnUpdate calls — they are stripped after the first pass.

## Runtime Risks
Zero. Stripped automatically before the destination world snapshot.

## Performance Notes
Zero runtime cost. Self-cleaning eliminates the need for explicit RemoveComponent in baking systems.

## Architecture Guidance
- [TemporaryBakingType] = "changed this frame" signal.
- [BakingType] = "data for this bake cycle."
- [BakingType] + ICleanupComponentData = "entity lifecycle tracking across passes."

Choose based on lifetime requirement, not convenience.

## Related Skills
[[baking-type-component]]
