---
name: wave5-fixed-step-simulation-system-group
description: Schedule physics-affecting and fixed-rate simulation systems inside FixedStepSimulationSystemGroup with correct ordering relative to PhysicsSystemGroup and its sub-groups.
tags: [physics, systems]
---

# Fixed-Step Simulation System Group — Physics Ordering

## Intent
Schedule physics-affecting and fixed-rate simulation systems inside FixedStepSimulationSystemGroup with correct ordering relative to PhysicsSystemGroup and its sub-groups.

## Use When
- Any system writes PhysicsVelocity, PhysicsCollider, or other physics state for the physics solver
- Simulation logic that must run at a fixed timestep regardless of render frame rate
- Reading physics solver results (collision events, contact data) after the solver completes

## Avoid When
- System is rendering-dependent (visual effects, camera) — use SimulationSystemGroup or PresentationSystemGroup
- System reads physics results but doesn't affect physics — can run in SimulationSystemGroup after completing physics dependency

## Senior Pattern
```csharp
// Pre-solve forces — run before physics world is built and solved:
[UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]
[UpdateBefore(typeof(PhysicsSystemGroup))]
[BurstCompile]
public partial struct PreSolveForceSystem : ISystem { ... }

// Post-solve event processing — run after solver emits events:
[UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]
[UpdateAfter(typeof(PhysicsSimulationGroup))]   // PhysicsSimulationGroup, NOT PhysicsSystemGroup
[BurstCompile]
public partial struct PostSolveEventSystem : ISystem { ... }
```

Execution order inside FixedStepSimulationSystemGroup:
```
→ [UpdateBefore(PhysicsSystemGroup)]         ← custom force/impulse systems
→ PhysicsSystemGroup
    → PhysicsBuildWorldGroup                 ← builds collision world from transforms + colliders
    → PhysicsSimulationGroup                 ← runs solver, emits trigger/collision events
→ [UpdateAfter(PhysicsSimulationGroup)]      ← event processing (trigger/collision results)
```

## Anti-Patterns
- [UpdateAfter(PhysicsSystemGroup)] for event processing — PhysicsSystemGroup encompasses build+simulation+cleanup; use PhysicsSimulationGroup for reading solver results before cleanup.
- SystemAPI.Time.DeltaTime inside fixed-step group — equivalent to fixedDeltaTime but using fixedDeltaTime makes intent explicit.
- Expensive structural changes (ECB playback) inside the fixed loop — archetype churn causes broad-phase rebuild overhead; defer to SimulationSystemGroup if possible.
- Placing event-response systems in SimulationSystemGroup (render rate) when they must respond to per-physics-tick events — may miss ticks when fixed loop runs twice per render frame.

## Runtime Risks
- FixedStepSimulationSystemGroup may run 0 or 2+ times per render frame during frame rate fluctuations — do not count on exactly once per frame; do not accumulate render-frame-relative state.
- Systems [UpdateAfter(PhysicsSimulationGroup)] still run inside the fixed-step loop — they run once per physics tick, not once per render frame.

## Performance Notes
- Default fixed rate: 50 Hz (0.02s); configurable via FixedStepSimulationSystemGroup.Timestep.
- Profile this group independently from the main simulation group — frame spikes often originate from catch-up ticks here.

## Architecture Guidance
- Force application: [UpdateBefore(PhysicsSystemGroup)] in FixedStepSimulationSystemGroup.
- Event processing: [UpdateAfter(PhysicsSimulationGroup)] in FixedStepSimulationSystemGroup.
- Never mix physics-rate and render-rate logic in the same system.
- For render-rate consumers of physics results: write to a snapshot component from the fixed-step system, read the snapshot from a SimulationSystemGroup system.

## Related Skills
[[fixed-step-simulation]], [[wave5-physics-velocity-force-application]], [[wave5-stateful-physics-event-buffers]], [[wave5-physics-world-singleton-queries]]
