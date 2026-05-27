---
name: isystem-burst-compile
description: Implement a system as an unmanaged struct with Burst-compiled entry points to eliminate managed dispatch overhead and enable native code generation on the hot update path.
tags: [core, systems, burst]
---

# ISystem with BurstCompile

## Intent
Implement a system as an unmanaged struct with Burst-compiled entry points to eliminate managed dispatch overhead and enable native code generation on the hot update path.

## Use When
Any new system that does not require managed types (MonoBehaviour references, strings, class components). This is the default system type in Entities 1.x.

## Avoid When
The system must access managed components, drive MonoBehaviour/GameObject state, or interoperate with managed Unity APIs. Use SystemBase only in those cases.

## Senior Pattern
- `public partial struct MySystem : ISystem` — partial required for source generation.
- [BurstCompile] on OnCreate, OnUpdate, OnDestroy.
- All ECS access via `ref SystemState state` parameter.
- Persistent frame-to-frame state stored as struct fields (e.g., cached EntityQuery, counter).
- No managed fields anywhere in the struct.

## Code Template
```csharp
[BurstCompile]
[UpdateInGroup(typeof(SimulationSystemGroup))]
public partial struct MovementSystem : ISystem
{
    private EntityQuery m_MovingQuery;

    [BurstCompile]
    public void OnCreate(ref SystemState state)
    {
        m_MovingQuery = SystemAPI.QueryBuilder()
            .WithAll<Velocity, LocalTransform>()
            .Build();
        state.RequireForUpdate(m_MovingQuery);
    }

    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        float dt = SystemAPI.Time.DeltaTime;
        foreach (var (transform, vel) in
            SystemAPI.Query<RefRW<LocalTransform>, RefRO<Velocity>>())
        {
            transform.ValueRW.Position += vel.ValueRO.Value * dt;
        }
    }

    [BurstCompile]
    public void OnDestroy(ref SystemState state) { }
}
```

## Anti-Patterns
- Storing a managed reference (List<T>, string, class instance) as a struct field — compile error.
- Calling Debug.Log, Object.FindObjectOfType, or any managed API inside a [BurstCompile] method — silently falls back to managed execution for that call site.
- Treating ISystem as a class with inheritance — it is a value type; no virtual dispatch, no base class.
- Calling state.EntityManager.CompleteAllTrackedJobs() as a workaround instead of properly chaining state.Dependency.

## Runtime Risks
- Non-Burst-safe call inside [BurstCompile] method: Burst silently removes the [BurstCompile] guarantee for that code path.
- Mutable struct fields shared across two copies of the system struct: divergence if the ECS runtime moves the struct.

## Performance Notes
Struct system = zero heap allocation for system state. Burst entry points eliminate JIT overhead. Prefer over SystemBase for all simulation code.

## Architecture Guidance
Systems are stateless by default. Add struct fields only for cached queries and counters — not for gameplay state (that belongs on components).
