---
name: fixed-step-simulation
description: Run a subset of systems at a fixed timestep decoupled from the variable render framerate, ensuring deterministic simulation, correct physics integration, and frame-rate-independent gameplay.
---

# Fixed-Step Simulation

## Intent
Run a subset of systems at a fixed timestep decoupled from the variable render framerate, ensuring deterministic simulation, correct physics integration, and frame-rate-independent gameplay.

## Use When
Physics simulation, game logic that must tick at a known rate (e.g., 30Hz/60Hz), network prediction, deterministic replay. Any system where variable DeltaTime produces wrong results.

## Avoid When
Visual/presentation systems, render-rate interpolation, and UI updates — these should run in SimulationSystemGroup or PresentationSystemGroup at variable rate.

## Senior Pattern
- `[UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]` on the system.
- `SystemAPI.Time.DeltaTime` inside this group returns the fixed delta (not the render delta).
- Systems in this group may run zero or multiple times per render frame (catch-up).
- Fixed-step state read by variable-rate systems requires explicit snapshot/interpolation.

## Code Template
```csharp
[BurstCompile]
[UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]
public partial struct PhysicsIntegrationSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        float fixedDt = SystemAPI.Time.DeltaTime;  // fixed delta, not render delta
        state.Dependency = new IntegrateJob
        {
            DeltaTime = fixedDt
        }.ScheduleParallel(state.Dependency);
    }
}
```

## Anti-Patterns
- Using `SystemAPI.Time.ElapsedTime` in a fixed-step system and assuming it matches wall-clock time — it tracks fixed-step accumulated time, which diverges from render time during catch-up.
- Spawning entities in a fixed-step system and immediately querying them in a render-rate system in the same render frame — the entities may not be visible yet.
- Mixing SystemAPI.Time.DeltaTime from inside FixedStepSimulationSystemGroup with render-rate state — time source mismatch.

## Runtime Risks
- Frame rate drops below fixed rate: multiple fixed steps run per render frame — CPU spike risk.
- Shared state written by fixed-step and read by render-rate systems: torn state visible in the renderer.

## Performance Notes
Zero overhead when frame rate exceeds fixed rate. CPU spike risk when catch-up steps accumulate. Consider fixed-step rate selection relative to expected minimum frame rate.

## Architecture Guidance
Treat fixed-step and variable-step as two separate simulation worlds. Define explicit state handoff points (snapshot buffers, interpolation components) for any data that crosses the boundary.

## Related Skills
[[wave5-fixed-step-simulation-system-group]], [[wave5-physics-velocity-force-application]], [[system-update-order]]
