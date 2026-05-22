# MCP Phase Gates
<!-- Hard enforcement of which MCP / unity-skills operations are allowed per execution phase. -->

## Overview

Every `/team` run passes through defined phases. Each phase has a strict MCP permission set.
Agents must declare their current phase before any MCP call.
The orchestrator enforces phase transitions — agents cannot self-advance.

## Phase Definitions

```
Phase 1 — Investigation   (READ ONLY)
Phase 2 — Implementation  (LIMITED WRITE)
Phase 3 — Validation      (PLAYMODE + READ)
Phase 4 — Refactor        (STEP-GATED WRITE)
```

Phase assignment by task mode:

| Task mode | Agents | Phases used |
|-----------|--------|-------------|
| `--bug` | bug-investigation | Phase 1 only |
| `--bug` | unity-dev | Phase 2 |
| `--bug` | tester | Phase 3 |
| `--feature` | system-mapper | Phase 1 |
| `--feature` | architect | Phase 1 (read) |
| `--feature` | unity-dev | Phase 2 |
| `--feature` | tester | Phase 3 |
| `--refactor` | refactor-agent | Phase 1 |
| `--refactor` | architect | Phase 1 (read) |
| `--refactor` | unity-dev | Phase 4 |
| `--refactor` | tester | Phase 3 (between steps) |
| `--fast-fix` | unity-dev | Phase 2 (scoped) |
| `--fast-fix` | tester | Phase 3 |

## Phase 1 — Investigation (READ ONLY)

**Agents:** bug-investigation, system-mapper, code-tracer, refactor-agent, architect (initial)

### Allowed MCP Operations

```
# Unity-Skills REST (read-only)
GET  /skills/unity_diagnose           ← ALWAYS first call
GET  /skills/scene_analyze
GET  /skills/scene_health_check
GET  /skills/scene_summarize
GET  /skills/scene_get_hierarchy
GET  /skills/scene_find_objects
GET  /skills/debug_get_errors
GET  /skills/debug_check_compilation
GET  /skills/debug_get_system_info
GET  /skills/debug_get_assembly_info
GET  /skills/debug_get_defines
GET  /skills/debug_get_memory_info
GET  /skills/console_get_logs
GET  /skills/console_get_stats
GET  /skills/profiler_get_stats
GET  /skills/profiler_get_memory
GET  /skills/profiler_get_runtime_memory
GET  /skills/profiler_get_object_count
GET  /skills/profiler_get_rendering_stats
GET  /skills/validate_find_missing_scripts
GET  /skills/validate_missing_references
GET  /skills/validate_find_unused_assets
GET  /skills/validate_scene
GET  /skills/validate_project_structure
GET  /skills/script_read
GET  /skills/script_find_in_file
GET  /skills/script_list
GET  /skills/script_get_info
GET  /skills/asset_find
GET  /skills/prefab_find_instances
GET  /skills/prefab_get_overrides
GET  /skills/project_stack_detect
GET  /skills/script_dependency_graph
GET  /skills/perception (all read variants)

# ai-game-developer MCP (read-only)
mcp__ai-game-developer__script-read
mcp__ai-game-developer__assets-find
mcp__ai-game-developer__assets-get-data
mcp__ai-game-developer__scene-list-opened
mcp__ai-game-developer__gameobject-component-get
mcp__ai-game-developer__console-get-logs
mcp__ai-game-developer__package-list

# agentmemory (read-only)
mcp__agentmemory__memory_recall
mcp__agentmemory__memory_smart_search
```

### Blocked in Phase 1 (ALL of these)

```
# Any skill with write/create/delete/modify/set in the name
# Examples:
script_create, script_replace, script_delete, script_append
gameobject_create, gameobject_delete, gameobject_move
component_add, component_remove, component_set_property
scene_save, scene_load, scene_create, scene_unload
prefab_create, prefab_apply, prefab_unpack, prefab_set_property
material_set_*, shader_*, shadergraph_add_*, shadergraph_connect_*
debug_force_recompile, debug_set_defines
editor_play, editor_pause, editor_stop
tests_run (Phase 3 only)
mcp__ai-game-developer__script-update-or-create
mcp__agentmemory__memory_lesson_save (Phase 1 output only — save after phase completes, not during)
```

