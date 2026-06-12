---
name: routing
description: Lazy skill loading router for the Unity DOTS agent team. Use this to determine which Unity-Skills modules to load before spawning agents. Never load all modules — select only what the task requires.
use-when: |-
  Load when the orchestrator needs to select which Unity-Skills modules to include for an agent prompt. Load when determining Layer 1/2/3 skill loading strategy before spawning any agent.
do-not-use-when: |-
  Do not load as a runtime skill inside any agent role. Internal orchestration helper only — never loaded by triage, unity-dev, architect, or tester.
platforms: [claude-code]
task-categories: [meta, orchestration]
metadata:
  source: internal
  version: 1.0.0
  tier: 1

---

# Unity Skill Router

## Status

Unity-Skills routing layer **vendored** at `.claude/skills/unity-skills/`
(upstream `Besty0728/Unity-Skills` v1.9.2 — see
`.claude/skills/unity-skills/VERSION`). 69 module SKILL.md files are
available locally; the orchestrator can resolve every `@.claude/skills/
unity-skills/skills/<module>/SKILL.md` reference without a missing-file
fallback. The Unity Editor package (`com.besty.unity-skills`) must still
be installed into the consuming Unity project for REST calls to
`http://localhost:8090` to succeed.

## Purpose

Select the minimum set of Unity-Skills modules to load for a given task.
Prevent prompt bloat. Maximize relevance. Preserve DOTS-first policy.

## Domain Gating (MANDATORY — applies before keyword routing)

The classifier from `.claude/docs/rules/dual-stack-domain-system.md` runs first.
Its output decides which side of the catalog the router is even allowed to
draw from:

| Triage domain | Layer 1 (DOTS) | Layer 2 (Unity Foundation) | Layer 3 (unity-skills modules) |
|---|---|---|---|
| **DOTS** (Domain 1) | Heavy — always | Light — always | **Skip by default.** Load only if a unity-skills module is explicitly required by a hybrid touchpoint (e.g. Baker authoring, presentation bridge). MonoBehaviour-first modules are forbidden in this domain. |
| **Unity** (Domain 2) | Light — advisory only | Heavy — always | **Primary source.** Use the keyword table below. Max 2 domain + 2 advisory. |
| **Hybrid** (Domain 3) | Heavy — DOTS owns runtime truth | Heavy — Unity owns presentation | **Both sides loaded.** Pick one DOTS-side concern and one Unity-side concern; `verification-contract.md` requires the bridge contract be documented in `workspace/design.md`. |
| **Ambiguous** | Layer 1 + 2 only | Layer 1 + 2 only | None — escalate to architect per `escalation-rules-domain.md`. |

Hard scoping rules:

- **DOTS domain → never load** `ui`, `animator`, `navmesh`, `dotween`,
  `event`, `gameobject`, `component` (all MonoBehaviour-first; see
  `unity-skills-conflicts.md`). The ecs-penalty modifier in
  `skill-confidence-routing.md` already drops these below threshold; the
  router must respect that and not bypass it.
- **Unity domain → never load** burst, scheduling, native-container, ECS
  job pattern advisory unless DOTS APIs are detected in touched code.
- **Hybrid domain → BOTH allowed**, but the bridge direction is one-way
  (DOTS writes state, Unity reads). Verify this in `ownership-boundaries.md`.
- **Loaded module budget** (any domain): max 2 domain + 2 advisory per agent
  per task. The confidence threshold ≥ 0.70 from
  `skill-confidence-routing.md` still applies.

## Hard Limits

- Maximum 2 domain skill modules per agent per task
- Maximum 2 advisory modules per agent per task
- NEVER load `workflow` or `smart` modules — they conflict with orchestration
- NEVER load DOTween modules for ECS simulation layer tasks
- NEVER load `gameobject` or `component` modules for runtime ECS entity tasks

## Unity-DOTS Skill Pack (ECS_DEFAULT — auto-loaded when triage classifies DOTS or Hybrid)

The `unity-dots/*` sub-skills (vendored under `.claude/skills/unity-dots/`) are loaded **in addition to** Layer 1 / Layer 2 when the triage domain classification is DOTS or Hybrid. They are NOT loaded for Unity-only tasks.

