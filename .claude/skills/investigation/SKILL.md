---
name: unity-investigation
description: Investigation skill layer for system-mapper, code-tracer, and bug-investigation agents. Covers REST-based scene reading, log analysis, compilation diagnostics, and performance snapshots. All skills in this layer are read-only unless explicitly noted.
---

# Unity Investigation Skills

Investigation agents use this layer for live Unity Editor evidence.
CRG (code-review-graph) is always the primary tool. Unity-Skills REST provides supplementary runtime evidence.

## Investigation Priority Order

1. **Check workspace/repo-knowledge.md** — prior architectural knowledge
2. **Check workspace/ecs-registry.md** — known component/system ownership
3. **CRG investigation** (code-review-graph) — code-level tracing
4. **unity_diagnose** — aggregated Unity Editor health snapshot (REST)
5. **Specific REST skills** — only when 1–4 leave gaps

Never skip to REST skills without first checking workspace files and CRG.

## Aggregated Diagnostic (always first REST call)

```
GET /skills/unity_diagnose
```
Returns: compilation status, play mode state, active scene, error count, memory summary.
Use this before any specific investigation skill — it often reveals the issue without further calls.

## Compilation Diagnostics

Module: `debug`

```
debug_check_compilation    — check if project compiles cleanly
debug_get_errors           — get compile errors with file/line
debug_force_recompile      — trigger recompile (SemiAuto — check mode first)
debug_get_defines          — list scripting define symbols
debug_get_assembly_info    — list loaded assemblies
```

Use `debug_check_compilation` before any bug investigation. If compilation fails, fix it before investigating runtime behavior — most apparent bugs are actually compile errors.

## Log Analysis

Module: `console`

```
console_get_logs           — get logs with optional filter
console_start_capture      — begin capturing (before play mode)
console_stop_capture       — end capturing
console_get_stats          — error/warning/log counts
```

For bug investigation: start capture before reproducing, stop after, filter by error type.

## Scene State Reading

Module: `perception`

```
scene_analyze              — full scene structure analysis
scene_health_check         — check for common scene problems
scene_summarize            — brief scene summary
scene_context              — scene state for AI context
project_stack_detect       — detect project tech stack
script_dependency_graph    — dependency visualization
```

Use `scene_analyze` to understand scene structure before CRG investigation for scene-specific bugs.
Use `project_stack_detect` at the start of system-mapper's first run to update workspace/repo-knowledge.md.

## Performance Evidence

Module: `profiler`

```
profiler_get_stats         — frame time, CPU/GPU stats
profiler_get_memory        — total memory breakdown
profiler_get_runtime_memory — runtime allocation breakdown
profiler_get_object_count  — active object/entity counts
profiler_get_rendering_stats — draw calls, batches, overdraw
```

profiler skills are read-only snapshots. They do NOT start/stop the Profiler window.
For ECS performance: profiler_get_stats gives frame time; use Unity Profiler window for job-level detail.

## Validation Evidence

Module: `validation`

```
validate_find_missing_scripts   — locate broken component references
validate_missing_references     — find null/missing asset refs
validate_shader_errors          — find shaders with errors
validate_scene                  — broad scene validation
validate_project_structure      — project hygiene check
```

For bug investigation: run `validate_find_missing_scripts` and `validate_missing_references` early.
Missing script/reference issues are a common source of NullReferenceExceptions that masquerade as logic bugs.

## ECS-Specific Investigation Notes

- ECS runtime state is NOT inspectable via unity-skills REST (no `entity_get_components` skill exists)
- For ECS investigation: use CRG + `debug_get_errors` + `console_get_logs` for compile/runtime errors
- For ECS performance: use profiler skills for frame-level data + Entities Profiler for entity-specific detail
- For baker issues: use `validate_missing_references` + `scene_analyze` on the authoring scene