### Enforcement Rule

If an agent calls a blocked skill in Phase 1:
```
[BLOCKED: Phase 1 violation — <skill_name> is write-only. Phase 1 is read-only.]
```
Orchestrator halts that agent, logs the violation to workspace/investigation.md, and does NOT proceed to Phase 2 until root cause of the call is understood.

---

## Phase 2 — Implementation (LIMITED WRITE)

**Agents:** unity-dev, data-tool (--with-tooling)

### Allowed MCP Operations

All Phase 1 operations PLUS:

```
# Script operations (primary code write channel)
mcp__ai-game-developer__script-update-or-create  ← PREFERRED write channel
POST /skills/script_create
POST /skills/script_create_batch
POST /skills/script_append
POST /skills/script_replace                       ← requires ECS Safety Checklist complete

# Scoped prefab edits (authoring layer only)
POST /skills/prefab_set_property                  ← scoped to authoring prefabs only
POST /skills/prefab_create                        ← new prefabs only
POST /skills/component_add                        ← authoring MonoBehaviours only
POST /skills/component_set_property               ← authoring layer only

# Compilation
POST /skills/debug_force_recompile                ← after edits, SemiAuto — check mode

# Editor tooling (data-tool only, --with-tooling)
POST /skills/uitoolkit_* (write variants)
POST /skills/validation_* (fix variants)

# Memory save (after ECS Safety Checklist)
mcp__agentmemory__memory_lesson_save              ← end of phase only
```

### Blocked in Phase 2

```
# Mass scene mutation
POST /skills/gameobject_delete_batch
POST /skills/scene_save                           ← save only after tester approval
POST /skills/scene_load                           ← do not reload scenes during implementation
POST /skills/component_remove                     ← structural — requires architect approval

# Architecture changes
POST /skills/debug_set_defines                    ← compilation define change = architecture risk
POST /skills/package_add, package_remove          ← dependency change = architect approval

# Playmode (Phase 3 only)
POST /skills/editor_play
POST /skills/tests_run

# Bulk operations without approval
POST /skills/prefab_apply                         ← SemiAuto — must check permission mode
POST /skills/prefab_unpack                        ← destructive — NeverInSemi
```

### Enforcement Rule

Before any Phase 2 write, unity-dev must:
1. Verify compilation is clean (`debug_check_compilation`)
2. Complete the ECS Safety Checklist (from unity-dev SKILL.md)
3. Confirm the operation is scoped to the design in `workspace/design.md`

If a blocked operation is attempted:
```
[BLOCKED: Phase 2 violation — <skill_name> requires architect approval or Phase 4 (step-gated). Write [ESCALATE: reason] to workspace.]
```

---

## Phase 3 — Validation (PLAYMODE + READ)

**Agents:** tester

### Allowed MCP Operations

All Phase 1 operations PLUS:

```
# Test execution
POST /skills/test_* (all test variants)
mcp__ai-game-developer__tests-run

# Playmode control
POST /skills/editor_play
POST /skills/editor_pause
POST /skills/editor_stop

# Runtime profiling (in playmode)
GET  /skills/profiler_get_stats           ← during playmode
GET  /skills/profiler_get_runtime_memory
GET  /skills/console_get_logs             ← during playmode
GET  /skills/console_start_capture
GET  /skills/console_stop_capture

# Screenshots for regression evidence
GET  /skills/scene_screenshot

# Validation runs
POST /skills/validate_scene
POST /skills/validate_find_missing_scripts

# Memory save (sign-off lessons)
mcp__agentmemory__memory_lesson_save
```

### Blocked in Phase 3

