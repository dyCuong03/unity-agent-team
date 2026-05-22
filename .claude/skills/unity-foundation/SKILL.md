---
name: unity-foundation
description: Lightweight Unity Foundation skill for the agent team. Always loaded for architect, unity-dev, and data-tool. Covers assembly design, scene lifecycle contracts, project navigation, and Unity-specific code quality. Does NOT replace core ECS skills — those take precedence.
---

# Unity Foundation

This skill is SECONDARY to core ECS skills. When ECS and foundation guidance conflict, ECS wins.

## Assembly Design (asmdef)

- Split editor code from runtime in separate assemblies (runtime.asmdef, editor.asmdef)
- Keep test code in a dedicated tests.asmdef — never reference test code from runtime
- Dependency direction: Tests → Runtime ← Editor (never Runtime → Editor)
- For ECS: additional split — authoring.asmdef references runtime.asmdef only
- Minimize inter-assembly dependencies to reduce compile times in large repos

## Scene Lifecycle Contracts

For hybrid ECS + MonoBehaviour projects:
- Define explicit entry/exit contracts for each scene (what ECS state exists on entry, what is cleaned on exit)
- MonoBehaviour bootstrap: one entry point (`[DefaultExecutionOrder(-10000)]`), no static singletons
- ECS world lifecycle: world is created at bootstrap, systems initialize in OnCreate, dispose in OnDestroy
- Hybrid boundary: MonoBehaviour components that exist for baker input only — mark with clear naming convention

## Project Navigation (for large repos)

- Before reading code: check workspace/repo-knowledge.md for prior system mapping
- Before designing: check workspace/ecs-registry.md for existing components
- Use `perception` REST skills to read live scene state when code reading is insufficient
- Use CRG `get_architecture_overview` for code-level system discovery

## Unity-Specific Code Quality

- Every Update/LateUpdate/FixedUpdate must open with guard clauses (isInitialized, null checks)
- Prefer early returns over nested conditionals
- Keep MonoBehaviour lifecycle methods as thin wrappers — delegate to plain C# classes
- For ECS: ISystem methods are already guard-free by design — no MonoBehaviour guard clauses needed
- Debug.Log is NOT stripped in Player builds by default — use conditional compilation or custom logger

## Unity-Skills REST Integration

When calling Unity-Skills REST skills:
1. Always check `GET /health` before first skill call — verify `currentMode`
2. Respect the permission mode — do not call SemiAuto skills without checking mode
3. Call `unity_diagnose` first for any debugging task — it provides an aggregated health snapshot
4. Prefer read-only skills (perception, debug, console) over mutating skills unless mutation is required
5. Batch-first: when touching 2+ objects, prefer `*_batch` skills over repeated single calls
6. Do NOT call `workflow` or `smart` modules — they conflict with agent orchestration
