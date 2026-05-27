---
name: wave6-entity-manager-set-component-enabled
description: Immediately enable or disable an IEnableableComponent on one entity or all entities matching a query using EntityManager.SetComponentEnabled or SystemAPI.SetComponentEnabled on the main thread.
---

# EntityManager.SetComponentEnabled — Immediate Main-Thread Toggle

## Intent
Immediately enable or disable an IEnableableComponent on one entity or all entities matching a query using EntityManager.SetComponentEnabled or SystemAPI.SetComponentEnabled on the main thread.

## Use When
- Immediate state change needed on main thread (no deferred overhead, no one-frame delay)
- Batch enable/disable of all entities matching a query in a single call
- Imperative gameplay logic that must branch and change enabled state in the same frame

## Avoid When
- Inside a parallel job — use ECB.SetComponentEnabled or EnabledRefRW<T>
- Inside a foreach iterating the same entities — invalidates query iterator mid-iteration; use ECB to defer

## Senior Pattern
```csharp
// Single entity (immediate):
SystemAPI.SetComponentEnabled<ActiveBehavior>(entity, true);

// Batch query (all entities matching query, immediate — O(chunks) not O(entities)):
EntityQuery spinQuery = SystemAPI.QueryBuilder().WithAll<Spin>().Build();
state.EntityManager.SetComponentEnabled<Spin>(spinQuery, false);

// Conditional branch using IsComponentEnabled (not HasComponent):
if (state.EntityManager.IsComponentEnabled<Carry>(playerEntity))
{
    // drop carried object
    var carry = state.EntityManager.GetComponentData<Carry>(playerEntity);
    state.EntityManager.SetComponentEnabled<Carry>(carry.Target, false);
    state.EntityManager.SetComponentEnabled<Carry>(playerEntity, false);
}
else
{
    // pick up nearest available ball
    foreach (var (_, entity) in
        SystemAPI.Query<RefRO<LocalTransform>>()
                 .WithDisabled<Carry>()
                 .WithEntityAccess())
    {
        state.EntityManager.SetComponentEnabled<Carry>(entity, true);
        break;
    }
}
```

## Anti-Patterns
- Calling SetComponentEnabled inside a foreach iterating the same entity — modifies chunk bitmask mid-iteration; causes iterator corruption; always use ECB to defer.
- Calling without completing state.Dependency first — jobs may still be reading/writing the component; triggers safety error.
- Calling on an entity that does not have the component — exception; use HasComponent guard if uncertain.
- Using HasComponent<T> to check if behavior is active — use IsComponentEnabled<T>; HasComponent returns true even when disabled.

## Runtime Risks
- IsComponentEnabled and HasComponent are different: `HasComponent<T>(entity)` returns `true` even when disabled; `IsComponentEnabled<T>(entity)` returns the actual bit state.
- Main-thread SetComponentEnabled causes a sync point if jobs have the component in their dependency chain — complete Dependency first.

## Performance Notes
- Per-entity call: O(1) bit flip.
- Per-query batch: O(chunks) — no per-entity loop; fastest path for bulk main-thread enable/disable.
- No archetype migration — cheaper than EntityManager.AddComponent/RemoveComponent.

## Architecture Guidance
- Main-thread imperative logic: EntityManager.SetComponentEnabled or SystemAPI.SetComponentEnabled.
- Parallel job same-entity: EnabledRefRW<T>.
- Parallel job cross-entity or deferred: ECB.SetComponentEnabled with [ChunkIndexInQuery] sort key.
- Always call `state.Dependency.Complete()` or ensure dependency is completed before main-thread SetComponentEnabled in a system.

## Related Skills
[[enableable-component]], [[wave6-ecb-set-component-enabled]], [[wave6-enabled-ref-rw-in-job]], [[wave6-is-component-enabled-check]], [[wave6-with-disabled-query-filter]]
