---
name: ecb-manual-immediate
description: Create an ECB inline within a single OnUpdate, play it back immediately, and dispose it — for cases where the structural change must be visible within the same system update without waiting for an ...
tags: [ecb]
---

# ECB Manual Immediate Playback

## Intent
Create an ECB inline within a single OnUpdate, play it back immediately, and dispose it — for cases where the structural change must be visible within the same system update without waiting for an ECBSystem boundary.

## Use When
One-shot initialisation systems. Cleanup after spawn (destroy the trigger entity immediately). Any scenario where a one-frame delay from an ECBSystem is semantically incorrect.

## Avoid When
The structural change happens inside a ScheduleParallel job — manual ECBs are not thread-safe without AsParallelWriter. Avoid for recurring per-frame operations — manual ECB allocation has more overhead than reusing an ECBSystem's pre-allocated buffer.

## Senior Pattern
- `var ecb = new EntityCommandBuffer(Allocator.Temp)` — cheapest allocator for within-frame use.
- Record commands during main-thread iteration (SystemAPI.Query foreach is safe for recording — structural changes happen at Playback, not during recording).
- `ecb.Playback(state.EntityManager)` — executes all recorded structural changes immediately.
- Allocator.Temp is automatically reclaimed at end of frame — no explicit Dispose needed, but calling it is harmless.
- Pair with `state.Enabled = false` for one-shot init systems that must never run again.

## Code Template
```csharp
[BurstCompile]
public partial struct SpawnAndCleanupSystem : ISystem
{
    public void OnCreate(ref SystemState state)
        => state.RequireForUpdate<SpawnTrigger>();

    public void OnUpdate(ref SystemState state)
    {
        var ecb = new EntityCommandBuffer(Allocator.Temp);

        foreach (var (trigger, entity) in
            SystemAPI.Query<RefRO<SpawnTrigger>>().WithEntityAccess())
        {
            for (int i = 0; i < trigger.ValueRO.Count; i++)
            {
                var spawned = ecb.Instantiate(trigger.ValueRO.Prefab);
                ecb.SetComponent(spawned, LocalTransform.FromPosition(
                    trigger.ValueRO.Origin + new float3(i, 0, 0)));
            }
            ecb.DestroyEntity(entity);  // remove the trigger
        }

        ecb.Playback(state.EntityManager);
        // state.Enabled = false;  // uncomment for true one-shot systems
    }
}
```

## Anti-Patterns
- Forgetting `ecb.Playback(state.EntityManager)` — all recorded commands are silently discarded, no error.
- Using Allocator.TempJob for a within-frame ECB — requires manual Dispose and has higher allocation cost than Temp.
- Using Allocator.Persistent for a within-frame ECB — allocates from the heap, must be disposed, no benefit.
- Calling Playback inside the SystemAPI.Query foreach that's still iterating — structural changes during iteration = iterator invalidation.

## Runtime Risks
- Missing Playback: silent no-op — the entity transformation never happens, bugs are invisible until runtime.
- Playback inside foreach: access exception or silent data corruption.

## Performance Notes
Allocator.Temp is allocation-free in practice (uses a linear allocator). Manual Playback is a synchronous structural change pass on the main thread — acceptable for infrequent one-shot use, not for per-frame hot paths.

## Architecture Guidance
Manual ECB = tactical immediate control. Reserve for init/cleanup systems. For recurring simulation-phase structural changes, always prefer ECBSystem boundaries.

## Related Skills
[[entity-command-buffer]]
