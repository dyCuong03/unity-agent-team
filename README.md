# Unity Agent Team

A production-grade, multi-agent Claude Code orchestration framework for Unity development — covering both Unity DOTS / ECS and traditional Unity (MonoBehaviour, UI, animation, addressables, networking). Agents investigate before implementing, classify your codebase domain before loading skills, and accumulate architectural knowledge over time.

**Not a toy.** Designed for 100k+ LOC Unity repositories, mixed ECS + MonoBehaviour codebases, production deadlines, and real debugging pressure.

---

## What it does

| Capability | Description |
|-----------|-------------|
| **Task-mode routing** | `--bug`, `--feature`, `--refactor`, `--fast-fix` — each with the right agents, right sequence, right gates |
| **Domain-aware routing** | Investigates your code first, classifies it as DOTS / Unity / Hybrid, then loads only relevant skills |
| **CRG-first investigation** | Uses `code-review-graph` before reading any files — no blind grepping |
| **Shared workspace** | Agents communicate through structured files, not prompt-embedding — token-efficient |
| **Knowledge system** | Stable facts + rolling recent changes + confidence decay — agents remember what matters |
| **Unity-Skills integration** | 714 REST skills (scene, UI, animation, shader, netcode, etc.) loaded lazily by domain |
| **MCP phase gates** | Phase 1 = read only / Phase 2 = limited write / Phase 3 = playmode+test / Phase 4 = step-gated refactor |
| **Authority model** | `[BLOCKED]`, `[REJECTED]`, `[ESCALATE_ARCHITECT]`, `[ESCALATE_HUMAN]` — hard stops with routing |
| **Learning loop** | Saves failure patterns, architecture decisions, regression anchors, performance findings |

---

## Install

```sh
# From your Unity project root:
git clone git@github.com:dyCuong03/unity-agent-team.git unity-agent-team-publish
claude unity-agent-team-publish/SETUP.md
```

Claude reads `SETUP.md` and runs the full installer: audits source, detects existing `.claude/`, asks before overwriting, copies everything, creates `workspace/`, verifies the install, checks MCP servers, and reports status.

### Enable full team UI (one pane per agent)

Add to your **user-level** `~/.claude/settings.json` — never commit this:

```json
{
  "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" },
  "preferences": { "tmuxSplitPanes": true }
}
```

Restart Claude Code. Then use `--teams` flag for visible parallel panes. Without `--teams`, agents run via the standard `Agent` tool — same results, no panes needed. See SETUP.md Step 6a for the per-platform install command.

---

## Required MCP Servers

| Server | Purpose | Required? |
|--------|---------|-----------|
| `ai-game-developer` | Unity Editor introspection and mutation | Strongly recommended |
| `agentmemory` | Cross-session memory | Strongly recommended |
| `code-review-graph` | Code graph for CRG investigation | Strongly recommended |

Agents state a single fallback line ("Running without MCP evidence") and continue if any is unavailable.

---

## Commands

### `/team <task> [mode] [--teams]`

The primary entrypoint. Pass a task mode flag to select the right agent composition and sequencing.

```sh
# Bug fix — investigation-first
/team Enemies stop chasing after teleport --bug

# New feature — architecture-first
/team Add stamina system with regeneration --feature

# Add feature + editor tooling
/team Add expedition reward screen --feature --with-tooling

# Refactor — blast-radius-first
/team Replace MonoBehaviour health with ECS component --refactor

# 1-3 line obvious fix (scope-limited)
/team Fix off-by-one in damage calculation --fast-fix

# General / unknown
/team Add stamina regeneration with cooldowns --full

# With full team UI (requires env var)
/team Add combat system --feature --teams
```

### `/bugfix <description>`

Alias for `/team --bug`. Identical flow.

```sh
/bugfix Health bar shows wrong value when two sources apply same frame
```

---

## Agents

### Core Engineering Agents (4)

| Agent | Role | Gate |
|-------|------|------|
| `architect` | Designs ECS architecture — components, system boundaries, update order, baker plan, acceptance criteria | No code starts before design is APPROVED |
| `unity-dev` | Implements from approved design — systems, jobs, bakers, runtime logic | ECS Safety Checklist + clean compile before signaling tester |
| `data-tool` | Editor tooling, validators, inspectors, diagnostics | Must not silently change runtime behavior |
| `tester` | Validates correctness, scale, regression, determinism | No sign-off without baseline-FAIL + post-fix-PASS evidence |

