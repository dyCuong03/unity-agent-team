# Unity DOTS Agent Team

This package runs an **adaptive Unity DOTS agent pipeline** in Claude Code.
There is no fixed team. Triage classifies the task; the orchestrator
(`.claude/scripts/orchestrate.py`) derives the minimum viable agent
composition; every phase boundary is a Python gate that exits non-zero on
violation. Markdown promises are not enforcement.

## Philosophy

- **Adaptive over fixed.** Most tasks need 1–2 agents. Spawn the agents
  the work actually requires; never the full team by default.
- **Artifacts over chat.** Every phase emits a schema-validated JSON
  (`triage.json`, `root_cause.json`, `approved_plan.json`,
  `impl_result.json`, `verification_result.json`,
  `ownership.lock.json`). The orchestrator verifies these before the
  next phase starts.
- **Certainty before parallelism.** Parallel execution is allowed only when
  triage reports `confidence_score ≥ 0.8`, complexity ≥ medium, and the
  architect partitioned ownership across ≥ 2 agents. Otherwise: sequential.
- **Skill packs over nested subagents.** Burst safety, ECS job patterns,
  memory safety, ownership partitioning — all loaded as text into the
  relevant agent. No `code-generator`, `burst-validator`, `memory-checker`
  spawning.
- **MCP and memory are pulled when needed.** Not as boot ceremony.

## Required MCP Servers

| Server | Purpose |
|---|---|
| `code-review-graph` | Mandatory for triage + investigators. Without it, agents fall back to targeted Grep and reduce confidence by 0.2. |
| `ai-game-developer` | Unity Editor introspection and mutation (script edits, scene/prefab inspection, tests). |
| `agentmemory` | Optional. Used by investigators to recall prior sessions. |

If a server is unavailable, agents state the fallback once and keep working.
See `@.claude/docs/mcp-integration.md`.

For `agentmemory` install + `.mcp.json` setup, see **SETUP.md → "Using agentmemory
with /team"**. Memory is optional; agents fall back to targeted search when absent.
Memory is **not** the source of truth — current repo files always win.

## Optional: tmux pane-per-agent UI

The default uses the standard `Agent` tool — works everywhere, zero config.

For one tmux pane per spawned agent, add to user-level `~/.claude/settings.json`:

```json
{
  "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" },
  "preferences": { "tmuxSplitPanes": true }
}
```

**Restart Claude Code after adding.** `/team` autodetects the env flag.
Without it, every feature still works.

> Never commit this user setting to the project repo.

## Entry Points

- `/team <intent> [depth] <task>` — **adaptive** pipeline (triage → orchestrate → gates)
  - `intent ∈ {bug, feature, refactor, explore}`
  - `depth  ∈ {quick, normal, deep}` (default `normal`)
- `/team --team <task>` — **Claude Agent Teams** mode: current session = teamlead,
  spawns exactly 4 Sonnet teammates (`architect`, `unity-dots-dev`, `unity-dev`,
  `qa-tester`) via `TeamCreate` + `Agent(team_name=…)` with a shared task list.
  NOT subagents, NOT simulated, NOT worktrees. Fails fast if Agent Teams is off.
- `/team --full <task>` — deprecated alias of `--team` (prints a deprecation notice).
- `/team --worktrees <task>` — advanced opt-in: manual tmux + git-worktree team
  (`full_team.py`). Separate from `--team`.

The old `--bug` / `--feature` / `--refactor` / `--fast` / `--full` / `--fast-fix` /
`--teams` flags were collapsed into `intent + depth`. See `MIGRATION.md`.

## Pipeline Composition (built into orchestrate.py)

| Complexity | Pipeline | Verification |
|------------|----------|--------------|
| tiny | `[unity-dev]` | bundle (no verification agent) |
| small | `[unity-dev, verifier]` | verifier |
| medium | `[architect, unity-dev, verifier]` | verifier |
| large | `[architect, unity-dev, tester]` | tester |
| critical | `[architect, unity-dev, data-tool, tester]` | tester |

Intent overrides:

- `bug` prepends `bug-investigation`
- `refactor` prepends `refactor-agent` and forces `architect` + `stepgated`
- `explore` produces an empty pipeline (triage-only run)

