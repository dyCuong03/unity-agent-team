---
name: dots-ecb-orchestration
description: Senior-level EntityCommandBuffer orchestration — which ECB system to record into, when playback happens, ParallelWriter rules, deterministic sort keys, and the difference between recording phase and playback phase. Use whenever code defers structural changes from jobs (AddComponent / RemoveComponent / Instantiate / DestroyEntity / SetComponentEnabled inside an `IJobEntity` / `IJobChunk`).
metadata:
  internal-only: true
  tier: 3
---

# ECB Orchestration — Senior Patterns

Structural changes inside a scheduled job are forbidden. The EntityCommandBuffer (ECB) records the intent in a job and plays it back on the main thread at a specific phase. Choosing the wrong phase silently delays your change by one frame, deadlocks dependency chains, or splits an atomic state transition.

## Intent

Defer structural mutations (and `Enabled` flips done from jobs) into a recorder, then let a known ECB system play them back at a deterministic point in the frame.

## The mental model: pick by playback phase, not by name

| ECB system | Plays back at | Use when |
|---|---|---|
| `BeginInitializationEntityCommandBufferSystem` | Start of frame, before any simulation | Bootstrapping at frame start |
| `EndInitializationEntityCommandBufferSystem` | End of init, before simulation | Last chance to set up before sim sees state |
| `BeginSimulationEntityCommandBufferSystem` | Start of simulation group | **Default choice** for "next frame" structural changes recorded this frame |
| `EndSimulationEntityCommandBufferSystem` | End of simulation, before presentation | When you need all sim systems to see the recorded change before presentation reads it |
| `BeginFixedStepSimulationEntityCommandBufferSystem` | Each fixed step start | Fixed-step physics-coupled mutations |
| `EndFixedStepSimulationEntityCommandBufferSystem` | Each fixed step end | After fixed-step sim, before per-frame sim |

**Decision rule:** Identify the reader of the post-change state. Pick the ECB that plays back **before** that reader.

## Senior pattern (single-writer, parallel job)

```csharp
public partial struct DestroyFallenSystem : ISystem
{
    [BurstCompile]
    public void OnCreate(ref SystemState state)
    {
        // Declare the dependency. Don't search for the ECB system every OnUpdate.
        state.RequireForUpdate<BeginSimulationEntityCommandBufferSystem.Singleton>();
    }

    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var ecbSingleton = SystemAPI.GetSingleton<BeginSimulationEntityCommandBufferSystem.Singleton>();
        var ecb = ecbSingleton.CreateCommandBuffer(state.WorldUnmanaged);

        // For parallel-scheduled jobs:
        var ecbParallel = ecb.AsParallelWriter();

        new DestroyFallenJob
        {
            EcbParallel = ecbParallel,
        }.ScheduleParallel();
    }
}

[BurstCompile]
partial struct DestroyFallenJob : IJobEntity
{
    public EntityCommandBuffer.ParallelWriter EcbParallel;

    void Execute([ChunkIndexInQuery] int chunkIndex, Entity entity, in LocalTransform t)
    {
        if (t.Position.y < 0f)
            EcbParallel.DestroyEntity(chunkIndex, entity);
    }
}
```

Key invariants:
- `[ChunkIndexInQuery]` provides the **sort key** for `ParallelWriter`. Commands are sorted by this key before playback, giving deterministic order even though job execution order is not deterministic.
- Get the ECB singleton via `RequireForUpdate<...Singleton>` + `SystemAPI.GetSingleton<...Singleton>()`. Don't cache an ECB across frames.
- One `CreateCommandBuffer` per system per frame. Don't reuse a buffer across frames or across systems.

## Sequential job (`Schedule()` not `ScheduleParallel()`)

If you call `.Schedule()` use a serial writer:

```csharp
new MyJob { Ecb = ecb }.Schedule(); // ecb here is the EntityCommandBuffer itself, not AsParallelWriter()
```

`ParallelWriter` requires the chunk-index sort key. A serial writer does not.

## Anti-patterns

- ❌ `state.EntityManager.AddComponent<Foo>(entity)` **inside** a scheduled job — instant crash with safety checks; corruption without.
- ❌ Calling `ecb.Playback(state.EntityManager)` manually. The ECB system plays back for you. Manual playback inside `OnUpdate` defeats the deferral.
- ❌ Multiple playbacks of the same recorder — once an ECB is played back, it must be disposed. The ECB system handles this.
- ❌ Using `AsParallelWriter()` and forgetting the `[ChunkIndexInQuery] int chunkIndex` parameter. Compiles, but commands play back in non-deterministic order — replay bugs.
- ❌ Recording into End*EntityCommandBuffer when the next system **in the same group, this frame** must see the change. Use Begin* of the next phase, or End* of the current phase, whichever runs *before* the reader.
- ❌ One ECB to span multiple frames. Recorders are single-frame artifacts.

## Failure modes

| Symptom | Likely cause |
|---|---|
| Changes appear one frame late | Wrong phase — picked End* when reader runs at start of frame |
| Same change applied twice | Two systems recording into the same ECB phase, both creating the entity |
| `InvalidOperationException: The EntityCommandBuffer has already been played back` | Manual `Playback()` plus the ECB system also playing back |
| Non-deterministic replays under the same seed | `ParallelWriter` used without `[ChunkIndexInQuery]` sort key |
| Crash on `RemoveComponent` of a component the entity doesn't have | ECB does not check; guard your job logic (`[WithAll]` / `[WithNone]`) |

## Runtime verification (Tester Verification Contract)

- **Static:** every `.ScheduleParallel()` whose job touches `EntityCommandBuffer.ParallelWriter` must accept `[ChunkIndexInQuery] int chunkIndex`; grep for `AsParallelWriter()` without a paired `[ChunkIndexInQuery]` parameter.
- **Runtime:** assert post-frame entity count matches expectation; assert determinism by running the same scenario twice with the same seed and comparing component snapshots.

## Performance notes

- ECBs allocate. Avoid creating one per entity. One ECB per system per frame is normal; one per entity is a bug.
- `ParallelWriter` adds a small per-command overhead vs a serial writer (sort key bookkeeping). Use serial when the job is `.Schedule()`.
- Playback cost scales with command count. If you find yourself recording thousands of `AddComponent` per frame, prefer **enableable components** (see `dots-enableable-components`) — no structural change, no ECB, no archetype move.

## Compile / editor safety

- `[BurstCompile]` on the job is required for hot paths. The ECB system itself is Burst-compatible.
- Do not capture managed objects in the job struct. The ECB itself is a value type — safe.

## Entities version notes (1.4.x)

- `EntityCommandBufferSystem.Singleton` (the `Singleton` nested type) is the current accessor. Old code referenced `World.GetExistingSystemManaged<BeginSimulationEntityCommandBufferSystem>().CreateCommandBuffer()` — refuse to write that.
- `AsParallelWriter()` + `[ChunkIndexInQuery]` is the current sort-key contract. Old code passing `int jobIndex` manually is a 0.x pattern.

## See also
- `dots-enableable-components` — first ask "do I actually need a structural change?"
- `dots-entity-lifecycle` — destroy/cleanup flows that depend on ECB phase
- `dots-spawning-patterns` — Instantiate via ECB from a job
