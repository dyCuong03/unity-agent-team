---
name: unity-skill-router
description: Lazy skill loading router for the Unity DOTS agent team. Use this to determine which Unity-Skills modules to load before spawning agents. Never load all modules — select only what the task requires.
---

# Unity Skill Router

## Purpose

Select the minimum set of Unity-Skills modules to load for a given task.
Prevent prompt bloat. Maximize relevance. Preserve DOTS-first policy.

## Hard Limits

- Maximum 2 domain skill modules per agent per task
- Maximum 2 advisory modules per agent per task
- NEVER load `workflow` or `smart` modules — they conflict with orchestration
- NEVER load DOTween modules for ECS simulation layer tasks
- NEVER load `gameobject` or `component` modules for runtime ECS entity tasks

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
