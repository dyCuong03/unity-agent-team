---
name: wave7-add-component-object-hybrid-attach
description: Attach a managed Unity object (MonoBehaviour, ScriptableObject, or any UnityEngine.Object subclass) to an ECS entity at runtime or bake time for hybrid access.
tags: [hybrid, managed]
metadata:
  internal-only: true
  tier: 3
---

# AddComponentObject — Hybrid Managed Object Attachment

## Intent
Attach a managed Unity object (MonoBehaviour, ScriptableObject, or any UnityEngine.Object subclass) to an ECS entity at runtime or bake time for hybrid access.

## Use When
- A system needs to read or write a MonoBehaviour component that lives on a companion GameObject linked to an entity
- Animator, AudioSource, or other UnityEngine.Object must be driven per-entity from an ECS system

## Avoid When
- The data can be baked into a blittable IComponentData — prefer baking over runtime hybrid attachment
- The attachment changes frequently at high entity counts — GC thrash

## Senior Pattern
```csharp
// Bake-time attachment (preferred — avoids runtime sync point):
public class HybridAuthoring : MonoBehaviour
{
    public Animator Animator;
}

public class HybridBaker : Baker<HybridAuthoring>
{
    public override void Bake(HybridAuthoring authoring)
    {
        var entity = GetEntity(TransformUsageFlags.Dynamic);
        AddComponentObject(entity, authoring.Animator);  // UnityEngine.Object subclass
    }
}

// Read in non-Burst system (main thread only):
[UpdateInGroup(typeof(PresentationSystemGroup))]
public partial class AnimationDriveSystem : SystemBase
{
    protected override void OnUpdate()
    {
        foreach (var animator in SystemAPI.Query<Animator>())
        {
            animator.SetTrigger("Attack");
        }
    }
}

// Runtime attachment (main thread only, triggers sync point):
entityManager.AddComponentObject(entity, someAnimator);
```

## Anti-Patterns
- Calling AddComponentObject at runtime inside a job — not allowed; main thread only.
- Querying managed components inside [BurstCompile] systems — compile error.
- Using AddComponentObject for data that changes every frame at high entity counts — GC thrash; use a blittable mirror component instead.
- Forgetting DependsOn() in Baker when the attached object references other assets — incremental baking may miss changes.

## Runtime Risks
- Main-thread-only access; if the managed object is destroyed (GO destroyed externally), the reference becomes a missing reference exception — add null guard in the consuming system.
- Runtime AddComponentObject triggers a structural change sync point — batch all attachments in InitializationSystemGroup.

## Performance Notes
- Each managed component access prevents Burst compilation for the accessing system.
- For high-frequency per-entity updates (>1000 entities), consider a pure ECS mirroring approach: blittable struct holds state, managed system reads struct and applies to managed object once per frame.

## Architecture Guidance
- Prefer bake-time AddComponentObject over runtime — baked state is serialized, no sync point at play.
- Keep managed component writes to initialization or low-frequency event paths.
- Use a dedicated non-Burst SystemBase in PresentationSystemGroup for all managed hybrid sync.

## Related Skills
[[managed-component-bridge]], [[wave7-system-api-managed-api-query]], [[wave7-companion-go-lifecycle]], [[wave7-ecs-to-go-transform-sync]], [[baker-authoring-conversion]]
