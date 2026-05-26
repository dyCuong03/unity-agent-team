---
name: dots-event-driven-ecs
description: Model one-frame events and external requests in ECS without dual ownership, polling, or persistent state leaks. Covers request-tag pattern with ECB, enableable command components (no structural change), event buffers (IBufferElementData), explicit consumer ownership, one-frame latency rules, and the banned C# event / UnityEvent / static bus anti-patterns. Use when input/UI/network must trigger ECS work, when a one-frame signal fans out to N consumers (damage, hit, collision), or when state changes must be processed exactly once.
---

# Event-Driven ECS — Senior Patterns

There is no event bus in Entities 1.x. There never will be. Senior teams encode events as **data** with explicit lifetime and explicit consumer ownership — request entities, enableable command components, and event buffers. Anything else (`Action`, `UnityEvent`, static collections) is a managed-world anti-pattern that breaks Burst, breaks determinism, and breaks replays.

## Intent

Make one-shot signals first-class data. Every event has a producer system, a known lifetime, exactly one named consumer (or an explicit broadcast contract), and a guaranteed clearing point.

## Three event shapes (pick by lifetime + cardinality)

| Shape | Lifetime | Cardinality | Cost |
|---|---|---|---|
| **Request entity** (transient `Entity` carrying a request component, destroyed by consumer) | 1 frame | producer → 1 consumer | Structural change (use ECB) |
| **Enableable command component** (per-entity enabled bit) | 1 frame typically; can persist | 1 entity → 1 consumer that watches the enabled-set | **Zero structural change** (preferred for hot paths) |
| **Event buffer** (`DynamicBuffer<T>` on a known entity, cleared by a late-phase system) | 1 frame, broadcast | 1 producer → N readers | Allocation per frame; broadcast model |

## Senior pattern — request entity (one-shot, simple)

```csharp
public struct DamageRequest : IComponentData
{
    public Entity Target;
    public float  Amount;
}

// Producer (e.g. collision system): record request, ECB plays back.
public partial struct CollisionDamageSystem : ISystem
{
    public void OnCreate(ref SystemState state)
        => state.RequireForUpdate<EndSimulationEntityCommandBufferSystem.Singleton>();

    public void OnUpdate(ref SystemState state)
    {
        var ecb = SystemAPI.GetSingleton<EndSimulationEntityCommandBufferSystem.Singleton>()
                           .CreateCommandBuffer(state.WorldUnmanaged);

        // On collision detection...
        var req = ecb.CreateEntity();
        ecb.AddComponent(req, new DamageRequest { Target = hitEntity, Amount = 10f });
    }
}

// Consumer: applies damage, destroys the request. EXACTLY ONE consumer.
public partial struct DamageApplySystem : ISystem
{
    public void OnCreate(ref SystemState state)
    {
        state.RequireForUpdate<DamageRequest>();
        state.RequireForUpdate<BeginSimulationEntityCommandBufferSystem.Singleton>();
    }

    public void OnUpdate(ref SystemState state)
    {
        var ecb = SystemAPI.GetSingleton<BeginSimulationEntityCommandBufferSystem.Singleton>()
                           .CreateCommandBuffer(state.WorldUnmanaged);

        foreach (var (req, entity) in
                 SystemAPI.Query<RefRO<DamageRequest>>().WithEntityAccess())
        {
            if (SystemAPI.HasComponent<HealthComponent>(req.ValueRO.Target))
            {
                var hpRef = SystemAPI.GetComponentRW<HealthComponent>(req.ValueRO.Target);
                hpRef.ValueRW.Current -= req.ValueRO.Amount;
            }
            ecb.DestroyEntity(entity); // request consumed
        }
    }
}
```

## Senior pattern — enableable command (hot-path, no structural change)

```csharp
// Per-entity command flag — zero archetype churn.
public struct WantsRespawn : IComponentData, IEnableableComponent { }

// Producer: enables the bit when criteria met.
public partial struct RespawnTriggerSystem : ISystem
{
    public void OnUpdate(ref SystemState state)
    {
        foreach (var (hp, respawnEnabled, _) in
                 SystemAPI.Query<RefRO<HealthComponent>, EnabledRefRW<WantsRespawn>>()
                          .WithEntityAccess())
        {
            if (hp.ValueRO.Current <= 0) respawnEnabled.ValueRW = true;
        }
    }
}

// Consumer: processes only entities whose WantsRespawn is enabled (default query semantics).
public partial struct RespawnApplySystem : ISystem
{
    public void OnUpdate(ref SystemState state)
    {
        foreach (var (transform, respawnEnabled) in
                 SystemAPI.Query<RefRW<LocalTransform>, EnabledRefRW<WantsRespawn>>())
        {
            transform.ValueRW.Position = SpawnPoint;
            respawnEnabled.ValueRW = false; // clear the command
        }
    }
}
```

