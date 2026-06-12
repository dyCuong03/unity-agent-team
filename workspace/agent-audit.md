# Agent System Audit — 2026-06-12

Context: post-portability migration (roots.py, project-config.json + setup.py,
migrate.py, validate_portability.py, 22 portability tests / 516 total passing).

## Verdict

DEGRADED — all three validators PASS and no project-specific leakage remains,
but the triage spawn double-loads four files (~24 KB redundant per run) and
team.md's "roots.py errors → run setup" contract can never fire because
roots.py exits 0 with silent defaults whose `coder`/`backend-dev`/`web-dev`
team profiles reference agents that do not exist.

## Findings (sorted by severity)

| # | Severity | Area | Finding | Evidence | Suggested fix | Fix owner |
|---|----------|------|---------|----------|---------------|-----------|
| 1 | HIGH | Commands × Agents (duplicate load path) | Triage spawn `@`-imports `skills/triage/SKILL.md`, `rules/GRAPH_FIRST.md`, `rules/api-fingerprinting-system.md`, `rules/domain-scoring-engine.md` — and `agents/triage.md` `@`-imports the same four files again. Every triage run loads ~24.4 KB twice. | `commands/team.md:180` vs `agents/triage.md:26-31`; bytes: 6937+4286+7170+5981 | Remove the four `@`-imports from one side (keep them in the agent definition; spawn prompt passes only task args) | framework maintainer |
| 2 | HIGH | Portability contract (team.md vs roots.py) | `team.md:42-43` says "If roots.py errors (missing or invalid project-config.json), STOP and run setup.py" — but roots.py exits 0 on missing config and silently emits fallback defaults (observed in this repo: `configPath: null`, `projectType: generic`). The STOP path is unreachable; `/team` proceeds un-setup. | `roots.py --json` output in repo with no `.claude/project-config.json`; `commands/team.md:42-43` | Either roots.py exits non-zero (or emits `"setupRequired": true`) when config absent, or team.md checks `configPath == null` and halts | framework maintainer |
| 3 | HIGH | Agents (broken role references) | Fallback/non-Unity team profiles name roles with no agent definition: `coder` (roots.py:188-189,346; setup.py:84-89), `backend-dev` (setup.py:73,81), `web-dev` (setup.py:77). `.claude/agents/` contains no coder.md / backend-dev.md / web-dev.md — `/team --team` on those project types spawns nonexistent agent types. | `ls .claude/agents/` (13 files, none of those names); `setup.py:68-89`; `roots.py:346` | Ship generic agent definitions for those roles, or map them to existing agents (`coder`→`unity-dev`-style generic dev), or restrict profiles to roles that exist | framework maintainer |
| 4 | MEDIUM | Commands (token cost) | `commands/team.md` is 38.8 KB (38,698 B) loaded whole on every `/team` invocation — far above the 5 KB shared-file guideline. Roughly half is the `--team`/`--worktrees` sections unused in the default adaptive path. | `wc -c commands/team.md` = 39,698 | Split `--team` and `--worktrees` flows into referenced docs read only when those flags are used | framework maintainer |
| 5 | MEDIUM | Agents (potential duplicate load path) | `agents/verifier.md:27-28` `@`-imports `skills/verifier/SKILL.md` (5.7 KB) + `rules/mcp-phase-gates.md` (11.1 KB) while the phase template (`team.md:266`) also appends `@.claude/skills/<m>/SKILL.md` per `skills_by_agent[verifier]` — if the router assigns the `verifier` module, the SKILL loads twice. Same pattern risk for architect/tester/data-tool/qa-tester `Reference:` lines. | `agents/verifier.md:27-28`; `commands/team.md:248,266` | Make route_skills.py exclude modules already `@`-imported by the agent definition, or strip `@` from agent-file references | framework maintainer |
| 6 | MEDIUM | Session evidence (stale artifact) | `workspace/verification_result.json` is the unmodified template (`status: BLOCKED`, `fail_reason: "Template — replace after verification"`, `risk_level: HIGH`) left over from setup smoke-testing, alongside an explore-run `triage.json`/`pipeline.json`. A run that gates on a pre-existing verification artifact without reset would read a phantom BLOCKED. | `workspace/verification_result.json` (238 B); `workspace/setup-smoke-test.md` | Have setup.py seed templates only under `.claude/workspace-templates/`, not live `workspace/`; add reset to STEP 1.5 | framework maintainer |
| 7 | LOW | Artifacts (internal inconsistency) | Smoke `triage.json` has `intent: explore` yet `recommended_pipeline: [architect, unity-dev, verifier]`; pipeline.json correctly emptied it (`explore intent — triage-only`). triage.py recommends a pipeline the planner must discard — harmless but confusing in artifacts. | `workspace/triage.json` vs `workspace/pipeline.json` | triage.py should emit `recommended_pipeline: []` for explore | framework maintainer |
| 8 | LOW | Skills (documented collisions) | `skills.py validate` PASS with 5 collision warnings / 5 internal_only (e.g. data-tool vs editor-data-tools on `inspector`). Resolutions are printed and a recent-changes entry (2026-06-11) records the reclassification — documented, not silent. | validator counters below; `workspace/recent-changes.md` entry 2026-06-11; `workspace/collision-disambiguation-draft.md` | None required; promote draft disambiguation doc to final | none (informational) |
| 9 | LOW | Devlogs | `devlogPaths` configured to `.claude/devlogs` but directory absent (`devlogPathsExisting: []`). Per audit charter: no devlogs configured — not a finding, noted for completeness. | `roots.py --json` | n/a | n/a |

