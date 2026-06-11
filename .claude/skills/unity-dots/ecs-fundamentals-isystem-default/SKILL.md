---
name: ecs-fundamentals-isystem-default
description: Senior-level rule for choosing between `ISystem` (unmanaged + Burst) and `SystemBase` (managed) in Entities 1.x. ISystem is the default; SystemBase is a deliberate exception. Covers Burst boundaries, the `[BurstDiscard]` silent-fallback trap, managed-field anti-patterns, and the bridge-system pattern for unavoidable managed work. Use when authoring or reviewing any runtime system, deciding whether to keep an existing `SystemBase`, or debugging "I thought this was Bursted but it's allocating GC".
metadata:
  internal-only: true
  tier: 3
---

# ISystem vs SystemBase — Senior Patterns

Entities 1.x gives two system base types: `ISystem` (unmanaged value-type system, Burst-compatible) and `SystemBase` (managed class). They look interchangeable in a tutorial, but at scale the choice decides whether a system is on the hot path or a frame-time anchor. Default to `ISystem`. Pick `SystemBase` deliberately and document why.

## Intent

Treat `ISystem` as the default execution model for runtime systems so Burst, zero-GC operation, and predictable scheduling are the default — not an opt-in that gets forgotten.

## Use when

- Authoring any new runtime system in Entities 1.x. There is no scenario where "I'll write a `SystemBase` because it feels like normal C#" is the right answer in production code.
- The system body can be expressed without managed references (no `Animator`, `Toggle`, `AudioSource`, `GameObject`, `string` interpolation, `List<T>`, `Dictionary<,>`).
- You want `[BurstCompile]` on `OnCreate` / `OnUpdate` — i.e. the typical case.
- Entity counts at runtime are anything above "a handful" — per-system managed allocation in `SystemBase` compounds across systems and shows up as steady GC pressure.

## Avoid when

- The system genuinely must hold managed references as fields (a live `Animator`, a Unity `Toggle`, an `AudioSource`, a `MonoBehaviour` it talks to). ISystem structs cannot hold managed fields safely.
- The system needs coroutines, `async`/`await` on the system class itself, or other managed orchestration that ISystem's value-type lifetime can't carry.
- You're writing throwaway editor scaffolding where Burst friction outweighs the win — but flag it as scaffolding and delete it before shipping.

In all three cases the right move is a small `SystemBase` with a one-line comment explaining why ISystem doesn't fit, sitting *adjacent* to ISystem peers in the same system group.

## Senior pattern

```csharp
using Unity.Burst;
using Unity.Entities;

[BurstCompile]
public partial struct FooSystem : ISystem
{
    [BurstCompile]
    public void OnCreate(ref SystemState state)
    {
        // The prerequisite contract for this system. See entity-query-patterns-requireforupdate-gating.
        state.RequireForUpdate<FooConfig>();
    }

    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var config = SystemAPI.GetSingleton<FooConfig>();
        // ... unmanaged work, jobs, ECB usage, etc.
    }
}
```

Both `OnCreate` and `OnUpdate` are annotated. Drop `[BurstCompile]` only on the specific method that genuinely touches a managed API — and consider whether that method belongs in a sibling `SystemBase` instead.

### Bridge pattern: when one method must be managed

If a single `OnUpdate` must run unmanaged for performance but a one-time setup step requires managed work, split the responsibility into two systems in the same group:

```csharp
// Managed "bridge" — owns the managed touchpoint. Runs once thanks to RequireForUpdate gating.
public partial class FooBridgeSystem : SystemBase
{
    protected override void OnCreate() => RequireForUpdate<FooBootstrapRequest>();
    protected override void OnUpdate()
    {
        // Touch the managed thing here (UI registration, Animator lookup, etc.),
        // then write the result into an unmanaged component for FooSystem to consume.
    }
}

// Unmanaged hot path — reads what the bridge produced. Burst-clean.
[BurstCompile]
public partial struct FooSystem : ISystem { /* ... */ }
```

The bridge contains the managed surface; the rest of the feature stays Burst-friendly. This is far cheaper than making the whole system `SystemBase` for one managed call.

## Anti-patterns

- Defaulting to `public partial class FooSystem : SystemBase` because "it looks like normal C#". Silently forfeits Burst, adds per-frame GC pressure on managed fields, and the choice is invisible in code review. If `SystemBase` is the right answer, the file should explain *why* in a comment.
- Marking an `ISystem` struct `[BurstCompile]` and then calling `GameObject.Find`, `Debug.Log` with interpolated strings, or any managed UI inside `OnUpdate`. Burst either rejects this at compile time or — worse, on some code paths — falls back silently and the system runs in C# while you believe it's Bursted.
- **The `[BurstDiscard]` silent-fallback trap.** Decorating a method with `[BurstDiscard]` so Burst skips it does not "make the call safe" — it means that call path runs in plain C# with full GC and managed-allocation cost. The surrounding system *looks* Bursted in code, the inspector *says* Burst is compiled, and the discarded path is still allocating every frame. If you see `[BurstDiscard]` on anything called inside `OnUpdate`, treat it as a serious smell: either the work belongs in a `SystemBase` bridge, or the call needs to be replaced with a Burst-compatible alternative. Do not use `[BurstDiscard]` as a "ship it" shortcut.
- Storing `List<T>`, `Dictionary<K,V>`, arrays, delegates, or any managed object as an `ISystem` struct field. ISystem structs are unmanaged value types; reach for `NativeList<T>`, `NativeHashMap<K,V>`, or `BlobAssetReference<T>`. If the data is fundamentally managed, that's the signal to use `SystemBase` for this one system — not to smuggle managed state into an ISystem.
- Using `state.EntityManager.GetComponentObject<T>` from a Burst-compiled `OnUpdate`. Component objects are managed; the call cannot be Bursted.

