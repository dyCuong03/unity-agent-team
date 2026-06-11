---
name: qa-validation
description: Validation rules for Unity DOTS features — correctness, scale, determinism, regression coverage, and release-readiness checklists. Use when creating test matrices, stress scenarios, reproduction steps, or performance regression anchors.
use-when: |
  Load for tester agent for any task requiring test design, regression validation,
  performance sign-off, or release-readiness verification. Also load for data-tool
  agent when building validation pipelines or authoring content validators.
do-not-use-when: |
  Do not load for unity-dev or unity-dots-dev during Phase 2 implementation.
  Do not load for architect or triage roles. Not needed before implementation is complete.
platforms: [claude-code, codex, copilot, cursor, windsurf]
metadata:
  source: internal
  version: 1.0.0
  tier: 1
  user-invocable: false
task-categories: [testing, qa, validation, evidence, playmode]

---

# QA Validation — Unity DOTS

When validating Unity DOTS features, prove correctness with **evidence**, not intuition. See `@.claude/docs/mcp-integration.md` for `ai-game-developer` and `agentmemory` tool usage.

> **MANDATORY contract:** every verification run by the `tester` or `verifier`
> agent MUST satisfy the **Tester Runtime + Static Verification Contract**.
> Read `@.claude/skills/qa-validation/verification-contract.md` before
> producing `workspace/verification_result.json`. Both layers (static +
> runtime) are required unless explicitly impossible per §7 of the contract.

## Core Principles

- Test **correctness, edge cases, failure modes, scale limits**.
- Verify **baker output, component state transitions, system ordering, entity lifecycle**.
- Add **stress scenarios** for high entity counts, bursty spawn/despawn, and structural changes.
- Check **regression risk** after every fix — every defect becomes a regression test.
- Prefer **reproducible setups, measurable evidence, concise failure reports**.
- Use `mcp__ai-game-developer__tests-run` and `console-get-logs` as primary evidence — not assertion in chat.

## Test Layers

| Layer | Tool | When |
|---|---|---|
| EditMode unit | `[Test]` in `Tests/EditMode` | Pure logic, baker output, blob construction |
| EditMode integration | `[Test]` with `World.Default` | System interaction, ECB playback, query results |
| PlayMode | `[UnityTest]` in `Tests/PlayMode` | Multi-frame behavior, gameplay scenarios |
| Stress | Custom scenes + `[UnityTest]` | 10k–100k entity scaling, churn, performance |

## ECS Test Patterns

### Pure system test
```csharp
[Test]
public void HealthSystem_AppliesDamage_ReducesHP() {
    using var world = new World("test");
    // arrange: create entity with HealthComponent
    // act: world.Update<HealthSystem>()
    // assert: query HealthComponent.Value
}
```

### Baker test
```csharp
[Test]
public void HealthAuthoring_BakesTo_HealthComponent() {
    var go = new GameObject();
    go.AddComponent<HealthAuthoring>();
    // Use BakingUtility or manual bake via test world
    // assert baker output
}
```

### Stress harness
- Build the test scene with `mcp__ai-game-developer__scene-create` + `gameobject-duplicate`.
- Enter play mode via `editor-application-set-state`.
- Sample frame time over a stable window (skip first 60 frames for warm-up).
- Capture results via `tests-run` output and `console-get-logs`.

## Evidence Requirements

Every validation report must answer:

1. **What behavior was tested?** — link to acceptance criteria
2. **Under what setup?** — scene, fixtures, seed, entity count, hardware
3. **What was expected?** — from Architect's spec
4. **What actually happened?** — raw output, not paraphrase
5. **Does the feature remain stable under stress?** — frame time, memory, error count
6. **What risks remain open?** — explicit "not tested" list

## Stress Test Targets

- **Frame time**: median + p99 over a 5s window after warm-up.
- **Memory**: GC alloc per frame should be 0 in steady state; managed heap stable; native allocations bounded.
- **Determinism**: same seed + same input → same output across 3 runs.
- **Race risk**: parallel jobs with overlapping writes must not produce per-run-different state.

## Anti-Patterns

- Sign-off based on a single play-mode session
- Ignoring intermittent failures ("ran 3 times, passed twice")
- Stress tests without warm-up — first-frame cost is not steady-state cost
- Regression tests that don't actually exercise the original fix path
- Reports without reproduction steps
- "It works on my machine" — capture hardware, Unity version, package versions

## Reproduction Format

```
ENV: Unity 2022.3.x, Entities 1.x, Windows 11
SCENE: Assets/Tests/StressScene_Health.unity
SEED: 12345
ENTITIES: 50000
STEPS:
  1. Open scene
  2. Play mode
  3. Wait 60 frames
  4. Frame 61: trigger DamageBurst event
EXPECTED: HP component count == initial; no exceptions in console
ACTUAL: 47 entities with HP < 0; NullReferenceException in HealthSystem.OnUpdate line 42
EVIDENCE: console-get-logs output attached; screenshot-game-view at frame 61
```