### Investigation Agents (4)

All use `code-review-graph` before reading any files. Max 8 files per investigation, each justified by graph evidence.

| Agent | Role | Primary CRG call |
|-------|------|-----------------|
| `system-mapper` | Maps existing ECS systems, boundaries, extension points — feeds the architect | `get_architecture_overview` |
| `code-tracer` | Traces how a feature works + where new code attaches — feeds unity-dev | `get_minimal_context` → `identify_extension_points` |
| `bug-investigation` | Traces symptom → root cause with API fingerprinting + domain classification | `trace_execution_flow` → `get_impact_radius` |
| `refactor-agent` | Maps full blast radius before any changes — feeds architect's approval | `get_impact_radius` → `trace_dependencies` |

---

## Task Mode Flows

### `--bug` (Bug fix)

```
Phase 1  sequential — WAIT
  bug-investigation
  ├─ agentmemory search (prior investigations of same symptom)
  ├─ CRG: trace_execution_flow → get_impact_radius
  ├─ API fingerprinting → domain classification → writes workspace/domain-analysis.md
  └─ writes workspace/investigation.md (root cause + fix strategy + regression guidance)

Phase 2  parallel — single message
  unity-dev                            tester
  reads investigation.md               runs regression test NOW (pre-fix state)
  completes ECS Safety Checklist        records Baseline: FAIL (required)
  verifies clean compile               waits for "Fix applied. Compilation: CLEAN"
  signals tester                    →  runs test again → writes test-plan.md

Phase 3  sequential — WAIT
  tester verifies: Baseline:FAIL + Post-fix:PASS both required
  PASS → sign off | FAIL → loop Phase 2 | 3rd FAIL → [ESCALATE_HUMAN]
```

### `--feature` (New feature)

```
Phase 1  sequential — WAIT
  system-mapper
  ├─ reads workspace/repo-knowledge.md + ecs-registry.md
  ├─ CRG: get_architecture_overview → trace_execution_flow → identify_extension_points
  ├─ API fingerprinting + pattern detection → domain classification
  └─ writes workspace/domain-analysis.md + updates workspace/repo-knowledge.md

Phase 2  sequential — WAIT
  architect
  ├─ reads domain-analysis.md (design from the map, not from guessed state)
  ├─ checks ecs-registry.md (no duplicate components)
  └─ writes workspace/design.md (STATUS: APPROVED or REJECTED)
     If REJECTED → stop

Phase 3  parallel — single message (domain skills loaded from routing result)
  unity-dev                  tester              data-tool (--with-tooling only)
  reads design.md            derives test        reads design.md
  spawns code-tracer         matrix from         spawns code-tracer
  implements from design     acceptance          anchors tools in
  ECS Safety Checklist       criteria            real components
  updates ecs-registry.md    → test-plan.md
```

### `--refactor` (Refactor / restructure)

```
Phase 1  sequential — WAIT
  refactor-agent
  ├─ CRG: get_impact_radius → trace_dependencies → identify_shared_symbols
  └─ writes workspace/migration-plan.md (steps + rollback strategy)
     if blast radius > 10 files → [ESCALATE]

Phase 2  sequential — WAIT
  architect
  ├─ reviews migration-plan.md
  └─ writes APPROVED or REJECTED with modifications

Phase 3  parallel + step gates
  unity-dev                              tester
  executes step N                        verifies step N
  writes "Step N complete" to plan   →   writes "Step N OK" or "Step N FAIL/BLOCKED"
  waits for OK before next step      ←   (max 3 BLOCKED → [ESCALATE_HUMAN])
  rolls back + [ESCALATE] if FAIL
```

### `--fast-fix` (1-3 line fix, no investigation)

```
unity-dev + tester in parallel
unity-dev: if > 20 lines or > 2 files → [SCOPE_EXCEEDED] → re-run as --bug
tester: verifies fix + adjacent regression check
```

### General (no flag)

All 4 core agents spawn in parallel. Each delegates to investigation agents before starting work. Self-correct when upstream data arrives.

---

## Domain-Aware Routing

The system classifies your code into one of three domains **before** loading any skills. Domain is determined by API evidence from touched files — not task keywords.

