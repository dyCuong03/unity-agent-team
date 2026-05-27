---
name: icleanupcomponentdata-runtime
description: React to entity destruction at runtime by attaching a cleanup component that survives DestroyEntity, allowing a system to detect destroyed entities, release associated resources, and finalise true ...
tags: [structural-change, lifecycle]
---

# ICleanupComponentData — Runtime Entity Lifecycle

## Intent
React to entity destruction at runtime by attaching a cleanup component that survives DestroyEntity, allowing a system to detect destroyed entities, release associated resources, and finalise true removal.

## Use When
An entity owns external resources (GPU buffers, physics bodies, audio instances, spatial index entries, registry slots) that must be explicitly released when the entity is destroyed. Any system that needs an "on-destroy" callback pattern.

## Avoid When
The entity has no associated resources requiring cleanup — cleanup components add chunk overhead for entities that don't need them. Do not use in the baking world without [BakingType] (see [[baking-type-cleanup-component]] for baking lifecycle tracking).

## Senior Pattern
- Declare `public struct MyCleanup : ICleanupComponentData { /* resource handles */ }`.
- A setup system adds MyCleanup to entities when they are created (or when the resource is acquired).
- DestroyEntity removes all non-cleanup components but keeps MyCleanup — the entity persists in a "tombstone" state.
- Cleanup system query: `.WithAll<MyCleanup>().WithNone<MyMainComponent>()` — matches only destroyed entities.
- Cleanup system: releases resource, then `ecb.RemoveComponent<MyCleanup>(entity)` — triggers true entity destruction.

## Code Template
```csharp
public struct AudioInstanceCleanup : ICleanupComponentData
{
    public int AudioHandle;
}

// Setup system — adds cleanup when audio entity is created
[BurstCompile]
public partial struct AudioSetupSystem : ISystem
{
    public void OnUpdate(ref SystemState state)
    {
        var ecb = SystemAPI
            .GetSingleton<BeginSimulationEntityCommandBufferSystem.Singleton>()
            .CreateCommandBuffer(state.WorldUnmanaged);

        foreach (var (audio, entity) in
            SystemAPI.Query<RefRO<AudioSource>>()
                .WithNone<AudioInstanceCleanup>()
                .WithEntityAccess())
        {
            int handle = AcquireAudioHandle(audio.ValueRO.ClipId);
            ecb.AddComponent(entity, new AudioInstanceCleanup { AudioHandle = handle });
        }
    }
}

// Cleanup system — detects destroyed audio entities, releases resources
[BurstCompile]
public partial struct AudioCleanupSystem : ISystem
{
    public void OnUpdate(ref SystemState state)
    {
        var ecb = SystemAPI
            .GetSingleton<BeginSimulationEntityCommandBufferSystem.Singleton>()
            .CreateCommandBuffer(state.WorldUnmanaged);

        // WithNone<AudioSource> = entity was destroyed (cleanup survived)
        foreach (var (cleanup, entity) in
            SystemAPI.Query<RefRO<AudioInstanceCleanup>>()
                .WithNone<AudioSource>()
                .WithEntityAccess())
        {
            ReleaseAudioHandle(cleanup.ValueRO.AudioHandle);
            ecb.RemoveComponent<AudioInstanceCleanup>(entity);  // triggers true destruction
        }
    }
}
```

## Anti-Patterns
- Query `.WithAll<MyCleanup, MyMainComponent>()` — matches live entities, not destroyed ones. Correct pattern is WithNone<MainComponent>.
- Forgetting to RemoveComponent<MyCleanup> after processing — entity persists forever as a tombstone, chunk space permanently consumed.
- Adding cleanup without a corresponding system to remove it — permanent entity leak.
- Using ICleanupComponentData for state that should be handled by ECB DestroyEntity alone — unnecessary complexity.

## Runtime Risks
- Missing cleanup removal: entity never truly destroys, archetype chunk fills with tombstones over time, memory leak.
- Wrong query (WithAll instead of WithNone on main component): processes live entities as if they're destroyed, incorrect resource release.

## Performance Notes
Tombstone entities occupy chunk space from DestroyEntity until cleanup removal. In high-entity-count games with frequent destruction, delayed cleanup accumulates. Always process and remove cleanup in the same frame it's detected.

## Architecture Guidance
ICleanupComponentData is the ECS equivalent of a destructor. Use it deliberately — only for entities with genuine resource associations. Keep the cleanup component lean (just the handles needed for release). The setup + tombstone + cleanup pattern is a three-system lifecycle: acquire → use → release.

## Related Skills
[[entity-command-buffer]], [[ecb-system-timing]], [[baking-type-cleanup-component]]
