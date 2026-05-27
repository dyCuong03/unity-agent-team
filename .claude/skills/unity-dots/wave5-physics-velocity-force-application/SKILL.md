---
name: wave5-physics-velocity-force-application
description: Apply forces and impulses to Unity Physics dynamic bodies by writing PhysicsVelocity from systems scheduled in FixedStepSimulationSystemGroup before PhysicsSystemGroup.
tags: [physics]
---

# Physics Velocity and Force Application

## Intent
Apply forces and impulses to Unity Physics dynamic bodies by writing PhysicsVelocity from systems scheduled in FixedStepSimulationSystemGroup before PhysicsSystemGroup.

## Use When
- Continuous forces (gravity well, wind, magnetic attraction) on dynamic rigid bodies
- Setting initial velocity on spawned physics bodies
- Impulses (explosions, projectile hits) on dynamic bodies

## Avoid When
- Moving kinematic bodies — write LocalTransform directly; PhysicsVelocity is ignored for kinematics
- Applying forces in SimulationSystemGroup (variable rate) — always use FixedStepSimulationSystemGroup

## Senior Pattern
```csharp
[UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]
[UpdateBefore(typeof(PhysicsSystemGroup))]
[BurstCompile]
public partial struct ForceSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        state.Dependency = new ApplyForceJob
        {
            DeltaTime = SystemAPI.Time.fixedDeltaTime,
            WellPosition = SystemAPI.GetSingleton<GravityWell>().Position
        }.ScheduleParallel(state.Dependency);
    }
}

[BurstCompile]
public partial struct ApplyForceJob : IJobEntity
{
    public float DeltaTime;
    public float3 WellPosition;

    [BurstCompile]
    public void Execute(ref PhysicsVelocity velocity, in PhysicsMass mass, in LocalTransform transform)
    {
        // Guard: mass.InverseMass == 0 for static/infinite-mass bodies
        if (mass.InverseMass == 0f) return;

        float3 dir = math.normalize(WellPosition - transform.Position);
        velocity.Linear += dir * (1f / mass.InverseMass) * DeltaTime;
    }
}

// One-shot initial velocity via ISystemStartStop:
public void OnStartRunning(ref SystemState state)
{
    foreach (var (initial, vel) in SystemAPI.Query<RefRO<InitialVelocity>, RefRW<PhysicsVelocity>>())
    {
        vel.ValueRW.Linear = initial.ValueRO.Linear;
        vel.ValueRW.Angular = initial.ValueRO.Angular;
    }
}
```

## Anti-Patterns
- Placing force systems in SimulationSystemGroup — variable rate, not fixed timestep, produces jitter and frame-rate-dependent physics.
- Writing LocalTransform to teleport a physics body — physics broad/narrow phase data is stale; body jumps but collision detection has a gap.
- Using SystemAPI.Time.DeltaTime inside FixedStepSimulationSystemGroup instead of fixedDeltaTime — same value at runtime but intent is wrong; use fixedDeltaTime explicitly.
- Dividing by InverseMass without guarding zero — static bodies have InverseMass == 0; division produces NaN velocity.

## Runtime Risks
- PhysicsMass.InverseMass == 0 for static (infinite-mass) bodies — always guard before force calculations.
- PhysicsVelocity.ApplyExplosionForce is a convenience extension — correct but has more per-call cost than simple velocity.Linear += for tight loops.

## Performance Notes
- ScheduleParallel over physics entities scales with body count.
- Profile FixedStepSimulationSystemGroup separately from the render-rate group — it may run 0 or 2+ times per render frame.

## Architecture Guidance
- Pre-solve forces: [UpdateBefore(PhysicsSystemGroup)] in FixedStepSimulationSystemGroup.
- Post-solve event processing: [UpdateAfter(PhysicsSimulationGroup)] in FixedStepSimulationSystemGroup.
- Initial velocity (one-shot): use ISystemStartStop.OnStartRunning paired with RequireForUpdate on InitialVelocity query.

## Related Skills
[[wave5-fixed-step-simulation-system-group]], [[isystem-start-stop]], [[wave5-physics-world-singleton-queries]], [[fixed-step-simulation]]
