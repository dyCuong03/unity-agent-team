# MCP Integration — `ai-game-developer` and `agentmemory`

This package is wired to two MCP servers that every role in the team must use:

| Server | Purpose | Required For |
|---|---|---|
| `ai-game-developer` | Live Unity Editor introspection and mutation (assets, scenes, GameObjects, components, scripts, console, tests, screenshots, reflection) | All roles — primary evidence source for Unity-side state |
| `agentmemory` | Cross-session memory: recall prior decisions, save lessons, consolidate findings, reflect on sessions | All roles — primary continuity layer across tasks |

## Core Rules

1. **Always prefer `ai-game-developer` MCP over guessing project state.**
2. **Always call `agentmemory` at the start and end of a task.** Recall first, save lessons last.
3. **If a tool is unavailable, state it explicitly** ("Running without MCP evidence" / "Running without memory recall") and fall back to code reading.

---

## `ai-game-developer` Tool Map

The Unity Editor MCP exposes the following capability groups. Use the exact tool names below — do not invent variants.

### Asset & project layout

| Tool | When to use |
|---|---|
| `mcp__ai-game-developer__assets-find` | Locate assets by name, type, label, or path |
| `mcp__ai-game-developer__assets-find-built-in` | Look up Unity built-in assets (materials, shaders) |
| `mcp__ai-game-developer__assets-get-data` | Read serialized data of an asset |
| `mcp__ai-game-developer__assets-create-folder` | Create folders under `Assets/` |
| `mcp__ai-game-developer__assets-copy` / `assets-move` / `assets-delete` | Reorganize project structure |
| `mcp__ai-game-developer__assets-modify` | Mutate serialized fields on an asset |
| `mcp__ai-game-developer__assets-refresh` | Force AssetDatabase refresh after external edits |
| `mcp__ai-game-developer__assets-material-create` | Create materials |
| `mcp__ai-game-developer__assets-shader-list-all` / `assets-shader-get-data` | Inspect shaders |
| `mcp__ai-game-developer__package-list` / `package-search` / `package-add` / `package-remove` | Check or change Unity packages (Entities, Burst, Jobs, etc.) |

### Prefab & scene

| Tool | When to use |
|---|---|
| `mcp__ai-game-developer__assets-prefab-open` / `assets-prefab-close` / `assets-prefab-save` | Edit prefabs in isolation |
| `mcp__ai-game-developer__assets-prefab-create` / `assets-prefab-instantiate` | Author new authoring prefabs |
| `mcp__ai-game-developer__scene-list-opened` / `scene-get-data` / `scene-open` / `scene-save` | Scene introspection and lifecycle |
| `mcp__ai-game-developer__scene-create` / `scene-set-active` / `scene-unload` | Build test/repro scenes |

### GameObject & component

| Tool | When to use |
|---|---|
| `mcp__ai-game-developer__gameobject-find` | Locate authoring or runtime objects |
| `mcp__ai-game-developer__gameobject-create` / `gameobject-duplicate` / `gameobject-destroy` | Author or tear down test fixtures |
| `mcp__ai-game-developer__gameobject-modify` / `gameobject-set-parent` | Rename, retag, restructure hierarchies |
| `mcp__ai-game-developer__gameobject-component-add` / `component-destroy` / `component-modify` | Attach or edit authoring components |
| `mcp__ai-game-developer__gameobject-component-get` / `component-list-all` | Inspect component state — primary baker-input verifier |
| `mcp__ai-game-developer__object-get-data` / `object-modify` | Generic object serialization access |

### Scripting & reflection

| Tool | When to use |
|---|---|
| `mcp__ai-game-developer__script-read` / `script-update-or-create` / `script-delete` | Edit C# from Unity's perspective (keeps AssetDatabase coherent) |
| `mcp__ai-game-developer__script-execute` | Run ad-hoc C# inside the editor (debug probes, one-shot inspection) |
| `mcp__ai-game-developer__reflection-method-find` / `reflection-method-call` | Probe internal types/methods without writing throwaway scripts |
| `mcp__ai-game-developer__type-get-json-schema` | Read a type's JSON schema before serializing/deserializing |

### Editor state & evidence capture

| Tool | When to use |
|---|---|
| `mcp__ai-game-developer__editor-application-get-state` / `editor-application-set-state` | Check or toggle play mode, pause, focused window |
| `mcp__ai-game-developer__editor-selection-get` / `editor-selection-set` | Drive editor selection for repro/debug |
| `mcp__ai-game-developer__console-get-logs` / `console-clear-logs` | Capture or reset console output |
| `mcp__ai-game-developer__screenshot-game-view` / `screenshot-scene-view` / `screenshot-camera` / `screenshot-isolated` | Visual evidence for QA and tooling |
| `mcp__ai-game-developer__tests-run` | Execute EditMode/PlayMode tests, capture results |
| `mcp__ai-game-developer__tool-list` | Discover available tools at runtime (use sparingly) |

---

## `agentmemory` Tool Map

`agentmemory` provides persistent, searchable memory across sessions. Every agent must integrate it.