Depth modifier:

- `quick` downgrades complexity one tier (refused if blast_radius ≥ multi-system)
- `normal` leaves it
- `deep` upgrades one tier AND always uses `tester` AND requires `/codex:review`

## Artifact Gating (Mandatory)

Every artifact has a JSON schema in `.claude/schemas/`:

| Artifact | Owner | Schema |
|----------|-------|--------|
| `triage.json` | `triage` (always) | `triage.schema.json` |
| `pipeline.json` | `orchestrate.py plan` | (derived from triage) |
| `root_cause.json` | `bug-investigation` / `refactor-agent` | `root_cause.schema.json` |
| `approved_plan.json` | `architect` (medium+) | `approved_plan.schema.json` |
| `impl_result.json` | `unity-dev`, `data-tool` | `impl_result.schema.json` |
| `verification_result.json` | `verifier`, `tester` | `verification_result.schema.json` |
| `ownership.lock.json` | `architect` (when parallel) or `triage` (when 2 writers) | `ownership.schema.json` |

Validate any artifact:

```sh
python .claude/scripts/orchestrate.py validate workspace/<artifact>.json <schema-name>
```

The phase gate before the next phase:

```sh
python .claude/scripts/orchestrate.py gate <phase-id>
```

Exit code 2 → halt; some prior artifact is missing or invalid. Do not
patch around it.

## Ownership Partitioning

When pipeline has ≥ 2 writers (any combination of `unity-dev` + `data-tool`,
or stepgated refactor), the architect writes `workspace/ownership.lock.json`
partitioning files by glob. Writers check before signaling next phase:

```sh
python .claude/scripts/orchestrate.py ownership-check <agent-name> <files...>
```

Exit code 3 → ownership violation. Revert and re-scope.

## Unity DOTS Rules

- Prefer `IComponentData`, `IBufferElementData`, `BlobAssetReference<T>`,
  `IAspect`, `ISystem`, jobs, and Burst.
- Optimize for data layout, cache locality, predictable frame cost.
- No managed allocations in hot paths.
- Minimize structural changes in tight loops (ECB or enableable components).
- Keep authoring/editor code separate from runtime (asmdef boundaries).
- Sync points, main-thread work, and archetype churn are explicit costs.

Domain-specific reasoning is loaded via skill packs based on triage's
`domain` classification (see `.claude/rules/dual-stack-domain-system.md`).

## Role Boundaries

| Role | Owns | Must not |
|---|---|---|
| `triage` | task classification, pipeline recommendation | spawn other agents, edit files |
| `architect` | design, ECS boundaries, update flow, ownership partition | code |
| `unity-dev` | runtime implementation | change architecture without `approved_plan.json` |
| `data-tool` | editor tools, validators, diagnostics | silently change runtime behavior |
| `verifier` | run verification bundle from `impl_result.json` | design tests, edit code |
| `tester` | test matrix, stress, regression, sign-off | approve without evidence |
| `bug-investigation` | root cause, evidence chain, fix strategy | implement the fix |
| `refactor-agent` | blast radius, migration plan, rollback | execute migration |
| `system-mapper` | read existing systems, update `repo-knowledge.md` | design new systems |

## Anti-Patterns (Banned)

### Pipeline
- Spawning the fixed 4-agent team out of habit
- Spawning `data-tool` for tasks that produce no tooling
- Spawning `tester` for tiny/small tasks unless confidence < 0.7
- Starting `unity-dev` before `approved_plan.json` exists (when plan requires it)
- Setting `parallel_allowed=true` with confidence < 0.8

### Investigation
- Reading files without CRG evidence
- Grepping the repository as a first step
- Opening more than 8 files in triage (it is a scout)
- Inferring architecture from filenames
- Calling `architecture-agent` (use `system-mapper`)

### Implementation
- Writing code before `triage.json` exists
- Fixing a bug without a proven root cause (`root_cause.json.status="COMPLETE"`)
- Opportunistic refactoring beyond the approved scope
- Signaling verifier before verifying compilation is clean
- Editing files outside the agent's ownership partition
- Removing `[BurstCompile]` from a hot-path `ISystem` (BLOCK)
- Performing structural changes inside a scheduled job (use ECB)