### Three Domains

| Domain | Trigger | DOTS reasoning | Unity reasoning |
|--------|---------|----------------|-----------------|
| **Runtime ECS** | `DOTS_score ≥ 0.70`, gap ≥ 0.20 | Dominant | Secondary |
| **Unity View / Authoring** | `Unity_score ≥ 0.70`, gap ≥ 0.20 | Secondary | Dominant |
| **Hybrid Boundary** | `Hybrid_score ≥ 0.60`, abs gap < 0.30 | Equal — explicit contract required | Equal |
| **Ambiguous** | None qualify | → `[ESCALATE_ARCHITECT: domain ambiguous]` | |

### API Fingerprinting

Investigation agents scan touched files (max 8) and score APIs:

**DOTS APIs (examples):** `ISystem` (0.20), `IJobEntity` (0.20), `[BurstCompile]` (0.20), `NativeArray<T>` (0.20), `SystemAPI` (0.20), `ComponentLookup<T>` (0.12), `LocalTransform` (0.20) ...

**Unity APIs (examples):** `MonoBehaviour` (0.20), `Canvas` (0.20), `Animator` (0.20), `DOTween` (0.20), `AsyncOperationHandle<T>` (0.20), `PlayableDirector` (0.20) ...

**Hybrid APIs (examples):** `Baker<T>` (0.25), `GetEntity()` (0.25), `CompanionComponent` (0.15) ...

Scores are normalized, thresholds applied, domain classified. Results written to `workspace/domain-analysis.md`.

### Ownership Boundaries

| State | Owner | Other stack role |
|-------|-------|-----------------|
| Entity health, movement, AI state, combat, cooldowns | **DOTS** (IComponentData) | Unity may read for display |
| Animation, timeline, audio, popups, VFX, HUD | **Unity** (MonoBehaviour) | DOTS may signal |
| ECS → view bindings, baker inputs | **Hybrid** — explicit contract | Both, one-way DOTS → Unity |

---

## Skill Loading

Skills load in 4 layers. Only Layer 3 varies per task.

| Layer | Content | Loaded when |
|-------|---------|-------------|
| **Layer 1 — ECS Core** | `unity-dots-best-practices/SKILL.md` | Always, every agent |
| **Layer 2 — Foundation** | `unity-foundation/SKILL.md` | Always, architect/unity-dev/data-tool |
| **Layer 3 — Domain** | Unity-Skills REST modules (`ui`, `animator`, `netcode`, `addressables-design`, etc.) | Lazy — confidence score ≥ 0.70, max 2 domain + 2 advisory |
| **Layer 4 — Investigation** | `investigation/SKILL.md` | Always for investigation agents |

**Confidence scoring** (replaces keyword-only routing):

```
score = 0.35 × keyword_match
      + 0.30 × symptom_pattern     ← 8 seeded patterns (stuck/leak/UI/animation/etc.)
      + 0.20 × repo_history        ← from workspace/repo-knowledge.md Session History
      + 0.10 × ECS_penalty         ← MonoBehaviour-first modules penalized in DOTS domain
      + 0.05 × issue_type          ← --bug adds debug/console bonus
```

**Token budget:** 800 tokens per agent (P1 core 200 + P2 foundation 100 + P3 facts 150 + P4 recent changes 75 + P5 domain 150–400 + P6 investigation 100).

**Skill cache:** First agent that loads a module writes a 150-token summary to `workspace/skill-cache/<module>.cache.md`. Subsequent agents read the summary (42–57% token reduction). SHA-256 hash in cache header — auto-invalidated when source SKILL.md changes.

---

## Unity-Skills Integration (optional)

**Unity-Skills** (`com.besty.unity-skills` v1.9.1) is an HTTP server running inside Unity Editor at `localhost:8090` with 714 REST skills across 49 modules.

Install in Unity Package Manager:
```
https://github.com/Besty0728/Unity-Skills.git?path=/SkillsForUnity
```

Agents call skills only in the right phase (MCP phase gates), at the right permission level (Approval/Auto/Bypass), for the right domain. **`workflow` and `smart` modules are blocked** — they conflict with agent orchestration.

