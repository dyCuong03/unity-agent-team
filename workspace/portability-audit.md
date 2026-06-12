# Portability Audit — unity-agent-team

Date: 2026-06-12
Scope: full framework (scripts, agents, commands, skills, rules, docs, tests, workspace).

## Part 1 — Inventory of hardcoded assumptions

### Root resolution (CRITICAL — 12 distinct mechanisms found)

| Pattern | Where | Problem |
|---|---|---|
| `Path(__file__).resolve().parents[2]` | orchestrate.py:43, route_skills.py:36 (+dup at :239), triage.py:41, build_skill_registry.py:29, migrate_tier1/2, validate_agentmemory_rule.py, validate_skill_pack.py, validate_skill_registry.py, validate_skill_routing.py | Assumes `.claude/scripts/` is exactly 2 levels below project root; ignores env override |
| `Path(__file__).resolve().parent.parent.parent` | skills_validator.py:28 | Same, less readable |
| `UNITY_TEAM_PROJECT_ROOT` env override + fallback | full_team.py:54-55, orchestrate.py:693-694 | Only 2/17 scripts respect it |
| `parents[1]` | tests/conftest.py:14 | Correct for tests, but hardcodes `.claude/scripts` path |

### Worktrees / branches

- full_team.py:56 `WORKTREE_BASE = REPO_ROOT.parent / "worktrees"` — fixed sibling dir, no project-name isolation, parent may be unwritable, two projects collide.
- Branch names generated (`unity-agent-team-<slug>-<agent>`) — OK; base branch is a parameter — OK; but no configured default branch source.

### Unity-only assumptions

- full_team.py:79-150 hardcoded ownership globs `Assets/**/*.cs`, `!Assets/**/Systems/**`, `DOTSFoundation`, etc.
- full_team.py:66 fixed `AGENTS = ["architect", "unity-dev", "unity-dots-dev", "qa-tester"]`.
- triage.py:46 example ownership `Assets/Scripts/Combat/**` (example only — keep, mark).
- unity_skills.py:27-28 hardcoded `http://localhost:8090`; registry in `~/.unity_skills/`.

### Hardcoded project names / absolute paths

