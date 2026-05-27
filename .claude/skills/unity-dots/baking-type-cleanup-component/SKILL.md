---
name: baking-type-cleanup-component
description: Track entity lifecycle (creation, re-parenting, destruction) within the incremental baking pipeline using ICleanupComponentData that survives entity destruction but is still stripped from the runti...
tags: [baking, structural-change]
---

# BakingType Cleanup Component — Entity Lifecycle Tracking

## Intent
Track entity lifecycle (creation, re-parenting, destruction) within the incremental baking pipeline using ICleanupComponentData that survives entity destruction but is still stripped from the runtime world.

## Use When
A baking system must detect which entities were destroyed or re-parented between baking passes, and recompute dependent data (e.g., compound bounding boxes when a child is removed).

## Avoid When
Simple single-pass baking without lifecycle tracking — unnecessary complexity. Avoid in the runtime world — ICleanupComponentData without [BakingType] persists into the runtime world and requires explicit removal.

## Senior Pattern
- Struct implementing both ICleanupComponentData and tagged with [BakingType].
- Baking system adds cleanup component to newly baked entities: query WithNone<BoundingBoxCleanup> WithAll<BoundingBox>.
- Destroyed entities: cleanup survives, [BakingType] primary component is removed. Query WithNone<BoundingBox> WithAll<BoundingBoxCleanup> catches them.
- Re-parented entities: compare stored Parent in cleanup to current Parent component.
- After processing, RemoveComponent the cleanup from destroyed entities to avoid stale accumulation.

## Code Template
```csharp
[BakingType]
public struct BoundingBoxCleanup : ICleanupComponentData
{
    public Entity PreviousParent;
}

[WorldSystemFilter(WorldSystemFilterFlags.BakingSystem)]
public partial struct BoundingBoxLifecycleSystem : ISystem
{
    public void OnUpdate(ref SystemState state)
    {
        // Add cleanup to new entities
        var newQuery = SystemAPI.QueryBuilder()
            .WithAll<BoundingBox>()
            .WithNone<BoundingBoxCleanup>()
            .Build();
        state.EntityManager.AddComponent<BoundingBoxCleanup>(newQuery);

        // Detect destroyed entities (cleanup survives, BoundingBox gone)
        var destroyedEntities = SystemAPI.QueryBuilder()
            .WithAll<BoundingBoxCleanup>()
            .WithNone<BoundingBox>()
            .Build()
            .ToEntityArray(Allocator.Temp);

        foreach (var entity in destroyedEntities)
        {
            var cleanup = state.EntityManager.GetComponentData<BoundingBoxCleanup>(entity);
            // Trigger recompute on previous parent
            TriggerParentRecompute(ref state, cleanup.PreviousParent);
            state.EntityManager.RemoveComponent<BoundingBoxCleanup>(entity);
        }
        destroyedEntities.Dispose();
    }
}
```

## Anti-Patterns
- Not marking the cleanup component [BakingType] — it leaks into the runtime world, entity is never truly destroyed from runtime's perspective.
- Not removing cleanup after processing destroyed entities — stale cleanup accumulates every baking pass, causing false reprocessing and memory growth.
- Using ICleanupComponentData in runtime systems without understanding its semantics — entity appears "alive" to cleanup queries even after DestroyEntity is called.

## Runtime Risks
If [BakingType] is omitted: runtime world contains cleanup components on entities that appear destroyed, causing incorrect system behavior.

## Performance Notes
Cleanup add/remove is proportional to entities destroyed or reparented per baking pass, not total entity count. Cost is low for typical scene editing.

## Architecture Guidance
ICleanupComponentData + [BakingType] is the baking equivalent of an "on-destroy" callback. Use it for hierarchy-aware baking (LOD groups, compound colliders, bounding box hierarchies) where child removal must trigger parent recomputation.

## Related Skills
[[baking-type-component]], [[baking-system]]
