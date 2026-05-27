---
name: wave4-world-update-allocator-per-frame-native
description: Allocate per-frame temporary NativeArrays and NativeContainers without manual `Dispose()` using `WorldUpdateAllocator` (RewindableAllocator), which auto-rewinds at end of each world update.
tags: [jobs, native-containers, performance]
---

# WorldUpdateAllocator — Per-Frame Native Allocations

## Intent
Allocate per-frame temporary NativeArrays and NativeContainers without manual `Dispose()` using `WorldUpdateAllocator` (RewindableAllocator), which auto-rewinds at end of each world update.

## Use When
- Temporary NativeArrays or NativeContainers needed for the duration of one frame's job pipeline.
- Avoiding manual `Dispose()` or `Allocator.TempJob` 4-frame lifetime limits.

## Avoid When
- Allocation must persist across frames — use `Allocator.Persistent` with explicit `Dispose` in `OnDestroy`.
- Allocation size is unknown until a job completes — cannot resize a rewindable allocation.

## Senior Pattern
```csharp
// Preferred form for NativeArray with typed allocator:
var arr = CollectionHelper.CreateNativeArray<float3, RewindableAllocator>(
    count, ref state.WorldUpdateAllocator);

// For NativeContainers:
var map = new NativeParallelMultiHashMap<int, int>(count, state.WorldUpdateAllocator);

// No Dispose() needed — auto-rewinds after world update completes
state.Dependency = new ProcessJob { Data = arr }.ScheduleParallel(state.Dependency);
```

## Anti-Patterns
- Caching `state.WorldUpdateAllocator` as a system field — allocator state shifts between frames; always access via `state.WorldUpdateAllocator` in `OnUpdate`.
- Using `world.UpdateAllocator.ToAllocator` for `CollectionHelper.CreateNativeArray<T, RewindableAllocator>` — type mismatch; use `ref world.UpdateAllocator`.
- Using `Allocator.TempJob` for large per-frame arrays — must Dispose within 4 frames; easy to forget, causes safety errors.
- Holding a reference to a `WorldUpdateAllocator` allocation across `OnUpdate` boundary — rewind happened, array is invalid memory.

## Runtime Risks
- Cross-frame access to a `WorldUpdateAllocator` allocation is undefined behavior — appears valid in dev builds (memory not zeroed) but is logically garbage.

## Performance Notes
- Bump allocation: O(1) regardless of size — fastest available Unity allocator.
- No GC pressure; no Dispose overhead.
- Use as the default for all per-OnUpdate temporary data.

## Allocation Hierarchy
1. `state.WorldUpdateAllocator` — per-frame, auto-disposed (default choice).
2. `Allocator.TempJob` — short-lived, must Dispose within 4 frames (avoid).
3. `Allocator.Persistent` — cross-frame, explicit Dispose in OnDestroy.

## Related Skills
[[entity-index-in-query-scatter-pattern]], [[native-parallel-multihashmap-parallel-writer]], [[job-dependency-chain]]
