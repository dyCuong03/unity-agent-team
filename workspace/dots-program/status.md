# DOTS Program — Status

Last updated: 2026-05-26 (Wave 1 specs verified — QA up next)

## Wave taxonomy (user-issued)

The DOTS program runs as an 8-wave learning program. Each wave = one coherent ECS subsystem.

| Wave | Topic | Target skill candidates |
|---|---|---|
| 1 | **HelloCube + Basic ECS Lifecycle** | `ecs-fundamentals`, `dots-update-groups`, `singleton-patterns`, `entity-query-patterns` |
| 2 | Baking + Authoring + SubScene | `baking-patterns`*, `baker-design`, `authoring-patterns`, `bake-runtime-boundary` |
| 3 | ECB + Structural Changes | `ecb-patterns`*, `structural-change-safety`, `deferred-spawn`*, `deferred-destroy` |
| 4 | Jobs + Burst | `jobs-and-burst`, `scheduling-patterns`, `dependency-management`, `burst-safe-patterns` |
| 5 | Transforms + Physics | `transform-patterns`, `physics-patterns`, `movement-architecture` |
| 6 | Enableable + State Flow | `enableable-patterns`*, `state-machine-ecs`, `tag-patterns` |
| 7 | Hybrid Bridge | `hybrid-bridge`, `presentation-patterns`, `hybrid-boundaries` |
| 8 | Debugging + Failure Modes | `ecs-debugging`, `ecs-failure-patterns`, `ecs-anti-patterns` |

(*) Already-shipped Wave-1-legacy skills cover this area; panels declare cross-link or partial replacement during the wave.

## Already shipped (Wave 1-legacy, pre-panel-protocol)

Under `.claude/skills/unity-dots/`:
- `dots-baking-patterns` (covers Wave 2 partly)
- `dots-ecb-orchestration` (covers Wave 3 partly)
- `dots-enableable-components` (covers Wave 6 partly)
- `dots-entity-lifecycle` (covers Wave 1 / Wave 3 partly)
- `dots-spawning-patterns` (covers Wave 3 partly)

## Current wave

**Wave 1 — IN FLIGHT (panel-owned)**
- Phase: QA Curator (approvals pending; Panel 3 / dots-qa-skill-builder)
- Kickoff verified: `inboxes/wave-1/{reverse-engineer,architect,qa-curator,skill-builder}.md` present; `gates/wave-1-kickoff` touched.
- Evidence verified by Coordinator: `outboxes/reverse-engineer/wave-1-evidence.md` (24 KB / 178 lines, 4 target skills covered with HelloCube + ExampleCode/ComponentsSystems.cs citations); `gates/wave-1-evidence-ready` touched.
- Specs verified by Coordinator: `outboxes/architect/wave-1-specs.md` (43 KB / 360 lines, 4 skills DRAFT, confidence 0.88–0.92, no DEFER/ESCALATE_QA/REJECT_DUPLICATE); `gates/wave-1-specs-ready` touched 2026-05-26 11:10.
- Next gate: `wave-1-qa-approved` OR `wave-1-qa-rejected` (Panel 3 / QA Curator)

## Gate ledger (Wave 1)

| Gate | Flipped? | Owner |
|---|---|---|
| `wave-1-kickoff` | ✅ 2026-05-26 | Coordinator |
| `wave-1-evidence-ready` | ✅ 2026-05-26 | Panel 2 |
| `wave-1-specs-ready` | ✅ 2026-05-26 | Panel 1 |
| `wave-1-qa-approved` | ❌ | Panel 3 |
| `wave-1-qa-rejected` | n/a | Panel 3 |
| `wave-1-skills-shipped` | ❌ | Panel 4 |
| `wave-1-routing-integrated` | ❌ | Coordinator |
| `wave-1-complete` | ❌ | Coordinator |

## Notes for the team

- The deferred `inboxes/wave-2/` directory is **OLD TAXONOMY** — see `inboxes/wave-2/DEPRECATED.md`. Do not work it.
- Orchestrator-synthesized scratch drafts at `scratch/wave-2-orchestrator-drafts/` cover `dots-update-groups`, `dots-singleton-patterns`, and three others. They are explicitly NON-CANONICAL — panels may consult format only, must NOT adopt content.