Domain-specific MCP strategy:
- **DOTS domain:** `unity_diagnose` → `profiler_get_stats` → `script_dependency_graph` (skip `ui_find_all`, `animator_get_info`)
- **Unity domain:** `unity_diagnose` → `scene_analyze` → `validate_find_missing_scripts` (skip entity profiling)
- **Hybrid domain:** both stacks queried; bridge traced via `script_find_in_file` + `ComponentLookup` pattern

---

## Knowledge System

Three-layer persistent knowledge. Each layer has strict ownership — no duplication.

```
CHANGELOG.md              ← humans only, permanent, unbounded prose
        ↕ (no overlap)
workspace/recent-changes.md  ← agents, rolling 14 days, ≤300 tokens, compressed entries
        ↕ (no overlap)
workspace/repo-knowledge.md  ← agents, stable facts, section-tag retrieval, confidence decay
```

### workspace/recent-changes.md

Rolling 14-day record of architectural mutations. Agents read filtered entries (≤5, ~75 tokens) — never the full CHANGELOG.

```
[2026-05-22] domain:routing impact:medium affects:all
change: hybrid domain threshold changed 0.65 → 0.50
risk: more tasks classified Hybrid — extra skill slots used
```

Writes triggered by: routing threshold changes, ownership boundary changes, MCP gate changes, ECS architecture changes, agent additions/removals, new conventions discovered. **Not** triggered by: typos, formatting, README prose, adding examples without changing rules.

### workspace/repo-knowledge.md

Stable architecture facts with confidence decay.

```markdown
## [tag:ecs-health,combat] Health Component Ownership
HealthComponent is owned by DamageSystem. Writers: DamageSystem, HealingSystem.
Readers: UIHealthBarSystem (read-only), StatSystem (read-only).

<!-- confidence:0.91 verified:2026-05-22 source:architect-run -->
```

Confidence decays by fact type (0.01–0.05 per week). Below 0.40 → `[STALE]` — agents skip it. Revalidation resets confidence to 1.00.

### Workspace File Registry

| File | Owner | Persists | Purpose |
|------|-------|---------|---------|
| `repo-knowledge.md` | architect | Yes | Stable architecture facts |
| `ecs-registry.md` | architect | Yes | ECS component/system ownership map |
| `recent-changes.md` | orchestrator | Yes (14-day) | Recent architectural mutations |
| `domain-analysis.md` | investigation agents | Session | Domain scores, API evidence, routing decision |
| `design.md` | architect | Session | Feature design for current run |
| `investigation.md` | bug-investigation | Session | Root cause + fix strategy |
| `test-plan.md` | tester | Session | Test matrix + baseline/post-fix results |
| `migration-plan.md` | refactor-agent → architect | Session | Step-by-step migration + rollback |
| `escalation-log.md` | orchestrator | Conditional | Escalation history (retained if BLOCK unresolved) |
| `skill-cache/<m>.cache.md` | orchestrator | Session (hash-invalidated) | 150-token skill summaries |

---

## MCP Phase Gates

| Phase | Agents | Allowed | Blocked |
|-------|--------|---------|---------|
| **Phase 1** Investigation | investigation agents | All read-only calls | Any write |
| **Phase 2** Implementation | unity-dev, data-tool | Scripts, scoped prefabs, authoring | Mass scene mutation, scene_save, editor_play |
| **Phase 3** Validation | tester | tests_run, editor_play, profiler (playmode) | Code changes, prefab_apply |
| **Phase 4** Refactor | unity-dev + tester | Phase 2 writes, per-step only | Scope expansion, skipping steps |

---

## Authority Model

| Signal | Blocking | Effect |
|--------|---------|--------|
| `[BLOCKED: reason]` | Yes | Halt phase — route to responsible agent |
| `[REJECTED: reason]` | Yes | Design or plan rejected — return to previous phase |
| `[ESCALATE_ARCHITECT: reason]` | Yes | Architect must respond before phase resumes |
| `[ESCALATE_HUMAN: reason]` | Yes | Human engineer required |
| `[AUTO_ESCALATE: reason]` | No | Appends to open risks, continues |
| `[SCOPE_EXCEEDED]` | Yes | --fast-fix exceeded limit → re-run as --bug |
| `[STALE: reason]` | No | repo-knowledge fact below confidence threshold |

### Mandatory escalation triggers

