# DOTS Program — Status

Last updated: 2026-05-26

Current wave: **2 (panel-redo)**
Current phase: **Awaiting panel kickoff** — coordinator has written inboxes; no gate flipped yet.
Blockers: none.
Next expected event: human opens 4 tmux panes, each pane reads its inbox.

## Waves

- **Wave 0** — SHIPPED (Phase 0 setup, skill-creator vendored, ECS samples verified, research docs)
- **Wave 1** — SHIPPED (5 skills under `.claude/skills/unity-dots/dots-{baking-patterns,ecb-orchestration,enableable-components,entity-lifecycle,spawning-patterns}/`). Authored pre-panel-protocol; not re-litigated.
- **Wave 2** — IN FLIGHT, panel-redo
  - Target skills: `dots-update-groups`, `dots-singleton-patterns`, `dots-transform-patterns`, `dots-hybrid-bridge`, `dots-event-driven-ecs`
  - Prior-session synthesis preserved under `scratch/wave-2-orchestrator-drafts/` (reference only — must NOT be shipped without panel re-authoring)
  - Prior-session subagent reports preserved under `inboxes/wave-2/prior-session-reports/` (starting material for Panels 1/2/3 to audit/extend, not adopt verbatim)
- **Wave 3** — BLOCKED on Wave 2

## Gate ledger (Wave 2)

| Gate | Flipped? | By |
|---|---|---|
| `wave-2-kickoff` | ❌ pending — coordinator must touch after final review | Coordinator |
| `wave-2-evidence-ready` | ❌ | Panel 2 (Reverse Engineer) |
| `wave-2-specs-ready` | ❌ | Panel 1 (Architect) |
| `wave-2-qa-approved` | ❌ | Panel 3 (QA Curator) |
| `wave-2-qa-rejected` | n/a | Panel 3 (rejection path) |
| `wave-2-skills-shipped` | ❌ | Panel 4 (Skill Builder) |
