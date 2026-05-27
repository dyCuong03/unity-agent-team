---
name: wave8-ecb-system-group-mismatch
description: Identify and fix bugs caused by using an ECB from the wrong system group, resulting in structural change commands executing at the wrong frame boundary.
tags: [ecb, antipattern, debug]
---

# ECB System Group Mismatch — Wrong Playback Timing

## Intent
Identify and fix bugs caused by using an ECB from the wrong system group, resulting in structural change commands executing at the wrong frame boundary.

## Use When
- Diagnosing one-frame-late structural changes, components appearing/disappearing unexpectedly, or ECB playback order bugs
- Code review of any system that records ECB commands to an ECBSystem singleton

## Avoid When
- Using a manually created ECB with explicit Playback — group mismatch only affects ECBSystem-owned buffers, not manual ECBs

## Senior Pattern
```csharp
// WRONG — EndSimulationECBSystem from within FixedStepSimulationSystemGroup:
// Commands play back after SimulationSystemGroup ends (variable rate), not after FixedStep ends
[UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]
public partial struct FixedPhysicsReactionSystem : ISystem
{
    public void OnUpdate(ref SystemState state)
    {
        // Wrong ECB system — playback happens at wrong frame boundary:
        var ecbSystem = SystemAPI.GetSingleton<EndSimulationEntityCommandBufferSystem.Singleton>();
        var ecb = ecbSystem.CreateCommandBuffer(state.WorldUnmanaged);
    }
}

// CORRECT — use the ECB system matching the enclosing group:
[UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]
public partial struct FixedPhysicsReactionSystem : ISystem
{
    public void OnUpdate(ref SystemState state)
    {
        var ecbSystem = SystemAPI.GetSingleton<EndFixedStepSimulationEntityCommandBufferSystem.Singleton>();
        var ecb = ecbSystem.CreateCommandBuffer(state.WorldUnmanaged);
        // Commands play back at end of FixedStepSimulationSystemGroup — correct timing
    }
}
```

## ECB System Selection Guide

| Enclosing System Group | Correct ECB System |
|---|---|
| InitializationSystemGroup | BeginInitializationEntityCommandBufferSystem or EndInitializationEntityCommandBufferSystem |
| SimulationSystemGroup | BeginSimulationEntityCommandBufferSystem or EndSimulationEntityCommandBufferSystem |
| FixedStepSimulationSystemGroup | EndFixedStepSimulationEntityCommandBufferSystem |
| PresentationSystemGroup | EndPresentationEntityCommandBufferSystem |

## Anti-Patterns
- Always using EndSimulationEntityCommandBufferSystem regardless of enclosing group — one-frame-late bugs in FixedStep systems; structural changes visible at wrong simulation tick.
- Mixing Begin and End ECB systems within the same system — playback order ambiguity; both valid individually but inter-system ordering breaks down.
- Using an ECB from a different World — throws InvalidOperationException at playback.
- Forgetting that FixedStepSimulationSystemGroup runs multiple times per rendered frame — using EndSimulation ECB means commands from tick N play back after SimulationSystemGroup, not between tick N and tick N+1.

## Runtime Risks
- Wrong ECB group causes structural changes to apply at the wrong system group boundary — one or more ticks late.
- In FixedStep scenarios, this can produce a one-rendered-frame delay that is difficult to reproduce deterministically (depends on whether the fixed group ran once or twice that frame).
- Silent correctness bug: no exception, just wrong frame-of-effect for spawning, destroying, and component changes.

## Performance Notes
- No performance difference between ECB systems — correctness is the only concern here.
- Wrong ECB system choice does not cause measurable performance impact; it causes logical correctness failures.

## Architecture Guidance
- Hard rule: match ECB system to enclosing system group.
- When the choice is non-obvious (e.g., Begin vs End within the same group), document which ECB system is used and why at the system declaration.
- For systems inside FixedStepSimulationSystemGroup, EndFixedStepSimulationEntityCommandBufferSystem is almost always correct.

## Related Skills
[[ecb-system-timing]], [[wave5-fixed-step-simulation-system-group]], [[wave8-wrong-system-group-fixed-timestep]], [[entity-command-buffer]]
