# Changelog

All notable changes to `unity-agent-team` are documented here.

For agent-facing recent changes, see `workspace/recent-changes.md`.

---

## 2026-05-26 — Panel-coordination protocol; Wave 2 rolled back

Enforces a strict anti-collapse rule on the DOTS skill program: 1 role =
1 Claude panel = 1 independent session. The coordinator routes work
through workspace inboxes/outboxes/gates and never writes final skills
or synthesizes implementation.

### Why
A prior Wave 2 attempt spawned 3 single-shot subagents for evidence,
specs, and QA — then synthesized their reports into 5 SKILL.md files in
the orchestrator session. That collapsed implementation back into the
coordinator, which the user explicitly forbade. The 5 drafts are
preserved as non-canonical reference material under `scratch/`.

### Added
- `workspace/dots-program/README.md` — full panel protocol: 4 roles,
  inbox/outbox/gate file substrate, wave lifecycle diagram, hard rules,
  tmux setup instructions.
- `workspace/dots-program/status.md` — at-a-glance state file the
  coordinator updates after each gate flip.
- `workspace/dots-program/inboxes/wave-2/{reverse-engineer,architect,qa-curator,skill-builder}.md`
  — per-panel work assignments for the Wave 2 redo. Each brief enforces
  what the panel may read, what it must write, what it must NOT touch,
  and the gate file it flips on completion.
- `workspace/dots-program/outboxes/{4 panel folders}/` — empty,
  panels write here.
- `workspace/dots-program/gates/` — empty; zero-byte marker files flip
  here as phases complete.

### Moved (rolled back)
- 5 orchestrator-synthesized Wave 2 SKILL.md drafts moved to
  `workspace/dots-program/scratch/wave-2-orchestrator-drafts/`. They
  are not on the routing table, not advertised in the unity-dots index,
  and explicitly non-canonical. Panels may consult them as format
  reference but must not adopt them as Wave 2 final output.

### Changed
- `.claude/skills/routing/SKILL.md` — Wave 2 keyword→skill rows removed
  (skills are not shipped yet; routing should not advertise them).
- `.claude/skills/unity-dots/SKILL.md` — Wave 2 section rewritten to
  "in flight — panel-owned", pointing at the workspace protocol.
- `docs/research/execution-plan.md` — Wave 2 entry rewritten as
  "ROLLED BACK"; documents the re-execution model and the preserved
  artifacts.

### Unchanged
- All Wave 1 skills (`dots-baking-patterns`, `dots-ecb-orchestration`,
  `dots-enableable-components`, `dots-entity-lifecycle`,
  `dots-spawning-patterns`) ship as-is. They were authored before the
  panel rule was enforced; not re-litigated.
- The `skill-creator` vendor and `unity-skills` routing layer remain.

### Next
- User opens 4 tmux panes; each pane reads its inbox brief and operates
  in its own Claude Code session. Coordinator (this role, or human)
  watches gates and pushes commits after `wave-2-skills-shipped`.

---

## 2026-05-26 — Unity-DOTS Skill Pack: Wave 1 Foundation

Ships the first 5 of ~14 planned senior-level DOTS skills, mined from
`Unity-Technologies/EntityComponentSystemSamples` (Entities 1.4.x).

### Added
- `.claude/skills/unity-dots/SKILL.md` — pack index (router-only, not a skill itself)
- `.claude/skills/unity-dots/dots-baking-patterns/SKILL.md`
  TransformUsageFlags, DependsOn dependency tracking, prefab refs via
  GetEntity, additional entities, banned 0.x APIs.
- `.claude/skills/unity-dots/dots-ecb-orchestration/SKILL.md`
  Phase selection across 6 ECB systems, ParallelWriter + ChunkIndexInQuery
  sort key, deterministic playback rules.
- `.claude/skills/unity-dots/dots-enableable-components/SKILL.md`
  Cost-model decision rule (frequency-based), EnabledRefRW, ECB
  SetComponentEnabled, IgnoreComponentEnabledState query option.
- `.claude/skills/unity-dots/dots-entity-lifecycle/SKILL.md`
  ECB-deferred destruction during query iteration, ICleanupComponentData
  two-phase teardown, Entity-as-(Index,Version) validity model.
