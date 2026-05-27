---
name: ecb-system-timing
description: Select the correct ECBSystem playback boundary (BeginSimulation vs EndSimulation) based on when the structural change result must be visible, and guard both with RequireForUpdate.
tags: [ecb, systems]
---

# ECB System Timing — Begin vs End Simulation

## Intent
Select the correct ECBSystem playback boundary (BeginSimulation vs EndSimulation) based on when the structural change result must be visible, and guard both with RequireForUpdate.

## Use When
Any system that needs deferred structural changes and can tolerate a one-frame-boundary delay. The standard choice for all production ECB usage.

## Avoid When
The structural change must be visible within the same system update — use a manual ECB (Allocator.Temp) with explicit Playback instead. Avoid when running in a custom World without standard ECBSystems — check with RequireForUpdate first.

## Senior Pattern
- In OnCreate: `state.RequireForUpdate<BeginSimulationEntityCommandBufferSystem.Singleton>()` — both a safety guard and a dependency declaration.
- In OnUpdate: `var ecbSingleton = SystemAPI.GetSingleton<BeginSimulationEntityCommandBufferSystem.Singleton>(); var ecb = ecbSingleton.CreateCommandBuffer(state.WorldUnmanaged);`
- BeginSimulation playback: runs before SimulationSystemGroup — structural changes are visible to all simulation systems in the current frame.
- EndSimulation playback: runs after SimulationSystemGroup — structural changes are visible from the next frame's simulation.
- Never cache the ECB reference across frames — the ECBSystem's internal buffer is reset after playback.

## Code Template
```csharp
[BurstCompile]
[UpdateInGroup(typeof(SimulationSystemGroup))]
public partial struct EnemyDestroySystem : ISystem
{
    [BurstCompile]
    public void OnCreate(ref SystemState state)
    {
        state.RequireForUpdate<BeginSimulationEntityCommandBufferSystem.Singleton>();
        state.RequireForUpdate<EnemyTag>();
    }

    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var ecb = SystemAPI
            .GetSingleton<BeginSimulationEntityCommandBufferSystem.Singleton>()
            .CreateCommandBuffer(state.WorldUnmanaged);

        foreach (var (health, entity) in
            SystemAPI.Query<RefRO<Health>>().WithEntityAccess())
        {
            if (health.ValueRO.Current <= 0)
                ecb.DestroyEntity(entity);
        }
    }
}
```

## Anti-Patterns
- Using EndSimulation when a spawned entity needs to be queried by simulation systems in the same frame — it won't exist until next frame.
- Using BeginSimulation when a destroyed entity must remain visible to post-simulation systems (e.g., rendering) until the frame ends — it gets destroyed mid-frame.
- Omitting RequireForUpdate on the singleton — GetSingleton throws in custom worlds or test environments.
- Caching the ECB reference as a system struct field — after playback the buffer is invalid, next frame access is undefined behaviour.

## Runtime Risks
- Missing RequireForUpdate: InvalidOperationException on GetSingleton in worlds that don't bootstrap standard ECBSystems.
- Cached ECB across frames: writing to an invalidated buffer — silent data corruption or safety exception.

## Performance Notes
ECBSystems batch all commands from all contributing systems and play them back in one structural change pass — cheaper than N independent Playback calls. CreateCommandBuffer is cheap (returns a view into the pre-allocated ECBSystem buffer).

## Architecture Guidance
- BeginSimulation = setup, spawning, state transitions that simulation systems must react to this frame.
- EndSimulation = cleanup, destruction, post-simulation bookkeeping.
- Default choice: BeginSimulation. Switch to EndSimulation only when explicit end-of-frame semantics are required.

## Related Skills
[[entity-command-buffer]], [[require-for-update-gate]]
