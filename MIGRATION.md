# Migrating from v1 (fixed-4) to v2 (adaptive pipeline)

The v2 framework is a redesign, not a patch. It replaces the fixed 4-agent
template with an adaptive pipeline that classifies the task and spawns only
the agents that work actually needs.

## TL;DR

- `/team <task> [--bug | --feature | --refactor] [--fast | --full | --fast-fix] [--teams]`
  is gone.
- New form: `/team <intent> [depth] <task>`
  - `intent ∈ {bug, feature, refactor, explore}`
  - `depth ∈ {quick, normal, deep}` (default `normal`)
- Triage agent always runs first. It writes `workspace/triage.json`.
- `orchestrate.py plan` reads `triage.json` and writes `workspace/pipeline.json`.
- You spawn only the agents `pipeline.json.phases[].agents[]` lists.
- Every phase boundary is a Python gate (`orchestrate.py gate <phase-id>`).
  Exit code 2 means halt; do not patch around it.

---

## Flag mapping

| v1 command | v2 command |
|------------|------------|
| `/team <task>` (general) | `/team feature <task>` |
| `/team <task> --full` | `/team feature deep <task>` |
| `/team <task> --fast` | `/team feature quick <task>` |
| `/team <task> --bug` | `/team bug <task>` |
| `/team <task> --feature` | `/team feature <task>` |
| `/team <task> --feature --with-tooling` | `/team feature deep <task>` (triage may pick `critical` and add `data-tool`) |
| `/team <task> --refactor` | `/team refactor <task>` |
| `/team <task> --fast-fix` | `/team bug quick <task>` |
| `/team <task> --teams` | Enable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `~/.claude/settings.json`; `/team` autodetects |

---

## Conceptual mapping

### Old: fixed roles, fixed sequence

v1 always spawned 2–4 of: `architect`, `unity-dev`, `data-tool`, `tester`.
The choice was a static lookup on flags.

### New: triage → pipeline.json → minimum spawn

v2 spawns whatever `pipeline.json` lists. Determined by:

1. Triage classifies complexity (`tiny | small | medium | large | critical`)
   and intent.
2. `orchestrate.py plan` maps complexity + intent to a pipeline.
3. Triage's `confidence_score` + `ownership_partition` determine whether
   parallel execution is allowed in any phase.

| Complexity | Pipeline | Verification |
|------------|----------|--------------|
| tiny | `[unity-dev]` | bundle (no agent) |
| small | `[unity-dev, verifier]` | verifier |
| medium | `[architect, unity-dev, verifier]` | verifier |
| large | `[architect, unity-dev, tester]` | tester |
| critical | `[architect, unity-dev, data-tool, tester]` | tester |

`verifier` is a new lightweight agent. It runs the verification bundle from
`impl_result.json` and emits `verification_result.json`. It does not design
tests. The full `tester` agent is reserved for `large` / `critical` or any
task where triage reports `confidence_score < 0.7`.

### Old: nested subagents

v1 instructed `unity-dev` to spawn `code-generator`, `job-optimizer`,
`burst-validator`, `memory-checker`. Architect spawned `design-analyzer`,
`dependency-mapper`. These nested spawns added orchestration overhead with
little incremental value.

### New: skill packs

The same guidance is loaded as text into the relevant agent:

| Pack | Loaded into | Replaces |
|------|-------------|----------|
| `burst-safety` | unity-dev (DOTS/Hybrid) | `burst-validator` |
| `ecs-job-patterns` | unity-dev (DOTS/Hybrid) | `job-optimizer` |
| `memory-safety` | unity-dev (DOTS/Hybrid) | `memory-checker` |
| `ownership-partitioning` | every writer (when parallel) | (new) |

`architect`'s former subagents (`design-analyzer`, `dependency-mapper`) are
covered by the existing skill files plus the triage agent's CRG report —
they were doing the same investigation work that triage now does upstream.

### Old: markdown gates

v1 said: "do not proceed until X." Agents could silently ignore.

### New: Python gates

Every gate is `python .claude/scripts/orchestrate.py …`. Exit non-zero halts
the next phase. There is no version of "I think it's fine" — the script
either passes or fails.

---

