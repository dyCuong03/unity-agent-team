---
name: baking-world-query-options
description: Configure entity queries in baking systems to correctly include disabled entities, prefab entities, and only entities that have completed a baking pass, ensuring all entity types are processed corr...
tags: [baking, query]
metadata:
  internal-only: true
  tier: 3
---

# Baking World Query Options

## Intent
Configure entity queries in baking systems to correctly include disabled entities, prefab entities, and only entities that have completed a baking pass, ensuring all entity types are processed correctly.

## Use When
Any baking system (WorldSystemFilterFlags.BakingSystem) that sets transform components, processes all entity types, or must differentiate between staged/transient entities and fully-baked entities.

## Avoid When
Runtime systems — IncludePrefab and IncludeDisabledEntities have different semantics at runtime (they expose entities that should never be directly simulated).

## Senior Pattern
- `EntityQueryOptions.IncludeDisabledEntities` — includes entities baked from inactive GameObjects.
- `EntityQueryOptions.IncludePrefab` — includes entities baked from prefab roots.
- `.WithAll<BakedEntity>()` — filters to entities that have completed a full baking pass (excludes transient baking-only entities).
- Combine all three for baking systems that must process every entity type: `.WithOptions(IncludeDisabledEntities | IncludePrefab).WithAll<BakedEntity>()`.

## Code Template
```csharp
[WorldSystemFilter(WorldSystemFilterFlags.BakingSystem)]
public partial struct CustomTransformBakingSystem : ISystem
{
    public void OnUpdate(ref SystemState state)
    {
        // Process all baked entity types — including inactive GOs and prefab roots
        foreach (var (transform, data) in
            SystemAPI.Query<RefRW<LocalTransform>, RefRO<CustomTransformData>>()
                .WithAll<BakedEntity>()
                .WithOptions(
                    EntityQueryOptions.IncludeDisabledEntities |
                    EntityQueryOptions.IncludePrefab))
        {
            transform.ValueRW = LocalTransform.FromPositionRotation(
                data.ValueRO.Position,
                data.ValueRO.Rotation);
        }
    }
}
```

## Anti-Patterns
- Omitting IncludePrefab in a baking transform system — prefab entities don't get their transforms set, runtime instantiation produces wrong initial positions.
- Omitting BakedEntity filter — baking-only staging entities (BakingOnlyEntity) get processed, wastes work and may produce errors.
- Using these options in a runtime system — IncludePrefab exposes prefab root entities which should never be simulated.

## Runtime Risks
No runtime risks from correct baking system use. Wrong omissions in the baking world produce wrong initial state that surfaces at runtime.

## Performance Notes
The additional options expand the query's entity set. WithAll<BakedEntity> narrows it back down — the net overhead vs a normal query is minimal.

## Architecture Guidance
In baking systems, think of the query as "all entities I should process" = all real entities (including inactive/prefab) that have finished baking. The three-part pattern (IncludeDisabledEntities + IncludePrefab + BakedEntity) is the standard baking system query template for transform and full-entity processing.

## Related Skills
[[baking-system]], [[baking-type-component]]
