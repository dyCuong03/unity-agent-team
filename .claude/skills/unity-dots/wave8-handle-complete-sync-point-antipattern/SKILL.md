---
name: wave8-handle-complete-sync-point-antipattern
description: Identify and eliminate inline handle.Complete() calls in production systems that create unintended main-thread stalls, and replace them with WorldUpdateAllocator + dependency chain patterns.
tags: [jobs, antipattern, debug, performance]
---

# handle.Complete() Sync Point Anti-Pattern

## Intent
Identify and eliminate inline handle.Complete() calls in production systems that create unintended main-thread stalls, and replace them with WorldUpdateAllocator + dependency chain patterns.

## Use When
- Profiling reveals unexpected main-thread "WaitForJobGroupID" stalls
- Code review finds handle.Complete() outside of test/editor contexts
- A system uses Allocator.Persistent NativeArrays read in the same OnUpdate that schedules work on them

## Avoid When
- Explicit sync is genuinely required (disposing a NativeArray at end of frame after a one-shot operation) — in that case, document why Complete() is necessary

## Senior Pattern
```csharp
// ANTI-PATTERN — inline Complete() stalls main thread:
public partial struct BrokenSystem : ISystem
{
    NativeArray<int> _results;

    public void OnCreate(ref SystemState state)
    {
        _results = new NativeArray<int>(100, Allocator.Persistent);
    }

    public void OnUpdate(ref SystemState state)
    {
        var job = new ComputeJob { Results = _results };
        var handle = job.Schedule();  // does not extend state.Dependency
        handle.Complete();            // SYNC POINT — stalls main thread every frame
        // Read _results here — destroys frame parallelism
    }

    public void OnDestroy(ref SystemState state) => _results.Dispose();
}

// CORRECT — WorldUpdateAllocator + dependency chain:
[BurstCompile]
public partial struct FixedSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        // Auto-freed after world update — no Dispose, no Complete():
        var results = CollectionHelper.CreateNativeArray<int>(100, state.WorldUpdateAllocator);
        state.Dependency = new ComputeJob { Results = results }
            .Schedule(state.Dependency);

        // Downstream system that reads results — chains via state.Dependency:
        state.Dependency = new ConsumeJob { Results = results }
            .Schedule(state.Dependency);
        // No Complete() — ECS propagates the handle to subsequent systems
    }
}

// CORRECT — when output must be passed to a managed system:
// Write result into a singleton component, read it in a non-Burst system next frame
public struct ComputeResult : IComponentData { public int Value; }
```

## Root Cause Patterns That Lead to Complete()

| Symptom | Root cause | Fix |
|---|---|---|
| `handle.Complete()` then read NativeArray | Allocator.Persistent array read same frame | Switch to WorldUpdateAllocator |
| `state.Dependency.Complete()` at start of OnUpdate | Previous frame's jobs not chained | Pass state.Dependency correctly through ScheduleParallel |
| Complete() to pass data to managed system | Cross-boundary data handoff | Write to IComponentData, read next frame |
| Complete() to "be safe" | No actual dependency issue | Remove; let ECS chain handle it |

## Anti-Patterns
- Scheduling a job without assigning to `state.Dependency` then calling `Complete()` — breaks the job chain and stalls.
- Calling `Complete()` at the start of OnUpdate to "wait for last frame" — indicates incorrect Allocator.Persistent usage; switch to WorldUpdateAllocator.
- Using `handle.Complete()` to read output and pass to a managed system — redesign: write to IComponentData, read next frame.
- Calling `Complete()` inside a loop over entities — per-entity sync point; catastrophic performance.

## Runtime Risks
- Main-thread stall equal to the scheduled job duration.
- In profiler: main thread blocked on "WaitForJobGroupID" immediately before or inside the system's marker.
- Magnitude scales with entity count and job complexity — in a 10,000-entity world this is commonly 2–8ms per frame.

## Performance Notes
- Eliminating a single misplaced `Complete()` in a hot system commonly recovers 2–8ms per frame on complex ECS worlds.
- Use WorldUpdateAllocator as default for per-frame NativeArrays — eliminates the most common source of unintended Complete() calls.
- Verify fix with Unity Profiler job markers: "WaitForJobGroupID" stall should disappear after removing the Complete().

## Architecture Guidance
- Review any `NativeArray` with `Allocator.Persistent` read in the same system that schedules work on it — these are the most common sources of unintended Complete() calls.
- Default NativeArray lifetime: WorldUpdateAllocator (per-frame, auto-freed).
- Cross-frame NativeArray: Allocator.Persistent with explicit Dispose in OnDestroy — never read in the scheduling frame.
- Data handoff to managed systems: write to IComponentData, read next frame.

## Related Skills
[[wave8-dependency-complete-editor-only-fence]], [[job-dependency-chain]], [[wave4-world-update-allocator-per-frame-native]], [[wave4-jobhandle-combine-dependencies]]
