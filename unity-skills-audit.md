# Unity-Skills Repository Audit
<!-- Source: https://github.com/Besty0728/Unity-Skills v1.9.1 -->
<!-- Grounded in real repository inspection — no invented modules -->

## Real Folder Structure

```
SkillsForUnity/
├── package.json                          (com.besty.unity-skills v1.9.1)
├── Editor/
│   ├── UnitySkills.Editor.asmdef
│   ├── AssemblyInfo.cs
│   ├── Skills/                           (74 C# skill files — REST skill implementations)
│   │   ├── AnimatorSkills.cs
│   │   ├── AudioSkills.cs
│   │   ├── AssetSkills.cs
│   │   ├── BatchSkills.cs
│   │   ├── CameraSkills.cs
│   │   ├── CinemachineSkills.cs
│   │   ├── ComponentSkills.cs
│   │   ├── ConsoleSkills.cs
│   │   ├── DebugSkills.cs
│   │   ├── DecalSkills.cs
│   │   ├── DiagnoseSkills.cs
│   │   ├── DOTweenSkills.cs
│   │   ├── EditorSkills.cs
│   │   ├── EventSkills.cs
│   │   ├── GameObjectSkills.cs
│   │   ├── GraphicsSkills.cs
│   │   ├── LightSkills.cs
│   │   ├── MaterialSkills.cs
│   │   ├── ModelSkills.cs
│   │   ├── NavMeshSkills.cs
│   │   ├── NetcodeSkills.cs
│   │   ├── OptimizationSkills.cs
│   │   ├── PackageSkills.cs
│   │   ├── PerceptionSkills.cs
│   │   ├── PhysicsSkills.cs
│   │   ├── PostProcessSkills.cs
│   │   ├── PrefabSkills.cs
│   │   ├── ProBuilderSkills.cs
│   │   ├── ProfilerSkills.cs
│   │   ├── ProjectSkills.cs
│   │   ├── SceneSkills.cs
│   │   ├── ScriptSkills.cs
│   │   ├── ScriptableObjectSkills.cs
│   │   ├── ShaderGraphSkills.cs
│   │   ├── ShaderSkills.cs
│   │   ├── SmartSkills.cs
│   │   ├── TerrainSkills.cs
│   │   ├── TestSkills.cs
│   │   ├── TextureSkills.cs
│   │   ├── TimelineSkills.cs
│   │   ├── UISkills.cs
│   │   ├── UIToolkitSkills.cs
│   │   ├── URPSkills.cs
│   │   ├── ValidationSkills.cs
│   │   ├── VolumeSkills.cs
│   │   ├── WorkflowSkills.cs
│   │   ├── XRSkills.cs
│   │   ├── YooAssetSkills.cs
│   │   └── ... (infrastructure: BatchExecutor, SkillRouter, SkillsModeManager, etc.)
│   └── UI/                               (Editor window — AI config panel)
├── Tests/
│   └── Editor/
│       ├── UnitySkills.Tests.Editor.asmdef
│       └── Core/                         (14 test files)
└── unity-skills~/                        (AI routing layer — installed into .claude/skills/)
    ├── SKILL.md                          (root AI definition — agent.md mirrors this)
    ├── scripts/
    │   └── unity_skills.py               (Python REST client v1.9.1)
    └── skills/
        ├── SKILL.md                      (module index — 49 functional + 20 advisory)
        ├── [49 functional module dirs]   (each with SKILL.md — REST callable)
        └── [20 advisory module dirs]     (each with SKILL.md — documentation only)
```

## 49 Functional REST Modules

Each module exposes REST skills callable via HTTP at `http://localhost:8090/skills/<name>`.

| Module | Category | Permission Mode | Batch | DOTS Safety |
|--------|----------|----------------|-------|-------------|
| `gameobject` | Scene manipulation | FullAuto | Yes | MonoBehaviour-first |
| `component` | Scene manipulation | Mixed | Yes | MonoBehaviour-first |
| `material` | Rendering | FullAuto | Yes | ECS-safe |
| `light` | Scene/Rendering | FullAuto | Yes | ECS-safe |
| `prefab` | Assets | FullAuto | Yes | ECS-safe (baker inputs) |
| `asset` | Assets | FullAuto | Yes | ECS-safe |
| `batch` | Infrastructure | Mixed | Yes | ECS-safe |
| `ui` | UI/UGUI | FullAuto | Yes | MonoBehaviour-first |
| `uitoolkit` | UI Toolkit | Mixed | No | ECS-compatible |
| `script` | Code | SemiAuto | Yes | ECS-safe |
| `scene` | Scene | SemiAuto | No | ECS-safe |
| `editor` | Editor control | Mixed | No | ECS-safe |
| `animator` | Animation | FullAuto | No | MonoBehaviour-first |
| `shader` | Rendering | FullAuto | Yes | ECS-safe |
| `shadergraph` | Rendering | Mixed | No | ECS-safe |
| `graphics` | Rendering | FullAuto | Yes | ECS-safe |
| `volume` | Rendering/PostFX | FullAuto | No | ECS-safe |
| `postprocess` | Rendering | FullAuto | No | ECS-safe |
| `urp` | Rendering | Mixed | No | ECS-safe |
| `decal` | Rendering | FullAuto | No | ECS-safe |
| `console` | Debugging | SemiAuto | No | ECS-safe |
| `validation` | Validation | SemiAuto | No | ECS-safe |
| `importer` | Assets | Mixed | No | ECS-safe |
| `cinemachine` | Camera | FullAuto | No | ECS-compatible |
| `probuilder` | Modeling | FullAuto | No | ECS-safe |
| `xr` | XR | Mixed | No | ECS-compatible |
| `terrain` | Scene | FullAuto | No | ECS-safe |
| `physics` | Physics | Mixed | No | ECS-compatible |
| `navmesh` | AI Navigation | FullAuto | No | MonoBehaviour-first |
| `timeline` | Animation/Cutscene | FullAuto | No | ECS-compatible |
| `workflow` | Orchestration | Mixed | No | ECS-safe |
| `cleaner` | Project hygiene | Mixed | No | ECS-safe |
| `smart` | Smart/batch ops | Mixed | No | ECS-safe |
| `perception` | Scene reading | SemiAuto | No | ECS-safe |
| `camera` | Camera | Mixed | No | ECS-compatible |
| `event` | Events | FullAuto | No | MonoBehaviour-first |
| `package` | Package Manager | Mixed | No | ECS-safe |
| `project` | Project analysis | Mixed | No | ECS-safe |
| `profiler` | Performance | SemiAuto | No | ECS-safe |
| `optimization` | Performance | Mixed | No | ECS-safe |
| `sample` | Sample/demo | FullAuto | No | ECS-safe |
| `debug` | Debugging | SemiAuto | No | ECS-safe |
| `test` | Testing | SemiAuto | No | ECS-safe |
| `bookmark` | Workflow memory | FullAuto | No | ECS-safe |
| `history` | Workflow history | Mixed | No | ECS-safe |
| `scriptableobject` | Data | FullAuto | No | ECS-safe |
| `netcode` | Networking | Mixed | Yes | ECS-compatible |
| `yooasset` | Asset management | Mixed | Yes | ECS-safe |
| `dotween` | Animation/Tweening | Mixed | Yes | MonoBehaviour-first |

