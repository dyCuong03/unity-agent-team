# Unity-Skills Integration Matrix
<!-- Based on real repository v1.9.1 inspection -->
<!-- Loading strategy for each module when integrated into the agent team -->

## Loading Strategy Definitions

| Strategy | Meaning |
|----------|---------|
| `ALWAYS_LOAD` | Included in every agent spawn regardless of task |
| `ECS_DEFAULT` | Loaded by default for ECS tasks; skipped for pure MonoBehaviour tasks |
| `CONDITIONAL` | Loaded only when task keywords match — see trigger rules |
| `GATED` | Loaded only with explicit user flag (e.g., --with-tooling) |
| `BLOCKED` | Never loaded — conflicts with our orchestration or safety model |

## Module Matrix

### Advisory Modules (documentation-only — safe to load freely)

| Module | Loading Strategy | Owner Agent | Trigger Keywords | DOTS Safety | Notes |
|--------|-----------------|-------------|-----------------|-------------|-------|
| `architecture` | `ECS_DEFAULT` | `architect` | architecture, design, system, boundary | Medium | MonoBehaviour-centric defaults; DOTS precedence rule applies |
| `asmdef` | `ECS_DEFAULT` | `architect` | assembly, asmdef, compile, dependency | High | Critical for ECS isolation |
| `performance` | `ECS_DEFAULT` | `data-tool`, `tester` | slow, frame time, performance, profil, lag | Critical | DOTS-relevant — hot paths, Update loops |
| `testability` | `ECS_DEFAULT` | `tester` | test, coverage, seam, mock, isolat | High | ECS logic is naturally testable |
| `patterns` | `CONDITIONAL` | `architect` | pattern, architecture, design | Medium | Some patterns MonoBehaviour-centric |
| `adr` | `CONDITIONAL` | `architect` | decision, trade-off, ADR | Medium | Design documentation |
| `async` | `CONDITIONAL` | `unity-dev` | async, UniTask, coroutine, await | Medium | Jobs replace async in DOTS hot paths |
| `scene-contracts` | `ECS_DEFAULT` | `architect` | scene, lifecycle, load, bootstrap | High | Critical for hybrid ECS scenes |
| `netcode-design` | `CONDITIONAL` | `architect`, `unity-dev` | network, multiplayer, client, server, netcode | High | 10 source-anchored critical rules |
| `yooasset-design` | `CONDITIONAL` | `unity-dev` | yooasset, hot update, AB, bundle | High | 11 critical rules from source |
| `addressables-design` | `CONDITIONAL` | `unity-dev` | addressables, remote, bundle, streaming | High | Dual-version 1.22.3 / 2.9.1 |
| `shadergraph-design` | `CONDITIONAL` | `unity-dev` | shader, shadergraph, node, graph | Medium | Version-specific rules |
| `project-scout` | `ECS_DEFAULT` | `system-mapper` | unfamiliar, explore, codebase, navigate | High | Large repo navigation |
| `inspector` | `GATED` | `data-tool` | inspector, authoring, editor UI | Medium | Only for --with-tooling |
| `scriptdesign` | `CONDITIONAL` | `unity-dev` | code quality, review, script | Medium | Code quality |
| `blueprints` | `GATED` | `unity-dev` | blueprint, generate, scaffold | Low | Scaffolding tool |

### Functional REST Modules — Read-Only / Investigation (safe for agents)

| Module | Loading Strategy | Owner Agent | Trigger Keywords | DOTS Safety | Notes |
|--------|-----------------|-------------|-----------------|-------------|-------|
| `debug` | `ECS_DEFAULT` | `bug-investigation`, `data-tool` | bug, error, compile, crash, stuck | ECS-safe | `unity_diagnose` is first-call always |
| `console` | `ECS_DEFAULT` | `bug-investigation`, `tester` | log, error, warning, exception | ECS-safe | Read-only log capture |
| `perception` | `ECS_DEFAULT` | `system-mapper`, `code-tracer` | scene, hierarchy, explore, understand | ECS-safe | Scene reading without mutation |
| `profiler` | `CONDITIONAL` | `data-tool` | slow, memory, performance, profil | ECS-safe | Performance measurement |
| `validation` | `ECS_DEFAULT` | `data-tool`, `tester` | broken, missing, reference, validate | ECS-safe | Read validation — safe |
| `script` (read) | `ECS_DEFAULT` | `code-tracer` | read script, find script, locate | ECS-safe | `script_read` and `script_find_in_file` only |

