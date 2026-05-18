---
name: editor-data-tools
description: Guidance for Unity data processing, editor tooling, validators, and DOTS debugging helpers. Use when building authoring workflows, diagnostics, inspectors, or developer utilities.
user-invocable: false
---

# Editor Data Tools

When building Unity data tools and diagnostics, design for **isolation, reproducibility, and disable-by-default cost**. See `@.claude/docs/mcp-integration.md` for `ai-game-developer` and `agentmemory` tool usage.

## Design Principles

- Editor-only code lives in `Editor/` folders or `*.Editor.asmdef` — **never** leak into runtime assemblies.
- Tools must be **optional** — toggleable via menu, attribute, or `#if UNITY_EDITOR`.
- Validators **fail with actionable messages**: "field X on asset Y at path Z is null; expected ...".
- Make baker output and runtime ECS state inspectable — prefer a custom editor window or inspector over `Debug.Log` spam.
- Keep diagnostics **cheap when disabled and explicit when enabled**.
- No debug-only dependencies in shipping runtime code (verify with `Player Build` not just `Editor`).
- Build **reproducible fixtures**, debug views, and tracing helpers for investigation.

## Editor Window Patterns

- Use `EditorWindow` with `[MenuItem]` registration.
- Persist state with `SerializedObject` or `[SerializeField]` on the window itself.
- Use `EditorGUILayout` for default; switch to `UIElements` (`VisualElement`) for complex layouts.
- Wire `Selection.selectionChanged` carefully — unhook in `OnDisable`.

## Inspector Patterns

- `[CustomEditor(typeof(MyAuthoring))]` for authoring component inspectors.
- Override `OnInspectorGUI` minimally — prefer extending the default with `base.OnInspectorGUI()` first.
- Show baker output preview via `DOTSEditor` introspection or by simulating bake via a Subscene's `World.Default`.

## Validation Patterns

- Validators are **functions**, not behaviors — pure: take an object, return a list of issues.
- Each issue should include: severity, target object, field path, expected vs actual, fix suggestion.
- Wire validators into:
  - `AssetPostprocessor` for on-import validation
  - `Menu` items for batch validation
  - `BuildPipeline.IPreprocessBuild` for ship-gate validation

## Debug Visualization

- Scene gizmos via `OnDrawGizmos` / `OnDrawGizmosSelected` only on authoring components, never on runtime ECS.
- For ECS state, draw via an `ISystem` that runs in `EditorWorld` or behind `#if UNITY_EDITOR` toggles.
- Use `Handles.DrawWireDisc` etc. for higher-quality drawing than `Gizmos`.

## Tool Definition Checklist

Every tool must clearly define:

1. **Target user** — designer, engineer, QA, or all
2. **Inputs** — what it reads (assets, components, scenes)
3. **Outputs** — what it produces (logs, files, asset mutations, UI)
4. **Validation behavior** — what it rejects and how it reports
5. **Performance impact** — cost when active vs inactive
6. **Failure modes** — what happens if input is malformed
7. **Entry points** — menu, hotkey, inspector button, attribute

## Anti-Patterns

- Editor scripts in non-Editor asmdef
- Silent `try { ... } catch { }` swallowing validation errors
- Tools that mutate prefabs without `Undo.RecordObject`
- `EditorApplication.update` subscriptions never unhooked
- Inspectors that bypass `serializedObject.ApplyModifiedProperties()` (changes don't persist)
- Per-frame editor work when window not focused
- Diagnostics that allocate every `OnGUI` repaint
