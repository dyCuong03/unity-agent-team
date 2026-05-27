---
name: enableable-component
description: Toggle a component''s active state without archetype migration, preserving component data while excluding the entity from standard queries until re-enabled.
---

# Enableable Component

## Intent
Toggle a component's active state without archetype migration, preserving component data while excluding the entity from standard queries until re-enabled.

## Use When
Component state that toggles at moderate-to-high frequency (sleeping/awake, visible/invisible, stunned/active). More efficient than AddComponent/RemoveComponent for toggle patterns.

## Avoid When
The state rarely changes (once at spawn or never) — structural change (add/remove) is more readable and has negligible cost at low frequency. Avoid when the disabled component's value should be reset on re-enable — enableable components preserve the last value.

## Senior Pattern
- Component implements both `IComponentData` and `IEnableableComponent`.
- Query sees only enabled entities by default. To iterate all (enabled and disabled): `.WithOptions(EntityQueryOptions.IgnoreComponentEnabledState)`.
- Read/write enable state via `EnabledRefRW<T>` or `EnabledRefRO<T>` in a query.
- From a job without ECB: set `enabledRef.ValueRW = false` directly (safe in IJobEntity).
- From a parallel job via ECB: `ecb.SetComponentEnabled<T>(chunkIndex, entity, false)` with sort key.

## Code Template
```csharp
public struct Sleeping : IComponentData, IEnableableComponent
{
    public float WakeTimer;
}

// Toggle from main thread:
foreach (var (sleeping, entity) in
    SystemAPI.Query<EnabledRefRW<Sleeping>>()
        .WithOptions(EntityQueryOptions.IgnoreComponentEnabledState)
        .WithEntityAccess())
{
    sleeping.ValueRW = ShouldBeAsleep(entity);
}

// Toggle from IJobEntity:
partial struct WakeJob : IJobEntity
{
    public float CurrentTime;
    void Execute(ref Sleeping sleeping, EnabledRefRW<Sleeping> sleepingEnabled)
    {
        if (CurrentTime >= sleeping.WakeTimer)
            sleepingEnabled.ValueRW = false;  // disable = entity is no longer sleeping
    }
}
```

## Query Filter Semantics (IEnableableComponent)
- `WithAll<T>()` — present AND enabled
- `WithDisabled<T>()` — present AND disabled
- `WithNone<T>()` — absent entirely (structural; do NOT use to filter disabled entities)
- `WithPresent<T>()` — present regardless of enabled bit (enabled OR disabled)
- `IgnoreComponentEnabledState` — all entities regardless of bit

## HasComponent vs IsComponentEnabled
- `HasComponent<T>(entity)` returns `true` even when the component is disabled.
- `IsComponentEnabled<T>(entity)` returns the actual enabled bit state.
- Confusing these is a silent correctness bug: `HasComponent` does not tell you whether the behavior is active.

## Anti-Patterns
- Mixing direct EnabledRefRW mutation and ECB.SetComponentEnabled on the same component in the same frame — ordering ambiguity.
- Querying without IgnoreComponentEnabledState when you need to process disabled entities — silently skips them.
- Using enableable component for state that should structurally transition the entity to a different archetype — misses the semantic clarity of archetype-based state.
- Using WithNone<T> to filter out disabled entities — WithNone means "component absent entirely"; use WithDisabled<T>.
- Using HasComponent<T> to check if behavior is active — use IsComponentEnabled<T> instead.

## Runtime Risks
- SetComponentEnabled via ECB in parallel job without sort key: non-deterministic enable order.
- Querying without IgnoreComponentEnabledState and expecting to see disabled entities: entities silently absent from results.

## Performance Notes
- SetComponentEnabled is O(1) per entity, no chunk move. Dramatically cheaper than AddComponent/RemoveComponent.
- Disabled entities remain in their chunk — chunk fragmentation does not occur.
- For high-frequency toggles (every frame on many entities), enableable component is always the right choice over structural change.

## Architecture Guidance
- Toggle frequency → enableable component.
- Rare structural transition → add/remove component.
- Per-frame value change → plain field on component.

This is the canonical decision tree for ECS state mutation patterns.

## Related Skills
[[wave6-ecs-state-machine-design]], [[wave6-enabled-ref-rw-in-job]], [[wave6-with-disabled-query-filter]], [[wave6-ecb-set-component-enabled]], [[wave6-zero-data-enableable-signal]]
