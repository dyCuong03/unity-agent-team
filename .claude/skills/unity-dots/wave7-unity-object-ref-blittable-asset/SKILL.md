---
name: wave7-unity-object-ref-blittable-asset
description: Store a reference to a UnityEngine.Object (Texture2D, AudioClip, Mesh, Sprite, etc.) in a blittable struct IComponentData so it can be stored in ECS chunks and passed through job structs without ma...
tags: [hybrid, managed]
metadata:
  internal-only: true
  tier: 3
---

# UnityObjectRef — Blittable Asset Reference

## Intent
Store a reference to a UnityEngine.Object (Texture2D, AudioClip, Mesh, Sprite, etc.) in a blittable struct IComponentData so it can be stored in ECS chunks and passed through job structs without making the component a class.

## Use When
- A per-entity asset reference is needed in a struct component (sprite per unit, audio clip per entity, material override)
- The asset reference must be stored in chunk memory for cache-efficient access
- Asset identity must be carried through the ECS pipeline to a point-of-use on the main thread

## Avoid When
- The asset reference is only needed on the main thread — AddComponentObject with class IComponentData is simpler
- Hot-path Burst code that dereferences the asset every frame — UnityObjectRef.Value access is main-thread only

## Senior Pattern
```csharp
public struct SpriteReference : IComponentData
{
    public UnityObjectRef<Sprite> Sprite;  // blittable (stores instance ID as int)
}

// Baker — implicit conversion from Sprite to UnityObjectRef<Sprite>:
public class SpriteReferenceBaker : Baker<SpriteReferenceAuthoring>
{
    public override void Bake(SpriteReferenceAuthoring authoring)
    {
        var entity = GetEntity(TransformUsageFlags.None);
        AddComponent(entity, new SpriteReference
        {
            Sprite = authoring.Sprite  // implicit conversion
        });
        DependsOn(authoring.Sprite);  // register asset dependency for incremental baking
    }
}

// Read asset identity in a job (blittable — safe to copy into job struct):
[BurstCompile]
public partial struct CategorizeJob : IJobEntity
{
    [BurstCompile]
    public void Execute(in SpriteReference spriteRef, ref RenderCategory category)
    {
        // UnityObjectRef carries instance ID — compare identity without dereferencing:
        category.IsHero = spriteRef.Sprite == heroSpriteRef;
    }
}

// Dereference to actual asset on main thread (point-of-use only):
[UpdateInGroup(typeof(PresentationSystemGroup))]
public partial class ApplySpriteSystem : SystemBase
{
    protected override void OnUpdate()
    {
        foreach (var (spriteRef, renderer) in
            SystemAPI.Query<RefRO<SpriteReference>, SpriteRenderer>())
        {
            renderer.sprite = spriteRef.ValueRO.Sprite.Value;  // main thread only
        }
    }
}
```

## Anti-Patterns
- Storing `Sprite` or `Texture2D` directly in a struct IComponentData — not blittable; compile error.
- Dereferencing `UnityObjectRef<T>.Value` inside a Burst job — unsafe; Unity assets are managed objects.
- Using UnityObjectRef for data that changes frequently at runtime — treat as an immutable baked reference; runtime reassignment requires main-thread structural change.
- Omitting DependsOn(asset) in Baker — incremental baking may not detect asset changes and serve stale baked data.

## Runtime Risks
- If the referenced asset is unloaded (Resources.UnloadUnusedAssets or Addressables release), `.Value` returns null — guard at point of use.
- UnityObjectRef stores the Unity instance ID; if the asset is reimported in Editor, the ID may change and the reference becomes stale until SubScene is rebaked.

## Performance Notes
- UnityObjectRef itself is a blittable int (instance ID) — cheap to copy into job structs and store in chunk memory.
- `.Value` dereference is a managed lookup — do it once per system update at point-of-use, not per entity per frame in a loop.
- Identity comparison (==) between two UnityObjectRef<T> is a simple int comparison — Burst-safe.

## Architecture Guidance
- Use UnityObjectRef to carry asset identity through the ECS pipeline.
- Dereference to the actual asset only at the point of use on the main thread (material swap, audio play, sprite assignment).
- Pair with DependsOn() in Baker to ensure incremental baking tracks asset changes.

## Related Skills
[[wave7-add-component-object-hybrid-attach]], [[managed-component-bridge]], [[baker-authoring-conversion]], [[wave7-ecs-to-go-transform-sync]]
