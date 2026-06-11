---
name: tag-component
description: Mark entity membership in a logical group or boolean state without storing any data, enabling query-level dispatch with zero chunk overhead.
tags: [core, components]
metadata:
  internal-only: true
  tier: 3
---

# Tag Component

## Intent
Mark entity membership in a logical group or boolean state without storing any data, enabling query-level dispatch with zero chunk overhead.

## Use When
Boolean, infrequently-changing state that drives which systems include or exclude an entity. Scene activation, feature flags, event signals, state labels.

## Avoid When
The state changes every frame or many times per second — structural change cost is non-trivial at high frequency. Use IEnableableComponent instead.

## Senior Pattern
- Empty struct implementing IComponentData.
- Add/remove via ECB, never during iteration.
- Use RequireForUpdate<T> to gate systems on tag presence.
- Use WithAll<T>/WithNone<T> in queries to filter on tag.

## Code Template
```csharp
public struct IsActiveEnemy : IComponentData { }

// Gate a system on tag existence:
state.RequireForUpdate<IsActiveEnemy>();

// Filter query — only entities that have IsActiveEnemy:
foreach (var transform in
    SystemAPI.Query<RefRW<LocalTransform>>().WithAll<IsActiveEnemy>())
{ }

// Add via ECB (safe from job):
ecb.AddComponent<IsActiveEnemy>(entity);
```

## Anti-Patterns
- Adding and removing a tag every frame on many entities — causes per-frame archetype migrations and chunk allocations.
- Using a tag where the actual state needs a value — unnecessary structural change when a field on an existing component would do.
- Checking tag presence via EntityManager.HasComponent in a per-entity loop — use query filters instead.

## Runtime Risks
- High-frequency add/remove of tags on large entity populations: archetype churn, chunk fragmentation, GC pressure from chunk reallocation.

## Performance Notes
- Zero bytes in chunk. Adding the tag moves the entity to a different archetype chunk — one-time cost per transition.
- Query filter on tag presence is O(archetypes), not O(entities).

## Architecture Guidance
Tags represent stable states with infrequent transitions. Design entity lifecycles around a small number of meaningful archetype states, not a high-churn tag soup.
