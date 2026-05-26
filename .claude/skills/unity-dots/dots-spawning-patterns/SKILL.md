---
name: dots-spawning-patterns
description: Senior-level entity spawning — batched Instantiate from prefab Entity, ECB.Instantiate from jobs, deterministic Random with CreateFromIndex, RequireForUpdate gating, and Allocator.Temp lifecycle. Use when implementing spawners, enemy waves, projectile fire, particle-like ECS entities, or any "create N entities per frame" code.
---

# Spawning Patterns — Senior Patterns

Spawning N entities efficiently is the difference between a 60fps shooter and a 6fps slideshow. The correct pattern is batched `Instantiate` from a baked prefab Entity, recorded into an ECB when called from a job, with a deterministic seed.

## Intent

Create entities in bulk, deterministically, without main-thread cost in hot paths.

## Senior pattern — main-thread spawner (one batch per trigger)

```csharp
public partial struct SpawnSystem : ISystem
{
    uint m_UpdateCounter;

    [BurstCompile]
    public void OnCreate(ref SystemState state)
    {
        // Don't run until a Spawner singleton exists (set by baking).
        state.RequireForUpdate<Spawner>();
    }

    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var spinningCubesQuery = SystemAPI.QueryBuilder().WithAll<RotationSpeed>().Build();

        // Only spawn when none exist — bursty, not per-frame.
        if (!spinningCubesQuery.IsEmpty) return;

        var prefab = SystemAPI.GetSingleton<Spawner>().Prefab;

        // Batched: instantiate 500 in one call, return a temp NativeArray of entities.
        var instances = state.EntityManager.Instantiate(prefab, 500, Allocator.Temp);

        // Deterministic random: CreateFromIndex hashes the seed so consecutive
        // seeds don't produce visually-similar results.
        var rng = Random.CreateFromIndex(m_UpdateCounter++);

        foreach (var entity in instances)
        {
            var transform = SystemAPI.GetComponentRW<LocalTransform>(entity);
            transform.ValueRW.Position = (rng.NextFloat3() - new float3(0.5f, 0, 0.5f)) * 20f;
        }
        // Allocator.Temp auto-frees at end of frame. No manual Dispose.
    }
}
```

## Senior pattern — spawn from inside a parallel job

When spawn cadence depends on per-entity state (e.g. each turret fires when its cooldown expires):

```csharp
public partial struct TurretFireSystem : ISystem
{
    [BurstCompile]
    public void OnCreate(ref SystemState state) {
        state.RequireForUpdate<Spawner>();
        state.RequireForUpdate<BeginSimulationEntityCommandBufferSystem.Singleton>();
    }

    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var prefab = SystemAPI.GetSingleton<Spawner>().BulletPrefab;
        var ecb = SystemAPI.GetSingleton<BeginSimulationEntityCommandBufferSystem.Singleton>()
                           .CreateCommandBuffer(state.WorldUnmanaged)
                           .AsParallelWriter();

        new FireJob {
            Ecb = ecb,
            Prefab = prefab,
            Dt = SystemAPI.Time.DeltaTime,
        }.ScheduleParallel();
    }
}

[BurstCompile]
partial struct FireJob : IJobEntity
{
    public EntityCommandBuffer.ParallelWriter Ecb;
    public Entity Prefab;
    public float Dt;

    void Execute([ChunkIndexInQuery] int chunkIndex,
                 ref TurretCooldown cd,
                 in LocalTransform t)
    {
        cd.TimeLeft -= Dt;
        if (cd.TimeLeft > 0) return;
        cd.TimeLeft = cd.Interval;

        // Record the spawn; ECB plays back next frame.
        var bullet = Ecb.Instantiate(chunkIndex, Prefab);
        Ecb.SetComponent(chunkIndex, bullet, LocalTransform.FromPosition(t.Position));
    }
}
```

## Deterministic randomness