| Keywords (case-insensitive) | unity-dots skill | Confidence floor |
|---|---|---|
| baking, baker, authoring, TransformUsageFlags, BlobAsset, prefab reference, DependsOn | `dots-baking-patterns` | 0.80 |
| ECB, EntityCommandBuffer, structural change, ParallelWriter, ChunkIndexInQuery, playback phase, BeginSimulation, EndSimulation | `dots-ecb-orchestration` | 0.80 |
| enableable, IEnableableComponent, EnabledRefRW, SetComponentEnabled, state flip, hot toggle, archetype churn | `dots-enableable-components` | 0.78 |
| DestroyEntity, lifecycle, ICleanupComponentData, orphan entity, two-phase teardown, subscene unload | `dots-entity-lifecycle` | 0.78 |
| spawn, Instantiate, batched spawn, Random.CreateFromIndex, RequireForUpdate, ECB.Instantiate | `dots-spawning-patterns` | 0.78 |

Loading rules:
- Apply on top of the existing per-domain budget (max 2 unity-skills domain + 2 advisory). Unity-dots skills count **separately** as ECS_DEFAULT — they are not gated by the 2+2 budget.
- Hard-cap unity-dots skills per agent: **2** for a tiny/small task, **3** for medium, **all** for large/critical or refactor-agent runs.
- For ambiguous classification: do NOT load unity-dots skills. Architect must classify first.

## Boot Requirement

Before calling any REST skill, the orchestrator MUST call:
```
GET http://localhost:8090/health
```
Check `currentMode`: `approval` / `auto` / `bypass`.
Agents must respect this mode — do not call SemiAuto or NeverInSemi skills without user confirmation in Approval mode.

## Layer Definitions

### Layer 1 — Core ECS (always loaded, no routing needed)
File: `@.claude/skills/unity-dots-best-practices/SKILL.md`
- Loaded for every agent in every task
- DOTS > OOP Unity — this layer's rules take precedence over all Unity-Skills advice

### Layer 2 — Unity Foundation (always loaded lightweight)
File: `@.claude/skills/unity-foundation/SKILL.md`
- Loaded for `architect`, `unity-dev`, `data-tool`
- Contains: asmdef guidance, scene-contracts, project-scout summary

### Layer 3 — Domain Skills (lazy loaded by routing rules below)
Path pattern: `@.claude/skills/unity-skills/skills/<module>/SKILL.md`
- Loaded only when task keywords match
- Maximum 2 per agent

### Layer 4 — Investigation Skills (loaded for investigation agents)
File: `@.claude/skills/investigation/SKILL.md`
- Loaded for: `system-mapper`, `code-tracer`, `bug-investigation`
- Contains: debug, console, perception usage guidance

## Routing Decision Table

For each task, the orchestrator scores keyword matches and selects top-2 domain modules.

### Domain Keyword → Module Mapping

| Keywords (case-insensitive) | Domain Module | Advisory Module | DOTS Flag |
|----------------------------|---------------|-----------------|-----------|
| UI, button, panel, canvas, HUD, popup, screen, menu | `ui` | — | MonoBehaviour-first — route to view layer |
| UI Toolkit, UXML, USS, UIDocument, VisualElement | `uitoolkit` | — | ECS-compatible |
| animation, animator, blend tree, state machine, clip | `animator` | — | MonoBehaviour-first — flag DOTS Animation alternative |
| shader, ShaderGraph, node graph, blackboard, HLSL | `shadergraph` | `shadergraph-design` | ECS-safe |
| timeline, cutscene, playable, sequence, signal track | `timeline` | — | ECS-compatible |
| camera, Cinemachine, vcam, dolly, follow camera | `cinemachine` | — | ECS-compatible |
| physics, Rigidbody, collider, raycast, physics mat | `physics` | — | ECS-compatible |
| navmesh, pathfinding, navigation, NavMeshAgent | `navmesh` | — | MonoBehaviour-first — no DOTS navmesh |
| netcode, multiplayer, NetworkVariable, host, client, server, RPC | `netcode` | `netcode-design` | ECS-compatible |
| Addressables, remote asset, bundle, streaming | — | `addressables-design` | ECS-safe |
| YooAsset, YOO, hot update, AB build | `yooasset` | `yooasset-design` | ECS-safe |
| DOTween, tween, Sequence, ease, DOMove | `dotween` | `dotween-design` | MonoBehaviour-first — NOT ECS-native |
| URP, HDRP, render pipeline, volume, post process | `urp` | — | ECS-safe |
| optimize, texture, mesh, LOD, overdraw, asset size | `optimization` | `performance` | ECS-safe |
| profil, frame time, memory usage, GC, allocation | `profiler` | `performance` | ECS-safe |
| prefab, baker input, authoring component | `prefab` | — | ECS-safe |
| ScriptableObject, SO, config asset, authored data | `scriptableobject` | — | ECS-safe |
| XR, VR, AR, headset, OpenXR, hand tracking | `xr` | — | ECS-compatible |
| pattern, singleton, factory, observer, event bus | — | `patterns` | Medium |
| async, UniTask, coroutine, await, async/await | — | `async` | Medium — Jobs preferred in ECS hot paths |
| architecture, system boundary, module design | — | `architecture` | Medium — DOTS precedence applies |
| asmdef, assembly, compile time, dependency graph | — | `asmdef` | High |

