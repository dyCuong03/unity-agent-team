---
name: wave8-enableable-component-query-mismatch
description: Select the correct EntityQuery filter method (WithAll, WithDisabled, WithNone, IgnoreComponentEnabledState) for IEnableableComponent to avoid silently processing the wrong entity set.
tags: [enableable, antipattern, debug]
---

# Enableable Component Query Mismatch

## Intent
Select the correct EntityQuery filter method (WithAll, WithDisabled, WithNone, IgnoreComponentEnabledState) for IEnableableComponent to avoid silently processing the wrong entity set.

## Use When
- Writing any query that targets an IEnableableComponent type
- Diagnosing systems that silently miss entities or process entities they should skip

## Avoid When
- The component is a plain struct IComponentData without IEnableableComponent — enabled-state filtering does not apply

## Senior Pattern
```csharp
public struct ActiveTag : IComponentData, IEnableableComponent { }

// Case 1 — Process ONLY entities where ActiveTag is ENABLED (default behavior):
foreach (var health in SystemAPI.Query<RefRW<Health>>().WithAll<ActiveTag>())
{
    health.ValueRW.Current -= damage;
    // Only processes entities where ActiveTag enabled bit is true
}

// Case 2 — Process ONLY entities where ActiveTag is DISABLED (e.g., sleeping/inactive):
foreach (var health in SystemAPI.Query<RefRW<Health>>().WithDisabled<ActiveTag>())
{
    health.ValueRW.Current += regenRate;
    // Only processes entities where ActiveTag enabled bit is false
}

// Case 3 — Process ALL entities regardless of enabled state:
var allQuery = SystemAPI.QueryBuilder()
    .WithAll<Health>()
    .WithOptions(EntityQueryOptions.IgnoreComponentEnabledState)
    .Build();
// Use sparingly — bypasses chunk-level enabled optimization

// Case 4 — Process ONLY entities that do NOT HAVE ActiveTag at all (structural absence):
foreach (var health in SystemAPI.Query<RefRW<Health>>().WithNone<ActiveTag>())
{
    // Entities that never had ActiveTag added — NOT for "disabled" filtering
}

// Case 5 — Read enabled state per-entity in IJobEntity:
[BurstCompile]
public partial struct ConditionalUpdateJob : IJobEntity
{
    [BurstCompile]
    public void Execute(EnabledRefRO<ActiveTag> isActive, ref Health health)
    {
        if (isActive.ValueRO)
            health.Current -= 1;
        // Only correct when IgnoreComponentEnabledState is set on the job's query
    }
}
```

## Filter Semantics Table

| Filter | Matches entities where... |
|---|---|
| `WithAll<T>` (T is IEnableableComponent) | T is structurally present AND enabled bit is true |
| `WithDisabled<T>` | T is structurally present AND enabled bit is false |
| `WithNone<T>` | T is NOT structurally present (absent from archetype) |
| `WithPresent<T>` | T is structurally present (enabled OR disabled) |
| `IgnoreComponentEnabledState` | All entities in matching archetypes regardless of bit |

## Anti-Patterns
- Using `WithAll<T>` when wanting to process disabled entities — silently skips them; no error, no warning.
- Using `WithNone<T>` to "process inactive entities" — WithNone matches entities WITHOUT the component entirely; disabled-but-present entities are NOT matched.
- Using `IgnoreComponentEnabledState` as default for all queries — negates the performance benefit of enableable components; forces per-chunk bitmask evaluation.
- Mixing EnabledRefRO<T> in a job without IgnoreComponentEnabledState — the query only returns enabled entities; the EnabledRefRO.ValueRO is always true, making the check redundant.

## Runtime Risks
- Query mismatch produces a silently incorrect entity set — no exception, no warning.
- Systems that should skip disabled entities process them; systems that should process sleeping/dead entities miss them.
- Both are correctness bugs that manifest only as wrong game behavior, making root cause diagnosis slow.

## Performance Notes
- `WithAll<T>` where T is IEnableableComponent uses chunk-level enabled-bit masks — faster than per-entity branch.
- `IgnoreComponentEnabledState` forces per-chunk mask evaluation — use only when genuinely needed.
- `WithDisabled<T>` is a bitmask check at chunk level — O(1) per chunk; efficient for processing minority disabled populations.

## Architecture Guidance
- Before writing any query targeting an IEnableableComponent, explicitly decide and document: enabled-only (WithAll), disabled-only (WithDisabled), or all (IgnoreComponentEnabledState).
- The query API does not make intent obvious at a glance — a comment stating the intent prevents future misreads.
- Test both enabled and disabled populations when a new IEnableableComponent system is introduced — silent mismatches only surface under specific runtime conditions.

## Related Skills
[[enableable-component]], [[wave6-with-disabled-query-filter]], [[wave6-enabled-ref-rw-in-job]], [[wave8-ijobchunk-use-enabled-mask-guard]]
