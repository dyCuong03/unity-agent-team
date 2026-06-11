---
name: dots-enableable-components
description: When to use IEnableableComponent vs structural add/remove for entity state flips. Covers the cost-model decision, query semantics (.WithAll vs .WithEnabled, IgnoreComponentEnabledState), and SetComponentEnabled inside jobs. Use when designing state that flips frequently (cooldowns, dirty flags, dead/alive, paused/active, "needs processing" tags).
metadata:
  internal-only: true
  tier: 3
---

# Enableable Components — Senior Patterns

`IEnableableComponent` lets you toggle a component on/off **without a structural change**. No archetype move, no chunk shuffle, no ECB playback. For state that flips often, this is the difference between a 0.05ms system and a 5ms system.

## Intent

Model boolean state that changes faster than once per second as an enabled/disabled bit on a present component, not as add/remove of a tag.

## Decision rule (memorize this)

| Toggle frequency | Pattern |
|---|---|
| Once per entity lifetime | Add at bake, never toggle — plain `IComponentData` tag |
| Rare (once per scene, once per quest stage) | Structural add/remove via ECB |
| Frequent (per-second, per-frame, per-hit) | **`IEnableableComponent`** — toggle the bit |

Cost model: structural change costs archetype move (potentially copying every component on the entity to a different chunk). Enableable toggle costs one bit flip in the chunk's enabled-mask. At any scale above "occasional" the bit wins by orders of magnitude.

## Senior pattern

```csharp
// Component: just an empty struct or one with payload, marked IEnableableComponent.
public struct Spin : IComponentData, IEnableableComponent
{
    public float RadiansPerSecond;
}

public partial struct SpinSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var dt = SystemAPI.Time.DeltaTime;

        // Default query semantics: only entities whose Spin is ENABLED match.
        foreach (var (transform, spin) in
                 SystemAPI.Query<RefRW<LocalTransform>, RefRO<Spin>>())
        {
            transform.ValueRW = transform.ValueRO.RotateY(
                spin.ValueRO.RadiansPerSecond * dt);
        }
    }
}

// Toggling the bit from a job: use EnabledRefRW<T>, not AddComponent/RemoveComponent.
[BurstCompile]
partial struct TogglerJob : IJobEntity
{
    void Execute(EnabledRefRW<Spin> spinEnabled, in HealthComponent hp)
    {
        spinEnabled.ValueRW = hp.Current > 0;
    }
}
```

## Iterating across both enabled AND disabled entities

The default query skips disabled. To touch all of them:

```csharp
foreach (var spinEnabled in
         SystemAPI.Query<EnabledRefRW<Spin>>()
                  .WithOptions(EntityQueryOptions.IgnoreComponentEnabledState))
{
    spinEnabled.ValueRW = !spinEnabled.ValueRO; // flip everyone
}
```

## ECB-based enable from a parallel job

```csharp
// In an IJobEntity scheduled with ScheduleParallel():
void Execute(Entity entity, [ChunkIndexInQuery] int chunkIndex, /* ... */)
{
    Ecb.SetComponentEnabled<Spin>(chunkIndex, entity, true);
}
```

Prefer `EnabledRefRW<T>` over ECB when the entity already matches the query — direct toggle is cheaper than recording + playing back. Use ECB only when you need to enable a component on entities that **aren't** in the current query.

## Anti-patterns

- ❌ Using `AddComponent` / `RemoveComponent` for hot-path on/off flips. Structural cost dominates.
- ❌ Storing the state as a `bool IsActive` field inside the component AND also relying on enabled-mask. Pick one source of truth — usually the enabled bit.
- ❌ Querying `.WithDisabled<T>()` expecting to also see entities without the component at all. `WithDisabled` only matches entities that **have** the component but it's disabled.
- ❌ Calling `state.EntityManager.SetComponentEnabled<T>(entity, false)` from inside a scheduled job. Same rule as any structural-ish change — use `EnabledRefRW<T>` or `ECB.SetComponentEnabled`.
- ❌ Marking every component `IEnableableComponent` "just in case". The bit costs a small per-chunk overhead. Mark only what actually toggles.

## Failure modes

| Symptom | Likely cause |
|---|---|
| State doesn't change despite "toggling" | Used `WithOptions(IgnoreComponentEnabledState)` for read but not for write — wrote to the wrong subset |
| Foreach over the query never iterates the entity that "should" match | The component is disabled; default query skips it |
| Random InvalidOperationException about safety | Mixed `EntityManager.SetComponentEnabled` with a job that has the component scheduled |
| Profiler shows archetype churn on a hot system | Still using `AddComponent` / `RemoveComponent` instead of converting to enableable |

## Runtime verification

- **Static:** any component named like `IsX` / `HasX` / `WasX` that gets added/removed in hot paths should be reviewed as a candidate for `IEnableableComponent`. Grep for `.AddComponent<T>` / `.RemoveComponent<T>` in `OnUpdate` of high-frequency systems.
- **Runtime:** for a state-flip system, capture pre/post entity counts in each archetype. If counts are identical (no archetype move), the enableable conversion is working. If counts change every frame, the conversion is missing.

## Performance notes

- Enableable toggle: ~one bit write per entity, no chunk move, no ECB playback. Roughly free at any reasonable scale.
- Structural add/remove: copies all component bytes of the entity into a different chunk. Linear in entity component size. Compounds with archetype fragmentation.
- The HelloCube `StateChange` sample explicitly compares VALUE / STRUCTURAL_CHANGE / ENABLEABLE_COMPONENT modes; enableable is consistently the cheapest above ~1k entities.

## Compile / editor safety

- `IEnableableComponent` is an interface added alongside `IComponentData`. No version guards needed in Entities 1.x.
- The component can still carry data — `Spin { RadiansPerSecond }` is valid. Enabled-bit and data coexist.

## Entities version notes (1.4.x)

- `EnabledRefRW<T>` / `EnabledRefRO<T>` are current. Old code calling `EntityManager.SetComponentEnabled` from main thread still works but is wrong inside jobs.
- `EntityQueryOptions.IgnoreComponentEnabledState` is current. The old `EntityQueryOptions.IncludeDisabledEntities` referred to disabled *entities*, not disabled components — different concept, easy to confuse.

## See also
- `dots-ecb-orchestration` — when you must use the ECB instead of `EnabledRefRW`
- `dots-entity-lifecycle` — enableable as a less-destructive alternative to "destroy and recreate"
