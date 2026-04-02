---
name: unity-dots-best-practices
description: Unity DOTS, ECS, Jobs, and Burst guidance for scalable runtime systems. Use when designing or implementing components, systems, bakers, blob assets, scheduling, or performance-sensitive simulation.
user-invocable: false
---

When working on Unity DOTS runtime code:

- Design around data layout and access patterns first.
- Prefer `IComponentData`, `IBufferElementData`, `BlobAsset`, `Aspect`, `ISystem`, Burst, and jobs where they clearly improve scale and maintainability.
- Keep hot paths allocation-free and avoid managed-object patterns in simulation code.
- Minimize structural changes in frequently executed loops.
- Treat archetype churn, sync points, and main-thread fallbacks as explicit costs.
- Keep authoring/baker code separate from runtime systems.
- Make update order and ownership explicit.
- Prefer deterministic, debuggable data flow over implicit side effects.

Before finalizing a design or implementation, check:

1. Is the data representation aligned with read/write patterns?
2. Are there avoidable sync points?
3. Are structural changes limited and intentional?
4. Is this Burst/job friendly?
5. Will the approach scale to large entity counts?
