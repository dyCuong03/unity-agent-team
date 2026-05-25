---
name: memory-safety
description: Native container lifetime, allocator selection, and GC-avoidance rules. Loaded into unity-dev when triage classifies the task as DOTS or Hybrid. Replaces the memory-checker subagent.
---

# Memory Safety

This is a skill pack, not an agent.

## Allocator Decision Tree

```
Lifetime ≤ this frame, this scope         → Allocator.Temp
Lifetime ≤ this job                       → Allocator.TempJob       (dispose in job)
Lifetime spans frames (system state)      → Allocator.Persistent    (Dispose in OnDestroy)
Job allocates output for main thread      → Allocator.TempJob
Asset/blob (read-only, long-lived)        → BlobAssetReference<T> (no allocator)
```

Rule: every `Allocator.Persistent` allocation must have a matching `Dispose()`
in `OnDestroy` (for ISystem use `state.Dispose`-bound `NativeArray`/`Lookup`
fields). Otherwise the Job Safety System will leak across domain reloads.

## Native Container Rules

1. **Never store a `NativeArray` allocated inside `OnCreate` without
   `Disposing` it in `OnDestroy`.**
2. **Never pass a `NativeArray` to a job and reuse it on the main thread the
   same frame** unless the job is `.Complete()`d first (= sync point — requires
   approval).
3. **Never resize a `NativeList` from a parallel job.** Use
   `NativeList<T>.ParallelWriter`.
4. **Don't share writable native containers across two parallel jobs without
   dependency chaining.** The Safety System will flag it as
   `InvalidOperationException` in editor; in player builds it silently corrupts.
5. **`NativeHashMap<K,V>` is not parallel-safe for writes.** Use
   `NativeParallelHashMap<K,V>.ParallelWriter` for writes from multiple threads.

## Managed Allocation Hotspots

These are silent GC bombs inside `OnUpdate` / hot paths. Audit before signaling
verifier:

| Anti-pattern | Replace with |
|--------------|--------------|
| `string.Format(...)` / `$"..."` | `FixedString*N*Bytes` or skip the log |
| `new List<T>()` | `NativeList<T>(Allocator.Temp)` |
| LINQ (`.Where`, `.Select`, `.ToList`) | manual loop or `IJobEntity` |
| `Enum.GetValues(typeof(...))` | a cached `static readonly` array outside hot path |
| Boxing (e.g. `object o = someStruct;`) | keep the type concrete |
| `Dictionary<K,V>.Add` in hot path | `NativeParallelHashMap<K,V>` |
| `Debug.Log("…" + obj)` | guard with `#if UNITY_EDITOR` if needed at all |

## Blob Assets

Use `BlobAssetReference<T>` for read-only, long-lived data (terrain LUTs,
ability defs, item tables):

- Build with `BlobBuilder` once, in a baker or `[CreateAsset]` flow.
- Pass by `BlobAssetReference<T>` field on a component.
- Never mutate after build — blobs are immutable.

## Pre-Verifier Checklist

- [ ] Every new `Allocator.Persistent` has a paired `Dispose()` in `OnDestroy`
- [ ] No `new` of managed type in `OnUpdate`
- [ ] No string interpolation in hot path
- [ ] No LINQ in hot path
- [ ] No `NativeHashMap` written from a parallel job (use parallel variant)
- [ ] `NativeArray` returned from a job to the main thread is `.Complete()`d
      with explicit approval, OR consumed by a follow-up job via dependency

## Profiler Evidence (recommended)

If complexity ≥ medium and triage flagged this as a hot system: take a
GC Alloc sample before and after via `profiler_get_runtime_memory` and include
the delta in `verification_bundle.logs_to_inspect`.