### Investigation Keyword → Module Mapping

| Keywords | Module | Notes |
|----------|--------|-------|
| bug, error, exception, crash, NullReference | `debug` | Call `unity_diagnose` first |
| log, warning, compile error | `console` | Read-only log capture |
| scene, hierarchy, explore scene | `perception` | Scene reading |
| slow, performance, frame time | `profiler` | Read-only snapshot |
| broken reference, missing script, validate | `validation` | Project health |

## Routing Examples

### Task: "Enemy stops chasing after teleport" → `--bug`
```
Investigation agent loads: debug, console (investigation layer)
unity-dev loads: (none — bug fix, no domain skills needed unless physics or navmesh)
tester loads: testability (foundation)
```

### Task: "Add shop UI popup" → `--feature`
```
system-mapper loads: perception (investigation layer)
architect loads: architecture (advisory), scene-contracts (foundation)
unity-dev loads: ui (domain), uitoolkit (domain if UI Toolkit project)
tester loads: validation (foundation)
data-tool (if --with-tooling): uitoolkit
```

### Task: "Add multiplayer lobby" → `--feature`
```
system-mapper loads: perception
architect loads: architecture, netcode-design (advisory)
unity-dev loads: netcode (domain), netcode-design (advisory)
tester loads: testability
```

### Task: "Addressables memory leak" → `--bug`
```
bug-investigation loads: debug, console
unity-dev loads: addressables-design (advisory) — no REST skills for Addressables
tester loads: testability, profiler
```

### Task: "Replace transform animation with DOTween" → `--feature`
```
WARNING — DOTS FLAG: DOTween is MonoBehaviour-first. Confirm this is for the view/presentation layer.
system-mapper loads: perception
architect loads: architecture (with DOTS boundary flag)
unity-dev loads: dotween (domain), dotween-design (advisory)
tester loads: testability
```

### Task: "ECS combat system rewrite" → `--refactor`
```
No domain skills loaded — pure DOTS task
refactor-agent: CRG only + performance (advisory)
architect: asmdef (advisory), architecture (advisory)
unity-dev: (none beyond Layer 1 ECS)
tester: testability
```

### Task: "Optimize texture memory" → general
```
data-tool loads: optimization (domain), profiler (domain), performance (advisory)
```

## DOTS Precedence Rule (MANDATORY)

When any Unity-Skills module gives advice that conflicts with DOTS-first policy:

1. **ISystem.OnUpdate() wins over MonoBehaviour Update()**
2. **Entity + IComponentData wins over GameObject + MonoBehaviour state**
3. **Jobs + Dependency wins over async/await in hot paths**
4. **ECB structural changes win over direct EntityManager in jobs**
5. **ECS singleton component wins over ScriptableObject for runtime state**

When a module is flagged MonoBehaviour-first: load it ONLY if the task is explicitly at the view/presentation/authoring boundary. State this boundary explicitly in the agent prompt.
