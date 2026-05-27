---
name: wave6-zero-data-enableable-signal
description: Use a zero-field IEnableableComponent as a single-bit signal between producer and consumer systems, avoiding event queues and DynamicBuffer cleanup overhead.
---

# Zero-Data Enableable Signal — Inter-System Signaling

## Intent
Use a zero-field IEnableableComponent as a single-bit signal between producer and consumer systems, avoiding event queues and DynamicBuffer cleanup overhead.

## Use When
- One system signals another that a condition occurred (repositioning needed, UI dirty, AI alert)
- Signal is boolean (happened / not happened) and carries no data payload
- Producer and consumer are on different systems with defined execution order

## Avoid When
- Signal must carry a data payload — use a separate IComponentData field or DynamicBuffer element
- Multiple independent signals of same type can occur in the same frame — a single bit cannot distinguish count; use DynamicBuffer for counted/multi-signal
- Multiple producers write to the same entity's signal — last write wins; use DynamicBuffer for multi-producer scenarios

## Senior Pattern
```csharp
// Zero-size signal component:
public struct RepositionNeeded : IComponentData, IEnableableComponent { }

// Baker: add signal component (starts disabled):
public override void Bake(TeamAuthoring authoring)
{
    var entity = GetEntity(TransformUsageFlags.None);
    AddComponent<RepositionNeeded>(entity);
    SetComponentEnabled<RepositionNeeded>(entity, false);
}

// Producer system — sets signal:
[UpdateInGroup(typeof(SimulationSystemGroup))]
[BurstCompile]
public partial struct TeamEventSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        foreach (var (teamData, entity) in
            SystemAPI.Query<RefRO<TeamData>>().WithEntityAccess())
        {
            if (teamData.ValueRO.NeedsReposition)
                SystemAPI.SetComponentEnabled<RepositionNeeded>(entity, true);
        }
    }
}

// Consumer system — reacts and MUST clear signal:
[UpdateInGroup(typeof(SimulationSystemGroup))]
[UpdateAfter(typeof(TeamEventSystem))]
[BurstCompile]
public partial struct RepositionSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        foreach (var (transform, entity) in
            SystemAPI.Query<RefRW<LocalTransform>>()
                     .WithAll<RepositionNeeded>()
                     .WithEntityAccess())
        {
            // handle repositioning
            DoReposition(ref transform.ValueRW);

            // MUST clear signal — consumer owns signal clearing:
            SystemAPI.SetComponentEnabled<RepositionNeeded>(entity, false);
        }
    }
}
```

## Anti-Patterns
- Consumer forgetting to disable signal after handling — signal remains enabled and fires every frame indefinitely.
- Missing [UpdateAfter(typeof(ProducerSystem))] on consumer — consumer runs before signal is set; reacts to last frame's signal one frame late.
- Multiple consumers reacting without coordination — both process it; neither clears it correctly; both fire every frame.
- Using a tag component (structural AddComponent) instead of an enableable signal for frequent signals — structural add/remove is 10-100x more expensive.
- Using for multi-count signals ("3 enemies entered this frame") — single bit cannot represent count; use DynamicBuffer<EnemyEnteredEvent>.

## Runtime Risks
- Signal persists until consumer explicitly clears it — if consumer system is disabled or its RequireForUpdate gate closes, signal accumulates indefinitely.
- Signal bit set by multiple producers in the same frame: last SetComponentEnabled call wins (OR semantics not guaranteed) — document single-producer ownership.

## Performance Notes
- Zero struct memory — zero-field IComponentData adds no data cost per entity.
- Single bit in chunk bitmask — producer enable and consumer disable are both O(1).
- No ECB overhead; no DynamicBuffer allocation; no buffer resize.

## Architecture Guidance
- Consumer owns signal clearing — document this ownership explicitly in code comments.
- Enforce ordering with [UpdateAfter(typeof(ProducerSystem))].
- For multiple consumers that must all see the signal: last consumer clears; use a counter component if ordering matters.
- Alternative: if signal carries data, replace with IComponentData field + IEnableableComponent on same struct.

## Related Skills
[[enableable-component]], [[wave6-enabled-ref-rw-in-job]], [[wave6-entity-manager-set-component-enabled]], [[wave6-ecs-state-machine-design]], [[tag-component]]
