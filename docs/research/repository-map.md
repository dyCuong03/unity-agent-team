# EntityComponentSystemSamples — Repository Map

**Source:** https://github.com/Unity-Technologies/EntityComponentSystemSamples
**Local path:** `E:/BuzzleStudio/BackpackAdventures/EntityComponentSystemSamples`
**Total size:** ~1.3 GB
**Entities package version range:** 1.4.3 – 1.4.4 (Entities 1.x current)
**Indexed:** 2026-05-26

This is the Phase 0 inventory. Sample listings; no patterns extracted yet.

---

## Top-level subprojects

| Folder | Type | Purpose | Entities pkg |
|---|---|---|---|
| `EntitiesSamples/` | Unity project | Reference samples — Baking, Boids, Streaming, ExampleCode, Graphical, UI Toolkit | 1.4.x via packages-lock |
| `Dots101/` | Project group | Tiered tutorials — Entities101, Jobs101, Netcode101, Physics101, ContentManagement101, OtherSamples | 1.4.x |
| `NetcodeSamples/` | Unity project | Multiplayer reference (Netcode for Entities) | 1.4.4 |
| `PhysicsSamples/` | Unity project | Unity Physics + ECS reference | 1.4.3 |
| `GraphicsSamples/` | Unity project | Hybrid Renderer / Entities Graphics reference | — |

**Wave 1 priority:** `EntitiesSamples/Assets/Baking`, `EntitiesSamples/Assets/ExampleCode`, `Dots101/Entities101/Assets/HelloCube`. These are the highest-density "production-pattern-per-line" sources.

---

## `EntitiesSamples/Assets/` — primary reference set

| Subfolder | Content | Skill domains it informs |
|---|---|---|
| `Baking/AutoAuthoring` | Auto-generated authoring from runtime components | `baking`, `authoring-conventions` |
| `Baking/BakingDependencies` | Baker dependency tracking (`DependsOn`, `GetComponent` in Baker) | `baking-dependencies` |
| `Baking/BakingTypes` | TransformUsageFlags choices, baking type filters | `baking-transform-flags` |
| `Baking/BlobAssetBaker` | Build BlobAssetReference at bake time | `blob-assets`, `baking` |
| `Baking/BlobAssetBakingSystem` | Bake-time system writing blob assets | `baking-systems` |
| `Baking/PrefabReference` | Entity prefab refs across scenes | `prefab-references`, `entity-lifecycle` |
| `Boids/` | Spatial query + parallel jobs at scale | `jobs-and-burst`, `chunk-iteration`, `performance` |
| `ExampleCode/Baking.cs` | Distilled baker patterns | `baking` |
| `ExampleCode/ComponentsSystems.cs` | Distilled component & system patterns | `ecs-architecture`, `system-design` |
| `ExampleCode/Jobs.cs` | Distilled job patterns | `jobs-and-burst` |
| `ExampleCode/Mathematics.cs` | Unity.Mathematics usage in jobs | `math-in-jobs` |
| `Streaming/AssetManagement` | Subscene / asset streaming | `subscenes`, `streaming` |
| `Streaming/PrefabAndSceneReferences` | Reference resolution across scenes | `prefab-references` |
| `Streaming/RuntimeContentManager` | Runtime addressables for entities | `streaming`, `content-management` |
| `Streaming/SceneManagement` | Subscene load/unload patterns | `subscenes`, `entity-lifecycle` |
| `Graphical/` | Hybrid rendering examples | `hybrid-renderer` (lower priority) |
| `UI Toolkit/` | UI Toolkit + ECS bridge | `hybrid-bridge` (lower priority) |

---

## `Dots101/Entities101/Assets/HelloCube` — 15 numbered micro-samples (gold mine)

Each sub-sample isolates one ECS concept. Highest density for skill mining.

| # | Sub-sample | Skill domain |
|---|---|---|
| 1 | MainThread | `system-design` baseline (no jobs) |
| 2 | IJobEntity | `jobs-and-burst` |
| 3 | Prefabs | `spawning`, `prefab-references` |
| 4 | IJobChunk | `chunk-iteration`, `jobs-and-burst` |
| 5 | Reparenting | `transform-patterns` |
| 6 | EnableableComponents | `enableable-components` |
| 7 | GameObjectSync | `hybrid-bridge` |
| 8 | CrossQuery | `entity-queries` |
| 9 | RandomSpawn | `spawning`, `determinism` |
| 10 | FirstPersonController | `input-to-ecs`, `hybrid-bridge` |
| 11 | FixedTimestep | `update-groups`, `determinism` |
| 12 | CustomTransforms | `transform-patterns` |
| 13 | StateChange | `enableable-components`, `structural-change` |
| 14 | ClosestTarget (+ KDTree) | `spatial-query`, `jobs-and-burst` |
| 15 | UnityObjectRef | `hybrid-bridge`, `managed-refs` |

## `Dots101/Entities101/Assets/{Kickball, Tornado, Firefighters}` — multi-step builds

Show how features compose. Useful for `ecs-architecture` and `system-design` *anti-patterns* — early steps often show naive patterns refactored in later steps.

| Project | Steps | Use for |
|---|---|---|
| Kickball | 5 (Step 1–5) | Feature decomposition over time |
| Tornado | flat + AtomicCounter | Parallel write coordination |
| Firefighters | 4 (Step 1–4) | Multi-system orchestration |

---

## `Dots101/` siblings (skim, lower priority for Wave 1)

- `Jobs101/` — pure Jobs system (not ECS-specific)
- `Netcode101/` — Netcode for Entities intro
- `Physics101/` — Unity Physics intro
- `ContentManagement101/` — addressables for entities
- `OtherSamples/` — misc

## Out-of-scope for Wave 1
- `NetcodeSamples/`, `PhysicsSamples/`, `GraphicsSamples/` — defer to dedicated waves. Each is large enough to need its own pass.

---

## What this map is NOT

- Not a pattern catalog. See `dots-pattern-catalog.md` (written in Phase 2).
- Not a skill list. See `skill-backlog.md` (written in Phase 3).
- Not a value judgment on the samples. The reverse-engineer role applies the "challenge the examples" rule in Phase 2.
