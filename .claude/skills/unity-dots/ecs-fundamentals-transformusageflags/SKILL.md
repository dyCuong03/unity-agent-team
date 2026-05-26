---
name: ecs-fundamentals-transformusageflags
description: Senior-level guide to selecting `TransformUsageFlags` at every `GetEntity()` call in a `Baker<T>`. Covers the four values (None / Renderable / Dynamic / ManualOverride), the silent-failure modes when the choice is wrong, archetype-bloat consequences at scale, and the `[WriteGroup(typeof(LocalToWorld))]` contract that must accompany `ManualOverride` to avoid last-writer-wins corruption with the default `TransformSystemGroup`. Use whenever you write a Baker, audit archetype memory, design a custom transform system, or debug "my entity won't move" / "my static entity is wasting transform components".
---

# TransformUsageFlags — Senior Patterns

Every `GetEntity()` call in a `Baker<T>` takes a `TransformUsageFlags`. The choice is silent — pick wrong, no exception, just wrong behavior or wasted memory. At small scale it doesn't matter; at thousands of entities, it's the difference between a clean archetype layout and chunks bloated with `LocalTransform` and `Parent` components on entities that never move.

## Intent

Make the transform-component footprint of each baked entity exactly match its runtime needs — no more, no less — so `TransformSystemGroup` only processes the entities that actually need processing.

## Use when

- Writing any `Baker<T>` — every `GetEntity()` requires a flag choice. There is no "default" the system picks for you.
- Auditing archetype memory: oversized chunks frequently trace back to unnecessary `TransformUsageFlags.Dynamic` on config or tag entities.
- Designing a custom transform-driving system that overrides the default math.
- Reviewing a Baker — flag selection is a code-review item, not a "looks fine" detail.

## Avoid when

There is no "avoid" case — the choice is mandatory at every `GetEntity()`. The skill is picking the *right* value, not deciding whether to pick at all.

## The four values, at senior level

| Flag | Components baked | When |
|---|---|---|
| `None` | No `LocalTransform`, no `LocalToWorld`, no `Parent` | Config singletons, registries, manager entities, anything without a world position |
| `Renderable` | `LocalToWorld` only | Static visuals — rendered in world space but never move or reparent at runtime |
| `Dynamic` | Full transform set (`LocalTransform` + `LocalToWorld` + `Parent` plumbing as needed) | Anything that moves, rotates, scales, or reparents at runtime |
| `ManualOverride` | None baked by the system — you opt out of the default transform stack and own `LocalToWorld` writes yourself | Custom transform systems, GPU-driven instancing, special-case math |

## Senior pattern — picking the flag

```csharp
public class EnemyAuthoring : MonoBehaviour
{
    public float Speed;

    class Baker : Baker<EnemyAuthoring>
    {
        public override void Bake(EnemyAuthoring a)
        {
            // Enemies move — Dynamic.
            var e = GetEntity(TransformUsageFlags.Dynamic);
            AddComponent(e, new EnemyTag());
            AddComponent(e, new MoveSpeed { Value = a.Speed });
        }
    }
}

public class GameConfigAuthoring : MonoBehaviour
{
    public float Gravity;

    class Baker : Baker<GameConfigAuthoring>
    {
        public override void Bake(GameConfigAuthoring a)
        {
            // Config singleton — no position, no transform components.
            var e = GetEntity(TransformUsageFlags.None);
            AddComponent(e, new GameConfig { Gravity = a.Gravity });
        }
    }
}

public class StaticDecorationAuthoring : MonoBehaviour
{
    class Baker : Baker<StaticDecorationAuthoring>
    {
        public override void Bake(StaticDecorationAuthoring a)
        {
            // Rendered in world space, never moves — Renderable.
            var e = GetEntity(TransformUsageFlags.Renderable);
            // ...
        }
    }
}
```

## Senior pattern — `ManualOverride` paired with `[WriteGroup]`

`ManualOverride` is the trickiest of the four because the failure mode is silent and intermittent. If you opt out of the default transform stack but don't tell the system *which* `LocalToWorld` writes are yours, the default `TransformSystemGroup` will keep overwriting your computed matrix every frame — and the last writer in the frame wins. The fix is `[WriteGroup(typeof(LocalToWorld))]` on the component that drives your custom transform: the default system then skips entities that carry your driver component.

```csharp
using Unity.Entities;
using Unity.Mathematics;
using Unity.Transforms;

// Mark this driver as the [WriteGroup] owner of LocalToWorld.
// Now the default TransformSystemGroup will SKIP any entity that has
// both LocalToWorld and CustomDrivenTransform — your system owns the write.
[WriteGroup(typeof(LocalToWorld))]
public struct CustomDrivenTransform : IComponentData
{
    public float3 Position;
    public quaternion Rotation;
}

public class CustomDrivenAuthoring : MonoBehaviour
{
    class Baker : Baker<CustomDrivenAuthoring>
    {
        public override void Bake(CustomDrivenAuthoring a)
        {
            // ManualOverride: do not let the system bake LocalTransform/Parent etc.
            // We will compute and write LocalToWorld ourselves.
            var e = GetEntity(TransformUsageFlags.ManualOverride);

            AddComponent(e, new CustomDrivenTransform
            {
                Position = (float3)a.transform.position,
                Rotation = a.transform.rotation
            });

            // Add LocalToWorld explicitly so renderers can find it. The [WriteGroup]
            // on CustomDrivenTransform tells the default TransformSystemGroup to
            // skip this entity — only the custom system writes here.
            AddComponent(e, new LocalToWorld { Value = float4x4.identity });
        }
    }
}

// The system that owns the write.
public partial struct CustomTransformSystem : ISystem
{
    public void OnUpdate(ref SystemState state)
    {
        foreach (var (driver, ltw) in SystemAPI.Query<RefRO<CustomDrivenTransform>, RefRW<LocalToWorld>>())
        {
            ltw.ValueRW.Value = float4x4.TRS(driver.ValueRO.Position, driver.ValueRO.Rotation, 1f);
        }
    }
}
```