```csharp
// Per-frame seed; the same frame number gives the same sequence — replay-safe.
var rng = Random.CreateFromIndex(updateCounter);

// Per-entity seed (so two entities created on the same frame diverge):
var rng = Random.CreateFromIndex((uint)entity.Index ^ updateCounter);
```

**Banned:**
- `UnityEngine.Random` — managed, not Burst-compatible, not deterministic across runs
- `new Random()` without seed — non-deterministic
- `Random.CreateFromIndex(0)` — `CreateFromIndex` rejects 0; will throw

## Anti-patterns

- ❌ `state.EntityManager.Instantiate(prefab)` called in a loop. Always use the batched overload that takes a count or a destination array.
- ❌ Spawning from a job using `state.EntityManager.Instantiate` directly. Must go through `Ecb.Instantiate` with `[ChunkIndexInQuery]`.
- ❌ Loading the prefab via `Resources.Load` or `Addressables` in `OnUpdate`. The prefab Entity is baked at conversion — fetch it once from a singleton.
- ❌ Spawning N entities per frame "just in case". Gate with `RequireForUpdate<T>` and intent components; spawn bursty, not continuous.
- ❌ Using `Allocator.Persistent` for the temp entity array from `Instantiate`. `Allocator.Temp` is right — it auto-frees at frame end.
- ❌ Forgetting `RequireForUpdate<Spawner>()` in `OnCreate`. Without it, `GetSingleton<Spawner>()` throws if no spawner exists.

## Failure modes

| Symptom | Likely cause |
|---|---|
| Spawn cost spikes in the profiler | Per-entity `Instantiate` instead of batched |
| "InvalidOperationException: Singleton does not exist" | Missing `RequireForUpdate<Spawner>` |
| Spawn position is always (0,0,0) | Forgot to set `LocalTransform` after `Instantiate`; prefab's transform applies but per-entity position not written |
| Replays diverge | `UnityEngine.Random` or unseeded `Random` |
| Crash on `Random.CreateFromIndex(0)` | Seed must be non-zero; use `(updateCounter | 1)` or `++updateCounter` |
| Bullets spawn one frame late | Expected — ECB playback. If you need same-frame visibility, the reader must run after the ECB phase you recorded into |

## Runtime verification

- **Static:** every `Instantiate(prefab)` call should use the batched overload or be wrapped in `Ecb.Instantiate`. Grep for `EntityManager.Instantiate(` with no second argument inside `OnUpdate`.
- **Runtime:** spawn N entities, assert query count rises by exactly N within the expected number of frames (1 for main-thread, 2 for ECB-deferred). Run twice with the same seed; assert positions are bit-identical.

## Performance notes

- Batched `Instantiate(prefab, 500, Allocator.Temp)` is roughly the cost of one structural change, not 500. Always batch.
- The baked prefab Entity has all components fully constructed; spawn copies them. Minimize prefab archetype size if spawning thousands per frame — every byte multiplies.
- Spawning a million entities at once is feasible; spawning ten per frame for a hundred thousand frames is not. Pick burst spawn over sustained drip.

## Compile / editor safety

- The prefab Entity reference is produced by a Baker (see `dots-baking-patterns`). Don't try to load it at runtime.
- `Random` here is `Unity.Mathematics.Random` (`using Unity.Mathematics;`) — Burst-friendly value type. `UnityEngine.Random` looks similar but is managed and banned in hot paths.

## Entities version notes (1.4.x)

- `state.EntityManager.Instantiate(prefab, count, allocator)` is the current batched overload.
- `Random.CreateFromIndex(seed)` is current. Old code used `new Random((uint)Time.frameCount)` — non-deterministic across builds, refuse it.
- `Allocator.Temp` for per-system, single-frame arrays. `Allocator.TempJob` only when an array is passed into a job that may outlive the calling method.

## See also
- `dots-baking-patterns` — how the prefab Entity ref gets made
- `dots-ecb-orchestration` — phase selection for in-job spawn
- `dots-entity-lifecycle` — destruction is the matching half