## Failure modes

| Symptom | Likely cause |
|---|---|
| Steady GC allocation per frame even though all systems "look unmanaged" | A `SystemBase` (often inherited from earlier code) sits on the hot path; or an `ISystem` is calling through `[BurstDiscard]` into managed code |
| Native crash with no managed stack trace, only after a long playmode session | Burst-compiled `OnUpdate` hit a managed-exception path; the original `Exception` got eaten and surfaced as a native fault |
| Burst Inspector shows the system as compiled, but profiler still shows GC and managed time inside it | `[BurstDiscard]` on a method called from `OnUpdate`; or a method that calls a managed API has implicitly been excluded by Burst |
| Compile error: "Burst error BC1051: managed objects cannot be used in Burst" | An `ISystem` `[BurstCompile]` method is touching a managed type. Either move that work into a `SystemBase` bridge or replace it with an unmanaged equivalent |
| `OnCreate` is fine but `OnUpdate` won't compile under Burst | Frequently `Debug.Log("...")` with string interpolation, or `string.Format`. Replace with `Debug.Log(FixedString.Format(...))` patterns or move the log outside the Burst region |
| "Why is my ISystem slower than I expected?" | `[BurstCompile]` was forgotten on the struct or on `OnUpdate` specifically — the attribute does not propagate from the struct to instance methods automatically; both annotations are required |

## Runtime verification

- **Static:** grep every system declaration. Every `: SystemBase` must be paired with a one-line comment explaining why ISystem doesn't fit (managed field, coroutine, async lifecycle). Every `: ISystem` struct should carry `[BurstCompile]` at the struct level AND on each lifecycle method (`OnCreate`, `OnUpdate`, `OnDestroy`). Flag any `[BurstDiscard]` reachable from `OnUpdate` for code review — these are almost always bugs.
- **Runtime:** open the Burst Inspector and confirm each `[BurstCompile]` system shows a green compiled entry. Open the Profiler — GC.Alloc on a frame where only ISystem code ran should be zero. If GC appears, the call path includes a `SystemBase`, a `[BurstDiscard]`, or a managed allocation inside an "unmanaged" system.

## Performance notes

- Typical speedup of Burst-compiled ISystem over a logically-equivalent `SystemBase` is 5–20×, driven by SIMD vectorization, removal of GC bookkeeping, and inlining across the system boundary. Demos with ten entities won't see it; gameplay with thousands will.
- `ISystem` structs live in unmanaged memory — zero GC per system instance, no managed object headers, no finalizer cost. `SystemBase` instances are managed objects with all the usual heap overhead.
- Burst compilation is per-method, not per-class. `[BurstCompile]` on the struct is convention/documentation; the *enforced* annotation is on each method that should be compiled. Forgetting it on `OnUpdate` while keeping it on the struct is the most common "thought it was Bursted" failure.

## Compile / editor safety

- Burst-compiled `OnUpdate` cannot throw managed exceptions cleanly. Failures surface as native crashes with no managed stack — design for `if`-guards and `SystemAPI.HasComponent<T>` checks rather than relying on `try/catch`.
- `ISystem` requires `partial struct` for source generation to attach `ISystemCompilerGenerated` plumbing. Forgetting `partial` produces obscure source-gen errors at build time.
- `[BurstCompile]` on `OnCreate` is desirable but not always essential — `OnCreate` runs once. The high-leverage placement is on `OnUpdate`.

## Entities version notes (1.4.x)

- `ISystem` is current and the recommended default. `SystemBase` remains supported and is still the right answer for managed-bound systems.
- The Entities 0.x distinction between `JobComponentSystem` and `SystemBase` is gone — refuse `JobComponentSystem` in reviews.
- `ref SystemState state` is the current parameter shape for `ISystem` lifecycle methods. Old code using `SystemState state` (no `ref`) is pre-1.0 — it won't compile against current Entities.
- `SystemAPI.GetSingleton<T>()` and similar API surface works identically in both `ISystem` and `SystemBase`. The choice is about the *system* type, not about how you access state inside it.

## See also

- [`entity-query-patterns-systemapi-query`](../entity-query-patterns-systemapi-query/SKILL.md) — the default iteration pattern inside `ISystem.OnUpdate`
- [`entity-query-patterns-requireforupdate-gating`](../entity-query-patterns-requireforupdate-gating/SKILL.md) — pair every ISystem with a prerequisite contract
- [`dots-ecb-orchestration`](../dots-ecb-orchestration/SKILL.md) — structural changes from a Burst-compiled ISystem
- [`singleton-patterns-config-and-access`](../singleton-patterns-config-and-access/SKILL.md) — how the bridge system hands data to its unmanaged sibling
