---
name: wave8-dependency-complete-editor-only-fence
description: Use state.Dependency.Complete() only as an editor-mode diagnostic fence to inspect intermediate job state, never as a production pattern for forcing job completion.
---

# state.Dependency.Complete() — Editor-Only Diagnostic Fence

## Intent
Use state.Dependency.Complete() only as an editor-mode diagnostic fence to inspect intermediate job state, never as a production pattern for forcing job completion.

## Use When
- Adding a temporary diagnostic fence in editor builds to isolate a job scheduling bug or verify intermediate NativeArray state
- Confirming a job's output in isolation before wiring it into a dependency chain

## Avoid When
- In any shipping build or production system — Complete() is a sync point anti-pattern
- As a substitute for proper job dependency chaining — fix the chain, do not paper over it

## Senior Pattern
```csharp
// EDITOR-ONLY diagnostic fence — not for production:
public partial struct DiagnosticSystem : ISystem
{
    public void OnUpdate(ref SystemState state)
    {
        var results = CollectionHelper.CreateNativeArray<int>(100, state.WorldUpdateAllocator);
        var job = new ComputeJob { Results = results };
        state.Dependency = job.Schedule(state.Dependency);

#if UNITY_EDITOR
        // Force sync to inspect intermediate state — remove before shipping:
        state.Dependency.Complete();
        UnityEngine.Debug.Log($"Intermediate result[0]: {results[0]}");
#endif
        // Production: dependency chain propagates — no Complete() needed
    }
}

// PRODUCTION correct pattern — never forced Complete():
[BurstCompile]
public partial struct ProductionSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var results = CollectionHelper.CreateNativeArray<int>(100, state.WorldUpdateAllocator);
        state.Dependency = new ComputeJob { Results = results }
            .ScheduleParallel(state.Dependency);
        // Dependency propagates to consuming systems automatically
    }
}
```

## Anti-Patterns
- `state.Dependency.Complete()` in every OnUpdate "to be safe" — full sync point every frame; eliminates all job parallelism; main-thread stall equal to all scheduled job duration.
- Using Complete() to read job output without `#if UNITY_EDITOR` guard — ships the anti-pattern into production builds.
- Using Complete() as a substitute for proper dependency chaining — masks scheduling bugs rather than fixing them.
- Calling Complete() at the start of OnUpdate to "wait for last frame's jobs" — indicates incorrect Allocator.Persistent usage; switch to WorldUpdateAllocator.

## Runtime Risks
- Unguarded Complete() forces the main thread to wait for all scheduled jobs — destroying frame parallelism.
- On a frame with 10ms of scheduled jobs, a Complete() in the middle stalls the main thread for up to 10ms.
- In profiler: main thread shows "WaitForJobGroupID" — this is the Complete() stall.

## Performance Notes
- One unguarded Complete() in a hot system can raise frame time by 5–15ms on complex ECS worlds.
- Use Unity Profiler job markers to identify the stall: look for main thread "WaitForJobGroupID" immediately followed by the system that called Complete().
- Eliminating a single misplaced Complete() in a 10,000-entity system commonly recovers 2–8ms per frame.

## Architecture Guidance
- If you feel the need to call Complete() in production: this signals the dependency chain is broken. Fix the chain; do not paper over it.
- For temporary diagnostics: always use `#if UNITY_EDITOR` guard; remove before merging to main.
- For reading job output on the same frame: pass results via WorldUpdateAllocator NativeArray through state.Dependency to a consuming system.

## Related Skills
[[job-dependency-chain]], [[wave4-jobhandle-combine-dependencies]], [[wave8-handle-complete-sync-point-antipattern]], [[wave4-world-update-allocator-per-frame-native]]