| Tool | When to use |
|---|---|
| `mcp__agentmemory__memory_recall` | At task start — recall recent decisions, gotchas, conventions related to the task |
| `mcp__agentmemory__memory_smart_search` | When you need targeted lookup of a specific subsystem, bug, or pattern |
| `mcp__agentmemory__memory_sessions` | List past sessions to find ones relevant to current work |
| `mcp__agentmemory__memory_save` | Save a discrete fact or observation worth remembering |
| `mcp__agentmemory__memory_lesson_save` | Save a lesson learned (root cause + fix + when it applies) at end of task |
| `mcp__agentmemory__memory_consolidate` | After multiple related entries, fold them into a tighter representation |
| `mcp__agentmemory__memory_reflect` | At end of session — high-level synthesis across what was learned |
| `mcp__agentmemory__memory_diagnose` | When memory results seem stale, missing, or contradictory |

### Memory lifecycle (mandatory per agent, per task)

```
START   → memory_recall ("task topic + Unity DOTS")
        → memory_smart_search if a specific subsystem/bug is named
WORK    → memory_save for any non-obvious decision, constraint, or workaround
END     → memory_lesson_save for each lesson (cause + symptom + fix)
        → memory_reflect once per /team run, by team lead
        → memory_consolidate when the same topic has accumulated 3+ entries
```

---

## Mandatory Usage Policy (Per Role)

Every role must perform the MCP calls below at the listed checkpoints.

### Architect

| Checkpoint | Calls |
|---|---|
| Task start | `memory_recall`, `memory_smart_search` for similar feature areas. `assets-find` / `scene-list-opened` to anchor design surface. `package-list` to confirm DOTS package availability. |
| During design | `scene-get-data`, `gameobject-find`, `gameobject-component-get` to verify authoring assumptions. `script-read` to inspect existing systems. |
| Before freeze | `console-get-logs` to confirm baseline has no blocking errors. `memory_save` for each major design decision. |
| Handoff | `memory_lesson_save` for design risks worth remembering. |

### Unity Developer

| Checkpoint | Calls |
|---|---|
| Task start | `memory_recall` for prior implementations of similar systems. `assets-find` / `script-read` to map current code surface. |
| During implementation | `script-update-or-create` for all C# edits. `script-execute` for one-shot probes. `gameobject-component-get` to verify baker input. `console-get-logs` after compile. |
| Before validation | `tests-run` (EditMode at minimum). `memory_save` for any non-obvious code pattern. |
| Handoff | `memory_lesson_save` for performance/Burst pitfalls discovered. |

### Data Tool Engineer

| Checkpoint | Calls |
|---|---|
| Task start | `memory_recall` for prior tooling in this area. `assets-find` to survey existing editor scripts. |
| During build | `assets-get-data` / `object-get-data` to anchor inspectors in real data. `reflection-method-find` for internal type access. `script-update-or-create` for tool code. |
| Validation | `screenshot-game-view` / `screenshot-scene-view` for visual confirmation. `console-get-logs` for diagnostics output. |
| Handoff | `memory_save` for each tool entry point. `memory_lesson_save` for observability gaps closed. |

### Tester / QA

| Checkpoint | Calls |
|---|---|
| Task start | `memory_recall` for prior defects in adjacent systems. `console-clear-logs`. |
| During validation | `tests-run` (EditMode and PlayMode where relevant). `console-get-logs` after each run. `screenshot-game-view` for visual regressions. `gameobject-component-get` to inspect post-test state. |
| Stress | `scene-create` / `gameobject-create` / `gameobject-duplicate` to build high-load scenes. `editor-application-set-state` for play-mode entry. |
| Handoff | `memory_lesson_save` for each defect found (symptom + cause + fix). `memory_consolidate` if the area has accumulated entries. |

---

## Decision Tree

### "What exists right now?"
Use `ai-game-developer` first: `assets-find`, `scene-list-opened`, `gameobject-find`, `console-get-logs`.

### "How is this implemented?"
Read source first (Read/Grep), then verify Unity-side state with `gameobject-component-get` / `object-get-data` only if it matters.

### "Has this been done before?"
Use `agentmemory` first: `memory_recall`, `memory_smart_search`.

### "Is this actually working?"
Use `tests-run` + `console-get-logs` + targeted screenshots. Trust nothing else.

---

## Anti-Patterns

- Assuming a baker output without `gameobject-component-get` confirmation
- Editing C# directly via Write/Edit when `script-update-or-create` keeps the AssetDatabase coherent
- Skipping `console-clear-logs` before a repro — stale errors will mislead diagnosis
- Skipping `memory_recall` at task start, then re-discovering a lesson the team already learned
- Saving every minor decision to memory — only save what would surprise a future reader
- Calling `memory_consolidate` reflexively — only when 3+ related entries exist in the same topic

---

## Fallback Policy

If `ai-game-developer` MCP is unavailable:
- State **"Running without MCP evidence"** in the role's status update.
- Fall back to file reads (Read/Grep) for code logic only.
- **Do not invent** scene hierarchies, serialized values, or test results.
- Re-attempt MCP calls each handoff in case the server comes back online.

If `agentmemory` MCP is unavailable:
- State **"Running without memory recall"** in the role's status update.
- Continue work without prior context.
- Re-attempt at next checkpoint.
