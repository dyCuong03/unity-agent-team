---
name: burst-safety
description: Burst-safe code rules for DOTS jobs and ISystem — managed type exclusions, Mathematics-only math, shared static limitations, and Burst compilation attribute requirements. Prevents Burst compilation errors and unsafe managed access in hot-path DOTS code.
use-when: |
  Load for unity-dots-dev when the task involves writing or debugging ISystem, IJobEntity,
  or IJobChunk code, or when Burst compilation errors appear. Load when any struct marked
  [BurstCompile] needs to be written or reviewed.
do-not-use-when: |
  Do not load for Unity classic (MonoBehaviour) tasks. Do not load for tester, verifier, or
  qa-tester roles. Not needed for pure authoring/Baker code without Burst.
platforms: [claude-code, codex, copilot, cursor, windsurf]
task-categories: [ecs, burst, safety, performance, dots]
metadata:
  source: https://docs.unity3d.com/Packages/com.unity.burst@1.8
  version: 1.8.18
  tier: 1

---

# Burst Safety

This is a skill pack, not an agent. Load when triage marks `domain=DOTS|Hybrid`.

## Hard Rules (do not violate without architect approval)

1. **No managed types in `[BurstCompile]` code paths.** No `string`, `List<T>`,
   `Dictionary<K,V>`, `class`, `object`, boxed value types, delegates, or
   `try/catch` (managed exceptions).
2. **No static mutable state.** Statics must be `readonly` and reference only
   blittable types. `[BurstCompile]` does not see managed singletons.
3. **No reflection.** `typeof(T).GetField(...)`, `Activator.CreateInstance`,
   `Marshal.*` — all forbidden inside burst.
4. **No virtual dispatch.** No interface calls on instances; use static methods,
   generic constraints, or function pointers.
5. **`fixed` blocks must use `UnsafeUtility.AddressOf` for managed objects** —
   in practice this means do not need `fixed` at all in burst code.
6. **Math: prefer `Unity.Mathematics`.** `math.sin`, `math.length`,
   `float3`/`int3`, not `Mathf.*` or `Vector3` (those are managed wrappers).
7. **`Debug.Log` is forbidden** in `[BurstCompile]` methods. Use
   `UnityEngine.Debug.Log` only outside burst, or `[BurstDiscard]` on a small
   log helper called from non-hot paths.

## Diagnostic Checklist Before Signaling Verifier

For every system or job you wrote or modified:

- [ ] `[BurstCompile]` is still on the method/struct if it was there before.
      Removing it requires `[BLOCK: performance]` escalation.
- [ ] `Burst Inspector` (or `BurstCompiler.Enable = false` toggle test) shows
      the method compiles without warnings.
- [ ] No `string`, `List`, `Dictionary` field added.
- [ ] No `try/catch` in `[BurstCompile]` body.
- [ ] No `Debug.Log` introduced in the hot path.
- [ ] If you needed scratch memory: `NativeArray<T>` with explicit
      `Allocator.Temp` (frame-scoped) or `Allocator.TempJob` (job-scoped),
      and disposed in the same frame/job.

## Common Burst Bugs (do not repeat)

| Symptom | Cause |
|---------|-------|
| "Burst error BC1015: Could not statically evaluate Type" | passing `object` or `Type` arg into burst method |
| "BC1042: Burst can not handle a fixed buffer of type" | char buffer or unsafe fixed array |
| Silent failure: code runs but no Burst speedup | `[BurstCompile]` was on a generic method without a concrete dispatch point |
| Cosmetic Mathf vs math mismatch | `Mathf.PI` is a `static readonly float` managed access — replace with `math.PI` |

## Boundary With Domain 2 (Unity)

If the touched code lives in a `MonoBehaviour` or editor tooling: this skill
does not apply. Use `unity-foundation/SKILL.md` reasoning instead.

## Reference

See full DOTS guidance in `.claude/skills/unity-dots-best-practices/SKILL.md`.
This pack is the minimum subset unity-dev needs to ship burst-safe code without
loading the full DOTS skill.