- `.claude/skills/unity-dots/dots-spawning-patterns/SKILL.md`
  Batched EntityManager.Instantiate, ECB.Instantiate from parallel jobs,
  Random.CreateFromIndex determinism, Allocator.Temp lifecycle.

### Changed
- `.claude/skills/routing/SKILL.md` — new "Unity-DOTS Skill Pack" section
  with keyword → skill mapping and per-complexity load cap. Loaded on
  DOTS/Hybrid domains in addition to standard layer 1/2; not loaded on
  Unity-only or Ambiguous.
- `docs/research/execution-plan.md` — Wave 1 retrospective appended.

### Source attribution
All skills grounded in real reads of (no inferred content):
- `EntitiesSamples/Assets/ExampleCode/{Baking,Jobs}.cs`
- `EntitiesSamples/Assets/Baking/BakingDependencies/`
- `Dots101/Entities101/Assets/HelloCube/{3,6,13}/*System.cs`

### What's NOT in this release
- The `/skill-creator` eval/iterate loop (description-tuning, trigger-
  accuracy benchmarks). That workflow needs Anthropic API access not
  available to this Claude Code session. Skill *format* matches the
  workflow's expected output; *measurement* is a follow-up.

### Next
- Wave 2: dots-update-groups, dots-singleton-patterns,
  dots-transform-patterns, dots-hybrid-bridge, dots-event-driven-ecs

---

## 2026-05-26 — DOTS skill program: Phase 0 setup (Wave 0)

(see prior commits)

---

## 2026-05-26 — Vendored Unity-Skills routing layer (v1.9.2)

The `Besty0728/Unity-Skills` AI routing layer is now committed in-tree at
`.claude/skills/unity-skills/`. Previously the router referenced paths
that did not exist on disk and silently fell back to role briefs. Now
every `@.claude/skills/unity-skills/skills/<module>/SKILL.md` resolves.

### Added
- `.claude/skills/unity-skills/SKILL.md` — root AI definition (from
  `unity-skills~/SKILL.md`).
- `.claude/skills/unity-skills/skills/` — 69 module SKILL.md files (49
  functional REST + 20 advisory).
- `.claude/skills/unity-skills/references/` — upstream reference docs.
- `.claude/skills/unity-skills/VERSION` — version pin and source URL.
- `.claude/skills/unity-skills/UPSTREAM-LICENSE` — upstream MIT license.
- `.claude/scripts/unity_skills.py` — Python REST client for the Unity
  Editor server at `http://localhost:8090`.

### Changed
- `.claude/skills/routing/SKILL.md` — new **Status** and **Domain
  Gating** sections at the top make the DOTS / Unity / Hybrid /
  Ambiguous scoping explicit and binding before the keyword table is
  consulted.
- `unity-skills-audit.md` — version bumped 1.9.1 → 1.9.2; marked as
  VENDORED with vendoring date.

### Scoping rule (now enforced by router, was advisory before)

| Triage domain | unity-skills modules |
|---|---|
| DOTS | Skipped unless hybrid touchpoint demands it; MonoBehaviour-first modules forbidden |
| Unity | Primary source — keyword table selects, max 2 domain + 2 advisory |
| Hybrid | Both stacks loaded; bridge contract required in `workspace/design.md` |
| Ambiguous | None — escalate to architect |

### Migration / setup for consuming projects
- No agent-side changes required — routing now resolves locally.
- Unity Editor package still needs separate installation
  (`com.besty.unity-skills` via UPM) for REST calls to succeed at
  runtime. The agents will issue `unity_diagnose` first and degrade
  gracefully if the server is unreachable.

---

## 2026-05-26 — Tester verification contract

Adds the mandatory **Tester Runtime + Static Verification Contract**. Both
the lightweight `verifier` (tiny/small/medium) and the full `tester`
(large/critical) must satisfy it on every run. The contract is project-
agnostic and ships with the package — installing this kit into a new Unity
project applies the contract automatically the first time `/team` runs.

### Added
- `.claude/skills/qa-validation/verification-contract.md` — canonical
  contract. Sections 1–7 cover static verification (compile + architecture
  safety), runtime verification (PlayMode → EditMode → repro scene →
  checklist), DOTS-specific testing rules, the editor compile safety gate,
  required output format, schema mapping, and the "explicitly impossible"
  exemption clause.

