---
name: baker-authoring-conversion
description: Convert designer-facing MonoBehaviour authoring data into unmanaged ECS components at subscene import time, with zero runtime conversion overhead.
tags: [core, baking, hybrid]
---

# Baker and Authoring Conversion

## Intent
Convert designer-facing MonoBehaviour authoring data into unmanaged ECS components at subscene import time, with zero runtime conversion overhead.

## Use When
Any ECS entity that originates from a Unity scene or prefab. All runtime components with inspector-configurable parameters require a Baker.

## Avoid When
Runtime-only entities created entirely by code (e.g., spawned from a prefab) — no Baker needed for the spawned instance, only for the prefab source entity.

## Senior Pattern
- Declare a public MonoBehaviour (`XyzAuthoring`) with inspector-visible fields.
- Nest a private `class Baker : Baker<XyzAuthoring>` inside it.
- In `Bake()`: call `GetEntity(TransformUsageFlags.X)` to obtain the entity, then `AddComponent(entity, new XyzComponent { ... })`.
- Convert editor units to runtime units at bake time (e.g., degrees → radians).
- For prefab entity references: `GetEntity(authoring.PrefabField, TransformUsageFlags.Dynamic)`.
- Use `TransformUsageFlags.Dynamic` for moving entities, `TransformUsageFlags.None` for static/data-only entities.

## Code Template
```csharp
public class EnemyAuthoring : MonoBehaviour
{
    public float MoveSpeedDegreesPerSecond = 90f;
    public GameObject ProjectilePrefab;

    class Baker : Baker<EnemyAuthoring>
    {
        public override void Bake(EnemyAuthoring authoring)
        {
            var entity = GetEntity(TransformUsageFlags.Dynamic);
            AddComponent(entity, new EnemyMoveSpeed
            {
                RadiansPerSecond = math.radians(authoring.MoveSpeedDegreesPerSecond)
            });
            AddComponent(entity, new EnemyProjectileRef
            {
                Prefab = GetEntity(authoring.ProjectilePrefab, TransformUsageFlags.Dynamic)
            });
        }
    }
}
```

## Anti-Patterns
- Doing unit conversion at runtime in OnUpdate instead of at bake time — wasted per-frame cost.
- Forgetting TransformUsageFlags.Dynamic on an entity that moves — missing LocalTransform at runtime, silent wrong behavior.
- Not calling GetEntity for a referenced prefab GameObject — the prefab won't be baked into an entity prefab reference.
- Storing state on the Baker instance — Baker is stateless per-bake, state is discarded after each call.
- Calling Resources.Load or doing file I/O inside Bake — baking must be deterministic and dependency-tracked.

## Runtime Risks
- Missing TransformUsageFlags.Dynamic: entity has no LocalTransform, transform system skips it, entity doesn't move.
- Unbaked prefab reference: entity field holds Entity.Null at runtime, causing silent spawn failures.

## Performance Notes
Baker runs only at import time (or on re-import due to asset change). Zero runtime cost. Subscene data is loaded directly from disk — no re-baking at runtime.

## Architecture Guidance
Baker is the sole bridge between the authoring world and the runtime world. Keep it simple — one Baker per authoring MonoBehaviour. Do all unit/format conversions here. Never let authoring types leak into runtime systems.