- Change touches > 3 ECS systems without architect approval
- `[BurstCompile]` removed from hot-path ISystem
- Synchronization point added to previously async system
- `> 500 lines` changed across files
- Bug fix fails 3+ times (same symptom)
- CRG blast radius unknown
- Domain ambiguity score > 0.40

---

## Quality Gates

| Gate | Rule | Enforcer |
|------|------|---------|
| G1 | Root cause proven by graph evidence before fix starts | bug-investigation |
| G2 | Regression test must fail pre-fix, pass post-fix | tester |
| G3 | Clean compilation verified before signaling tester | unity-dev |
| G4 | ECS Safety Checklist before any code signal | unity-dev |
| G5 | No implementation before system-mapper maps existing code | system-mapper |
| G6 | No implementation before architect approves design | architect |
| G7 | Blast radius documented before any refactor change | refactor-agent |
| G8 | Architect approves migration plan before execution | architect |
| G9 | Behavior verified step-by-step during refactor | tester |
| G10 | No sign-off without correctness + stress evidence | tester |

---

## ECS Safety Checklist

unity-dev completes this before signaling tester on any change:

- [ ] No structural changes (`AddComponent`/`RemoveComponent`) inside scheduled jobs — use ECB
- [ ] System update order (`[UpdateBefore/After]`) not changed without architect approval
- [ ] `[BurstCompile]` not removed from hot-path ISystem
- [ ] No managed allocations in `ISystem.OnUpdate` (no `new List<>`, no LINQ, no string formatting)
- [ ] ECB playback timing unchanged — if moved, flag to architect
- [ ] No unintended archetype changes in hot loops

---

## Bundled Scripts

| Script | Purpose |
|--------|---------|
| `preflight.py` | Checks agent-team-mode, tmux, MCP servers. Never blocks. |
| `dots_scan.py` | Fast DOTS anti-pattern scan over C# files. |
| `validate_skill_pack.py` | Validates frontmatter on every SKILL.md and agent file. |

```sh
python .claude/scripts/preflight.py
python .claude/scripts/dots_scan.py Assets/
python .claude/scripts/validate_skill_pack.py
```

---

## File Structure

