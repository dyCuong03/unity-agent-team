---
name: wave6-ecs-state-machine-design
description: Choose the correct ECS state representation — enum field, IEnableableComponent, or structural add/remove — based on transition frequency, state count, and query-filtering requirements.
tags: [enableable, state-machine]
metadata:
  internal-only: true
  tier: 3
---

# ECS State Machine Design — Decision Model

## Intent
Choose the correct ECS state representation — enum field, IEnableableComponent, or structural add/remove — based on transition frequency, state count, and query-filtering requirements.

## Decision Model

| Criterion | Enum Field | IEnableableComponent | Structural Add/Remove |
|-----------|-----------|---------------------|----------------------|
| State count | 3+ exclusive states | Exactly 2 (active/inactive) | Any; data ownership varies |
| Transition frequency | Any | High (per-frame) | Low (lifecycle) |
| Downstream query filter | No (branch in system) | Yes (automatic at query level) | Yes (archetype-level) |
| Memory when inactive | Always present | Always present | Freed |
| Cost per transition | Field write (cheapest) | Bit flip (O(1)) | Chunk move (10-100x) |

## Senior Pattern — Enum FSM
```csharp
public enum BotState { MoveToTarget, Attack, Retreat, Idle, Dead }

public struct BotAI : IComponentData
{
    public BotState State;
    public float StateTimer;
}

[BurstCompile]
public partial struct BotFSMJob : IJobEntity
{
    public float DeltaTime;

    [BurstCompile]
    public void Execute(ref BotAI bot, ref LocalTransform t)
    {
        switch (bot.State)
        {
            case BotState.MoveToTarget:
                bot.StateTimer -= DeltaTime;
                if (bot.StateTimer <= 0) bot.State = BotState.Attack;
                break;
            case BotState.Attack:
                // attack logic
                break;
            // ...
        }
    }
}
```

## Senior Pattern — Enableable Binary Flag
```csharp
// Zero-size component — just the enabled bit matters:
public struct Stealth : IComponentData, IEnableableComponent { }

// Systems automatically see only active entities:
new StealthBehaviorJob().ScheduleParallel(state.Dependency);   // only enabled
new StealthRevealJob().ScheduleParallel(state.Dependency);     // only enabled

// Mixed: enum for internal FSM, enableable for external visibility:
public struct EnemyAI : IComponentData { public EnemyState State; }
public struct DetectedByPlayer : IComponentData, IEnableableComponent { }
// Internal transitions via enum field; player detection via enableable
```

## Senior Pattern — Structural (Lifecycle)
```csharp
// Spawn → Active (ECB adds components once):
ecb.AddComponent<EnemyAI>(entity, new EnemyAI { State = EnemyState.Patrol });
ecb.AddComponent<PhysicsVelocity>(entity, default);

// Death (ECB removes components once — entity enters cleanup archetype):
ecb.RemoveComponent<EnemyAI>(entity);
ecb.AddComponent<DeadTag>(entity);
```

## Anti-Patterns
- Structural AddComponent/RemoveComponent for per-frame transitions — 10-100x more expensive than enum write or bit flip; causes archetype churn.
- IEnableableComponent for 3+ exclusive states — no query can express "exactly state X of N"; use enum.
- Enum fields when downstream systems need to query-filter automatically — requires branch inside every system; enableable components filter at chunk level.
- Creating a separate entity per state — unnecessary structural complexity; prefer enum or enableable on the same entity.

## Performance Benchmark (from ECS StateChange sample)
- Enum field write: fastest for single-entity per-frame transitions
- Enableable bit flip: fastest for bulk query-filtered transitions (no chunk move)
- Structural change: 10-100x slower; reserve for entity lifecycle only

## Architecture Guidance
- Mixed approach is valid and common: enum for internal FSM state, IEnableableComponent for external visibility/behavior flags.
- Document state ownership: which system writes state, which systems read it.
- For 2-state binary: prefer IEnableableComponent when downstream systems should auto-filter; prefer enum field when only one system cares.

## Related Skills
[[enableable-component]], [[wave6-enabled-ref-rw-in-job]], [[wave6-with-disabled-query-filter]], [[structural-change-cost-model]], [[icleanupcomponentdata-runtime]]
