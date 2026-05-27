---
name: multi-entity-baker
description: Create multiple runtime entities from a single authoring GameObject using CreateAdditionalEntity, with BakingOnlyEntity marking staging entities that should not appear in the runtime world.
---

# Multi-Entity Baker

## Intent
Create multiple runtime entities from a single authoring GameObject using CreateAdditionalEntity, with BakingOnlyEntity marking staging entities that should not appear in the runtime world.

## Use When
One authoring GO conceptually represents N runtime entities (procedural tiles, image-to-entity conversion, mesh-to-particle conversion, grid spawning). The N is known at bake time from authoring data.

## Avoid When
The count is not known at bake time (runtime-spawned entities) — use EntityCommandBuffer at runtime instead. Avoid when the additional entities are purely internal staging entities that a baking system will process — use [BakingType] buffer + baking system instead.

## Senior Pattern
- Call `CreateAdditionalEntity(TransformUsageFlags.X)` inside the Baker to create each additional entity.
- Use `AddBuffer<T>(mainEntity)` to pass the list of additional entities to a baking system via a [BakingType] buffer.
- Use `AddComponent(entity, new ComponentTypeSet(...))` to batch-add all components in one structural change.
- Call `AddComponent<BakingOnlyEntity>(stagingEntity)` on any entity that exists only to carry data to a baking system and should not appear in the runtime world.
- SetComponent after AddComponent to initialise transform and data.

## Code Template
```csharp
[BakingType]
public struct TileEntityRef : IBufferElementData
{
    public Entity Value;
}

class Baker : Baker<TileGridAuthoring>
{
    public override void Bake(TileGridAuthoring authoring)
    {
        var mainEntity = GetEntity(TransformUsageFlags.None);

        // main entity is only a staging container
        AddComponent<BakingOnlyEntity>(mainEntity);

        var tileRefs = AddBuffer<TileEntityRef>(mainEntity);

        for (int y = 0; y < authoring.Height; y++)
        for (int x = 0; x < authoring.Width; x++)
        {
            var tile = CreateAdditionalEntity(TransformUsageFlags.ManualOverride);

            // Single structural change for all components
            AddComponent(tile, new ComponentTypeSet(
                ComponentType.ReadWrite<LocalTransform>(),
                ComponentType.ReadWrite<LocalToWorld>(),
                ComponentType.ReadWrite<TileData>()
            ));
            SetComponent(tile, LocalTransform.FromPosition(
                new float3(x * authoring.TileSize, 0, y * authoring.TileSize)));
            SetComponent(tile, new TileData { GridX = x, GridY = y });

            tileRefs.Add(new TileEntityRef { Value = tile });
        }
    }
}
```

## Anti-Patterns
- Forgetting BakingOnlyEntity on a staging/intermediate entity — it persists in the runtime world as a useless empty entity.
- Calling AddComponent separately for each component on a newly created entity — N structural changes instead of 1. Use ComponentTypeSet.
- Not registering DependsOn for source data that determines the entity count — Baker won't rerun when the count changes.

## Runtime Risks
- Missing BakingOnlyEntity: unwanted entities in runtime world pollute archetypes, waste chunk space, may be incorrectly matched by queries.

## Performance Notes
- ComponentTypeSet batch add: 1 archetype migration vs N separate migrations. Critical for Bakers that create hundreds of additional entities.
- Additional entities created by a Baker are tied to the authoring GO's lifetime — no manual lifecycle management needed.

## Architecture Guidance
Use multi-entity Bakers when the authoring representation is inherently different from the runtime representation (e.g., "a 10×10 grid" in authoring → 100 individual tile entities at runtime). For runtime spawning patterns, keep the Baker to a prefab reference and spawn at runtime.

## Related Skills
[[baker-authoring-conversion]], [[baking-type-component]]