## 20 Advisory Design Modules

Documentation-only. No REST calls. Safe to load as context. No mutations.

| Module | Purpose | DOTS Relevance |
|--------|---------|----------------|
| `architecture` | System boundary planning | High — but MonoBehaviour-centric by default |
| `asmdef` | Assembly dependency planning | Critical for ECS assembly isolation |
| `adr` | Architectural decision records | High — design traceability |
| `performance` | Hot path review | Critical for DOTS optimization |
| `testability` | Extract testable logic | High — ECS logic is naturally testable |
| `patterns` | Pattern selection | Medium — some patterns are MonoBehaviour-centric |
| `async` | Async model choice | Medium — Jobs replace async in ECS hot paths |
| `inspector` | Inspector field design | Low for ECS; relevant for authoring components |
| `script-roles` | Script responsibility design | Medium |
| `scene-contracts` | Scene lifecycle contracts | High for hybrid ECS scenes |
| `blueprints` | Blueprint generation | Low |
| `project-scout` | Project navigation | High for large repos |
| `scriptdesign` | Script quality | Medium |
| `netcode-design` | Netcode design rules | High — 10 critical rules from source |
| `yooasset-design` | YooAsset design rules | High — 11 critical rules from source |
| `addressables-design` | Addressables version-specific rules | High — dual-version (1.22.3/2.9.1) |
| `unitask-design` | UniTask usage rules | Medium |
| `dotween-design` | DOTween design rules | Low — MonoBehaviour-only |
| `shadergraph-design` | ShaderGraph version rules | Medium |

## Architecture: REST Server Model

Unity-Skills runs as an HTTP server inside Unity Editor at `http://localhost:8090/`.

- AI agents call skills via HTTP REST (`POST /skills/<name>`) or via the Python client
- The server uses a producer-consumer model: HTTP thread queues requests, Unity main thread executes
- Permission gate: every skill call is filtered by the active mode (Approval/Auto/Bypass)
- Transactional: failed skill calls trigger automatic undo
- Domain Reload resilient: server survives Unity domain reloads

**Three permission modes** (must be checked before calling any skill):
- **Approval**: every skill requires user confirmation in Unity panel
- **Auto**: safe FullAuto skills execute automatically; SemiAuto pauses for large batches
- **Bypass**: all skills execute automatically (no confirmation)

**~121 SemiAuto skills**: pause in Auto mode for batches >=5 objects, prefab applies, irreversible changes
**~40+ NeverInSemi skills**: never auto-execute even in Auto mode (destructive or structural)

## Semi-Auto vs Full-Auto Classification for Engineering Workflows

**SAFE for deterministic engineering workflow (ECS-safe, read-only, advisory):**
- All 20 advisory modules (documentation only)
- `debug`, `console`, `profiler`, `validation`, `perception` (read-only snapshots)
- `script_read`, `scene_get_hierarchy`, `asset_find` (read-only queries)

**SAFE with CARE (functional but contained mutations):**
- `script_create`, `script_create_batch` (creates new files, no mutation)
- `validation` query skills (find issues, no fix)
- `package` query skills
- `optimization` analyze skills

**DANGEROUS for deterministic DOTS production (irreversible, structural):**
- `gameobject_delete`, `scene_save`, `scene_load` (structural mutation)
- `prefab_apply`, `prefab_unpack` (prefab structure change)
- `script_replace`, `script_delete` (code mutation)
- `component_add`, `component_remove` (scene mutation)
- `debug_set_defines` (compilation mutation)
- `workflow` module (orchestration risk — could conflict with our agent orchestrator)

**BLOCKED (must never run autonomously in our agent system):**
- `workflow` module — conflicts with our deterministic orchestration
- `smart` module — high-level automation that may overlap agent decision-making
- Any NeverInSemi skill in Auto mode without explicit orchestrator approval