### Orchestration
- Skipping `orchestrate.py validate` on any artifact
- Skipping `orchestrate.py gate` between phases
- Treating gate exit-2 as a warning instead of a halt
- Manually splitting tmux panes
- Declaring a run complete while `verification_result.json.status != "PASS"`
- Running `git commit`/`git push` by hand instead of `orchestrate.py commit`
  (the gate enforces PASS-only + current-branch + no force-push)
- Committing a FAIL or no-verification run

## Knowledge System (unchanged)

Persistent across sessions, committed to repo:

- `workspace/repo-knowledge.md` — stable architecture facts (section-tagged,
  confidence-decayed)
- `workspace/ecs-registry.md` — ECS component/system ownership
- `workspace/recent-changes.md` — 14-day rolling architectural mutations

Session-scoped, gitignored:

- `workspace/triage.json`, `pipeline.json`, `root_cause.json`,
  `approved_plan.json`, `impl_result.json`, `verification_result.json`,
  `ownership.lock.json`, `escalation-log.md`
- `workspace/skill-cache/*.cache.md`

Read the full rules:
- `@.claude/rules/knowledge-ownership-model.md`
- `@.claude/rules/knowledge-decay-system.md`
- `@.claude/rules/knowledge-token-budget.md`
- `@.claude/rules/agent-knowledge-policy.md`

## Codex Review Gate (deep depth only)

When `depth=deep` OR `complexity=critical`:

1. **Plan review** — after `architect` writes `approved_plan.json`, run
   `/codex:review` against the plan. Blocker → architect re-issues.
2. **Implementation review** — after `verifier`/`tester` writes
   `verification_result.json` and BEFORE `orchestrate.py finalize`, run
   `/codex:review` over the diff. Blocker → re-spawn `unity-dev`.

For `quick` and `normal` depth: Codex review is optional. Not running it is
not a process violation.

## Skill Discovery Policy

Skill loading is **deterministic**, not ad-hoc. `route_skills.py` selects skills per agent
based on role, domain, and task keywords. The registry is the single source of truth.

### Local skills always win

Check `.claude/skills/registry.json` before any external search.
If a local skill covers the task, use it. External discovery runs only when no local match exists.

### Safe discovery workflow (required order)

1. Search → inspect source/reputation → read SKILL.md → read scripts/permissions →
   verify compatibility → install → `skills:validate` → use

**Never:** search → auto-install → execute.

### Block external skills that

- Request broad filesystem write permissions
- Run shell without showing the command text
- Access secrets or `.env` files
- Modify global Claude config or MCP server list
- Exfiltrate data to external URLs
- Have no verifiable source (no repo, no author, no license)
- Contain prompt-injection instructions
- Missing `use-when` field (cannot be safely routed)

### Validation after install

`python .claude/scripts/skills.py validate` must report `orphans:0, unreachable:0, unresolved_duplicates:0`.

See `AGENTS.md` at repo root for the full policy.

### Skill CLI

```bash
python .claude/scripts/skills.py list          # all registered skills
python .claude/scripts/skills.py validate      # full validation report
python .claude/scripts/skills.py doctor        # fix suggestions (no auto-apply)
python .claude/scripts/skills.py unused        # dead-skill report (fails on orphans)
```

---

## Reference

- `team.md` — the command itself
- `MIGRATION.md` — moving from the fixed-4 v1 flow to v2 adaptive pipeline
- `AGENTS.md` — external skill discovery policy
- `.claude/skills/registry.json` — skill registry (single source of truth)
- `.claude/scripts/route_skills.py` — per-role skill routing
- `.claude/scripts/skills.py` — skill management CLI
- `.claude/rules/GRAPH_FIRST.md` — CRG-first investigation rules
- `.claude/rules/mcp-phase-gates.md` — Phase 1–4 MCP permission gates
- `.claude/rules/ownership-boundaries.md` — DOTS vs Unity ownership of state
- `.claude/rules/escalation-policy.md` — escalation signals and routing
- `.claude/rules/dual-stack-domain-system.md` — DOTS / Unity / Hybrid domains
