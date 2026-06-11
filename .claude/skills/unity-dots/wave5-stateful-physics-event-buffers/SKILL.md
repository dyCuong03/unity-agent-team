---
name: wave5-stateful-physics-event-buffers
description: Detect Enter, Stay, and Exit states for trigger and collision events using Unity Physics''s built-in stateful event buffer systems, which maintain per-entity DynamicBuffer<StatefulTriggerEvent>.
tags: [physics]
metadata:
  internal-only: true
  tier: 3
---

# Stateful Physics Event Buffers

## Intent
Detect Enter, Stay, and Exit states for trigger and collision events using Unity Physics's built-in stateful event buffer systems, which maintain per-entity DynamicBuffer<StatefulTriggerEvent>.

## Use When
- Trigger zones (enter/exit): pickups, portals, damage volumes
- Collision events with Enter/Stay/Exit semantics: landing detection, impact response

## Avoid When
- Only "something is overlapping this frame" is needed — use SimulationSingleton.ScheduleCallbacks directly (cheaper, stateless)
- Event count is very high (>10,000/frame) — the clear+collect+convert chain adds per-frame overhead

## Setup Requirements
- Add StatefulTriggerEventBufferAuthoring component to entities needing trigger event tracking.
- Set PhysicsShapeAuthoring Collision Response = "Raise Trigger Events" on the trigger collider.
- Unity Physics includes StatefulTriggerEventBufferSystem and StatefulCollisionEventBufferSystem built-in.

## Senior Pattern
```csharp
[UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]
[UpdateAfter(typeof(StatefulTriggerEventBufferSystem))]
[BurstCompile]
public partial struct TriggerZoneSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        state.Dependency = new ProcessTriggerJob().ScheduleParallel(state.Dependency);
    }
}

[BurstCompile]
public partial struct ProcessTriggerJob : IJobEntity
{
    [BurstCompile]
    public void Execute(ref TriggerZoneState zone,
                        in DynamicBuffer<StatefulTriggerEvent> events)
    {
        for (int i = 0; i < events.Length; i++)
        {
            switch (events[i].State)
            {
                case StatefulEventState.Enter: zone.EnteredCount++; break;
                case StatefulEventState.Exit:  zone.EnteredCount--; break;
                // StatefulEventState.Stay: fires every frame overlap persists — handle if needed
            }
        }
    }
}
```

Event states:
- StatefulEventState.Enter — first frame of overlap
- StatefulEventState.Stay — overlap continues (fires every frame)
- StatefulEventState.Exit — first frame overlap ends

## Anti-Patterns
- Reading DynamicBuffer<StatefulTriggerEvent> before StatefulTriggerEventBufferSystem runs — empty buffer; always [UpdateAfter(StatefulTriggerEventBufferSystem)].
- Forgetting StatefulTriggerEventBufferAuthoring — no buffer is created; events silently dropped.
- Not filtering by ev.State == Enter — Stay events fire every frame overlap persists; unguarded code fires every frame.
- Accessing buffer elements across frames — buffer is cleared and rebuilt every fixed tick.

## Runtime Risks
- Buffer cleared every fixed tick — do not cache references to buffer elements across frames.
- StatefulTriggerEventExclude component on an entity suppresses event collection — use for performance optimization on high-frequency entities that don't need state tracking.
- Both entities in a trigger pair receive events — guard against double-processing in symmetric handlers.

## Performance Notes
- Clear is parallel; collection and conversion are sequential — three-job chain per fixed tick.
- Group trigger-zone entities in same archetype for buffer cache locality.
- For very high event counts, prefer stateless SimulationSingleton.ScheduleCallbacks.

## Architecture Guidance
- Event detection: FixedStepSimulationSystemGroup [UpdateAfter(StatefulTriggerEventBufferSystem)].
- Gameplay responses (VFX, audio via hybrid bridge): SimulationSystemGroup reading snapshot results from fixed step.
- Collision events: same pattern with StatefulCollisionEventBufferSystem / DynamicBuffer<StatefulCollisionEvent>.

## Related Skills
[[wave5-fixed-step-simulation-system-group]], [[wave5-physics-velocity-force-application]], [[icleanupcomponentdata-runtime]], [[enableable-component]]
