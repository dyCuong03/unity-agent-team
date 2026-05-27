---
name: wave7-companion-go-lifecycle
description: Manage the full creation, synchronization, and destruction lifecycle of a companion GameObject paired with an ECS entity using the four-phase marker/spawn/sync/destroy pattern.
tags: [hybrid, managed, lifecycle]
---

# Companion GO Lifecycle — Marker/Spawn/Sync/Destroy

## Intent
Manage the full creation, synchronization, and destruction lifecycle of a companion GameObject paired with an ECS entity using the four-phase marker/spawn/sync/destroy pattern.

## Use When
- An entity needs a companion GO for VFX, audio, or UI that cannot be rendered by Entities Graphics
- Companion GO must be created and destroyed in sync with ECS entity lifecycle

## Avoid When
- Pure ECS rendering via Entities Graphics is sufficient — companion GOs add main-thread cost and GC pressure
- The companion GO count is very high (>500) — main-thread instantiation and sync become bottlenecks

## Senior Pattern
```csharp
// Marker component (baked or added at runtime):
public struct CompanionGoNeeded : IComponentData { }

// Reference component (added after spawn):
public struct CompanionGoRef : IComponentData
{
    public UnityObjectRef<GameObject> Go;
}

// PHASE 1 — SPAWN: create GO when marker present, ref absent:
[UpdateInGroup(typeof(InitializationSystemGroup))]
public partial class CompanionGoSpawnSystem : SystemBase
{
    protected override void OnUpdate()
    {
        var ecb = new EntityCommandBuffer(Allocator.Temp);

        foreach (var (_, entity) in
            SystemAPI.Query<RefRO<CompanionGoNeeded>>()
                     .WithNone<CompanionGoRef>()
                     .WithEntityAccess())
        {
            var go = new GameObject("Companion_" + entity.Index);
            ecb.AddComponent(entity, new CompanionGoRef { Go = go });
            ecb.RemoveComponent<CompanionGoNeeded>(entity);
        }

        ecb.Playback(EntityManager);
        ecb.Dispose();
    }
}

// PHASE 2 — SYNC: update GO transform every frame (PresentationSystemGroup):
// See wave7-ecs-to-go-transform-sync.md

// PHASE 3 — DESTROY: clean up GO when ref present but entity marked for removal:
[UpdateInGroup(typeof(InitializationSystemGroup))]
public partial class CompanionGoDestroySystem : SystemBase
{
    protected override void OnUpdate()
    {
        var ecb = new EntityCommandBuffer(Allocator.Temp);

        // ICleanupComponentData pattern — entity destroyed but CompanionGoRef remains:
        foreach (var (goRef, entity) in
            SystemAPI.Query<RefRO<CompanionGoRef>>()
                     .WithNone<CompanionGoNeeded>()
                     .WithEntityAccess())
        {
            var go = goRef.ValueRO.Go.Value;
            if (go != null)
                UnityEngine.Object.Destroy(go);

            ecb.RemoveComponent<CompanionGoRef>(entity);
        }

        ecb.Playback(EntityManager);
        ecb.Dispose();
    }
}
```

## Anti-Patterns
- Instantiating GOs inside Burst jobs — not allowed; GO creation is main-thread only.
- Forgetting to destroy the GO when the entity is destroyed — persistent GO leak, invisible in profiler until scene unload.
- Updating GO transform outside PresentationSystemGroup — out-of-order sync; Transform reflects pre-simulation state.
- Using CompanionGoRef directly as ICleanupComponentData — ICleanupComponentData has special structural semantics; better to use a separate cleanup component or explicit destroy system.
- Creating companion GOs per-frame without pooling — GO instantiation is expensive; pool or batch.

## Runtime Risks
- If entity is destroyed before destroy system runs, GO persists until next frame — use ICleanupComponentData on CompanionGoRef to guarantee cleanup system runs even after entity destruction.
- UnityObjectRef<GameObject>.Value returns null if GO was destroyed externally — always null-guard in sync and destroy systems.

## Performance Notes
- GO instantiation: expensive (main thread, GC, physics registration). Batch in InitializationSystemGroup. Never instantiate per-frame.
- Object.Destroy is deferred to end of frame by Unity — GO persists in scene until then.
- Profile sync system at >200 companion GOs — see wave7-ecs-to-go-transform-sync.md for culling strategies.

## Architecture Guidance
- Four-phase lifecycle: Marker → Spawn → Sync → Destroy.
- Spawn and Destroy: InitializationSystemGroup.
- Sync: PresentationSystemGroup exclusively.
- Never read GO Transform.position back into ECS — ECS is the source of truth.

## Related Skills
[[wave7-ecs-to-go-transform-sync]], [[wave7-add-component-object-hybrid-attach]], [[wave7-idisposable-managed-component]], [[icleanupcomponentdata-runtime]], [[wave7-unity-object-ref-blittable-asset]]
