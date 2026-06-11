---
name: wave6-is-component-enabled-check
description: Check the current enabled state of an IEnableableComponent on a specific entity using EntityManager.IsComponentEnabled<T>() for imperative main-thread branching.
tags: [enableable]
metadata:
  internal-only: true
  tier: 3
---

# IsComponentEnabled — Main-Thread Enabled State Check

## Intent
Check the current enabled state of an IEnableableComponent on a specific entity using EntityManager.IsComponentEnabled<T>() for imperative main-thread branching.

## Use When
- Main-thread gameplay logic must branch on whether a component is enabled
- Conditional logic reads enabled state before deciding to enable or disable
- Single-entity check before an imperative sequence of SetComponentEnabled calls

## Avoid When
- Inside a parallel job — use EnabledRefRO<T> in IJobEntity.Execute() instead
- Checking every entity in a query — use query filters (WithAll, WithDisabled) instead; much more efficient

## Senior Pattern
```csharp
// Carry pickup/drop logic on main thread:
if (state.EntityManager.IsComponentEnabled<Carry>(playerEntity))
{
    // Player is currently carrying something — drop it
    var carry = state.EntityManager.GetComponentData<Carry>(playerEntity);
    state.EntityManager.SetComponentEnabled<Carry>(carry.Target, false);
    state.EntityManager.SetComponentEnabled<Carry>(playerEntity, false);
}
else
{
    // Find nearest available ball (Carry present but disabled):
    foreach (var (transform, entity) in
        SystemAPI.Query<RefRO<LocalTransform>>()
                 .WithDisabled<Carry>()
                 .WithEntityAccess())
    {
        if (IsNearest(transform.ValueRO.Position))
        {
            state.EntityManager.SetComponentEnabled<Carry>(entity, true);
            break;
        }
    }
}

// In-job form (read-only):
public void Execute(EnabledRefRO<Carry> carryEnabled, ref PickupDecision decision)
{
    decision.ShouldAttempt = !carryEnabled.ValueRO;
}
```

## Anti-Patterns
- Confusing `HasComponent<T>(entity)` with `IsComponentEnabled<T>(entity)` — HasComponent returns `true` even when the component is disabled; IsComponentEnabled returns the actual bit.
- Calling on an entity that does not have the component at all — exception; use `HasComponent<T>` guard if structural presence is uncertain.
- Using IsComponentEnabled in hot per-entity loops — use query filters (WithAll/WithDisabled) for bulk cases; O(1) per entity but unnecessary when query-level filtering can replace it.
- Calling IsComponentEnabled without completing state.Dependency — jobs may still be writing the enabled bit; safety error.

## Runtime Risks
- `HasComponent<T>` and `IsComponentEnabled<T>` are NOT interchangeable: HasComponent answers "is this component structurally present?"; IsComponentEnabled answers "is the behavior bit set?". Confusing them is a silent correctness bug.
- Main-thread read of enabled bit requires no sync point (read-only), but SetComponentEnabled after reading requires Dependency completion.

## Performance Notes
- O(1) bit read per call; main-thread only.
- Avoid in hot loops — prefer query filters for bulk enabled-state decisions.
- For per-job read: use EnabledRefRO<T> parameter in IJobEntity.Execute() — zero overhead, Burst-safe.

## Architecture Guidance
- Main-thread imperative branch: IsComponentEnabled → branch → SetComponentEnabled.
- Bulk filtering: WithAll<T> / WithDisabled<T> query filters — do not call IsComponentEnabled per entity.
- In-job read: EnabledRefRO<T> parameter — Burst-safe, no main-thread call.

## Related Skills
[[enableable-component]], [[wave6-entity-manager-set-component-enabled]], [[wave6-with-disabled-query-filter]], [[wave6-enabled-ref-rw-in-job]]
