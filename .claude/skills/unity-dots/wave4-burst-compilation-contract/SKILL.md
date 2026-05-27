---
name: wave4-burst-compilation-contract
description: Apply `[BurstCompile]` correctly to ISystem methods and job structs to guarantee native-code compilation of both scheduling and execution paths.
---

# Burst Compilation Contract

## Intent
Apply `[BurstCompile]` correctly to ISystem methods and job structs to guarantee native-code compilation of both scheduling and execution paths.

## Use When
All ISystem implementations and all job structs — apply `[BurstCompile]` by default. Opt out only when managed APIs are unavoidably required.

## Avoid When
- Method calls managed APIs (string formatting, `List<T>`, class allocations) — Burst fails or silently inserts `[BurstDiscard]` behavior.
- System extends `SystemBase` — `OnUpdate` cannot be Burst-compiled; only inner job structs can.

## Senior Pattern
```csharp
// ISystem: mark the struct AND each method individually
[BurstCompile]
public partial struct MySystem : ISystem
{
    [BurstCompile]
    public void OnCreate(ref SystemState state) { }

    [BurstCompile]
    public void OnUpdate(ref SystemState state) { }

    [BurstCompile]
    public void OnDestroy(ref SystemState state) { }
}

// Job struct: mark both the struct AND Execute()
[BurstCompile]
public partial struct MyJob : IJobEntity
{
    public float Delta;

    [BurstCompile]
    public void Execute(ref Position pos, in Velocity vel)
    {
        pos.Value += vel.Value * Delta;
    }
}

// Isolating managed calls in Burst path via [BurstDiscard]:
[BurstDiscard]
private static void DebugOnly(string msg) { Debug.Log(msg); }
```

## Anti-Patterns
- Marking only the struct `[BurstCompile]` but not `Execute()` — struct compilation does not transitively compile `Execute` in all Unity versions.
- Calling `Debug.Log` inside a `[BurstCompile]` method — compilation error in strict mode.
- Adding `[BurstCompile]` to `SystemBase.OnUpdate` — silently ignored.
- Missing `[BurstCompile]` on `Execute()` is not a compile error — job runs at IL2CPP/Mono speed (10–100x slower for math-heavy code) with no warning.

## Runtime Risks
- `[BurstDiscard]` on initializer methods means Burst-compiled callers skip initialization entirely — requires `EarlyJobInit<T>.Init()` call in `OnCreate` to pre-initialize job reflection data.

## Performance Notes
- 10–100x speedup for math-heavy loops (float4x4 transforms, spatial hashing, physics response).
- Enables auto-vectorization (SIMD) and hardware intrinsics via `Unity.Burst.Intrinsics`.
- Audit with Burst Inspector (Jobs > Burst Inspector): "Compiled" vs "Failed" vs "Not Compiled" status per method.

## Architecture Guidance
Apply `[BurstCompile]` to ALL ISystem methods and ALL job structs as project-wide default. Code review checklist: any ISystem or IJob* type without `[BurstCompile]` requires explicit written justification. Never add managed context to a `[BurstCompile]` method; if needed, move to `OnCreate`/`OnDestroy` or a non-compiled helper.

## Related Skills
[[isystem-burst-compile]], [[ijobentity-advanced-patterns]], [[ijobchunk-full-anatomy]]
