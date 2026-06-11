---
name: wave4-systembase-with-inner-ijobentity
description: Use managed `SystemBase` class when the system itself requires managed resources, while delegating hot-path work to Burst-compiled inner IJobEntity structs.
tags: [jobs, systems, managed]
metadata:
  internal-only: true
  tier: 3
---

# SystemBase with Inner IJobEntity

## Intent
Use managed `SystemBase` class when the system itself requires managed resources, while delegating hot-path work to Burst-compiled inner IJobEntity structs.

## Use When
- System must hold managed references (physics callbacks, coroutine coordinators, managed subscene access, interface references).
- Multiple jobs per `OnUpdate` need to share implicit dependency chain.

## Avoid When
System has no managed needs — use `partial struct : ISystem` with `[BurstCompile]` on `OnUpdate` (lower overhead, Burst-compilable scheduling).

## Senior Pattern
```csharp
public partial class AnimationSystem : SystemBase
{
    [BurstCompile]
    partial struct UpdateFrameJob : IJobEntity
    {
        public float DeltaTime;

        [BurstCompile]
        public void Execute(ref AnimationState anim, in AnimationClipRef clipRef)
        {
            anim.Time += DeltaTime;
        }
    }

    [BurstCompile]
    partial struct ApplyTransformJob : IJobEntity
    {
        [BurstCompile]
        public void Execute(ref LocalTransform transform, in AnimationState anim)
        {
            // apply animation state to transform
        }
    }

    protected override void OnUpdate()
    {
        float dt = SystemAPI.Time.DeltaTime;
        new UpdateFrameJob { DeltaTime = dt }.ScheduleParallel();
        new ApplyTransformJob().ScheduleParallel();
        // SystemBase.Dependency auto-chains between sequential ScheduleParallel calls
    }
}
```

## Anti-Patterns
- Marking `OnUpdate` with `[BurstCompile]` — `SystemBase.OnUpdate` is virtual managed; Burst cannot compile it.
- Two inner jobs writing the same component without chaining — `SystemBase` auto-chains sequential `ScheduleParallel` calls within one `OnUpdate`, but manually completing `Dependency` between calls breaks the chain.
- Preferring `SystemBase` for simplicity when no managed context is needed — adds virtual dispatch overhead every frame for no benefit.

## Runtime Risks
- Multiple `ScheduleParallel` calls on same system auto-chain via `Dependency` property; manually completing `Dependency` between calls breaks the chain.
- `SystemBase` does not support `[BurstCompile]` on `OnUpdate`; only inner job structs can be Burst-compiled.

## Performance Notes
- `SystemBase` overhead: one virtual dispatch per frame + managed object GC root.
- Inner IJobEntity jobs: identical performance to ISystem-hosted jobs when `[BurstCompile]` applied.
- Prefer ISystem unless managed context is unavoidable.

## Architecture Guidance
Use `SystemBase` only as the outer shell; move all data processing into inner Burst-compiled jobs. If managed need can be resolved in `OnCreate`/`OnDestroy` (event subscription), use ISystem and handle managed work separately.

## Related Skills
[[isystem-burst-compile]], [[ijobentity-advanced-patterns]], [[burst-compilation-contract]]