```
.claude/
├── agents/
│   ├── architect.md            # ECS architecture designer
│   ├── unity-dev.md            # ECS implementer
│   ├── data-tool.md            # Editor tooling / diagnostics
│   ├── tester.md               # QA / validation
│   ├── system-mapper.md        # Maps existing ECS systems (CRG)
│   ├── code-tracer.md          # Traces feature execution + extension points (CRG)
│   ├── bug-investigation.md    # Root cause tracing (CRG + API fingerprinting)
│   └── refactor-agent.md       # Blast radius analysis (CRG)
├── commands/
│   ├── team.md                 # /team slash command (all modes)
│   └── bugfix.md               # /bugfix alias
├── rules/
│   ├── GRAPH_FIRST.md                  # CRG-first investigation policy
│   ├── dual-stack-domain-system.md     # 3-domain precedence model
│   ├── api-fingerprinting-system.md    # DOTS/Unity/Hybrid API weights
│   ├── domain-scoring-engine.md        # Confidence scoring formula
│   ├── architecture-pattern-detection.md  # 9 design pattern detectors
│   ├── code-aware-routing-engine.md    # 8-step routing pipeline
│   ├── dynamic-skill-reload.md         # Mid-investigation domain reclassification
│   ├── ownership-boundaries.md         # State ownership contracts
│   ├── domain-aware-mcp.md             # Per-domain MCP call sequences
│   ├── escalation-rules-domain.md      # Domain-specific escalation triggers
│   ├── skill-confidence-routing.md     # Confidence scoring algorithm
│   ├── cross-agent-skill-cache.md      # 150-token summaries, 42-57% savings
│   ├── mcp-phase-gates.md              # Phase 1-4 permission matrices
│   ├── repo-learning-loop.md           # 5 learning triggers + quality gate
│   ├── escalation-policy.md            # 4 signal types, 4 categories
│   ├── recent-changes-system.md        # Rolling 14-day agent change tracking
│   ├── change-trigger-policy.md        # When to write recent-changes entries
│   ├── relevance-filtering.md          # Scored filtering of recent-changes
│   ├── knowledge-decay-system.md       # Confidence decay + STALE markers
│   ├── knowledge-ownership-model.md    # Single source of truth per fact type
│   ├── skill-cache-freshness.md        # SHA-256 hash-based cache invalidation
│   ├── documentation-retrieval.md      # Section-tag retrieval from repo-knowledge
│   ├── knowledge-token-budget.md       # 800-token hard cap, P1-P6 priority
│   ├── change-impact-system.md         # Impact metadata + agent notification routing
│   ├── workspace-knowledge-layout.md   # Complete workspace registry
│   └── agent-knowledge-policy.md       # Per-agent read/write obligations
├── skills/
│   ├── unity-dots-best-practices/SKILL.md   # Layer 1 — always loaded
│   ├── unity-foundation/SKILL.md            # Layer 2 — always loaded
│   ├── investigation/SKILL.md               # Layer 4 — investigation agents
│   ├── routing/SKILL.md                     # Lazy loading router
│   ├── codebase-understanding/SKILL.md      # CRG navigation
│   ├── architect/SKILL.md                   # Role brief
│   ├── unity-dev/SKILL.md                   # Role brief (with ECS Safety Checklist)
│   ├── data-tool/SKILL.md                   # Role brief
│   └── tester/SKILL.md                      # Role brief
├── workspace-templates/                     # Templates copied at session start
│   ├── OWNERS.md                            # File ownership registry
│   ├── domain-analysis.md
│   ├── investigation.md
│   ├── design.md
│   ├── test-plan.md
│   ├── migration-plan.md
│   ├── escalation-log.md
│   └── recent-changes.md                    # Bootstrap template
├── docs/
│   ├── architecture.md
│   ├── mcp-integration.md
│   └── setup.md
├── scripts/
│   ├── preflight.py
│   ├── dots_scan.py
│   └── validate_skill_pack.py
└── CLAUDE.md                                # Always-loaded project context

workspace/                                   # Created by SETUP.md at install
├── repo-knowledge.md        # COMMIT — stable architecture facts (with decay)
├── ecs-registry.md          # COMMIT — ECS component/system ownership
├── recent-changes.md        # COMMIT — rolling 14-day architectural mutations
├── domain-analysis.md       # session-scoped
├── design.md                # session-scoped
├── investigation.md         # session-scoped
├── test-plan.md             # session-scoped
├── migration-plan.md        # session-scoped
├── escalation-log.md        # session-scoped (retained if BLOCK unresolved)
└── skill-cache/             # session-scoped (hash-invalidated)
```

---

## Requirements

- **Claude Code** with `Agent` tool (no config needed for standard mode)
- **Unity 2022.3+** with DOTS packages (Entities, Jobs, Burst) for ECS features
- **`ai-game-developer` MCP** — strongly recommended (Unity Editor introspection)
- **`agentmemory` MCP** — strongly recommended (cross-session memory)
- **`code-review-graph`** — strongly recommended (CRG investigation)
- **Python 3.8+** — for bundled scripts only
- **`unity-skills` package** — optional but recommended (714 REST skills for scene/UI/anim/etc.)
- **tmux** — optional, only for `--teams` pane mode

---

## Customizing

```sh
# Extend a role's skill set
edit .claude/skills/<role>/SKILL.md

# Add a domain skill mapping
edit .claude/rules/routing/SKILL.md

# Adjust escalation thresholds
edit .claude/rules/escalation-policy.md

# Add a known failure pattern
edit workspace/repo-knowledge.md  # append a Failure Pattern entry

# Tighten or relax MCP phase permissions
edit .claude/rules/mcp-phase-gates.md
```

---

## Design Principles

1. **Investigation before implementation.** CRG runs first. No guessing from filenames.
2. **Code evidence drives decisions.** Domain classification from API fingerprints, not keywords.
3. **Right stack for right code.** DOTS leads ECS. Unity leads view/authoring. Explicit contract for hybrid.
4. **Architecture before code.** Design approval gates implementation. Root cause gates bug fix.
5. **Workspace over prompt embedding.** Agents write structured files. Others read sections they need.
6. **Knowledge decays.** Facts age. Stale facts are flagged, not silently applied.
7. **Token budget enforced.** 800 tokens per agent. Lowest priority dropped first.
8. **Deterministic orchestration.** DAG execution. No autonomous swarms. No peer mesh.

---

## License

MIT — see LICENSE.
