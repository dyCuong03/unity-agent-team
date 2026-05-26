---
name: entity-query-patterns-requireforupdate-gating
description: Senior-level convention that every `ISystem` / `SystemBase` gates `OnUpdate` with `state.RequireForUpdate<T>()` (or the query overload) so the system only runs when its prerequisites — config singletons, feature toggles, baked content — actually exist. Covers the AND semantics of multiple gates, the empty-tag feature-flag pattern (generalizing the sample `ExecuteXxx` tags), the `state.RequireForUpdate(query)` overload for complex prerequisites, and why this strictly beats `if (!HasSingleton<T>()) return;`. Use when authoring any system, designing a feature toggle, or debugging first-frame "Singleton not found" / `NullReferenceException` crashes.
---

# RequireForUpdate Gating — Senior Patterns

`state.RequireForUpdate<T>()` is the contract that says "this system has nothing to do until `T` exists in the world". When the contract isn't satisfied, the entire system is skipped — `OnUpdate` is not called, the scheduler doesn't even traverse it. This is strictly better than guarding inside `OnUpdate`, and it's the only correct guard against the first-frame race with subscene baking.

## Intent

Make every system's prerequisites explicit, AND-combined at `OnCreate`, and free at runtime — so the system runs exactly when it has work to do, and never throws on a half-initialized world.

## Use when

- Authoring any system. As a convention, every system declares at least one `RequireForUpdate` — the list *is* the system's prerequisite contract. A system with no gate is a system that "runs every frame regardless of state", which is almost never what you actually mean.
- A system depends on a singleton existing (config, registry, input, prefab table). Without the gate, the first frame can fire before subscene baking finishes and `GetSingleton<T>()` throws.
- A system should only run when a feature is enabled. Bake an empty tag from an authoring toggle; gate the system on it. Toggling the authoring bool disables the entire feature with zero runtime overhead.
- A system needs multiple prerequisites — `RequireForUpdate` calls compose with AND semantics.

## Avoid when

- The system genuinely must run every frame regardless of world state. Rare in practice — usually the right gate is "until the world is loaded" via a `WorldLoadedTag` or similar.
- The prerequisite is "any entity matching a complex query" (e.g. "at least one entity with both `Damaged` and `Enabled`"). Use the `state.RequireForUpdate(query)` overload, not the generic — see below.

## Senior pattern — generic gates

```csharp
using Unity.Burst;
using Unity.Entities;

[BurstCompile]
public partial struct CombatSystem : ISystem
{
    [BurstCompile]
    public void OnCreate(ref SystemState state)
    {
        // Multiple RequireForUpdate calls AND together — system runs only when ALL satisfied.
        state.RequireForUpdate<GameConfig>();         // singleton must exist
        state.RequireForUpdate<EnableCombatFeature>(); // feature flag tag must exist
    }

    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var config = SystemAPI.GetSingleton<GameConfig>();
        // ... combat logic
    }
}
```

## Senior pattern — query-based gating

When the prerequisite is "at least one matching entity" rather than "this singleton exists":

```csharp
public void OnCreate(ref SystemState state)
{
    var damagedQuery = state.GetEntityQuery(
        ComponentType.ReadOnly<HealthComponent>(),
        ComponentType.ReadOnly<DamagedTag>());

    // System runs only when the query has at least one matching entity.
    state.RequireForUpdate(damagedQuery);
}
```

This is the right overload when the prerequisite is compositional ("A AND B exist on the same entity, somewhere"). The generic `RequireForUpdate<T>()` is shorthand for "at least one entity has `T`", but it can't express "at least one entity has BOTH `T` and `U`".

## Senior pattern — feature-flag tags

Empty `IComponentData` tags toggled by an authoring boolean generalize the `ExecuteXxx` pattern from the EntityComponentSystemSamples. The system gates on the tag; the authoring inspector toggles whether the tag is baked.

```csharp
// One-line tag per feature. Empty struct — no payload, just an archetype membership signal.
public struct EnableCombatFeature   : IComponentData {}
public struct EnableInventoryFeature : IComponentData {}

// Authoring on a per-scene "feature config" GameObject:
public class FeatureFlagsAuthoring : MonoBehaviour
{
    public bool Combat = true;
    public bool Inventory = true;

    class Baker : Baker<FeatureFlagsAuthoring>
    {
        public override void Bake(FeatureFlagsAuthoring a)
        {
            // Singleton entity carries whichever flags are enabled this build.
            var e = GetEntity(TransformUsageFlags.None);
            if (a.Combat)    AddComponent<EnableCombatFeature>(e);
            if (a.Inventory) AddComponent<EnableInventoryFeature>(e);
        }
    }
}

// Every system in the Combat feature gates on EnableCombatFeature.
// Toggling the bool in the inspector disables the whole feature cleanly —
// no per-system code change, no runtime branching, zero cost when off.
```

