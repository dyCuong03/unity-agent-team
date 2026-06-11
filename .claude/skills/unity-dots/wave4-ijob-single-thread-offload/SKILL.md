---
name: wave4-ijob-single-thread-offload
description: Schedule sequential work off the main thread using IJob without parallelism overhead.
tags: [jobs]
metadata:
  internal-only: true
  tier: 3
---

# IJob — Single-Thread Offload

## Intent
Schedule sequential work off the main thread using IJob without parallelism overhead.

## Use When
- Work is order-dependent or too small to justify parallel splitting.
- One-shot initialization or serial dependency chain must run off-thread.
- Total element count is small (< ~1000 elements where parallel overhead exceeds benefit).

## Avoid When
- Work is embarrassingly parallel and element count is large — use IJobParallelFor or IJobEntity.
- Data is ECS entities/components — use IJobEntity.

## Senior Pattern
```csharp
[BurstCompile]
public struct MySerialJob : IJob
{
    public NativeArray<float> Data;
    public float Delta;

    public void Execute()
    {
        for (int i = 0; i < Data.Length; i++)
            Data[i] += Delta;
    }
}

// In ISystem.OnUpdate:
state.Dependency = new MySerialJob
{
    Data = myData,
    Delta = 5f
}.Schedule(state.Dependency);
```

## Anti-Patterns
- Calling `handle.Complete()` immediately after `Schedule()` — sync point negates the offload.
- Not assigning `state.Dependency = job.Schedule(state.Dependency)` — orphaned handle causes safety errors in subsequent systems.
- Using IJob for large arrays where IJobParallelFor gives N-core speedup.

## Runtime Risks
- Unreferenced job handles cause `InvalidOperationException` when subsequent systems touch the same component data.
- Never call `handle.Complete()` in a hot path unless a deliberate sync point is required.

## Performance Notes
- One worker thread; no cache-line contention.
- Suitable for < ~1000 elements where parallel dispatch overhead exceeds the work cost.
- Pair with `WorldUpdateAllocator` to avoid manual Dispose.

## Architecture Guidance
Use as a leaf node in a job DAG; assign handle to `state.Dependency`; let downstream systems resolve dependency naturally. For one-shot init in `OnCreate`, `handle.Complete()` is acceptable since startup sync points are acceptable.

## Related Skills
[[ijobentity-parallel-job]], [[state-dependency-job-chaining]], [[job-dependency-chain]]
