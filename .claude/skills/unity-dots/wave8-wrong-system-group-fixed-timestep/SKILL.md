---
name: wave8-wrong-system-group-fixed-timestep
description: Identify and fix the failure mode of placing fixed-timestep physics or simulation logic in the wrong system group, causing frame-rate-dependent execution instead of fixed-rate execution.
tags: [systems, antipattern, debug]
metadata:
  internal-only: true
  tier: 3
---

# Wrong System Group — Fixed Timestep Failure Mode

## Intent
Identify and fix the failure mode of placing fixed-timestep physics or simulation logic in the wrong system group, causing frame-rate-dependent execution instead of fixed-rate execution.

## Use When
- Diagnosing why physics behavior is frame-rate dependent or non-deterministic
- Code review of any system that writes PhysicsVelocity, applies forces, or handles collision response

## Avoid When
- The system intentionally runs every rendered frame — SimulationSystemGroup or PresentationSystemGroup are correct for those cases

## Senior Pattern
```csharp
// WRONG — runs every rendered frame, not at fixed timestep:
[UpdateInGroup(typeof(SimulationSystemGroup))]
public partial struct PhysicsResponseSystem : ISystem
{
    public void OnUpdate(ref SystemState state)
    {
        // Applies forces — frame-rate dependent, non-deterministic physics
    }
}

// CORRECT — runs at fixed timestep (default 50Hz):
[UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]
[UpdateBefore(typeof(PhysicsSystemGroup))]
[BurstCompile]
public partial struct PhysicsResponseSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        // Applies forces — deterministic, fixed-rate
    }
}

// CORRECT — set custom fixed rate once at initialization:
[UpdateInGroup(typeof(InitializationSystemGroup))]
public partial class FixedRateBootstrapSystem : SystemBase
{
    protected override void OnCreate()
    {
        World.GetExistingSystemManaged<FixedStepSimulationSystemGroup>().Timestep = 1f / 30f;
        Enabled = false;  // run once
    }
    protected override void OnUpdate() { }
}
```

## Diagnosis Checklist
- System writes PhysicsVelocity or PhysicsMass → must be in FixedStepSimulationSystemGroup
- System reads PhysicsWorldSingleton for queries → can be in SimulationSystemGroup (after physics completes)
- System handles collision/trigger events → must be in FixedStepSimulationSystemGroup [UpdateAfter(PhysicsSimulationGroup)]
- System interpolates for rendering → must be in PresentationSystemGroup

## Anti-Patterns
- Using SimulationSystemGroup for physics force application — frame-rate dependent results; diverges between 30fps debug and 120fps release.
- Placing collision response in PresentationSystemGroup — runs after rendering, one frame late.
- Setting FixedStepSimulationSystemGroup.Timestep every frame in OnUpdate — must be set once at initialization; per-frame mutation disrupts the accumulator.
- Combining physics-rate logic and render-rate logic in the same system — run rates diverge; shared state is torn.

## Runtime Risks
- Systems in the wrong group cause non-deterministic physics, collision tunneling at low frame rates, and gameplay that diverges between debug (low FPS) and release (high FPS) builds.
- FixedStepSimulationSystemGroup may execute 0, 1, or multiple times per rendered frame — systems inside it must not assume single-execution-per-rendered-frame.

## Performance Notes
- Default fixed rate: 50 Hz (0.02s). At 60 FPS render rate, the group runs once most frames and twice occasionally (catch-up).
- Profile FixedStepSimulationSystemGroup independently from SimulationSystemGroup — frame spikes here often indicate physics world rebuild cost from structural changes.

## Architecture Guidance
- Force application + physics write: FixedStepSimulationSystemGroup [UpdateBefore(PhysicsSystemGroup)].
- Physics event processing: FixedStepSimulationSystemGroup [UpdateAfter(PhysicsSimulationGroup)].
- Spatial queries against built world: SimulationSystemGroup.
- Visual interpolation / rendering sync: PresentationSystemGroup.

## Related Skills
[[wave5-fixed-step-simulation-system-group]], [[fixed-step-simulation]], [[wave5-physics-velocity-force-application]], [[wave8-ecb-system-group-mismatch]]
