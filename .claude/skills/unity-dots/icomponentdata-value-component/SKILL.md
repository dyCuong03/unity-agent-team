---
name: icomponentdata-value-component
description: Store per-entity state as an unmanaged, cache-coherent struct that ECS can lay out contiguously in archetype chunks.
tags: [core, components, data-layout]
metadata:
  internal-only: true
  tier: 3
---

# IComponentData Value Component

## Intent
Store per-entity state as an unmanaged, cache-coherent struct that ECS can lay out contiguously in archetype chunks.

## Use When
Any per-entity data that is blittable (numbers, float3, bool, enums, nested blittable structs). This is the default component type.

## Avoid When
The data contains managed references (string, object, List<T>, UnityEngine.Object). Use managed IComponentData (bridge-only pattern) in that case only.

## Senior Pattern
- Declare a public struct implementing IComponentData.
- Fields must be blittable value types only.
- Size to the minimum required for one concern — split unrelated data into separate components.
- Mark read-only accesses with `in` or `RefRO<T>` in query/job signatures to prevent false write dependencies.

## Code Template
```csharp
public struct Health : IComponentData
{
    public int Current;
    public int Max;
}

// Read-only access in query:
foreach (var (transform, health) in
    SystemAPI.Query<RefRW<LocalTransform>, RefRO<Health>>())
{
    // transform.ValueRW — write; health.ValueRO — read only
}
```

## Anti-Patterns
- Adding a string, List<T>, or any managed field — silently breaks Burst compatibility and loses chunk layout guarantees.
- Packing unrelated fields into one large component — inflates struct size, reduces entities-per-chunk, hurts cache.
- Mutating component data via EntityManager.GetComponentData in a loop — defeats chunk-coherent access.

## Runtime Risks
- Managed field: Burst compile error or silent fallback to managed execution.
- Oversized struct (>64 bytes): measurably fewer entities per chunk, higher cache miss rate.
- Missing `in`/`RefRO` on read-only access: serialises jobs that could safely run in parallel.

## Performance Notes
- Tag components (zero fields) occupy zero bytes in chunk — use freely for boolean state.
- Struct size directly controls entities-per-chunk. 128-byte structs hold 16x fewer entities than 8-byte components.
- SIMD-friendly if data is contiguous and access is sequential.

## Architecture Guidance
Component owns data, system owns logic. Never add methods that mutate state to a component struct. One component = one concern.