Without `[WriteGroup]`, the visible symptom is "my custom transform works half the time" — really it works every frame, but the default system overwrites it in the same frame, and which one wins depends on system order.

## Anti-patterns

- Defaulting every `GetEntity()` to `TransformUsageFlags.Dynamic` "to be safe". Every config singleton, every manager entity, every pure-data tag now carries `LocalTransform` and `Parent` plumbing it will never use. Chunks fragment, cache density drops, and `TransformSystemGroup` walks entities it has nothing to do for.
- Tagging an entity that *does* move as `None` or `Renderable`. Queries that filter on `LocalTransform` silently return nothing, your movement system "doesn't see" the entity, and nothing logs an error — the entity just sits still. This is one of the easiest senior debugging traps in DOTS.
- Using `ManualOverride` without `[WriteGroup(typeof(LocalToWorld))]` on the driver component. Both your custom system and the default `TransformSystemGroup` race to write `LocalToWorld` every frame; the result is non-deterministic flicker or "works on my machine".
- Forgetting to add `LocalToWorld` explicitly when using `ManualOverride`. Renderers look up `LocalToWorld`; without it the entity bakes but never appears.

## Failure modes

| Symptom | Likely cause |
|---|---|
| "My entity won't move" — system code looks right, no exception | Baker used `None` or `Renderable` for an entity that needs `Dynamic`. The movement query has nothing to iterate |
| Entity flickers or "jumps" between two positions every frame | `ManualOverride` without `[WriteGroup(typeof(LocalToWorld))]`. The default transform group and your system both write `LocalToWorld`; whichever ran last wins |
| Entity bakes but isn't visible | `ManualOverride` without explicitly adding `LocalToWorld`. Renderers have no world matrix to consume |
| Profiler shows fat archetypes with `LocalTransform`/`Parent` on config entities | Bakers used `Dynamic` reflexively. Switch the config ones to `None` |
| Performance degrades faster than entity count suggests | Archetype bloat from over-Dynamic flags — more chunks, fewer entities per chunk, worse cache behavior |
| Custom rendering pipeline using GPU instancing receives stale transforms | `ManualOverride` chosen but the custom system isn't actually running, or runs in the wrong group order — verify in Systems Window |

## Runtime verification

- **Static:** grep every `GetEntity(` call. Each one should sit immediately next to a comment justifying the chosen flag, or use a clear pattern (e.g. config Bakers use `None`, gameplay Bakers use `Dynamic`). Every `ManualOverride` site must have a paired `[WriteGroup(typeof(LocalToWorld))]` on the driver component AND an explicit `AddComponent(e, new LocalToWorld { ... })`.
- **Runtime:** open the Entity Hierarchy / Inspector during play. Verify config entities have no `LocalTransform`. Verify dynamic entities have `LocalTransform` + `LocalToWorld`. For `ManualOverride` entities, scrub the timeline and confirm `LocalToWorld.Value` matches what your custom system wrote — if it disagrees, the `[WriteGroup]` is missing or the default group is still writing.

## Performance notes

- Smaller archetypes → more entities per chunk → better cache density → faster iteration. The win compounds with system count: every system that walks transforms walks fewer of them.
- `TransformUsageFlags.None` eliminates `TransformSystemGroup` work for that entity entirely. For tens of thousands of config / registry / "data only" entities, this is meaningful.
- Significant at scale; marginal in a demo with twenty entities. Don't micro-optimize a tutorial, but always pick correctly in production — the cost of getting it right is zero.

## Compile / editor safety

- `TransformUsageFlags` is part of `Unity.Entities` and required at every `GetEntity()` overload that creates an entity. The compiler enforces *that* a value is passed; it cannot enforce *which* value is right.
- `[WriteGroup]` lives in `Unity.Entities`. Source-gen needs to see it at compile time on the driver component, not just at runtime.

## Entities version notes (1.4.x)

- `TransformUsageFlags` is the current 1.x surface; the 0.x `TransformUsageFlags` enum had different names — refuse old-name references in reviews.
- `LocalTransform` (1.x) replaces the 0.x `Translation` / `Rotation` / `Scale` / `LocalToParent` quartet. A Baker that adds `Translation` is pre-1.0 — flag and update.
- `[WriteGroup]` semantics are unchanged from 0.x → 1.x but the default transform system is now `TransformSystemGroup` containing `LocalToWorldSystem` and friends. Read its source if you need to verify exactly which systems your `[WriteGroup]` is suppressing.

## See also

- [`dots-baking-patterns`](../dots-baking-patterns/SKILL.md) — the broader Baker contract this skill sits inside
- [`dots-spawning-patterns`](../dots-spawning-patterns/SKILL.md) — runtime `Instantiate` from a prefab Entity inherits whatever the prefab Baker chose
- [`ecs-fundamentals-isystem-default`](../ecs-fundamentals-isystem-default/SKILL.md) — the system type for a custom transform-driving system
