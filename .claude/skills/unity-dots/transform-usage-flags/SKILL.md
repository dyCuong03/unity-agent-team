---
name: transform-usage-flags
description: Declare exactly which transform components an entity needs at bake time, preventing spurious LocalTransform/LocalToWorld components on data-only entities and missing transforms on moving entities.
tags: [baking, transforms]
metadata:
  internal-only: true
  tier: 3
---

# TransformUsageFlags

## Intent
Declare exactly which transform components an entity needs at bake time, preventing spurious LocalTransform/LocalToWorld components on data-only entities and missing transforms on moving entities.

## Use When
Every call to GetEntity() and CreateAdditionalEntity() in a Baker. The flag must match the entity's actual runtime behavior.

## Avoid When
There is no "avoid when" — TransformUsageFlags must always be specified explicitly. Never guess; derive the flag from how the entity will be used at runtime.

## Senior Pattern
- `TransformUsageFlags.None` — data-only entities (config, singletons, tags, staging entities). No LocalTransform added.
- `TransformUsageFlags.Dynamic` — entities that move at runtime. Adds LocalTransform + LocalToWorld.
- `TransformUsageFlags.Renderable` — entities rendered but not moved by ECS systems (static mesh renderers). Adds LocalToWorld only.
- `TransformUsageFlags.ManualOverride` — Baker takes full responsibility for adding transform components. Used when batch-adding many components via ComponentTypeSet to minimize archetype migrations.
- For prefab entity references: `GetEntity(authoring.PrefabField, TransformUsageFlags.Dynamic)`.

## Code Template
```csharp
class Baker : Baker<EnemyAuthoring>
{
    public override void Bake(EnemyAuthoring authoring)
    {
        // Moving enemy — needs LocalTransform
        var entity = GetEntity(TransformUsageFlags.Dynamic);
        AddComponent(entity, new EnemyData { Speed = authoring.Speed });

        // Config singleton — no transform needed
        var configEntity = CreateAdditionalEntity(TransformUsageFlags.None);
        AddComponent(configEntity, new EnemyConfig { MaxCount = authoring.MaxCount });

        // Batch add via ManualOverride — single structural change
        var tileEntity = CreateAdditionalEntity(TransformUsageFlags.ManualOverride);
        AddComponent(tileEntity, new ComponentTypeSet(
            ComponentType.ReadWrite<LocalTransform>(),
            ComponentType.ReadWrite<LocalToWorld>(),
            ComponentType.ReadWrite<TileData>()
        ));
        SetComponent(tileEntity, LocalTransform.FromPosition(authoring.TileOffset));
    }
}
```

## Anti-Patterns
- Using `TransformUsageFlags.Dynamic` on a static/data-only entity — wastes chunk space, triggers unnecessary TransformSystemGroup processing every frame.
- Using `TransformUsageFlags.None` on an entity that moves — LocalTransform is absent at runtime, transform system skips it, entity never moves.
- Using `TransformUsageFlags.ManualOverride` and forgetting to AddComponent the transform manually — silently broken transforms, no compile or runtime error until movement is attempted.

## Runtime Risks
- Wrong flag = wrong archetype = wrong system behavior. Static entities with Dynamic flag waste memory and CPU. Moving entities with None flag are invisible to the transform system.

## Performance Notes
- None = smallest archetype footprint. Prefer for all config/singleton entities.
- ManualOverride + ComponentTypeSet batch add = single structural change for all components, minimum archetype migrations during baking.

## Architecture Guidance
Match the flag to how the runtime system will use the entity. If unsure, check which systems query for LocalTransform — if your entity needs to be in those queries, use Dynamic.

## Related Skills
[[baker-authoring-conversion]]