No project-name leakage found: grep for the previous host project's identifiers
across agents/, commands/, rules/, docs/, CLAUDE.md returned zero hits. All
`.claude/...` paths referenced by agents and team.md exist (only `settings.json`
matches were user-level `~/.claude/settings.json` — tolerated). Test suite:
516 passed.

## Token Cost Snapshot

| Role | Files loaded at spawn | Bytes | Notes |
|------|----------------------|-------|-------|
| triage | triage.md + 4 `@`-imports, then team.md re-imports same 4 | 3,285 + 24,374 (+24,374 duplicated) | Finding #1 — worst offender |
| verifier | verifier.md + verifier SKILL + mcp-phase-gates | 2,926 + 5,677 + 11,149 | mcp-phase-gates (11.1 KB) loaded whole for a Phase-3-only role |
| unity-dots-dev | unity-dots-dev.md + routed skills | 5,397 + variable | largest agent file; within budget |
| unity-dev | unity-dev.md + routed skills | 4,197 + variable | OK |
| all (via /team) | commands/team.md | 39,698 | Finding #4 |
| all (project ctx) | .claude/CLAUDE.md | 13,256 | auto-loaded; acceptable for orchestrator context |

## Validation Counters

```
skills.py validate:
  collision_warnings 5 | duplicate_candidates 0 | gated 0 | internal_only 5
  merged 0 | newly_created 0 | orphans 0 | removed 0 | routable 19
  total_skills 23 | unreachable 0 | unresolved_duplicates 0
  RESULT: PASS (with 5 warnings)

skills.py unused:
  orphans 0 | unreachable 0 | duplicate-cands 0 — PASS

validate_portability.py:
  portability: PASS (0 finding(s)) root=/mnt/e/BuzzleStudio/BackpackAdventures/unity-agent-team

pytest tests/: 516 passed
```

## Deltas Since Last Audit

First audit in this format (no previous `workspace/agent-audit.md`). The
2026-06-05 flow audit (`workspace/audit/SYNTHESIS.md`) flagged "two competing
team.md implementations (V1 in host repo vs V2 in this package)" — the host
repo's `.claude` is outside CLAUDE_ROOT and was not rescanned (hard rule), so
that item is carried as UNRESOLVED (since 2026-06-05) pending host-side cleanup.