### Functional REST Modules — Domain Skills (lazy loaded by task type)

| Module | Loading Strategy | Owner Agent | Trigger Keywords | DOTS Safety | Notes |
|--------|-----------------|-------------|-----------------|-------------|-------|
| `ui` | `CONDITIONAL` | `unity-dev` | UI, button, panel, canvas, HUD, popup | MonoBehaviour-first | UGUI — document DOTS hybrid boundary |
| `uitoolkit` | `CONDITIONAL` | `unity-dev`, `data-tool` | UI Toolkit, UXML, USS, UIDocument | ECS-compatible | Document-based — can integrate with ECS |
| `animator` | `CONDITIONAL` | `unity-dev` | animation, animator, blend tree, state machine | MonoBehaviour-first | DOTS Animation is separate — flag this |
| `shadergraph` | `CONDITIONAL` | `unity-dev` | shader, shadergraph, material graph | ECS-safe | Rendering agnostic |
| `timeline` | `CONDITIONAL` | `unity-dev` | timeline, cutscene, playable, sequence | ECS-compatible | Playable API can drive ECS |
| `cinemachine` | `CONDITIONAL` | `unity-dev` | camera, cinemachine, vcam, dolly | ECS-compatible | Works in ECS projects |
| `physics` | `CONDITIONAL` | `unity-dev` | physics, rigidbody, collider, raycast | ECS-compatible | Physics for Entities exists |
| `netcode` | `CONDITIONAL` | `unity-dev` | network, multiplayer, host, client, server | ECS-compatible | Netcode for GameObjects; note DOTS Netcode alternative |
| `yooasset` | `CONDITIONAL` | `unity-dev` | yooasset, hot update, bundle, YOO | ECS-safe | Asset loading agnostic |
| `optimization` | `CONDITIONAL` | `data-tool` | optimize, texture, mesh, LOD, overdraw | ECS-safe | Asset optimization |
| `prefab` | `CONDITIONAL` | `unity-dev`, `system-mapper` | prefab, baker input, authoring | ECS-safe | Baker input management |
| `scene` | `CONDITIONAL` | `system-mapper` | scene load, scene hierarchy, scene query | ECS-safe | Scene reading / management |
| `scriptableobject` | `CONDITIONAL` | `unity-dev` | ScriptableObject, SO, config, authored data | ECS-safe | Config assets |
| `navmesh` | `CONDITIONAL` | `unity-dev` | navmesh, pathfinding, navigation, AI | MonoBehaviour-first | No DOTS navmesh — flag this |
| `dotween` | `CONDITIONAL` | `unity-dev` | DOTween, tween, Sequence, animation | MonoBehaviour-first | NOT ECS-native — flag this |
| `xr` | `CONDITIONAL` | `unity-dev` | XR, VR, AR, headset, OpenXR | ECS-compatible | XR Interaction Toolkit |

### BLOCKED Modules

| Module | Reason |
|--------|--------|
| `workflow` | Conflicts with our deterministic agent orchestration |
| `smart` | Autonomous multi-step operations — unpredictable in orchestrated context |
| `batch` (as standalone) | Use batch skills within specific module calls only |
| `history` | Session state — not relevant for agent context |
| `bookmark` | Session state — not relevant for agent context |
| `sample` | Demo scaffolding — not production-appropriate |

## Token Cost Estimates

| Module type | Approximate prompt tokens | Load frequency |
|-------------|--------------------------|----------------|
| Advisory module SKILL.md | 200–400 tokens | Per-task when relevant |
| Simple functional SKILL.md | 300–600 tokens | Per-task when relevant |
| Complex design module (netcode-design, addressables-design) | 800–1500 tokens + sub-docs | Only when task requires it |
| All 70 modules loaded at once | ~30,000–50,000 tokens | NEVER — prompt explosion |

## Loading Budget per Agent per Task

| Agent | Max advisory modules | Max domain modules | Always-loaded |
|-------|---------------------|-------------------|---------------|
| `architect` | 3 | 0 | architecture, asmdef, scene-contracts |
| `unity-dev` | 1 | 2 | (none always; 1 advisory + 2 domain max) |
| `data-tool` | 1 | 2 | debug, validation |
| `tester` | 1 | 1 | testability, console |
| `system-mapper` | 1 | 2 | perception, project-scout |
| `code-tracer` | 0 | 1 | debug, script (read-only) |
| `bug-investigation` | 0 | 1 | debug, console |
| `refactor-agent` | 1 | 0 | performance |
