---
name: system-update-order
description: Declare a system''s group membership and relative ordering within that group using attributes, producing deterministic execution order verified at world initialization.
tags: [core, systems]
---

# System Update Order

## Intent
Declare a system's group membership and relative ordering within that group using attributes, producing deterministic execution order verified at world initialization.

## Use When
Any system that must run relative to physics, transforms, ECB playback, or other systems in a defined sequence.

## Avoid When
Order relative to other systems is genuinely irrelevant — omitting UpdateBefore/UpdateAfter reduces coupling and gives the scheduler more parallelism freedom.

## Senior Pattern
- `[UpdateInGroup(typeof(SimulationSystemGroup))]` — group membership.
- `[UpdateBefore(typeof(OtherSystem))]` / `[UpdateAfter(typeof(OtherSystem))]` — relative order within the same group only.
- `[UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]` — for physics/deterministic systems.
- `[UpdateInGroup(typeof(TransformSystemGroup))]` `[UpdateAfter(typeof(ParentSystem))]` — for custom transform systems.
- `[WorldSystemFilter(WorldSystemFilterFlags.Default | WorldSystemFilterFlags.Editor)]` — for systems that must run in the editor's live-baking world.

## Code Template
```csharp
[BurstCompile]
[UpdateInGroup(typeof(SimulationSystemGroup))]
[UpdateAfter(typeof(PhysicsSystemGroup))]
public partial struct DamageResolveSystem : ISystem { }

// Custom transform that must work in editor subscene preview:
[BurstCompile]
[WorldSystemFilter(WorldSystemFilterFlags.Default | WorldSystemFilterFlags.Editor)]
[UpdateInGroup(typeof(TransformSystemGroup))]
[UpdateAfter(typeof(ParentSystem))]
public partial struct CustomTransformSystem : ISystem { }
```

## Anti-Patterns
- UpdateBefore/UpdateAfter referencing a system in a different group — constraint is silently ignored.
- Circular ordering (A before B, B before A) — startup exception.
- Over-constraining (every system has UpdateBefore/After) — reduces scheduler parallelism and makes order hard to reason about.
- Forgetting UpdateInGroup — system lands in SimulationSystemGroup by default, may run at wrong time relative to physics or transforms.

## Runtime Risks
- Constraint referencing a system in a different group: silently has no effect — appears to work but ordering is undefined.
- Circular constraint: world initialization throws, world never starts.

## Performance Notes
Ordering resolution is O(systems) at world creation only. No per-frame cost.

## Architecture Guidance
Prefer coarse group assignment (InitializationSystemGroup, SimulationSystemGroup, PresentationSystemGroup, FixedStepSimulationSystemGroup) over fine-grained UpdateBefore/After. Reserve UpdateBefore/After for genuine data-dependency ordering, not cosmetic preference.
