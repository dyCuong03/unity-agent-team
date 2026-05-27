---
name: wave5-isystem-start-stop
description: Implement one-shot ECS initialization and cleanup using ISystemStartStop.OnStartRunning and OnStopRunning, which fire once per enable/disable cycle rather than every frame.
tags: [systems]
---

# ISystemStartStop — One-Shot Init and Cleanup

## Intent
Implement one-shot ECS initialization and cleanup using ISystemStartStop.OnStartRunning and OnStopRunning, which fire once per enable/disable cycle rather than every frame.

## Use When
- One-time init that depends on ECS components being present (initial velocity, cached handles)
- Cleanup when system conditions are no longer met (reset state, release resources)
- Avoiding a bool firstFrame guard in OnUpdate

## Avoid When
- Work must run every frame — use OnUpdate
- System never toggles enabled/disabled — OnCreate or OnUpdate with a guard is simpler

## Senior Pattern
```csharp
[BurstCompile]
public partial struct InitializeBodySystem : ISystem, ISystemStartStop
{
    public void OnCreate(ref SystemState state)
    {
        // Gate on InitialVelocity + PhysicsVelocity both present:
        state.RequireForUpdate(
            SystemAPI.QueryBuilder()
                .WithAll<InitialVelocity, PhysicsVelocity>()
                .Build());
    }

    // Fires once when RequireForUpdate conditions first become true
    // (and again each time conditions toggle false → true):
    public void OnStartRunning(ref SystemState state)
    {
        foreach (var (initial, vel) in
            SystemAPI.Query<RefRO<InitialVelocity>, RefRW<PhysicsVelocity>>())
        {
            vel.ValueRW.Linear  = initial.ValueRO.Linear;
            vel.ValueRW.Angular = initial.ValueRO.Angular;
        }
    }

    // Required even if empty — interface mandates both methods:
    public void OnStopRunning(ref SystemState state) { }

    [BurstCompile]
    public void OnUpdate(ref SystemState state) { }
}
```

## Anti-Patterns
- Using OnStartRunning for work that must happen every frame — fires only on enable transition, not every frame.
- Not implementing OnStopRunning even when empty — compile error; ISystemStartStop interface requires both methods.
- Assuming OnStartRunning fires only once ever — fires again each time system toggles disabled→enabled (RequireForUpdate query goes empty→non-empty multiple times).
- Marking OnStartRunning or OnStopRunning with [BurstCompile] — these are managed interface methods; Burst cannot compile them.

## Runtime Risks
- If RequireForUpdate conditions fluctuate rapidly, OnStartRunning fires multiple times — ensure initialization is idempotent if truly once-ever is required.
- OnStartRunning is not Burst-compiled — avoid tight loops or heavy computation; schedule a job if needed.

## Performance Notes
- Zero per-frame cost during normal enabled operation — fires only on enable/disable transitions.
- Suitable for caching component type handles, registering with external systems, or applying one-shot physics state.

## Architecture Guidance
- Standard use: apply initial physics state (see physics-velocity-force-application), cache expensive results, register with managed systems.
- Pair with RequireForUpdate to control the enable trigger — OnStartRunning fires when the gate opens.
- For truly once-ever initialization, add a tag component in OnStartRunning and query WithNone<InitializedTag> in OnCreate's RequireForUpdate.

## Related Skills
[[require-for-update-gate]], [[isystem-burst-compile]], [[wave5-physics-velocity-force-application]], [[icleanupcomponentdata-runtime]]
