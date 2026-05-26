---
name: unity-dots
description: Index of senior-level Unity DOTS / ECS skills mined from Unity's EntityComponentSystemSamples. Use the sub-skills below by routing keywords; do NOT load this index as a skill on its own — it's a directory.
---

# Unity DOTS Skill Pack — Index

Senior-level Unity DOTS engineering skills. Each sub-skill is small and composable. Skills target Entities 1.4.x.

Source-of-truth: `Unity-Technologies/EntityComponentSystemSamples` (read once, generalized; future agents should not need to re-read it).

## Wave 1 — Foundation (shipped)

| Skill | Trigger keywords | Pairs with |
|---|---|---|
| [`dots-baking-patterns`](dots-baking-patterns/SKILL.md) | baking, baker, authoring, TransformUsageFlags, BlobAsset, prefab reference, DependsOn, IBaker | spawning, lifecycle |
| [`dots-ecb-orchestration`](dots-ecb-orchestration/SKILL.md) | ECB, EntityCommandBuffer, structural change, ParallelWriter, ChunkIndexInQuery, BeginSimulation, EndSimulation, playback phase | enableable, lifecycle, spawning |
| [`dots-enableable-components`](dots-enableable-components/SKILL.md) | enableable, IEnableableComponent, EnabledRefRW, SetComponentEnabled, state flip, hot toggle, archetype churn | ecb, lifecycle |
| [`dots-entity-lifecycle`](dots-entity-lifecycle/SKILL.md) | DestroyEntity, lifecycle, ICleanupComponentData, cleanup component, orphan entity, two-phase teardown, subscene unload, Entity.Exists | ecb, enableable |
| [`dots-spawning-patterns`](dots-spawning-patterns/SKILL.md) | spawn, Instantiate, batched spawn, Random.CreateFromIndex, RequireForUpdate, prefab Entity, ECB.Instantiate | baking, ecb, lifecycle |

## Wave 2 — Architecture & Hybrid (in flight — panel-owned)

Wave 2 is **NOT shipped**. The orchestrator-synthesized drafts from a prior session are preserved under `workspace/dots-program/scratch/wave-2-orchestrator-drafts/` as reference material. Per the panel-owned execution model, Wave 2 must be re-authored by the 4 Claude panels:

1. Reverse Engineer (Panel 2) audits/extends the prior evidence package
2. Architect (Panel 1) approves the skill specs
3. QA Curator (Panel 3) validates against the checklist
4. Skill Builder (Panel 4) writes the canonical SKILL.md files into this directory via `/skill-creator`

See `workspace/dots-program/README.md` for the protocol and `workspace/dots-program/inboxes/wave-2/` for each panel's assignment.

Target skills (panel-pending): `dots-update-groups`, `dots-singleton-patterns`, `dots-transform-patterns`, `dots-hybrid-bridge`, `dots-event-driven-ecs`.

## Planned (Wave 3+ — see `docs/research/execution-plan.md`)

- `dots-chunk-iteration`, `dots-versioning-1x`, `dots-anti-patterns`, `dots-debugging-flow` (QA-gated)

## Authoring rules (apply to every skill in this pack)

- Senior-level only. No tutorial content. No "Hello Cube".
- Entities 1.x APIs only. Deprecated 0.x APIs get a "DO NOT USE" callout, not a separate skill.
- Each skill: intent, use-when, avoid-when, senior pattern, anti-patterns, failure modes, runtime + static verification, performance notes, Entities version notes.
- Each skill must answer "what does a senior DOTS engineer know that a junior doesn't" — if it doesn't, it's rejected.

## Source attribution

Patterns extracted from (read 2026-05-26):
- `EntitiesSamples/Assets/ExampleCode/{Baking,Jobs,ComponentsSystems}.cs`
- `EntitiesSamples/Assets/Baking/BakingDependencies/`
- `Dots101/Entities101/Assets/HelloCube/{3.Prefabs, 6.EnableableComponents, 9.RandomSpawn, 13.StateChange}/`

Source is **learning material**, not truth. Each skill explicitly challenges sample shortcuts (e.g. the StateChange sample uses both modes for comparison — the skill says "the enableable path wins, ignore the others except as a benchmark").
