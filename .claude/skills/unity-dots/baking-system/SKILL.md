---
name: baking-system
description: Perform post-Baker ECS processing in the baking world — cross-entity aggregation, complex structural changes, blob asset construction, and render mesh setup — that cannot be expressed within a sing...
tags: [baking]
---

# Baking System

## Intent
Perform post-Baker ECS processing in the baking world — cross-entity aggregation, complex structural changes, blob asset construction, and render mesh setup — that cannot be expressed within a single Baker.

## Use When
The baking work requires querying multiple entities produced by different Bakers, performing structural changes that would invalidate Baker iteration, or accessing ECS APIs not available to Bakers (e.g., full EntityManager, ComponentLookup across entities).

## Avoid When
The work can be done entirely within one Baker — prefer Baker-local logic to avoid the split-responsibility complexity of Baker + baking system.

## Senior Pattern
- `[WorldSystemFilter(WorldSystemFilterFlags.BakingSystem)]` on a `partial struct : ISystem`.
- Baking systems run after all Bakers complete, with full ECS API access.
- Use `SetChangedVersionFilter` and `RequireForUpdate` to skip unnecessary work on incremental rebakes.
- For structural changes while iterating: call `query.ToEntityArray(Allocator.Temp)` first, then process via EntityManager random access — never mutate archetypes inside a SystemAPI.Query foreach.
- Baking systems cannot register DependsOn — Baker must stage all dependency data as [BakingType] components.

## Code Template
```csharp
[WorldSystemFilter(WorldSystemFilterFlags.BakingSystem)]
[UpdateAfter(typeof(TransformBakingSystem))]
public partial struct BoundingBoxAggregateSystem : ISystem
{
    private EntityQuery m_ChangedQuery;

    public void OnCreate(ref SystemState state)
    {
        m_ChangedQuery = SystemAPI.QueryBuilder()
            .WithAll<BoundingBox, BoundingBoxCleanup>()
            .Build();
        m_ChangedQuery.SetChangedVersionFilter(ComponentType.ReadOnly<BoundingBox>());
        state.RequireForUpdate(m_ChangedQuery);
    }

    public void OnUpdate(ref SystemState state)
    {
        // ToEntityArray first — then structural changes are safe
        var entities = m_ChangedQuery.ToEntityArray(Allocator.Temp);
        foreach (var entity in entities)
        {
            var box = state.EntityManager.GetComponentData<BoundingBox>(entity);
            // aggregate, then write runtime component
            state.EntityManager.SetComponentData(box.Parent, ComputeAggregateBounds(entity));
        }
        entities.Dispose();
    }
}
```

## Anti-Patterns
- Registering DependsOn inside a baking system — not supported, silently ignored, produces stale bakes.
- Calling EntityManager.AddComponent inside a SystemAPI.Query foreach — invalidates the iterator.
- Not using SetChangedVersionFilter — baking system reruns every bake pass even when nothing changed, slows iterative workflow.
- Querying baking world entities without `IncludeDisabledEntities | IncludePrefab` when transforms must be set — disabled GameObjects and prefab roots are silently skipped.

## Runtime Risks
Baking system errors produce wrong baked data, not runtime exceptions. Symptoms: wrong initial values, missing components, stale blob assets.

## Performance Notes
Use `RequireForUpdate` and `SetChangedVersionFilter` aggressively. Every unnecessary baking system pass slows the editor live-baking loop. Incremental baking performance directly affects iteration speed.

## Architecture Guidance
Baker = input declaration + data staging. Baking system = output computation. Keep Bakers focused on one entity's concerns. Baking systems handle cross-entity work.

## Related Skills
[[baker-authoring-conversion]], [[baking-type-component]]
