# Unity-Skills Integration Conflict Report
<!-- Based on real repository v1.9.1 -->

## Architecture Conflicts

### Conflict 1: MonoBehaviour Update() vs ISystem.OnUpdate()

**Source**: `architecture/SKILL.md` default guidance recommends "thin MonoBehaviour scripts as composition bridges."
**Conflict**: In a DOTS-first project, MonoBehaviour is a boundary layer — not the primary execution model.
**Resolution**: When `architecture/SKILL.md` advice conflicts with DOTS-first policy:
- `ISystem.OnUpdate()` > MonoBehaviour `Update()`
- ECS query > per-object `Update()` loop
- `architect` agent must override architecture module advice when the task is ECS-bound

### Conflict 2: ScriptableObject as runtime state vs ECS singleton

**Source**: `patterns/SKILL.md` recommends ScriptableObject for shared state.
**Conflict**: ECS uses singleton components (`SystemAPI.GetSingleton<T>()`) for shared runtime state.
**Resolution**:
- ScriptableObject → ECS: use ScriptableObject for authored config (baker input only)
- Runtime shared state → `IComponentData` singleton on a dedicated entity
- Flag to architect when `patterns/SKILL.md` suggests ScriptableObject for runtime use

### Conflict 3: Coroutine / UniTask vs Jobs

**Source**: `async/SKILL.md` recommends coroutines or UniTask for sequences.
**Conflict**: In ECS hot paths, async = Jobs + `Dependency` chains, not coroutines.
**Resolution**:
- ECS hot path → Jobs with dependency handles
- Bootstrap/initialization sequences (not hot paths) → coroutines or UniTask acceptable
- `unity-dev` must override `async/SKILL.md` recommendations when the task is ECS-bound

### Conflict 4: gameobject/component modules vs Entity/IComponentData

**Source**: `gameobject/SKILL.md` and `component/SKILL.md` work exclusively with GameObjects.
**Conflict**: ECS entities are not GameObjects. Calling `component_add` on a runtime ECS entity does not exist.
**Resolution**:
- `gameobject` and `component` modules are valid ONLY for authoring MonoBehaviours and Baker inputs
- Runtime entity manipulation → EntityCommandBuffer, `EntityManager`, ISystem jobs
- These modules must NEVER be loaded for tasks involving runtime ECS entity manipulation

### Conflict 5: animator module vs DOTS Animation

**Source**: `animator/SKILL.md` works with the MonoBehaviour Animator component.
**Conflict**: DOTS uses the Animator Graph (DOTS Animation package) with different APIs.
**Resolution**:
- `animator/SKILL.md` is valid for the authoring layer only
- For DOTS Animation, the module provides no applicable skills — `unity-dev` must use ECS Animation package APIs directly
- Flag this explicitly when `--feature` involves character animation in an ECS project

### Conflict 6: navmesh module — no DOTS equivalent

**Source**: `navmesh/SKILL.md` works with Unity's MonoBehaviour-based Navigation system.
**Conflict**: There is no production-ready NavMesh for Entities in Unity DOTS as of 2024.
**Resolution**:
- NavMesh work in a DOTS project → hybrid boundary: NavMesh agent on GameObject, position synced to entity
- `architect` must explicitly design the hybrid boundary — `navmesh/SKILL.md` provides authoring support only
- Flag this as a known hybrid necessity

### Conflict 7: dotween module — MonoBehaviour only

**Source**: `dotween/SKILL.md` and `dotween-design/SKILL.md` work exclusively with DOTween animations on transforms, UI, and MonoBehaviour state.
**Conflict**: DOTween has no ECS integration. DOTween tweens target UnityEngine.Transform and MonoBehaviour fields.
**Resolution**:
- DOTween is valid for the presentation/view layer only (UI, cutscene, authoring animation)
- For ECS-driven movement → Jobs, mathematical interpolation, or Timeline Playables
- Never load DOTween modules for tasks in the ECS simulation layer

### Conflict 8: workflow module — orchestration collision

**Source**: `workflow/SKILL.md` provides multi-step task orchestration within Unity Skills.
**Conflict**: Our agent team already orchestrates multi-step workflows. Letting unity-skills `workflow` module run autonomously creates a parallel orchestrator.
**Resolution**: `workflow` module is **BLOCKED** in our system. All orchestration stays in the agent team.

## Responsibility Conflicts

### Conflict A: system-mapper vs perception module

**system-mapper** runs CRG to map architecture. `perception/SKILL.md` reads live scene state via REST.
**Not a conflict — complementary**: system-mapper uses CRG for code-level architecture. Perception reads runtime scene state.
**Resolution**: system-mapper may call `perception` skills when it needs live scene evidence to complement CRG findings. It owns the final output.

### Conflict B: code-tracer vs script/scene modules

**code-tracer** uses CRG to trace execution. `script/SKILL.md` and `scene/SKILL.md` can read the same files via REST.
**Resolution**: code-tracer should prefer CRG. It may use `script_read` and `scene_get_hierarchy` as supplementary evidence when CRG coverage is insufficient. CRG result takes precedence.

### Conflict C: data-tool vs validation/profiler/optimization modules

**data-tool** builds diagnostics and tooling. These modules extend what data-tool can build and observe.
**Resolution**: No conflict — additive. data-tool is the owner; these modules are its domain skill set.

### Conflict D: tester vs testability/validation modules

**tester** designs and runs tests. `testability/SKILL.md` and `validation/SKILL.md` provide advisory and runtime checks.
**Resolution**: No conflict — additive. tester is the owner.

## Token-Cost Risks

### Risk 1: Design modules with sub-docs

`addressables-design/SKILL.md` references 8 sub-files (INIT.md, HANDLES.md, LOADING.md, etc.).
`netcode-design/SKILL.md` references 8 sub-files.
`yooasset-design/SKILL.md` references 8 sub-files.
`dotween-design/SKILL.md` references 9 sub-files.
`shadergraph-design/SKILL.md` references 5 sub-files.

**Risk**: An agent loading all sub-files would add 3000–8000 tokens per design module.
**Mitigation**: Load only the top-level `SKILL.md` first. Load sub-files only when the specific sub-topic is confirmed necessary (e.g., load `PITFALLS.md` when the task matches a known failure mode).

### Risk 2: Loading all modules for "general" tasks

A general task like "improve the game" could match many keyword triggers simultaneously.
**Mitigation**: Hard cap of 2 domain modules + 2 advisory modules per agent per task. Orchestrator must select top-2 most relevant by keyword density, not load all matches.

### Risk 3: Redundant investigation

`perception`, `debug`, `console`, and `validation` all provide scene/project state.
**Mitigation**: Call `unity_diagnose` first (aggregated health snapshot). Only call specific modules if `unity_diagnose` reveals a gap.

## Dangerous Automation Risks

### Risk A: workflow + smart modules

Both provide multi-step, high-level automation that could mass-mutate scenes.
**Mitigation**: Both are BLOCKED in our agent system.

### Risk B: script_replace in bug-fix mode

`script_replace` can overwrite any file in the project.
**Mitigation**: Requires orchestrator pre-approval. Never used in automated fast-fix mode. Only after ECS Safety Checklist.

### Risk C: gameobject_delete_batch

Can delete multiple GameObjects in one call. Irreversible without undo.
**Mitigation**: NeverInSemi — always requires user confirmation. Agents must check permission mode before calling.

### Risk D: debug_set_defines

Changes scripting define symbols, triggering full recompilation.
**Mitigation**: SemiAuto — requires user confirmation. Agents must not call this without explicit orchestrator approval.
