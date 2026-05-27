---
name: wave6-enabled-ref-rw-in-job
description: Read and write the enabled bit of an IEnableableComponent directly inside IJobEntity.Execute() or SystemAPI.Query foreach using EnabledRefRW<T>, avoiding ECB overhead and one-frame delay.
---

# EnabledRefRW in Jobs — Inline Bit Toggle

## Intent
Read and write the enabled bit of an IEnableableComponent directly inside IJobEntity.Execute() or SystemAPI.Query foreach using EnabledRefRW<T>, avoiding ECB overhead and one-frame delay.

## Use When
- Enable/disable decision depends on component data computed inside a job (proximity culling, LOD activation, range-based behavior)
- Bulk enable/disable in one pass without ECB one-frame delay
- Toggle must happen in same frame without deferred playback cost

## Avoid When
- Enable/disable targets a different entity than the one being iterated — use ECB.SetComponentEnabled
- Only reading enabled state (not writing) — use EnabledRefRO<T>

## Senior Pattern
```csharp
// Main-thread foreach — toggle ALL entities (enabled AND disabled):
foreach (var (posRO, flagEnabled) in
    SystemAPI.Query<RefRO<LocalTransform>, EnabledRefRW<ActiveBehavior>>()
             .WithOptions(EntityQueryOptions.IgnoreComponentEnabledState))
{
    flagEnabled.ValueRW = math.distancesq(posRO.ValueRO.Position, origin) <= radiusSq;
}

// IJobEntity (parallel) — same IgnoreComponentEnabledState requirement:
[BurstCompile]
[WithOptions(EntityQueryOptions.IgnoreComponentEnabledState)]
public partial struct ToggleInRangeJob : IJobEntity
{
    public float3 Origin;
    public float RadiusSq;

    [BurstCompile]
    public void Execute(in LocalTransform t, EnabledRefRW<ActiveBehavior> enabled)
    {
        enabled.ValueRW = math.distancesq(t.Position, Origin) <= RadiusSq;
    }
}

// Schedule:
state.Dependency = new ToggleInRangeJob
{
    Origin = origin,
    RadiusSq = radius * radius
}.ScheduleParallel(state.Dependency);
```

## Anti-Patterns
- Using EnabledRefRW<T> without IgnoreComponentEnabledState when intending to process all entities — default query only returns enabled entities; disabled are silently skipped, enabling them is impossible.
- Writing enabledRef.ValueRW from two parallel workers on the same entity — IJobEntity is safe (each chunk dispatched once); manual parallel splits are not.
- Using ECB.SetComponentEnabled when EnabledRefRW is available in the same job — ECB adds one-frame delay and playback cost unnecessarily.

## Runtime Risks
- EnabledRefRW writes are visible immediately within the same job but not to parallel jobs already in flight on the same chunk — IJobEntity guarantees disjoint chunk access so this is safe.
- Mixing EnabledRefRW and ECB.SetComponentEnabled for the same component in the same frame produces ordering ambiguity.

## Performance Notes
- Single bit write per entity; no archetype migration; no ECB playback.
- Optimal for bulk proximity-based culling — entire operation is one pass with no structural change cost.
- Burst-compiled toggle loop over 10,000 entities is effectively free compared to structural AddComponent/RemoveComponent equivalent.

## Architecture Guidance
- Build query with IgnoreComponentEnabledState in OnCreate and cache it; pass explicitly to ScheduleParallel.
- For cross-entity toggles (entity A decides to enable entity B), use ECB.SetComponentEnabled — EnabledRefRW only works on the entity being executed.
- Producer/consumer pattern: producer writes EnabledRefRW; consumer queries WithAll<T> in [UpdateAfter] — no ECB needed.

## Related Skills
[[enableable-component]], [[wave6-ecb-set-component-enabled]], [[wave6-with-disabled-query-filter]], [[wave6-zero-data-enableable-signal]]