### Changed
- `.claude/skills/qa-validation/SKILL.md` — front-matter callout pointing
  to the contract; both verification agents inherit it.
- `.claude/skills/tester/SKILL.md` — sign-off now requires both layers;
  contract added to the Reference list.
- `.claude/skills/verifier/SKILL.md` — procedure extended from 5 to 6
  steps (static layer first); BLOCKED on broken compilation; result
  artifact now includes `static_verification` and `runtime_verification`
  blocks.
- `.claude/schemas/verification_result.schema.json` — added optional
  `static_verification` and `runtime_verification` objects (backward
  compatible; required by the contract unless §7 exemption is recorded in
  `notes`).

### Migration
- Existing `verification_result.json` artifacts remain valid (new fields
  are optional in the schema).
- New runs that omit either layer without a recorded §7 reason should be
  rejected by the verification agent itself (`status="BLOCKED"`); the
  schema does not enforce this — the contract does.

---

## 2026-05-25 — v2: Adaptive Pipeline (breaking)

Full redesign. The fixed 4-agent template is removed in favor of an adaptive
pipeline driven by a triage agent and enforced by a Python orchestrator.

### Breaking
- `/team` flag set replaced. `--bug | --feature | --refactor | --fast | --full
  | --fast-fix | --teams` are gone. New form: `/team <intent> [depth] <task>`
  where `intent ∈ {bug, feature, refactor, explore}` and
  `depth ∈ {quick, normal, deep}`. See `MIGRATION.md` for the 1:1 mapping.
- Fixed 4-agent spawn is removed. Pipeline composition is now derived per
  task from `workspace/triage.json` by `orchestrate.py plan`.
- Markdown-only gates removed. Every phase boundary is now
  `python .claude/scripts/orchestrate.py gate <phase-id>` and exits non-zero
  to halt.
- `tester` is no longer always-on. New lightweight `verifier` agent runs the
  deterministic verification bundle from `impl_result.json` for tiny/small/
  medium. `tester` is spawned only for `large`/`critical` complexity, when
  confidence < 0.7, or when depth=deep.
- `/team bugfix` subcommand removed (subsumed by `/team bug`).
- `.claude/skills/start-unity-dots-team/` removed (no fixed team to start).
- Nested subagents removed: `code-generator`, `job-optimizer`,
  `burst-validator`, `memory-checker`, `design-analyzer`,
  `dependency-mapper`. Their guidance is now loaded as skill packs.

### Added
- `.claude/scripts/orchestrate.py` — runtime enforcer with subcommands
  `preflight | reset | validate | plan | gate | ownership-check | finalize`.
  Stdlib only. Exit codes are the contract.
- `.claude/scripts/triage.py` — helper that emits a schema-valid
  `workspace/triage.json`.
- `.claude/schemas/` — JSON-schemas for every artifact
  (`triage`, `root_cause`, `approved_plan`, `impl_result`,
  `verification_result`, `ownership`).
- `.claude/workspace-templates/*.json` — canonical empty artifacts.
- `.claude/agents/triage.md`, `.claude/agents/verifier.md` — new subagent_types.
- `.claude/skills/triage/SKILL.md`, `.claude/skills/verifier/SKILL.md` — new.
- `.claude/skills/burst-safety/SKILL.md`,
  `.claude/skills/ecs-job-patterns/SKILL.md`,
  `.claude/skills/memory-safety/SKILL.md`,
  `.claude/skills/ownership-partitioning/SKILL.md` — skill packs replacing
  the v1 nested subagents.
- `MIGRATION.md` — v1 → v2 migration guide.
- `workspace/ownership.lock.json` — partition lock enforced by
  `orchestrate.py ownership-check`.

### Changed
- `.claude/commands/team.md` — full rewrite as an adaptive, gated command.
- `SETUP.md` — rewritten around install + verify; no more boot ceremony.
- `README.md` — rewritten around the adaptive pipeline.
- `.claude/CLAUDE.md` — replaces "spawn 4 agents in parallel" rules with
  pipeline-derived agent composition; documents new gates and skill packs.

