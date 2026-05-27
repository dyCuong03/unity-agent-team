---
name: managed-component-bridge
description: Store managed references (GameObject, MonoBehaviour, Unity UI objects) on an ECS entity to bridge the ECS and GameObject worlds during hybrid initialization.
tags: [core, managed, hybrid]
---

# Managed Component Bridge

## Intent
Store managed references (GameObject, MonoBehaviour, Unity UI objects) on an ECS entity to bridge the ECS and GameObject worlds during hybrid initialization.

## Use When
An ECS system must drive a GameObject or Unity UI element, and there is no alternative to holding a managed reference on the entity. One-time initialization scenarios only.

## Avoid When
Any hot runtime path, simulation loop, or Burst-compiled system. If the data can be unmanaged, it must be unmanaged.

## Senior Pattern
- `public class MyManagedData : IComponentData` (class, not struct).
- Access only from a managed system (SystemBase or non-Burst ISystem).
- The initialization system sets `state.Enabled = false` after setup — it runs exactly once.
- Managed component entities are sparse and cold — never in the simulation hot path.

## AddComponentObject API
```csharp
// Attach a managed object (UnityEngine.Object subclass or class IComponentData) at runtime:
entityManager.AddComponentObject(entity, new ManagedSpriteData { Sprite = mySprite });

// Or bake-time (preferred — avoids runtime sync point):
public override void Bake(HybridAuthoring authoring)
{
    var entity = GetEntity(TransformUsageFlags.Dynamic);
    AddComponentObject(entity, authoring.Animator);  // UnityEngine.Object subclass
}

// Read per-entity in a non-Burst system:
foreach (var (data, entity) in SystemAPI.Query<ManagedSpriteData>().WithEntityAccess())
{
    data.Sprite = newSprite;  // direct mutation, managed heap
}
```

## GC Cost Model
- Each entity with a class IComponentData = one GC-tracked heap allocation.
- Structural changes (AddComponent/RemoveComponent) on managed components trigger full sync point, identical to struct components but GC pressure compounds.
- Target: single-digit managed component entity counts per scene. At >100 entities with managed components, measure GC allocation pressure explicitly.

## Code Template
```csharp
public class UISlotRef : IComponentData
{
    public RectTransform SlotTransform;
    public UISlotRef() { }
}

// Initialization system (runs once, self-disabling):
public partial class UIInitSystem : SystemBase
{
    protected override void OnCreate()
    {
        RequireForUpdate<UISlotRef>();
    }

    protected override void OnUpdate()
    {
        foreach (var (slot, entity) in
            SystemAPI.Query<UISlotRef>().WithEntityAccess())
        {
            // wire up the slot to ECS-driven data sources
            _ = entity;
        }
        Enabled = false;
    }
}
```

## Anti-Patterns
- Accessing a managed component from a [BurstCompile] system or job — compile error.
- Using managed components for per-entity state that could be unmanaged — defeats ECS performance model.
- Keeping the initialization system enabled after it has done its work — wastes scheduler overhead.
- Storing disposable resources (NativeArray, etc.) inside a managed component class without cleanup in OnDestroy.

## Runtime Risks
- Burst access: compile error or safety exception.
- Memory leak: managed component holds onto a disposable resource and is never cleaned up.

## Performance Notes
Heap allocation per entity. GC pressure proportional to managed component count. Reserved strictly for the boundary layer. Keep count minimal (typically single digits per scene).

## Architecture Guidance
Managed component = boundary adapter. One-time init system, self-disabling. Never proliferate managed components across gameplay systems.

## Related Skills
[[wave7-add-component-object-hybrid-attach]], [[wave7-idisposable-managed-component]], [[wave7-system-api-managed-api-query]], [[wave7-managed-singleton-pattern]], [[wave7-companion-go-lifecycle]]
