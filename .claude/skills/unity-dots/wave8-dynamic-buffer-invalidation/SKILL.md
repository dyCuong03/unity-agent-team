---
name: wave8-dynamic-buffer-invalidation
description: Prevent unsafe access to DynamicBuffer references after structural changes have invalidated the underlying chunk memory pointer.
---

# DynamicBuffer Invalidation After Structural Changes

## Intent
Prevent unsafe access to DynamicBuffer references after structural changes have invalidated the underlying chunk memory pointer.

## Use When
- Any system reads a DynamicBuffer reference and then performs structural changes (AddComponent, RemoveComponent, DestroyEntity, CreateEntity) on any entity in the same frame

## Avoid When
- No structural changes occur in the system — buffer references are stable within a single structural-change-free frame

## Senior Pattern
```csharp
// WRONG — structural change invalidates the buffer reference:
var buffer = SystemAPI.GetBuffer<WaypointElement>(entity);
EntityManager.AddComponent<DeadTag>(entity);   // structural change — buffer pointer now invalid
var count = buffer.Length;                      // undefined behavior, potential crash

// CORRECT — read buffer contents before structural change:
var buffer = SystemAPI.GetBuffer<WaypointElement>(entity);
var waypointCount = buffer.Length;             // read before structural change
var lastWaypoint = waypointCount > 0 ? buffer[waypointCount - 1] : default;

// Then defer structural change via ECB:
var ecb = new EntityCommandBuffer(Allocator.Temp);
ecb.AddComponent<DeadTag>(entity);             // deferred — buffer still valid until Playback
ecb.Playback(EntityManager);
ecb.Dispose();
// After Playback: buffer reference is invalid — do not access

// CORRECT alternative — re-fetch after structural change:
EntityManager.AddComponent<DeadTag>(entity);                      // structural change
var freshBuffer = SystemAPI.GetBuffer<WaypointElement>(entity);   // re-fetch
```

## Anti-Patterns
- Storing a DynamicBuffer reference in a field and reading it across system updates — invalid after any structural change.
- Calling EntityManager.GetBuffer<T> and then EntityManager.AddComponent in the same method without re-fetching — pointer invalidation.
- Caching buffer references in NativeArray fields between frames — never valid across structural changes.
- Reading a buffer reference after ECB.Playback in the same method — Playback is a structural change; the reference is invalid after it.

## Runtime Risks
- Access to invalidated buffer memory causes silent data corruption or NullReferenceException.
- The safety system catches this in editor builds (throws InvalidOperationException) but may silently corrupt in release builds — do not rely on editor-only detection.

## Performance Notes
- Re-fetching a buffer is cheap (O(1) archetype lookup). The cost of getting it wrong is a crash or corruption.
- Always prefer ECB to defer structural changes and keep buffer references valid for the current frame's read pass.

## Architecture Guidance
- Treat DynamicBuffer references as frame-scoped and structural-change-scoped.
- Separate read passes from structural change passes within a system's OnUpdate.
- Use ECB to push structural changes after all reads complete.
- If both read and structural change are required in the same method, re-fetch the buffer after the structural change.

## Related Skills
[[entity-command-buffer]], [[ecb-system-timing]], [[toentityarray-snapshot-pattern]], [[structural-change-cost-model]]
