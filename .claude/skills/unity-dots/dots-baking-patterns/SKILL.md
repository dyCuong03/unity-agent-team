---
name: dots-baking-patterns
description: Senior-level Unity DOTS baking patterns — TransformUsageFlags, Baker dependency tracking, prefab references, and additional entity creation. Use when writing or reviewing `Baker<T>`, authoring MonoBehaviours, baking systems, or any code that translates GameObject scene state into entity components.
metadata:
  internal-only: true
  tier: 3
---

# DOTS Baking — Senior Patterns

Baking translates authoring-scene GameObjects into runtime entities. Get baking wrong and you get incremental-bake misses, runtime null references, archetype churn, and broken Live Baking — none of which surface until much later.

## Intent

Convert authoring state to entity state **once**, **deterministically**, and with **explicit dependencies**. Baking is not "Awake for entities" — it runs in the editor at conversion time, not at runtime.

## Use when
- Translating MonoBehaviour authoring into `IComponentData`
- Producing prefab Entity references for runtime instantiation
- Generating additional entities from one authoring component (e.g. one image → N pixel entities)
- Sharing static lookup data (build a `BlobAssetReference<T>` at bake time)

## Avoid when
- Implementing **runtime** logic. Bakers run only in editor / build conversion. They never tick.
- Mutating asset state. Bakers must be pure read-from-authoring → write-to-entity.
- Hidden side effects (logging that depends on bake order, file writes, etc.).

## Senior pattern

```csharp
public class EnergyShieldAuthoring : MonoBehaviour
{
    public int MaxHitPoints;
    public float RechargeDelay;
    public float RechargeRate;
    public GameObject Prefab;           // referenced prefab
    public Mesh Mesh;                   // referenced asset

    public class Baker : Baker<EnergyShieldAuthoring>
    {
        public override void Bake(EnergyShieldAuthoring authoring)
        {
            // 1. Declare dependencies BEFORE early-out null checks.
            //    A null ref may mean "missing asset" — bake must re-run when it returns.
            DependsOn(authoring.Mesh);

            // 2. Choose TransformUsageFlags deliberately:
            //    - None        → no transform components, smallest archetype
            //    - Renderable  → static world-space transform only
            //    - Dynamic     → full LocalTransform + Parent (movable at runtime)
            //    - ManualOverride → opt out; you add the transform components yourself
            var entity = GetEntity(TransformUsageFlags.None);

            if (authoring.Mesh == null) return;

            // 3. Read sibling GameObject components THROUGH the Baker — never via
            //    authoring.transform — so dependencies are tracked.
            var t = GetComponent<Transform>();

            AddComponent(entity, new EnergyShield {
                HitPoints     = authoring.MaxHitPoints,
                MaxHitPoints  = authoring.MaxHitPoints,
                RechargeDelay = authoring.RechargeDelay,
                RechargeRate  = authoring.RechargeRate,
                // 4. Prefab references go through GetEntity, which converts them
                //    AND registers the dependency in one call.
                Prefab        = GetEntity(authoring.Prefab, TransformUsageFlags.Dynamic),
                VertexCount   = authoring.Mesh.vertexCount,
            });
        }
    }
}
```

## Anti-patterns

- ❌ `authoring.transform.position` — bypasses dependency tracking; moving the GO does not re-bake.
- ❌ Early-out null checks **before** `DependsOn(...)` — when the missing asset is restored, the baker won't re-run.
- ❌ One `MonoBehaviour` → multiple `Baker<T>` subclasses. Convention: one Baker per authoring.
- ❌ Direct `EntityManager` access in Baker. Use `AddComponent`, `AddBuffer`, `SetComponent`, `AddComponentObject`.
- ❌ Mutating authoring state from the Baker.
- ❌ Calling `Random.Range`, `Time.time`, `Application.persistentDataPath` — anything non-deterministic. Baking must be reproducible.

## Failure modes

| Symptom | Likely cause |
|---|---|
| "Sometimes the entity has stale values after editing the prefab" | `DependsOn` missing on the referenced asset |
| "Moving the authoring GO in scene view doesn't update the entity in Live Baking" | Used `authoring.transform` instead of `GetComponent<Transform>()` |
| Two of the same component on one entity at runtime | Two Bakers running on the same authoring MonoBehaviour |
| Transform components missing on a runtime-moved entity | TransformUsageFlags was `None` or `Renderable` instead of `Dynamic` |
| `CreateAdditionalEntity` extras have unexpected transforms | Forgot `TransformUsageFlags.ManualOverride` when manually adding LocalTransform |

## Runtime verification (from Tester Verification Contract)

- **Static:** confirm exactly one `Baker<T>` per authoring class; confirm `[BurstCompile]` is NOT on the Baker (Bakers don't run in Burst); confirm no `UnityEngine.Random` / `DateTime.Now` / `Application.*` in Baker bodies.
- **Runtime:** open the authoring subscene, enter Play Mode, query the world for the expected archetype, assert component values match authoring. Toggle an authoring field — Live Baking must re-bake within one editor frame.

## Performance notes

- `TransformUsageFlags.None` saves chunk space when an entity never moves. Default to `None` unless transform is needed.
- Batched `AddComponent(entity, typeSet)` (using `ComponentTypeSet`) is cheaper than N successive `AddComponent` calls — it avoids intermediate archetype moves.
- `CreateAdditionalEntity` is the right tool for fan-out (one MonoBehaviour → N entities). Don't write a runtime spawner for what bakes once.

## Compile / editor safety

- Bakers live in editor + runtime asmdefs because they use `MonoBehaviour`. Keep authoring assemblies separate from runtime-only ECS asmdefs; the Baker class lives in the authoring asmdef.
- Managed-component Bakers (`AddComponentObject`) must guard with `#if !UNITY_DISABLE_MANAGED_COMPONENTS` if the project might disable managed components.

## Entities version notes (1.4.x)

- `Baker<T>` is current. `IConvertGameObjectToEntity` is the deprecated 0.x predecessor — refuse to use it.
- `GetEntity(authoring.prefab, TransformUsageFlags.X)` is the only correct way to convert + register a referenced prefab. The old `ConversionUtility.GetPrimaryEntity` is gone.
- `[TemporaryBakingType]` and `BakingOnlyEntity` are available for bake-time scratch data that should not survive into runtime.

## See also
- `dots-spawning-patterns` — using baked prefab Entity refs at runtime
- `dots-entity-lifecycle` — how baked entities relate to subscene load/unload
