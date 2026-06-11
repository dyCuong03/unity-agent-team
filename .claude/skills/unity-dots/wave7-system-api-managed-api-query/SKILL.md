---
name: wave7-system-api-managed-api-query
description: Query managed IComponentData and UnityEngine components from ECS systems using the correct non-Burst API surface (SystemAPI.ManagedAPI or SystemAPI.Query for managed types).
tags: [hybrid, managed, query]
metadata:
  internal-only: true
  tier: 3
---

# SystemAPI.ManagedAPI — Managed Component Query

## Intent
Query managed IComponentData and UnityEngine components from ECS systems using the correct non-Burst API surface (SystemAPI.ManagedAPI or SystemAPI.Query for managed types).

## Use When
- A system needs to read or write managed components (class IComponentData or MonoBehaviour attachments) per-entity
- Singleton managed component access is needed via ManagedAPI.GetSingleton

## Avoid When
- The system is [BurstCompile] — managed API access is illegal inside Burst; compile error
- High-frequency per-entity access at large entity counts — managed queries are main-thread only bottleneck

## Senior Pattern
```csharp
// Non-Burst SystemBase in PresentationSystemGroup:
[UpdateInGroup(typeof(PresentationSystemGroup))]
public partial class HybridSyncSystem : SystemBase
{
    protected override void OnUpdate()
    {
        // Query managed + blittable components together:
        foreach (var (animator, transform) in
            SystemAPI.Query<Animator, RefRO<LocalToWorld>>())
        {
            animator.transform.SetPositionAndRotation(
                transform.ValueRO.Position,
                transform.ValueRO.Rotation);
        }
    }
}

// ManagedAPI for explicit managed singleton access:
var config = SystemAPI.ManagedAPI.GetSingleton<GameConfigManaged>();
int maxEnemies = config.Asset.MaxEnemies;

// ManagedAPI per-entity query:
foreach (var go in SystemAPI.ManagedAPI.Query<UnityEngine.GameObject>())
{
    go.SetActive(true);
}

// Mixing managed class component with blittable struct component in one query:
foreach (var (spriteData, health) in
    SystemAPI.Query<ManagedSpriteData, RefRO<Health>>())
{
    if (health.ValueRO.Current <= 0)
        spriteData.Sprite = deadSprite;
}
```

## Anti-Patterns
- Calling SystemAPI.Query<ManagedType>() inside [BurstCompile] — compile error.
- Mixing managed and unmanaged component access in the same Burst job — not possible; fails at compile.
- Using `Entities.ForEach` with managed components — deprecated; use SystemBase with SystemAPI.Query.
- Calling SystemAPI.ManagedAPI inside ISystem (struct system) — ManagedAPI requires SystemBase context or main-thread ISystem; ensure system is not Burst-compiled.

## Runtime Risks
- No Burst acceleration; GC allocation possible if query materializes a managed list internally.
- Archetype fragmentation if managed components are added/removed frequently — identical structural change cost to blittable components but GC compounds.
- ManagedAPI.GetSingleton throws if no entity with the component exists or if multiple exist — guard with HasSingleton check if uncertain.

## Performance Notes
- Managed queries run on main thread only.
- For large entity counts this is a bottleneck — cap managed component queries to low-frequency systems.
- PresentationSystemGroup or a dedicated HybridSyncGroup are the correct homes.
- Do not call ManagedAPI inside FixedStepSimulationSystemGroup — fixed step runs at physics rate and managed overhead compounds.

## Architecture Guidance
- Isolate all managed/hybrid queries in SystemBase subclasses placed in PresentationSystemGroup or a dedicated HybridSyncGroup.
- Never let managed component queries cross into Burst-compiled systems — enforce via system group placement and code review.
- For singleton managed access: prefer ManagedAPI.GetSingleton over per-entity query.

## Related Skills
[[managed-component-bridge]], [[wave7-managed-singleton-pattern]], [[wave7-add-component-object-hybrid-attach]], [[wave7-ecs-to-go-transform-sync]], [[singleton-access]]