## Artifact gating (the heart of v2)

Each agent must emit a schema-validated JSON artifact:

| Agent | Artifact | Schema |
|-------|----------|--------|
| `triage` | `triage.json` | `triage.schema.json` |
| `bug-investigation` / `refactor-agent` | `root_cause.json` | `root_cause.schema.json` |
| `architect` (medium+) | `approved_plan.json` (status must be `APPROVED`) | `approved_plan.schema.json` |
| `unity-dev` / `data-tool` | `impl_result.json` (compilation must be `CLEAN`, `verification_bundle` non-empty) | `impl_result.schema.json` |
| `verifier` / `tester` | `verification_result.json` (status `PASS` to complete) | `verification_result.schema.json` |
| `architect` (when partitioning) | `ownership.lock.json` | `ownership.schema.json` |

Validate before signaling:

```sh
python .claude/scripts/orchestrate.py validate workspace/<artifact>.json <schema-name>
```

The orchestrator's gate runs the same validation plus a status check (e.g.
rejects `approved_plan.json` with `status="REJECTED"`).

---

## Tester optimization

v1 spawned tester on every run. v2 spawns tester only when:

- complexity ≥ `large`, OR
- `confidence_score < 0.7`, OR
- `depth == "deep"`, OR
- after 2 consecutive `verifier` FAILs on the same task.

For everything else, `verifier` runs the deterministic bundle that
`unity-dev` wrote in `impl_result.verification_bundle`. Triage decides which
verification strategy in `triage.json.verification_strategy`.

---

## Removed files

| Removed | Reason |
|---------|--------|
| `.claude/commands/bugfix.md` | Subsumed by `/team bug <task>` |
| `.claude/skills/start-unity-dots-team/` | There is no fixed team to start |

---

## Behavior changes you will notice

1. **Most runs spawn 1–3 agents, not 4.** A typical small bug fix runs
   `bug-investigation → unity-dev → verifier`. No architect, no data-tool,
   no tester.
2. **Parallel execution is rarer and only when justified.** Old runs spawned
   all agents in parallel on the first message. v2 spawns parallel only
   when triage's `confidence_score ≥ 0.8`, complexity ≥ medium, and an
   ownership partition with ≥ 2 agents exists.
3. **You will see explicit gate output.** Every phase prints
   `[gate] OK — clear to enter phase-N` or `[gate] BLOCK — cannot enter
   phase-N: …`. The blocks are real halts.
4. **tmux is no longer pre-split or counted.** It is an optional UI for
   pane-per-agent visibility. The orchestration is identical with or
   without it.
5. **The fixed 4-agent completion banner is gone.** `orchestrate.py finalize`
   prints a deterministic completion report from the artifacts; do not
   paraphrase it.

---

## Persistent knowledge files

These are unchanged. They still live in `workspace/` and are committed to
the repo:

- `repo-knowledge.md` — stable architecture facts, section-tagged
- `ecs-registry.md` — ECS component/system ownership
- `recent-changes.md` — 14-day rolling architectural mutations

The decay/relevance/ownership rules in `.claude/rules/` still apply. No
migration needed for these files.

---

## Migration checklist for an existing project

1. Pull the latest `.claude/` from this package over your existing one.
2. Add `workspace/` (except the persistent files) to `.gitignore` — see the
   template in `.gitignore`.
3. Run `python .claude/scripts/orchestrate.py preflight`. Expect "schemas
   present, templates present."
4. Run `python .claude/scripts/orchestrate.py validate
   .claude/workspace-templates/triage.json triage`. Expect OK.
5. Update any internal docs / scripts that reference the old flag set.
6. Try a small `/team explore <something>` to confirm the triage path works
   end-to-end without spawning anything else.
7. Try `/team bug <known small bug>` to confirm a full pipeline runs and the
   completion report appears.

---