```
# Code changes (implementation is closed)
mcp__ai-game-developer__script-update-or-create
POST /skills/script_create, script_replace, script_delete

# Architecture changes
POST /skills/component_add, component_remove
POST /skills/prefab_apply, prefab_unpack, prefab_create

# Scene mutation
POST /skills/scene_save, scene_load
POST /skills/gameobject_*_create, *_delete
```

### Enforcement Rule

If tester needs a code change based on test findings:
1. Tester writes the finding to `workspace/test-plan.md` with evidence
2. Tester writes [BLOCKED: test failed — return to unity-dev] to workspace
3. Orchestrator routes back to Phase 2 for unity-dev
4. Tester does NOT make code changes directly

---

## Phase 4 — Refactor (STEP-GATED WRITE)

**Agents:** unity-dev (execution), tester (per-step verification)

### Step Gate Protocol

```
For each migration step N in workspace/migration-plan.md:

  unity-dev executes step N:
    → Allowed: Phase 2 write operations (scoped to this step only)
    → Writes step result to workspace/migration-plan.md Step Execution Log

  unity-dev signals:
    → Writes "Step N complete: <what changed>" to migration-plan.md

  tester verifies:
    → Runs behavior preservation tests (Phase 3 allowed operations)
    → Writes "Step N OK" or "Step N FAIL: <reason>" or "Step N BLOCKED: <reason>"
    → unity-dev WAITS — cannot proceed to step N+1 without explicit "Step N OK"

  If tester writes FAIL:
    → unity-dev rolls back step N using the rollback strategy in migration-plan.md
    → Writes [ESCALATE: step N failed after rollback] to migration-plan.md
    → Orchestrator routes to architect

  If tester writes BLOCKED:
    → unity-dev does NOT wait indefinitely
    → After 3 BLOCKED signals: write [ESCALATE: tester blocked 3 times on step N]
    → Orchestrator intervenes
```

### Allowed in Phase 4

All Phase 2 write operations, scoped to the current migration step only.

### Blocked in Phase 4

```
# Scope expansion — only approved steps
Any changes not in the approved migration plan → [SCOPE_EXCEEDED]

# Skipping steps
unity-dev must not proceed to step N+1 without Step N OK

# Rollback bypass
unity-dev must not skip rollback if step fails
```

## Phase Gate Summary Matrix

| Operation | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|-----------|---------|---------|---------|---------|
| Read scene/hierarchy | ✓ | ✓ | ✓ | ✓ |
| Read logs/console | ✓ | ✓ | ✓ | ✓ |
| Read profiler | ✓ | ✓ | ✓ (playmode) | ✓ |
| Validate (read) | ✓ | ✓ | ✓ | ✓ |
| Create/edit scripts | ✗ | ✓ | ✗ | ✓ (per-step) |
| Prefab edit (scoped) | ✗ | ✓ | ✗ | ✓ (per-step) |
| Component add (authoring) | ✗ | ✓ | ✗ | ✓ (per-step) |
| Run tests | ✗ | ✗ | ✓ | ✓ (per-step) |
| Enter playmode | ✗ | ✗ | ✓ | ✗ |
| Mass scene mutation | ✗ | ✗ | ✗ | ✗ |
| Architecture changes | ✗ | ✗ | ✗ | ✗ |
| debug_set_defines | ✗ | ✗ | ✗ | ✗ |

✓ = allowed | ✗ = blocked | architect approval required for any ✗

## Failure Handling

| Violation | Response |
|-----------|----------|
| Phase 1 write attempt | [BLOCKED] — halt agent, log to investigation.md |
| Phase 2 mass mutation | [BLOCKED] — require architect approval before retry |
| Phase 3 code change attempt | [BLOCKED] — tester cannot edit code; return to unity-dev |
| Phase 4 step skip | [BLOCKED] — step-gate violation; re-run step in order |
| Phase 4 tester BLOCKED ×3 | [ESCALATE] → orchestrator, then architect |
| Unity-Skills server unreachable | Degrade gracefully — continue with CRG + file reading |
| MCP permission denied | Check currentMode; if Approval required: pause and wait for user |
