---
name: singleton-access
description: Access a globally unique configuration or state entity in O(1) time without query overhead, using GetSingleton / GetSingletonRW / GetSingletonEntity.
tags: [core, singleton]
---

# Singleton Access

## Intent
Access a globally unique configuration or state entity in O(1) time without query overhead, using GetSingleton / GetSingletonRW / GetSingletonEntity.

## Use When
Config data, prefab entity handles, ECB system references, or any world-global state that is guaranteed to have exactly one entity. Pair with RequireForUpdate as a precondition gate.

## Avoid When
There may legitimately be zero or more than one entity with the component — use a regular query instead. Avoid GetSingletonRW when you only read the value — unnecessary dirty marking.

## Senior Pattern
- Read-only access: `SystemAPI.GetSingleton<T>()` — returns a copy.
- Writable access: `SystemAPI.GetSingletonRW<T>()` — returns RefRW, marks component dirty for change filtering.
- Entity reference: `SystemAPI.GetSingletonEntity<T>()` — returns the entity handle.
- Gate with `state.RequireForUpdate<T>()` in OnCreate to prevent runtime exceptions when the entity does not yet exist.

## Code Template
```csharp
// OnCreate gate:
state.RequireForUpdate<GameConfig>();

// OnUpdate read-only:
var config = SystemAPI.GetSingleton<GameConfig>();
float speed = config.PlayerSpeed;

// OnUpdate read-write:
var configRW = SystemAPI.GetSingletonRW<GameConfig>();
configRW.ValueRW.Score += 10;

// Get the entity itself:
var configEntity = SystemAPI.GetSingletonEntity<GameConfig>();
```

## Anti-Patterns
- Calling GetSingleton without RequireForUpdate — throws if the entity hasn't been created yet.
- Using GetSingletonRW when the value is only read — causes unnecessary change filter invalidation.
- Creating a second entity with the same singleton component — GetSingleton throws at runtime, difficult to debug.
- Storing the returned struct copy and mutating it without writing back — changes are lost.

## Runtime Risks
- Multiple entities with the singleton component: exception on GetSingleton.
- Missing RequireForUpdate: exception before the entity is created during world initialization.
- Storing a cached RefRW across frames — the reference may be invalidated by structural changes.

## Performance Notes
O(1) lookup. GetSingleton is faster than any query iteration. Prefer over a 1-entity query loop.

## Architecture Guidance
Singletons are the ECS equivalent of global config. Use them for scene-level configuration, prefab catalogs, and ECB system handles. Enforce uniqueness by construction (only one baker or spawning system creates the entity).
