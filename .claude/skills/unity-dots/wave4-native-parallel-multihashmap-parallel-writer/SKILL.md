---
name: wave4-native-parallel-multihashmap-parallel-writer
description: Enable multiple parallel workers to insert into a shared hash map concurrently without locks, using `AsParallelWriter()` for spatial partitioning, bucketing, or grouping patterns.
---

# NativeParallelMultiHashMap — Parallel Writer

## Intent
Enable multiple parallel workers to insert into a shared hash map concurrently without locks, using `AsParallelWriter()` for spatial partitioning, bucketing, or grouping patterns.

## Use When
- Parallel jobs need to insert entity data into buckets keyed by spatial hash, type, or ID.
- Multiple values per key are expected (spatial grid cells, LOD groups, collision pairs).
- Result will be consumed by a subsequent sequential or parallel read job.

## Avoid When
- Only one writer — use regular `NativeHashMap`.
- Total insertion count is small and threading overhead is not justified.

## Senior Pattern
```csharp
var spatialMap = new NativeParallelMultiHashMap<int, int>(
    entityCount, state.WorldUpdateAllocator);

var hashJob = new SpatialHashJob
{
    SpatialMap = spatialMap.AsParallelWriter(),
    InvCellSize = 1f / cellRadius
};
var hashHandle = hashJob.ScheduleParallel(entityQuery, state.Dependency);

var readJob = new ProcessCellsJob { SpatialMap = spatialMap };
state.Dependency = readJob.Schedule(hashHandle);

// Standard spatial hash formula in Execute:
// int key = (int)math.hash(new int3(math.floor(position * invCellSize)));
// SpatialMap.Add(key, entityIndexInQuery);

// Iteration in sequential read job:
// if (SpatialMap.TryGetFirstValue(key, out var val, out var it))
//     do { /* process val */ } while (SpatialMap.TryGetNextValue(out val, ref it));
```

## Anti-Patterns
- Allocating fewer slots than expected insertions — silent data loss in Burst release builds (no exception).
- Reading from the map in the same parallel job that writes via `AsParallelWriter` — parallel writer is write-only.
- Using `Allocator.TempJob` instead of `WorldUpdateAllocator` — requires manual Dispose within 4 frames.

## Runtime Risks
- Under-capacity allocation is the most common failure mode — always allocate at least `entityCount`.
- Accessing non-parallel `NativeParallelMultiHashMap` from a parallel job without `AsParallelWriter()` = safety error.

## Performance Notes
- Lock-free bucket insertion; contention scales with hash collision rate.
- O(1) amortized insertion per worker.
- Bucket capacity rounded up to next power of two internally.

## Architecture Guidance
Use for the scatter phase of scatter-gather: parallel scatter into buckets, sequential or parallel gather from buckets. Standard spatial hashing key: `(int)math.hash(new int3(math.floor(position * invCellSize)))`.

## Related Skills
[[entity-index-in-query-scatter-pattern]], [[world-update-allocator-per-frame-native]], [[ijobentity-advanced-patterns]]