## Help / troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `[gate] BLOCK — cannot enter phase-N: <agent> → <artifact>: artifact missing` | Upstream agent never emitted its artifact | Re-spawn the agent with a prompt that tells it to emit the artifact |
| `[gate] BLOCK — … status='REJECTED'` | Architect rejected the plan | Read `approved_plan.json.rejection_reason`; address it; re-spawn architect |
| `[gate] BLOCK — … compilation='BROKEN'` | unity-dev signaled before compilation was clean | Re-spawn unity-dev; do not advance |
| `[ownership-check] BLOCK` | A writer touched a file outside its partition | `git checkout` the offending file; re-scope or escalate to architect |
| `[finalize] BLOCK — verification status='FAIL'` | Verification failed | Read `verification_result.fail_reason`; route to unity-dev; up to 2 retries before tester escalation |
| Triage returned `domain="Ambiguous"` | CRG evidence was insufficient | Architect classifies manually; update `approved_plan.json` before unity-dev runs |
| `Running without CRG evidence` | code-review-graph MCP is unavailable | Install/start it, or accept the confidence-score penalty |

For anything else: read the script source. `orchestrate.py` is ~400 lines of
stdlib Python; it is meant to be read.

---

# v2 → portable (2026-06)

The framework no longer assumes it lives at the root of one specific Unity
repo. All path resolution goes through a single resolver, configuration is a
JSON file, and the same `.claude/` works embedded, shared across repos, or
inside a monorepo.

## What changed

| Area | Before | After |
|------|--------|-------|
| Path resolution | each script computed paths itself (parents[2] of `__file__`, cwd guesses) | **`roots.py`** — single resolver every script imports. Resolution order for `PROJECT_ROOT`: explicit `--project-root` → env → `project-config.json` → `git rev-parse --show-toplevel` → walk up for `.claude/` → fail with `RootResolutionError` (never guess) |
| Configuration | hardcoded assumptions (repo name, Unity root, branch) | **`.claude/project-config.json`** — projectName/Type, unityProjectRoot, defaultBranch, workspaceDir, worktreeRoot, teamProfiles, agentMemoryEnabled, … |
| Setup | manual copy + hope | **`setup.py`** — idempotent init: detects project type, creates dirs, writes config (never overwrites user values without `--force`), seeds knowledge files |
| Worktree dir | `<parent>/worktrees` (shared by every project — collision-prone) | `<parent>/<projectName>-worktrees` (namespaced; override via `worktreeRoot`) |
| Team composition | fixed agent names baked into scripts/docs | **team profiles** per `projectType` in config (`teamProfiles.default` / `.full` / `.dots`, see `setup.py TEAM_PROFILE_DEFAULTS`) |
| Env override | `UNITY_TEAM_PROJECT_ROOT` | **`AGENT_TEAM_PROJECT_ROOT`** (legacy name still honored as an alias) |
| Install modes | embedded only | embedded · external/shared · monorepo (see `CLONE-SETUP.md`) |

## How to migrate an existing install

```sh
python3 .claude/scripts/migrate.py --check    # report what's old-style; changes nothing
python3 .claude/scripts/migrate.py            # apply: runs setup.py --yes, writes report
```

What `migrate.py` detects: missing `project-config.json`, the legacy
`UNITY_TEAM_PROJECT_ROOT` env var, absolute paths baked into `.claude/**/*.md`
or `.mcp.json`, and an old un-namespaced `<parent>/worktrees` dir.

What apply does — and does not do:

- Runs `setup.py --yes` (idempotent; existing config values are **never**
  overwritten — same semantics as setup.py itself).
- Writes `workspace/migration-report.md` listing findings and changes.
- Does **not** auto-edit your markdown/`.mcp.json` (absolute paths are
  reported file:line for manual fixing) and does **not** delete the old
  worktrees dir.
- Refuses to apply if `.claude/` has uncommitted git changes
  (override: `--allow-dirty`).

Rename the env var in your shell profile if you used the old name:

```sh
# before:  export UNITY_TEAM_PROJECT_ROOT=/path/to/my-unity-game
export AGENT_TEAM_PROJECT_ROOT=/path/to/my-unity-game
```

## How to revert

Migration is additive only. To undo:

```sh
git checkout -- .claude/                 # restore any framework files
rm .claude/project-config.json           # remove generated config (if unwanted)
# knowledge seeds (workspace/repo-knowledge.md etc.) are only created when
# absent — delete them if you don't want them
```

If you committed the migration and want it gone: `git revert <commit>`.
