---
name: wave6-with-disabled-query-filter
description: Query only entities where a specific IEnableableComponent is present but currently disabled using .WithDisabled<T>(), enabling systems to act specifically on inactive populations.
tags: [enableable, query]
---

# WithDisabled Query Filter

## Intent
Query only entities where a specific IEnableableComponent is present but currently disabled using .WithDisabled<T>(), enabling systems to act specifically on inactive populations.

## Use When
- Logic must act only on entities in the "inactive" state (balls not being carried, units not yet activated)
- Multi-phase state filtering where different systems handle active vs inactive populations separately

## Avoid When
- Component may be absent entirely — WithDisabled requires component to be present; use WithNone only when component absence is the correct filter

## Senior Pattern
```csharp
// Query filter semantics for IEnableableComponent:
// WithAll<T>()     — present AND enabled
// WithDisabled<T>()— present AND disabled
// WithNone<T>()    — absent entirely (structural)
// WithPresent<T>() — present regardless of bit (enabled OR disabled)
// IgnoreComponentEnabledState — all entities regardless of bit

// Foreach — find available (not-carried) balls:
foreach (var (transform, entity) in
    SystemAPI.Query<RefRO<LocalTransform>>()
             .WithAll<Ball>()
             .WithDisabled<Carry>()
             .WithEntityAccess())
{
    // ball is present and NOT being carried — can be picked up
}

// IJobEntity form:
[WithAll(typeof(Ball))]
[WithDisabled(typeof(Carry))]
[BurstCompile]
public partial struct FindAvailableBallsJob : IJobEntity
{
    [BurstCompile]
    public void Execute(Entity entity, in LocalTransform transform)
    {
        // process available balls
    }
}

// IJobChunk form — SetChangedVersionFilter equivalent:
query = state.GetEntityQuery(
    ComponentType.ReadOnly<Ball>(),
    ComponentType.Disabled<Carry>());   // Disabled<T> is the ComponentType variant
```

## Anti-Patterns
- Using WithNone<T> instead of WithDisabled<T> — WithNone excludes entities with the component entirely (both enabled and disabled); completely wrong semantics for "present but inactive".
- Using WithAll<T> and expecting to see disabled entities — WithAll on an IEnableableComponent filters to enabled-only.
- Using IgnoreComponentEnabledState when only the disabled population is needed — processes all entities; less efficient than WithDisabled.

## Runtime Risks
- WithDisabled is evaluated at chunk level via bitmask — if even one entity in a chunk is enabled, the chunk is still included but only disabled entities are iterated.
- A component that is absent entirely (never added) is NOT matched by WithDisabled — it requires the component to be structurally present.

## Performance Notes
- WithDisabled filter is a bitmask check at chunk level — O(1) per chunk.
- More efficient than IgnoreComponentEnabledState + per-entity enabled check when disabled population is a minority.
- Combine WithDisabled with WithAll/WithNone for maximum query precision.

## Architecture Guidance
- Two-system pattern: SystemA queries WithAll<T> (handles active), SystemB queries WithDisabled<T> (handles inactive) — clean separation.
- Never use WithNone as a substitute for WithDisabled — they have fundamentally different semantics that cannot be interchanged.

## Related Skills
[[enableable-component]], [[wave6-enabled-ref-rw-in-job]], [[wave6-ecs-state-machine-design]], [[wave6-ecb-set-component-enabled]]
