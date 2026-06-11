---
name: wave6-ecb-set-component-enabled
description: Record a deferred enable/disable command for an IEnableableComponent from a parallel job using ECB.SetComponentEnabled<T>() with a deterministic sort key.
tags: [enableable, ecb]
metadata:
  internal-only: true
  tier: 3
---

# ECB.SetComponentEnabled — Deferred Parallel Enable/Disable

## Intent
Record a deferred enable/disable command for an IEnableableComponent from a parallel job using ECB.SetComponentEnabled<T>() with a deterministic sort key.

## Use When
- Parallel IJobEntity or IJobChunk must conditionally enable/disable based on computed per-entity logic
- The target entity is different from the entity being iterated (cross-entity enable/disable)
- EnabledRefRW is not available because the component is on a different entity

## Avoid When
- Toggle can happen on main thread immediately — use EntityManager.SetComponentEnabled (no deferred overhead)
- EnabledRefRW can be used inline on the same entity — cheaper, no one-frame delay

## Senior Pattern
```csharp
[BurstCompile]
public partial struct ActivateInRangeJob : IJobEntity
{
    public EntityCommandBuffer.ParallelWriter Ecb;
    public float3 Origin;
    public float RadiusSq;

    [BurstCompile]
    public void Execute(
        [ChunkIndexInQuery] int chunkIndex,
        Entity entity,
        in LocalTransform transform)
    {
        bool inRange = math.distancesq(transform.Position, Origin) <= RadiusSq;
        Ecb.SetComponentEnabled<ActiveBehavior>(chunkIndex, entity, inRange);
    }
}

// Schedule and playback:
[UpdateInGroup(typeof(SimulationSystemGroup))]
[BurstCompile]
public partial struct ActivationSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var ecb = SystemAPI.GetSingleton<EndSimulationEntityCommandBufferSystem.Singleton>()
                           .CreateCommandBuffer(state.WorldUnmanaged);

        state.Dependency = new ActivateInRangeJob
        {
            Ecb = ecb.AsParallelWriter(),
            Origin = SystemAPI.GetSingleton<PlayerPosition>().Value,
            RadiusSq = activationRadius * activationRadius
        }.ScheduleParallel(state.Dependency);
    }
}
```

## Anti-Patterns
- Missing [ChunkIndexInQuery] sort key — non-deterministic ECB playback order; enableable state flips are order-dependent when multiple commands target same entity.
- Recording ECB.SetComponentEnabled<T> on an entity that does not have T — exception at playback.
- Using ECB.SetComponentEnabled when EnabledRefRW is available on the same entity — ECB adds one-frame delay and playback cost unnecessarily.
- Using ECB.AddComponent/RemoveComponent instead of SetComponentEnabled for frequent toggles — structural change; 10-100x more expensive at playback.

## Runtime Risks
- Change is not visible to queries in the same frame the command is recorded — takes effect after ECB playback.
- Two workers recording conflicting SetComponentEnabled for the same entity: the command with the higher sort key wins during deterministic playback.
- ECB playback happens at the ECBSystem boundary — ensure the boundary (Begin/EndSimulation) is appropriate for the timing requirements.

## Performance Notes
- At ECB playback: one bit flip per command; no archetype migration.
- Cheaper at playback than ECB.AddComponent/RemoveComponent — no chunk move.
- Still has ECB allocation and playback overhead — prefer EnabledRefRW when toggling the iterated entity's own components.

## Architecture Guidance
- Cross-entity enable/disable (entity A decides to enable entity B): ECB.SetComponentEnabled is the correct tool.
- Same-entity enable/disable inside the executing job: EnabledRefRW is preferred.
- Use EndSimulationEntityCommandBufferSystem for toggles that should be visible next frame; use BeginSimulationEntityCommandBufferSystem for toggles that other systems in the same frame should see (after playback boundary).

## Related Skills
[[enableable-component]], [[wave6-enabled-ref-rw-in-job]], [[wave6-entity-manager-set-component-enabled]], [[ecb-parallel-writer]], [[ecb-system-timing]]
