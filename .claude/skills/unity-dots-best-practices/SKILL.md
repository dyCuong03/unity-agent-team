---
name: unity-dots-best-practices
description: Unity DOTS, ECS, Jobs, and Burst guidance for scalable runtime systems. Core best-practices covering components, systems, bakers, blob assets, scheduling, structural change costs, and performance-sensitive simulation patterns for Entities 1.3+.
use-when: |
  Load for unity-dots-dev on any DOTS or Hybrid domain task. Always included as P1
  knowledge for architect and unity-dots-dev. Load when writing ISystem, IJobEntity,
  Baker, blob assets, ECB, or any ECS architecture decisions.
do-not-use-when: |
  Do not load for the unity-dev classic lane (MonoBehaviour tasks). Do not load for
  tester or verifier roles. Not needed for pure editor-tooling with no runtime ECS.
platforms: [claude-code, codex, copilot, cursor, windsurf]
metadata:
  source: https://docs.unity3d.com/Packages/com.unity.entities@1.3
  version: 1.3.8
  tier: 1
  user-invocable: false
task-categories: [ecs, performance, burst, jobs, dots]

---

# Unity DOTS Best Practices

When working on Unity DOTS runtime code, design and verify against these constraints. See `@.claude/docs/mcp-integration.md` for `ai-game-developer` and `agentmemory` tool usage.

## Design Principles

- Design around **data layout and access patterns first**.
- Prefer `IComponentData`, `IBufferElementData`, `BlobAssetReference<T>`, `IAspect`, `ISystem`, Burst, and jobs where they clearly improve scale and maintainability.
- Keep hot paths **allocation-free** — no managed objects in simulation code.
- Minimize **structural changes** inside frequently executed loops.
- Treat **archetype churn**, **sync points**, and **main-thread fallbacks** as explicit costs, not background noise.
- Keep **authoring/baker code separate** from runtime systems (asmdef boundaries).
- Make **update order and ownership** explicit. Never imply ordering.
- Prefer **deterministic, debuggable data flow** over implicit side effects.

## Component & Buffer Design

- One concern per component. Don't pack unrelated fields just because they share an entity.
- `IBufferElementData` for variable-size per-entity data; cap with `InternalBufferCapacity` thoughtfully.
- `BlobAssetReference<T>` for large, immutable, shared data (e.g., level configs, ability data).
- `IEnableableComponent` for state toggles that would otherwise cause add/remove churn.
- Avoid managed components except for editor-bridging cases.

## System Design

- Prefer `ISystem` (Burst-compilable) over `SystemBase` for hot paths.
- Use `SystemAPI` for queries, singletons, time, lookups — keeps intent explicit.
- Explicit `[UpdateInGroup]`, `[UpdateAfter]`, `[UpdateBefore]` — never rely on implicit ordering.
- Keep system responsibilities narrow. Compose, don't merge.

## Job Design

- `IJobEntity` for per-entity work where chunk access is not needed.
- `IJobChunk` when you need chunk-level batching, change filtering, or component lookup optimization.
- `EntityCommandBuffer` for structural changes, with intentional playback point.
- `EntityCommandBuffer.ParallelWriter` for parallel structural changes — pass `sortKey` correctly.
- Manage `Dependency` explicitly when chaining multiple jobs.

## Burst Compatibility

- No managed references, no virtual dispatch, no `string`, no `throw` in hot loops.
- `BurstCompile` everything that can be Burst-compiled. Address compilation failures immediately.
- `[BurstCompile(CompileSynchronously = true)]` for tests so failures surface in CI.

## NativeContainers

- Allocator choice: `Allocator.Temp` (single frame, main thread), `Allocator.TempJob` (≤4 frames), `Allocator.Persistent` (long-lived).
- Always dispose. Use `using` or explicit `.Dispose()` in `OnDestroy`.
- Pass `[ReadOnly]` and `[WriteOnly]` attributes to enable parallelism.

## Self-Check Before Finalizing

1. Is the data representation aligned with read/write patterns?
2. Are there avoidable sync points? (`EntityManager.CompleteAllTrackedJobs`, `.GetSingleton`, structural changes outside ECB)
3. Are structural changes limited and intentional?
4. Is this Burst/job friendly? Any non-Burst-compatible types?
5. Will the approach scale to large entity counts (target: 10k–100k)?
6. Have I memoized any per-frame allocations into job-owned containers?
7. Have I confirmed Unity-side state with `mcp__ai-game-developer__gameobject-component-get` (for authoring) or `tests-run` (for behavior)?
8. Have I saved a `memory_lesson_save` for non-obvious decisions?

## Anti-Patterns

- `EntityManager.CreateEntity` / `AddComponent` inside `OnUpdate` without ECB
- Capturing managed lambdas in `SystemBase.Entities.ForEach` hot paths
- Using `SystemBase` where `ISystem` would work
- Implicit system ordering ("it happens to run before X")
- Buffers used as unbounded queues without consume logic
- One giant component that everyone reads and writes
- Manager-pattern singletons disguised as ECS singletons
