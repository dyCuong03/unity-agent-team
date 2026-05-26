---
name: dots-update-groups
description: How to choose the right ECS system group and ordering so per-frame and per-fixed-step work is deterministic and never races its own readers. Covers InitializationSystemGroup / SimulationSystemGroup / PresentationSystemGroup / FixedStepSimulationSystemGroup / VariableRateSimulationSystemGroup, UpdateBefore / UpdateAfter peer ordering, OrderFirst / OrderLast group-boundary placement, RateManager, and the cross-group ordering trap. Use when adding an ISystem, fixing "value visible one frame late" bugs, or coupling simulation to a fixed timestep.
---

# Update Groups — Senior Patterns

The group an `ISystem` lives in is a contract about *when it runs and how often* — not a label. Get it wrong and reads see stale state, physics tunnels, and replays diverge.

## Intent

Pick the update group, the relative order, and the timestep semantics deliberately. Make the data dependency graph match the system schedule.

## The five built-in groups

| Group | Runs | Time | Use for |
|---|---|---|---|
| `InitializationSystemGroup` | Once per frame, first | wall-clock | Input sampling, frame-start state setup, ECB.Begin/EndInitialization |
| `SimulationSystemGroup` | Once per frame | wall-clock `Time.DeltaTime` | Game logic, frame-coupled simulation |
| `FixedStepSimulationSystemGroup` | **0 or N times** per frame | fixed `Time.DeltaTime` | Physics, netcode prediction, deterministic motion |
| `VariableRateSimulationSystemGroup` | Per its own `RateManager` | manager-controlled | Low-frequency work (AI ticking at 10Hz) |
| `PresentationSystemGroup` | Once per frame, last | wall-clock | Camera follow, hybrid GO sync, render-side reads |

`SystemAPI.Time.DeltaTime` resolves *to whatever the current group's RateManager dictates*. Inside FixedStep it is the fixed step. Inside Variable it's the manager's delta. This is the subtle trap: code copy-pasted across groups silently changes meaning.

## Senior pattern

```csharp
// Frame-coupled: render-side read after sim writes.
[UpdateInGroup(typeof(PresentationSystemGroup))]
public partial struct HudReadSystem : ISystem { /* ... */ }

// Deterministic motion: physics-coupled projectile.
[UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]
public partial struct ProjectileSystem : ISystem
{
    public void OnUpdate(ref SystemState state)
    {
        var dt = SystemAPI.Time.DeltaTime; // = fixed step, NOT wall clock
        // ...
    }
}

// Peer ordering INSIDE the same group.
[UpdateInGroup(typeof(SimulationSystemGroup))]
[UpdateAfter(typeof(InputCollectionSystem))]   // both must live in SimulationSystemGroup
[UpdateBefore(typeof(MovementSystem))]
public partial struct CommandResolveSystem : ISystem { /* ... */ }

// Group-boundary placement (rare): make this run first/last *within* the group.
[UpdateInGroup(typeof(SimulationSystemGroup), OrderFirst = true)]
public partial struct FrameStartSystem : ISystem { /* ... */ }
```

## Decision rule

```
Is the timing deterministic-critical (physics, netcode, replay)?
  YES → FixedStepSimulationSystemGroup
  NO  → Is it sampling input / preparing the frame?
          YES → InitializationSystemGroup
          NO  → Is it reading what sim wrote, for output?
                  YES → PresentationSystemGroup
                  NO  → SimulationSystemGroup (default)
```

For low-frequency work (AI scanning, distant-LOD updates): `VariableRateSimulationSystemGroup` + a custom `RateManager` that returns true only every N seconds. Cheaper than gating with timers inside `OnUpdate`.

## Anti-patterns

- ❌ `[UpdateBefore(typeof(X))]` where X lives in a different group. **Silently ignored.** No error. Order doesn't apply across group boundaries.
- ❌ Calling `ComponentSystemGroup.SortSystems()` manually. Entities 1.x sorts via attributes only — manual sort is a 0.x managed pattern.
- ❌ Frame-coupled mutation inside `FixedStepSimulationSystemGroup`. The group runs 0–N times per frame; allocating, spawning, or reading per-frame input here under/over-fires.
- ❌ Two `[UpdateBefore]` attributes forming a cycle (A before B; B before A) — throws at world creation. Read the exception, don't suppress it.
- ❌ Creating a custom group just to "hold one system to be safe." Custom groups are for *bounded cooperating sets*, not for escaping ordering bugs.

## Failure modes

| Symptom | Cause |
|---|---|
| Reader sees value one frame late | Reader in same group as writer with no `[UpdateAfter(Writer)]` — registration order resolves it the wrong way |
| Physics tunneling / jitter at variable FPS | Physics in `SimulationSystemGroup` instead of `FixedStepSimulationSystemGroup` |
| Non-deterministic replays under same seed | Two peer systems with no explicit ordering attribute — order set by registration |
| `InvalidOperationException: Found circular dependency` | `[UpdateBefore]` cycle. Trace the chain and break it |
| Bullets fire 0 times some frames, 2× others | `[UpdateAfter]` references a system in another group — silently ignored, bullets gated by something that "should" precede them but doesn't |

## Runtime verification (Tester Verification Contract)

- **Static:** grep every `[UpdateBefore]` / `[UpdateAfter]` reference and confirm the target system carries an `[UpdateInGroup]` of the *same* group. Cross-group ordering attributes are a guaranteed bug.
- **Runtime:** in the Entities Hierarchy window (or via `World.Systems` enumeration), print the actual resolved system order for the group. Compare against design intent. For determinism, run the scenario 3× with same seed and bit-compare entity snapshots.

## Performance notes

- `FixedStepSimulationSystemGroup` running 3× per frame on a slow frame means your simulation cost triples. Cap the catch-up via the group's `RateManager.Timestep` and `MaximumDeltaTime`.
- `VariableRateSimulationSystemGroup` is the cheapest way to throttle expensive systems. Don't roll your own `if (timer > k) {…}` gate — it still pays the OnUpdate dispatch cost.
- `OrderFirst = true` / `OrderLast = true` create implicit dependencies on every other system in the group. Use sparingly; chains of OrderFirst become impossible to reason about.

## Compile / editor safety

- Group ordering is resolved at world creation. Cycles fail loudly. Cross-group attributes fail silently — keep a CI lint.
- `[CreateBefore]` / `[CreateAfter]` exist for `OnCreate` ordering (rare, used when systems read from each other's OnCreate state). Don't confuse with `[UpdateBefore]`.

## Entities version notes (1.4.x)

- `ComponentSystemBase.SortSystems()` is gone. Attribute-driven sort only.
- `[UpdateInGroup(typeof(G), OrderFirst = true)]` / `OrderLast` are current.
- `RateManager` is the current API for custom-rate groups. The 0.x `FixedStepSimulationSystemGroup.Timestep` setter is now `group.RateManager` cast to the concrete manager type.

## See also
- `dots-ecb-orchestration` — ECB system playback phase IS an update-group decision (cross-link, don't redefine here)
- `dots-singleton-patterns` — `RequireForUpdate` gates the system independent of group
- `dots-event-driven-ecs` — "events visible one frame late" is fundamentally a group-order issue