This is one of the cleanest large-scale toggle mechanisms in DOTS: feature off ⇒ tag absent ⇒ entire system tree skipped ⇒ no work, no scheduling, no profiler footprint.

## Anti-patterns

- Skipping `RequireForUpdate` and adding `if (!SystemAPI.HasSingleton<Config>()) return;` at the top of `OnUpdate`. The system still gets walked by the scheduler every frame; the early-return only saves the body. The gate eliminates that bookkeeping entirely.
- Calling `SystemAPI.GetSingleton<T>()` without a matching `state.RequireForUpdate<T>()` and "hoping bake finishes first". First-frame race; the player build will crash here even if the editor seems to work.
- Using a single feature-flag tag to gate dozens of unrelated systems that should be independently togglable. Split tags by feature so disabling Combat doesn't also disable Inventory.
- Misjudging the AND semantics. `RequireForUpdate<A>()` and `RequireForUpdate<B>()` together mean "both must exist". If you wanted "either A or B", use the query overload with `WithAny<A, B>()` or split into two systems.
- Putting `RequireForUpdate` in `OnUpdate` instead of `OnCreate`. It must be in `OnCreate` — the gate is set up once, not redeclared per frame.

## Failure modes

| Symptom | Likely cause |
|---|---|
| `InvalidOperationException: GetSingleton<T> requires exactly one entity` on first frame | Missing `state.RequireForUpdate<T>()` in `OnCreate`. System ran before bake; the singleton didn't exist yet |
| `NullReferenceException` deep in source-gen'd query code on first frame | Same root cause — the system fired before the world was ready |
| "I disabled the feature in the inspector but the system still runs" | The feature-flag tag is being baked unconditionally, or the system isn't actually gated on the tag — grep its `OnCreate` |
| System "doesn't run" and you can't tell why | One of the `RequireForUpdate` gates isn't satisfied. Open the Systems Window — gated-out systems are visibly skipped. The AND semantics catch most surprises |
| Feature-flag tag disables one system but not its peers | Each system declares its own `RequireForUpdate` — adding the gate to one system doesn't cascade. Add the gate everywhere or move the systems into a `ComponentSystemGroup` that itself gates on the tag |
| System runs at frame 0 then stops running | A query-based `RequireForUpdate(query)` started matching, then the matching entities were consumed/destroyed and the query went empty — usually this is correct; if you wanted it to keep running, gate on a different prerequisite |

## Runtime verification

- **Static:** convention check — every system declaration should have at least one `state.RequireForUpdate<T>()` (or `RequireForUpdate(query)`) in its `OnCreate`. Systems without any gate are either intentional (rare; one-shot bootstrap) or oversights (common).
- **Static:** every `SystemAPI.GetSingleton<T>()` call inside `OnUpdate` should have a matching `state.RequireForUpdate<T>()` in `OnCreate` of the same system file. Mismatch = first-frame race.
- **Runtime:** open the Systems Window in playmode. Gated-out systems show as not running. Toggle a feature flag — confirm the gated systems disappear from the active set, not just from the profiler.

## Performance notes

- Negligible per-frame cost when the gate passes. The scheduler does an archetype-presence check, which is constant-time.
- Zero per-frame cost when the gate fails — the system is fully skipped. `OnUpdate` doesn't execute, no jobs are scheduled from this system, no queries are walked.
- Strictly cheaper than guarded early-return inside `OnUpdate`. The early-return still pays the system-walk cost; the gate doesn't.

## Compile / editor safety

- `state.RequireForUpdate<T>()` is generic and Burst-compatible. Place inside a `[BurstCompile]` `OnCreate` without issue.
- The query overload `state.RequireForUpdate(query)` requires the query to be created in `OnCreate` (or earlier). Don't create new queries per-frame just to gate on them.

## Entities version notes (1.4.x)

- `state.RequireForUpdate<T>()` (generic) and `state.RequireForUpdate(EntityQuery)` (overload) are current.
- `state.RequireForUpdate(world, query)` and other 0.x signatures are gone.
- For `SystemBase`, the equivalent is `RequireForUpdate<T>()` directly on the system (no `state` parameter). Same semantics, same AND composition.
- The `[RequireMatchingQueriesForUpdate]` attribute is a related but distinct mechanism — it gates on the queries the system actually uses, automatically. Useful for simple systems but doesn't replace explicit `RequireForUpdate` for singletons or feature flags.

## See also

- [`singleton-patterns-config-and-access`](../singleton-patterns-config-and-access/SKILL.md) — the canonical "singleton + RequireForUpdate" pair
- [`ecs-fundamentals-isystem-default`](../ecs-fundamentals-isystem-default/SKILL.md) — the host system type where `OnCreate` declares these gates
- [`entity-query-patterns-systemapi-query`](../entity-query-patterns-systemapi-query/SKILL.md) — the iteration this system performs once its gates pass
- [`dots-baking-patterns`](../dots-baking-patterns/SKILL.md) — how feature-flag tags get baked from an authoring toggle
