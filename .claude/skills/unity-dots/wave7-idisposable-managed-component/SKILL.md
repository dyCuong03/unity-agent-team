---
name: wave7-idisposable-managed-component
description: Safely release unmanaged or native resources held by a managed IComponentData when the component is removed or the entity is destroyed.
tags: [hybrid, managed, lifecycle]
metadata:
  internal-only: true
  tier: 3
---

# IDisposable Managed Component — Native Resource Cleanup

## Intent
Safely release unmanaged or native resources held by a managed IComponentData when the component is removed or the entity is destroyed.

## Use When
- Your class IComponentData holds NativeArray, NativeList, or other IDisposable resources that must be freed
- Native resources must be explicitly freed before structural change (RemoveComponent, DestroyEntity)

## Avoid When
- The component holds only managed .NET objects with their own GC lifecycle — IDisposable is unnecessary overhead
- The native resource lifetime is managed externally (e.g., WorldUpdateAllocator) — no manual Dispose needed

## Senior Pattern
```csharp
public class NativeDataComponent : IComponentData, IDisposable
{
    public NativeArray<float> Buffer;

    public void Dispose()
    {
        if (Buffer.IsCreated) Buffer.Dispose();
    }
}

// CORRECT — Dispose before removing:
entityManager.GetComponentObject<NativeDataComponent>(entity).Dispose();
entityManager.RemoveComponent<NativeDataComponent>(entity);

// CORRECT — Dispose before destroy (use cleanup system pattern):
[UpdateInGroup(typeof(InitializationSystemGroup))]
public partial class NativeDataCleanupSystem : SystemBase
{
    protected override void OnUpdate()
    {
        var ecb = new EntityCommandBuffer(Allocator.Temp);

        // PendingDestroy tag signals intent to destroy:
        foreach (var (nativeData, entity) in
            SystemAPI.Query<NativeDataComponent>()
                     .WithAll<PendingDestroy>()
                     .WithEntityAccess())
        {
            nativeData.Dispose();
            ecb.DestroyEntity(entity);
        }

        ecb.Playback(EntityManager);
        ecb.Dispose();
    }
}
```

## Anti-Patterns
- Removing the component without calling Dispose — native memory leak; no automatic ECS lifecycle hook calls Dispose.
- Relying on the GC to call Dispose — GC finalizers are not guaranteed to run; and NativeArray leak detection fires immediately.
- Storing a managed component with native resources without IDisposable — leak is undetectable until native memory exhaustion.
- Calling Dispose inside a job — managed component Dispose must run on the main thread.

## Runtime Risks
- Native memory leak if Dispose is not called explicitly before structural change — Unity's leak detection will flag this in development builds.
- No automatic ECS lifecycle hook calls Dispose — the developer must arrange cleanup explicitly.
- If entity is destroyed via DestroyEntity without Dispose, the GC will eventually collect the class but the NativeArray inside will leak permanently.

## Performance Notes
- Disposal is a one-time cost. The risk is leak accumulation over session lifetime, not per-frame cost.
- NativeArray.IsCreated guard before Dispose prevents double-free; always include it.

## Architecture Guidance
- Canonical pattern: add a `PendingDestroy` tag component; cleanup system queries `WithAll<PendingDestroy>`, calls Dispose, then ECB.DestroyEntity.
- Alternatively use ICleanupComponentData to guarantee cleanup runs even after ECS entity destruction — see icleanupcomponentdata-runtime.md.
- Document every NativeDataComponent field with the responsible owner for Dispose — prevents cross-system confusion.

## Related Skills
[[managed-component-bridge]], [[icleanupcomponentdata-runtime]], [[wave7-companion-go-lifecycle]], [[wave4-world-update-allocator-per-frame-native]]
