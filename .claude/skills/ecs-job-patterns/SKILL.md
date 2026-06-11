---
name: ecs-job-patterns
description: ECS job scheduling patterns — IJobEntity, IJobChunk, dependency chains, ECB usage, ScheduleParallel safety. Loaded for unity-dots-dev when implementing or debugging DOTS jobs. Replaces the job-optimizer subagent anti-pattern.
use-when: |
  Load for unity-dots-dev when the task involves writing IJobEntity, IJobChunk, ECB playback,
  parallel scheduling, dependency chain setup, or debugging job-related errors such as
  AccessViolation, AtomicSafetyHandle, or AddJobHandleForProducer issues.
do-not-use-when: |
  Do not load for Unity classic MonoBehaviour tasks. Do not load for tester, verifier,
  qa-tester, or data-tool roles. Not needed if the task has no job scheduling.
platforms: [claude-code, codex, copilot, cursor, windsurf]
task-categories: [ecs, jobs, scheduling, performance, dots]
metadata:
  source: https://docs.unity3d.com/Packages/com.unity.entities@1.3
  version: 1.3.8
  tier: 1

---

# ECS Job Patterns

This is a skill pack, not an agent.

## Job Type Selection

| Use case | Pattern |
|----------|---------|
| Per-entity transform/component work, parallelisable | `IJobEntity` with `[WithAll]` / `[WithNone]` query filters |
| Chunk-level access, cache-friendly batch ops | `IJobChunk` |
| One-shot scratch processing across `NativeArray`s | `IJobParallelFor` |
| Single-thread main-loop work | `IJob` |
| Inside `OnUpdate` without scheduling | Foreach via `SystemAPI.Query<...>().WithAll<...>()` |

Rule of thumb: prefer `IJobEntity` unless you specifically need chunk pointers
or cross-chunk accumulation.

## Dependency Chain Discipline

1. **Read `state.Dependency` in.** Schedule with `JobHandle = job.Schedule(state.Dependency)`.
2. **Write `state.Dependency` out.** `state.Dependency = handle;` at the end.
3. **Never call `.Complete()` inside `OnUpdate`** unless you need the result for
   a main-thread action this frame — that is a sync point and must be approved.
4. **Combine handles** with `JobHandle.CombineDependencies(a, b)` when reading
   from two prior systems — do not double-write `state.Dependency` and leak one.

## Structural Changes — Use ECB

Structural changes (`AddComponent`, `RemoveComponent`, `CreateEntity`,
`DestroyEntity`) inside a scheduled job are **always** done via
`EntityCommandBuffer.ParallelWriter`. Never call `EntityManager` from a job.

```csharp
var ecb = SystemAPI.GetSingleton<BeginSimulationEntityCommandBufferSystem.Singleton>()
                   .CreateCommandBuffer(state.WorldUnmanaged).AsParallelWriter();
new MyJob { ecb = ecb }.ScheduleParallel(...);
```

ECB singleton must match the SystemGroup playback point. Pick the right one:

| Playback group | Singleton |
|----------------|-----------|
| `InitializationSystemGroup` | `BeginInitializationEntityCommandBufferSystem.Singleton` |
| Start of `SimulationSystemGroup` | `BeginSimulationEntityCommandBufferSystem.Singleton` |
| End of `SimulationSystemGroup` | `EndSimulationEntityCommandBufferSystem.Singleton` |
| Before `PresentationSystemGroup` | `BeginPresentationEntityCommandBufferSystem.Singleton` |

## ComponentLookup vs SystemAPI

| Need | Use |
|------|-----|
| Random access to a component by entity inside a job | `ComponentLookup<T>` created in `OnUpdate`, passed by value |
| Foreach with full chunk iteration | `SystemAPI.Query<...>()` |
| Singleton read | `SystemAPI.GetSingleton<T>()` |
| Singleton write | `SystemAPI.GetSingletonRW<T>().ValueRW` |

`ComponentLookup` must be `Update`d each `OnUpdate`:
`var lookup = SystemAPI.GetComponentLookup<HealthComponent>(isReadOnly: true);`

## Update Order

Do not change `[UpdateBefore]` / `[UpdateAfter]` / `[UpdateInGroup]` without
architect approval. Scheduling order is architecture; silently changing it is a
`[BLOCK: architecture risk]` per `escalation-policy.md`.

If you genuinely need to add a new system after an existing one:
1. Document the dependency in `workspace/approved_plan.json` under `constraints`.
2. Architect approves before `unity-dev` writes the attribute.

## Pre-Verifier Checklist

- [ ] No `EntityManager.*` calls inside scheduled job structs
- [ ] `state.Dependency` is read AND written in every `OnUpdate` that schedules
- [ ] No `.Complete()` added that was not there before
- [ ] ECB singleton matches the intended playback group
- [ ] `ComponentLookup` is `.Update(ref state)`d at the top of `OnUpdate`
- [ ] No new `[UpdateBefore/After]` attribute without `approved_plan.json`
      entry in `constraints`