This is the preferred shape for any "per-entity one-frame command" — no ECB, no structural change. See `dots-enableable-components`.

## Senior pattern — broadcast via event buffer

```csharp
public struct CombatEvent : IBufferElementData
{
    public Entity Attacker;
    public Entity Victim;
    public float  Damage;
}

// Producer writes to a buffer on a known singleton entity.
// Multiple readers consume; a dedicated cleanup system clears.

public partial struct CombatEventClearSystem : ISystem
{
    [UpdateInGroup(typeof(SimulationSystemGroup), OrderLast = true)]
    public void OnUpdate(ref SystemState state)
    {
        var buf = SystemAPI.GetSingletonBuffer<CombatEvent>();
        buf.Clear();
    }
}
```

## Anti-patterns

- ❌ `Action<DamageEvent>` / `UnityEvent` / static `List<Event>` for ECS gameplay. Breaks Burst. Breaks determinism. Cannot exist inside `ISystem`. Refuse.
- ❌ Boolean field on a persistent component used as a one-shot flag (`bool IsHit`). Will leak across frames because clearing it isn't enforced by the type system. Use `IEnableableComponent` instead.
- ❌ Two systems consuming the same request component with no defined consumer ownership. They race to destroy the request; one may apply damage twice; one may apply zero times. If two systems must react to the same event, they consume different shapes or read from a shared buffer with `OrderLast` cleanup.
- ❌ Creating request entities from a parallel job without ECB sort key (`[ChunkIndexInQuery]`). Non-deterministic event order — replay bug.
- ❌ Leaving event entities undestroyed "for debugging." They accumulate across frames; the next frame's consumer applies stale damage.
- ❌ A buffer-based broadcast where the cleanup system is gated by `RequireForUpdate<Something>` that excludes the buffer's host entity. Cleanup never runs → unbounded buffer growth.

## Failure modes

| Symptom | Cause |
|---|---|
| Damage applied twice | Two consumer systems read the same `DamageRequest`; both processed before either destroyed |
| Event silently dropped | Consumer in a group/phase that executes *before* producer this frame — see `dots-update-groups` |
| Request entities accumulate forever | Consumer gated wrong, or producer side wasn't paired with a consumer |
| Hit registers next frame for some entities, this frame for others | Mixed ECB phases — producer used `BeginSimulationECB`, sometimes `EndSimulationECB` |
| Replays diverge | Parallel job recorded requests without `[ChunkIndexInQuery]` sort key |
| Burst error on event field | Event component holds managed type (string, class); switch to `FixedString` / blittable |

## Runtime verification (Tester Verification Contract)

- **Static:** for every `IComponentData` whose name ends in `Request` / `Event` / `Command`, grep for exactly one consumer system that destroys it (or for an `IEnableableComponent` request, one consumer that sets it false). Zero or >1 → reject.
- **Runtime:** after one full frame of producing M events, the query count of un-consumed events must be exactly 0 (request entity pattern) or all bits must be cleared (enableable pattern). Run a soak test for 100 frames at peak event rate; assert no growth in event entity count.

## Performance notes

- Request-entity pattern costs M structural changes per M events (create + destroy). Batched via ECB it's tolerable up to a few thousand events/frame. Beyond that, switch to enableable.
- Enableable pattern is essentially free per event (one bit flip). The cost is "do you have a component on the entity?" — if not, you pay one structural add at attachment time and never again.
- Event buffers cost the buffer's chunk size + per-event element write. Clear cost is O(events). Buffer-singleton broadcast is the cheapest "1→N" pattern when N readers really need the same events.

## Compile / editor safety

- `IBufferElementData` types must be blittable. No managed fields. Use `FixedString64Bytes` for inline strings.
- Event components targeting Burst hot paths should be `[BurstCompile]`-friendly: no `UnityObjectRef<T>` deref inside the producer/consumer's job code (capture and pre-deref on main thread).

## Entities version notes (1.4.x)

- `IEnableableComponent` + `EnabledRefRW<T>` — current; preferred shape for hot-path per-entity events.
- `ECB.CreateEntity()` + `AddComponent` for request pattern — current.
- C# `event` keyword / `UnityEvent` / `Action<T>` — banned inside `ISystem`; not Burst-safe.
- `EntityCommandBuffer.ParallelWriter.CreateEntity(sortKey)` requires `[ChunkIndexInQuery] int chunkIndex` parameter — see `dots-ecb-orchestration`.

## See also
- `dots-enableable-components` — the zero-archetype-churn implementation detail for command components
- `dots-ecb-orchestration` — phase selection for parallel event creation
- `dots-entity-lifecycle` — request entities need disciplined destroy; cleanup-component pattern if state must outlive the entity
- `dots-update-groups` — producer-before-consumer ordering