- `.claude/skills/agentmemory-codebase-recall/SKILL.md` — `BackpackAdventures` in example lesson.
- CLONE-SETUP.md:59 — `/mnt/e/BuzzleStudio/BackpackAdventures` example.
- docs/research/* — absolute `E:/BuzzleStudio/...` paths (research artifacts).
- workspace/audit/, workspace/dots-program/, workspace/full-team/, workspace/collision-disambiguation-draft.md — committed session/research debris containing absolute paths. Not framework assets.
- tests/test_env_compat.py — project-name references.

### Workspace/devlog/report paths

- orchestrate.py:44-46, triage.py:42 — `workspace/`, `.claude/workspace-templates`, `.claude/schemas` fixed relative to root (acceptable once root is unified, but must come from one constant source).
- full_team.py:634/637/963/970 — mixes `REPO_ROOT / "reports"` and bare relative `"reports/team/{slug}"` (cwd-dependent).
- No devlog resolution anywhere; installed-copy auditor previously hardcoded one project's devlog path.

### Game-specific examples in generic rules (LOW — mark as examples)

PopupPresenter / HealthBarBinding / EnemyMovementSystem / RegionLoadSystem etc. in
architecture-pattern-detection.md, domain-scoring-engine.md, dual-stack-domain-system.md,
escalation-policy.md, change-impact-system.md, change-trigger-policy.md, domain-aware-mcp.md,
relevance-filtering.md. Action: keep as clearly-marked generic examples.

### Missing-file contracts (decision per file)

| File | Decision |
|---|---|
| `MIGRATION.md` | EXISTS. Keep (option 4): extend with portability migration section. |
| `AGENTS.md` | EXISTS. Keep as-is (project-agnostic policy). |
| `workspace/repo-knowledge.md` | OPTIONAL (option 2): setup creates seeded version when knowledge system selected; all commands tolerate absence. |
| `workspace/ecs-registry.md` | OPTIONAL, Unity/DOTS projects only: setup creates when projectType=unity; commands tolerate absence. |
| `workspace/recent-changes.md` | OPTIONAL (option 2): setup creates seeded version; commands tolerate absence. |

Source of truth for codebase knowledge: the target project's own `workspace/` knowledge files
(created by setup), supplemented by agentmemory when enabled. Framework ships templates only.

## Part 2 — Root/Config architecture (design)

### Root concepts

| Root | Definition | Resolution |
|---|---|---|
| `FRAMEWORK_ROOT` | Dir containing the installed framework `.claude/` (scripts live at `<FRAMEWORK_ROOT>/.claude/scripts/`) | `Path(__file__).parents[2]` of `roots.py` — structural, never configured |
| `CLAUDE_ROOT` | Active `.claude/` configuration dir | `<FRAMEWORK_ROOT>/.claude` (embedded) or `<PROJECT_ROOT>/.claude` when project has its own |
| `PROJECT_ROOT` | Repository being worked on | (1) explicit arg → (2) `AGENT_TEAM_PROJECT_ROOT` env (legacy alias `UNITY_TEAM_PROJECT_ROOT`) → (3) `project-config.json: projectRoot` → (4) `git rev-parse --show-toplevel` from cwd → (5) walk-up for `.claude/` → (6) FAIL with actionable error |
| `UNITY_PROJECT_ROOT` | Dir with `Assets/` + `Packages/manifest.json` + `ProjectSettings/ProjectVersion.txt` | config `unityProjectRoot` → scan PROJECT_ROOT then its depth-1/2 children → `None` (non-Unity) |
| `WORKSPACE_ROOT` | Optional multi-repo parent | config `workspaceRoot` / env `AGENT_TEAM_WORKSPACE_ROOT` → `None`. Never auto-guessed by walking up. |

One module: `.claude/scripts/roots.py`. Every other script imports it. No other file
computes roots. Validator enforces this.

### Project config — `.claude/project-config.json`

All fields optional; setup generates defaults. Paths relative to PROJECT_ROOT.

```json
{
  "projectName": "my-unity-game",
  "projectRoot": ".",
  "projectType": "unity | cloudcode | web | backend | cocos | generic",
  "unityProjectRoot": ".",
  "defaultBranch": "main",
  "allowedBranches": ["main", "develop"],
  "devlogPaths": [".claude/devlogs"],
  "workspaceDir": "workspace",
  "reportsDir": "reports",
  "worktreeRoot": "../<projectName>-worktrees",
  "agentMemoryEnabled": false,
  "agentMemoryIndexPath": ".agentmemory",
  "teamProfiles": {
    "default": ["architect", "unity-dev", "tester"],
    "full": ["architect", "unity-dots-dev", "unity-dev", "qa-tester"]
  },
  "ownershipDefaults": { "<agent>": ["glob", "!glob"] }
}
```

### Installation modes

| Mode | Layout | PROJECT_ROOT | Notes |
|---|---|---|---|
| Embedded | `.claude/` copied into target repo root | == FRAMEWORK_ROOT | default; config at `<repo>/.claude/project-config.json` |
| External/shared | framework repo elsewhere; `AGENT_TEAM_PROJECT_ROOT` or config `projectRoot` points at target | explicit | framework `.claude` is CLAUDE_ROOT; project may add local `.claude/devlogs` etc. |
| Monorepo | workspace dir contains framework + N projects | per-task explicit | agents operate ONLY on active PROJECT_ROOT; cross-project requires explicit config `workspacePaths` allow-list |

### Devlog resolution (auditor + all agents)

1. `<PROJECT_ROOT>/<p>` for each `devlogPaths` entry. 2. Missing → report optional-absent,
never an error unless workflow requires devlogs. 3. Multi-repo: only repos in active task /
config allow-list. 4. No unbounded parent scanning.

### Adaptive team composition

`teamProfiles` in config; `/team --full|--team` uses profile `full`; adaptive pipeline maps
complexity tiers to roles available in the active profile set; Unity-specific roles
(unity-dots-dev, unity-dev) auto-disabled when `projectType != unity` and replaced by `coder`.

### Validation additions

`validate_portability.py`: banned-name scan (known project names in framework files,
excluding workspace/ session dirs), broken internal refs, root-resolver uniqueness
(`parents[2]` etc. allowed only in roots.py + tests/conftest.py), config path validation,
devlog/worktree path safety (no escape outside PROJECT_ROOT without cross-project grant).

## Part 3 — Findings → fixes mapping

| # | Fix | Owner |
|---|---|---|
| 1 | `roots.py` unified resolver + config loader | core |
| 2 | `setup.py` idempotent init (--check, --non-interactive) | core |
| 3 | Migrate all 17 scripts to roots.py | scripts agent |
| 4 | full_team.py: AGENTS+ownership+worktree from config | scripts agent |
| 5 | commands/agents/skills md → placeholders + spawn context | md agent |
| 6 | Mark game-specific rule examples as examples | md agent |
| 7 | validate_portability.py + tests + fixtures | validation agent |
| 8 | migrate.py + MIGRATION.md portability section + docs | docs agent |
| 9 | Purge/gitignore workspace debris with absolute paths | core |
| 10 | Smoke tests in 3 differently-named fixture repos | final |

## Part 4 — Final status (2026-06-12, post-implementation)

### Delivered

- `.claude/scripts/roots.py` — single resolver (5 roots, documented order, env `AGENT_TEAM_PROJECT_ROOT` + legacy alias, stderr note when unconfigured)
- `.claude/scripts/setup.py` — idempotent init (`--check/--yes/--force/--project-root`), per-type team profiles + knowledge seeds
- `.claude/scripts/migrate.py` — old-install detection, git-safe, report to workspace/migration-report.md
- `.claude/scripts/validate_portability.py` — banned names, single-resolver, broken refs, config validation, cwd-dependence; waiver syntax `portability-allow:`
- 17 scripts migrated to roots.py; worktrees per-project namespaced; team rosters from `teamProfiles`; ownership globs config-overridable; non-unity neutral fallback
- All md (CLAUDE.md, commands, 12+3 agents, skills, rules) project-agnostic; spawn-context injection; STEP -1 resolution gate (incl. `configPath: null` check)
- New generic agents: `coder`, `backend-dev`, `web-dev`; portable `agent-auditor`
- Docs rewritten (README/SETUP/CLONE-SETUP/MIGRATION) with generic names + 3 install modes; .gitignore debris entries
- tests/test_portability.py (22 tests) — total suite 516 passed

### Verification

- `validate_portability.py`: PASS (0 findings)
- pytest: 516 passed
- `skills.py validate`: PASS (5 documented collision warnings)
- Cold-start smoke: 3 fixtures PASS (see workspace/setup-smoke-test.md)
- agent-auditor: initial DEGRADED with 3 HIGH → all fixed:
  H1 triage triple-load (de-@'d agent bodies + spawn self-import removed; verifier too)
  H2 unreachable setup gate (configPath-null check in team.md + roots.py stderr note)
  H3 nonexistent profile roles (coder/backend-dev/web-dev agent definitions added)

### Documented non-blocking remainders

- `team.md` ~39 KB loaded per `/team` invocation (pre-existing; split candidate)
- 5 skill trigger collisions (documented priority resolutions)
- Vendor `unity-skills/*/SKILL.md` contain upstream doc example paths (E:/CodeSpace) — vendor content, reported by migrate.py --check, intentionally not auto-edited
- Explore-intent triage emits non-empty recommended_pipeline that planner discards (cosmetic)