### Retained (unchanged)
- `.claude/rules/GRAPH_FIRST.md`, `mcp-phase-gates.md`,
  `ownership-boundaries.md`, `escalation-policy.md`,
  `dual-stack-domain-system.md`, `domain-scoring-engine.md`,
  `api-fingerprinting-system.md`, `architecture-pattern-detection.md`,
  `domain-aware-mcp.md`, `escalation-rules-domain.md`,
  `knowledge-*.md`, `recent-changes-system.md`, `relevance-filtering.md`,
  `skill-confidence-routing.md`, `cross-agent-skill-cache.md`,
  `skill-cache-freshness.md`, `change-trigger-policy.md`,
  `change-impact-system.md`, `documentation-retrieval.md`,
  `repo-learning-loop.md`, `agent-knowledge-policy.md`,
  `code-aware-routing-engine.md`, `dynamic-skill-reload.md`,
  `workspace-knowledge-layout.md`.
- `workspace/repo-knowledge.md`, `ecs-registry.md`, `recent-changes.md`
  (persistent knowledge files — schema unchanged).
- `.claude/skills/unity-dots-best-practices/SKILL.md`,
  `unity-foundation/SKILL.md`, `codebase-understanding/SKILL.md`,
  `editor-data-tools/SKILL.md`, `investigation/SKILL.md`,
  `qa-validation/SKILL.md`, `routing/SKILL.md`,
  per-role `architect/`, `unity-dev/`, `data-tool/`, `tester/`.

### Removed
- `.claude/commands/bugfix.md`
- `.claude/skills/start-unity-dots-team/`

---

## 2026-05-22

### Added
- Multi-layer knowledge system (recent-changes, decay, ownership, token budget, agent policy)
- `workspace/recent-changes.md` — rolling 14-day agent-facing architectural awareness layer
- Knowledge confidence decay (`knowledge-decay-system.md`) — facts decay without revalidation
- Section-tag retrieval for `repo-knowledge.md` — agents read relevant sections only
- Hash-based skill cache freshness (`skill-cache-freshness.md`) — SHA-256 invalidation
- Token budget governance (`knowledge-token-budget.md`) — 800-token hard cap per agent
- Change impact system — risk-category metadata on recent-changes entries
- Per-agent knowledge reading policy (`agent-knowledge-policy.md`)
- Dual-stack domain system — 3 domains (Runtime ECS, Unity View/Authoring, Hybrid Boundary)
- API fingerprinting (50+ DOTS/Unity/Hybrid APIs with confidence weights)
- Domain scoring engine with worked examples
- Dynamic skill reload on domain contradiction
- Domain-aware MCP strategy per domain
- Code-aware routing engine (8-step pipeline replaces keyword routing)
- Architecture pattern detection (9 patterns)

### Changed
- DOTS Conflict Resolution Policy → Domain-Aware Precedence Policy
- `STEP 1.5` now includes hash-based cache invalidation + recent-changes filtering
- `OWNERS.md` — `recent-changes.md` added as persistent team knowledge file
- `CLAUDE.md` — Knowledge System section added above Hardening Rules

### Fixed
- `architecture-agent`, `codebase-reader`, `feature-dev-agent` orphaned agents removed
- `system-mapper` and `code-tracer` cleanly replace deprecated agents

---

## 2026-05-21 (approximate)

### Added
- Full team UI setup (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"`) in SETUP.md Step 6a
- Unity-Skills v1.9.1 integration — layered skill loading (Layer 1–4)
- Skill confidence routing engine with symptom pattern library (8 patterns)
- Cross-agent skill cache (150-token summaries, 42–57% token reduction)
- MCP phase gates (Phase 1–4 permission matrices)
- Repository learning loop (5 triggers, quality gate, retention policy)
- Escalation policy (4 signal types, 4 categories, decision tree)
- Shared workspace (6 structured files replacing prompt embedding)
- Authority model (`[BLOCKED]`, `[REJECTED]`, `[ESCALATE]`, `[SCOPE_EXCEEDED]`)

### Changed
- `team.md` — `--bug`, `--feature`, `--refactor`, `--fast-fix` task mode flags
- Agent prompts — domain-appropriate reasoning injected per phase
- SETUP.md — workspace creation step, unity-skills install guide

### Fixed
- Refactor step-by-step deadlock prevention (BLOCKED signal + orchestrator intervention)
- Compilation gate added to `--bug` flow (verify clean before signaling tester)
- Baseline-FAIL requirement enforced for regression tests

---

## Earlier

See git log for changes prior to 2026-05-21.
