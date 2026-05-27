---
name: ecb-multiplayback
description: Create a reusable ECB with PlaybackPolicy.MultiPlayback that can be played back multiple times — for streaming scenarios where the same entity creation sequence must execute on every subscene load.
---

# ECB MultiPlayback — Reusable Command Buffers

## Intent
Create a reusable ECB with PlaybackPolicy.MultiPlayback that can be played back multiple times — for streaming scenarios where the same entity creation sequence must execute on every subscene load.

## Use When
Subscene streaming systems that must replay a fixed set of entity creation commands each time a section loads. Any pattern where an ECB is serialised into a component and replayed on demand.

## Avoid When
The ECB is only played back once — SinglePlayback (the default) is sufficient and cheaper. Avoid Allocator.Temp or TempJob for MultiPlayback ECBs — they must use Allocator.Persistent.

## Senior Pattern
- `new EntityCommandBuffer(Allocator.Persistent, PlaybackPolicy.MultiPlayback)` — persistent lifetime, multi-replay safe.
- Store the ECB in a component field (e.g., `struct PostLoadCommandBuffer : IComponentData { public EntityCommandBuffer CommandBuffer; }`).
- Call `ecb.Playback(entityManager)` on each subscene load event.
- Dispose the ECB explicitly when the owning entity is destroyed (OnDestroy hook or cleanup system).

## Code Template
```csharp
public struct SectionPostLoadCommands : IComponentData
{
    public EntityCommandBuffer CommandBuffer;
}

// At bake time or init: create the reusable ECB
var ecb = new EntityCommandBuffer(Allocator.Persistent, PlaybackPolicy.MultiPlayback);
var setupEntity = ecb.CreateEntity();
ecb.AddComponent(setupEntity, new SectionConfig { TileOffset = offset });
state.EntityManager.AddComponentData(sectionEntity,
    new SectionPostLoadCommands { CommandBuffer = ecb });

// On each section load:
var commands = SystemAPI.GetComponent<SectionPostLoadCommands>(sectionEntity);
commands.CommandBuffer.Playback(state.EntityManager);

// On section unload / entity destroy:
commands.CommandBuffer.Dispose();
```

## Anti-Patterns
- Using PlaybackPolicy.SinglePlayback (default) and calling Playback twice — second call throws a safety exception.
- Using Allocator.Temp or TempJob with MultiPlayback — the ECB is freed before the second playback.
- Forgetting to Dispose a Persistent ECB — memory leak that persists until world destruction.
- Using MultiPlayback for a single-use ECB — unnecessary overhead and complexity.

## Runtime Risks
- SinglePlayback called twice: InvalidOperationException on second Playback.
- Missing Dispose on Persistent ECB: memory leak.

## Performance Notes
Allocator.Persistent is heap-allocated — higher overhead than Temp. Use only when the multi-replay semantics are genuinely required. For the streaming use case, the cost is negligible (one ECB per subscene section).

## Architecture Guidance
MultiPlayback ECB = a reusable command script. Treat it as a data asset stored in a component, not as an ephemeral command buffer. Scope its lifetime explicitly to the subscene section or the system that owns it.

## Related Skills
[[entity-command-buffer]]
