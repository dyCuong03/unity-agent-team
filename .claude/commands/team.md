---
description: Adaptive agent pipeline (project context resolved via roots.py). Triage classifies the task; orchestrate.py derives the minimum viable agent composition; each phase is artifact-gated by Python, not by markdown promises. Use --team (deprecated alias --full) for a real Agent Teams team (roster from config teamProfiles.full) on Sonnet.
argument-hint: "[--team] <intent: bug | feature | refactor | explore> [depth: quick | normal | deep] <task description>"
---

# `/team` — Adaptive Unity DOTS Pipeline

```
/team <intent> [depth] <task description>
/team --team <task description>      # deprecated alias: --full

intent  ∈ { bug, feature, refactor, explore }
depth   ∈ { quick, normal, deep }   default: normal
```

Two modes:

| Mode | Command | Behavior |
|------|---------|----------|
| **Adaptive** (default) | `/team <intent> [depth] <task>` | Triage → minimum agents → artifact-gated (in-process subagents) |
| **Team** | `/team --team <task>` (deprecated alias `--full`) | **Claude Agent Teams** — current session is teamlead; persistent teammates from config `teamProfiles.full` on **Sonnet** (NOT subagents, NOT simulated, NOT tmux/worktree) |
| **Worktrees** | `/team --worktrees <task>` | Advanced opt-in: manual tmux + git-worktree team via `full_team.py` |

## STEP -1 — Resolve project context (ALL modes, before anything else)

Run the unified resolver **once** at the start of every `/team` invocation:

```sh
python3 .claude/scripts/roots.py --json
```

All subsequent paths come from this output — never from assumptions about cwd,
repo name, or layout:

- `workspaceDir` → every `workspace/...` path mentioned in this command
- `reportsDir` → every `reports/...` path
- `worktreeRoot` → worktree locations (`--worktrees` mode)
- `defaultBranch` → base branch for worktree branches and merges
- `PROJECT_ROOT`, `projectType`, `UNITY_PROJECT_ROOT`, `projectName`,
  `teamProfiles` → injected into every agent/teammate prompt

If `roots.py` errors, **STOP** and tell the user to run
`python3 .claude/scripts/setup.py`, then re-run `/team`.

`roots.py` exits 0 with built-in defaults when no `project-config.json`
exists — so ALSO check the output: if `configPath` is `null`, the project has
not been set up. **STOP** and instruct the user to run
`python3 .claude/scripts/setup.py` (defaults like `teamProfiles` and
`projectType=generic` are placeholders, not a configured project).

---

The adaptive path **always** runs `triage` first, **always** calls
`orchestrate.py plan` to derive the pipeline, and **never** spawns agents that
the plan does not list. Every phase boundary is a Python gate; if the gate
exits non-zero, you halt — no exceptions, no markdown promises.

**Exception:** `/team --team` (deprecated alias `/team --full`) bypasses adaptive
triage and runs a **Claude Agent Teams** team — the current session is the
teamlead and spawns the teammates listed in the config's `teamProfiles.full`
(from the STEP -1 `roots.py --json` output) on Sonnet via `TeamCreate` +
`Agent(team_name=…)`, with a shared task list. See the `--team` section below.

## Flags

### `--team`

Use Claude Agent Teams mode. The current Claude Code session is the teamlead and
creates the Agent Teams teammates on Sonnet. **The teammate roster comes from
config: `teamProfiles.full` in the `roots.py --json` output — never a hardcoded
list.** The documented default profile for `projectType=unity` is:
- `architect`
- `unity-dots-dev`
- `unity-dev`
- `qa-tester`

Non-unity project types use their configured profile (e.g. `cloudcode` →
`architect`, `backend-dev`, `qa-tester`). If a profile names a role with no
`.claude/agents/<role>.md` definition, spawn it as a generic `claude` teammate
with the role described in the prompt.

Real Agent Teams teammates with shared task coordination and teammate-to-teammate
messaging. This mode does **not** use normal subagents, **not** simulated markdown
roles, **not** single-agent execution, and **not** the manual tmux/worktree path.
If Agent Teams is unavailable, it **fails fast** — no degraded fallback.

### `--full`

**Deprecated** alias for `--team`. On use, print:
`[DEPRECATED] /team --full is an alias for /team --team. Prefer /team --team.`
then behave exactly as `--team`.

### `--worktrees`

Separate advanced mode: manual tmux + git-worktree isolation via `full_team.py`
(4 real `claude` CLI sessions, one worktree+branch each). Opt-in only; not
implied by `--team`/`--full`.

## What changed from the fixed 4-agent team

| Old | New |
|---|---|
| Always architect + unity-dev + data-tool + tester | Triage picks the minimum (1–4 agents) |
| `--bug` / `--feature` / `--refactor` / `--fast` / `--full` / `--fast-fix` / `--teams` | `intent` + `depth` |
| Per-role nested subagents (code-generator, burst-validator, …) | Loaded as skill packs (`burst-safety`, `ecs-job-patterns`, `memory-safety`, `ownership-partitioning`) |
| Markdown promises ("don't proceed until X") | `orchestrate.py gate` exits 2; you halt |
| Always-on tester | `verifier` for small/medium; tester only for large/critical or confidence < 0.7 |
| Parallel agents from message 1 | Sequential by default; parallel allowed only when confidence ≥ 0.8 AND complexity ≥ medium AND ownership partitioned |
| tmux as a hard dependency | tmux is optional UI only; orchestration runs identically without it |

---

## DISPATCH — read the flags first

Before STEP 0, scan the arguments:

- If they contain **`--team`** → **Claude Agent Teams mode**. Do NOT run
  triage/plan/gates. Do NOT run `full_team.py`. Jump to the **`/team --team`**
  section below: run the Step 0 availability check, then `TeamCreate` + spawn the
  Sonnet teammates from `teamProfiles.full` via `Agent(team_name=…)`. Strip the
  flag from `<task>`.
- If they contain **`--full`** → same as `--team`, but FIRST print:
  `[DEPRECATED] /team --full is an alias for /team --team. Prefer /team --team.`
- If they contain **`--worktrees`** → the separate manual tmux/worktree mode
  (`full_team.py`). See the `/team --worktrees` section.
- Otherwise → **Adaptive mode**. Continue to STEP 0 below.

---

## STEP 0 — Bootstrap (informational, never blocks)

```sh
python3 .claude/scripts/orchestrate.py preflight
python3 .claude/scripts/orchestrate.py reset
```

`preflight` reports env, MCP, tmux state. `reset` clears session artifacts:
`triage.json`, `pipeline.json`, `root_cause.json`, `approved_plan.json`,
`impl_result.json`, `verification_result.json`, `ownership.lock.json`,
`escalation-log.md`. Persistent files (`repo-knowledge.md`,
`ecs-registry.md`, `recent-changes.md`) are preserved.

---

## agentmemory codebase recall (ALL `/team` modes — mandatory rule)

Agents must not explore the codebase at random. Every agent that reads or modifies
code follows the `agentmemory-codebase-recall` skill:

```
Before broad Read/Grep/Glob exploration, query agentmemory when available.
Use memory to narrow the search.
Then read the current files directly.
Do not claim facts based only on memory.
Do not edit based only on memory.
If agentmemory is unavailable, report [MEMORY UNAVAILABLE] and use targeted search.
```

Correct flow (memory is a recall layer, **not** the source of truth — current repo
files always win):

```
agentmemory query
→ targeted file discovery
→ Read current files
→ verify memory against files
→ analyze or edit
→ save important findings back to agentmemory
```

`agentmemory-codebase-recall` is routed into every code-reading role (see the
per-agent skill map). When agentmemory MCP is absent, this is non-blocking: agents
report `[MEMORY UNAVAILABLE]` once and fall back to targeted CRG/Grep — never random
folder reads. Setup: **SETUP.md → "Using agentmemory with /team"**.

---

## STEP 1 — Triage (ALWAYS, exactly once)

Spawn one `triage` agent. Wait for its artifact. No exceptions.

```
Agent({
  subagent_type: "triage",
  description: "Adaptive pipeline triage",
  prompt: "@.claude/skills/triage/SKILL.md @.claude/rules/GRAPH_FIRST.md @.claude/rules/api-fingerprinting-system.md @.claude/rules/domain-scoring-engine.md\n\nIntent: <INTENT>\nDepth: <DEPTH>\nTask: <TASK>\n\nProduce workspace/triage.json via .claude/scripts/triage.py and validate it. Return only the rationale paragraph and the artifact path."
})
```

After triage returns, validate (script does this too but be explicit):

```sh
python3 .claude/scripts/orchestrate.py validate workspace/triage.json triage
```

If validation fails → halt and report the error. Do not spawn anything else.

---

## STEP 2 — Plan (deterministic mapping)

```sh
python3 .claude/scripts/orchestrate.py plan workspace/triage.json
```

This writes `workspace/pipeline.json` with:

- `phases[]` — each has `id`, `agents[]`, `mode ∈ {sequential, parallel}`
- `verification_strategy ∈ {bundle, verifier, tester, stepgated, none}`
- `parallel_allowed` (only true when confidence ≥ 0.8, complexity ≥ medium,
  and ownership has ≥ 2 partitions)
- `artifacts_required` — what JSON each agent must emit

**Read `workspace/pipeline.json` now.** The phases drive every subsequent
spawn. Do not re-derive them in your head.

### Complexity → pipeline (built into orchestrate.py)

| Complexity | Pipeline | Verification |
|------------|----------|--------------|
| tiny | `[unity-dev]` | bundle (no agent) |
| small | `[unity-dev, verifier]` | verifier |
| medium | `[architect, unity-dev, verifier]` | verifier |
| large | `[architect, unity-dev, tester]` | tester |
| critical | `[architect, unity-dev, data-tool, tester]` | tester |

Intent overrides:

- `bug` prepends `bug-investigation`
- `refactor` prepends `refactor-agent` then forces `architect` approval and
  `stepgated` verification
- `explore` produces an empty pipeline (triage-only run)

---

## STEP 3 — Execute phases (gated)

For each phase in `pipeline.json.phases` in order:

1. **Gate** before spawning:

   ```sh
   python3 .claude/scripts/orchestrate.py gate <phase-id>
   ```

   Non-zero exit means a prior phase's artifact is missing, malformed, or has
   the wrong status. **Halt and surface the gate output** — do not patch around
   it, do not retry the spawn, do not "just try anyway".

2. **Spawn** the agents listed in `phase.agents`:
   - `mode == "sequential"` → one agent at a time, wait for each artifact
   - `mode == "parallel"` → spawn all in one message
   - Each agent prompt MUST `@`-import the **lane-correct skills for that agent**
     from `pipeline.json.skills_by_agent[<agent>]` — one `@.claude/skills/<m>/SKILL.md`
     per listed module. Do NOT hardcode `unity-dots-best-practices` for every agent:
     the Unity-classic lane (`unity-dev`) gets `unity-classic`, the DOTS lane
     (`unity-dots-dev`) gets `unity-dots-best-practices` + DOTS extras. `orchestrate.py`
     already attached DOTS `skill_packs` to DOTS lanes only — do not re-add them to
     `unity-dev`/`tester`/`verifier`/`data-tool`.
   - Each agent prompt MUST instruct it to validate its artifact before
     returning:
     `python3 .claude/scripts/orchestrate.py validate workspace/<artifact> <schema>`

3. **After all agents in the phase finish**, gate again before the next phase.

### Phase template

```
Agent({
  subagent_type: "<agent name from phase.agents>",
  description: "<role> — phase <id>",
  prompt: "@.claude/agents/<agent>.md [one @.claude/skills/<m>/SKILL.md per module in pipeline.json.skills_by_agent[<agent>]]\n\nIntent: <INTENT>\nTask: <TASK>\nRead workspace/triage.json and any prior artifacts listed in pipeline.json.artifacts_required for upstream agents.\n\nProduce workspace/<your-artifact>.json. Validate before returning:\n  python3 .claude/scripts/orchestrate.py validate workspace/<your-artifact>.json <schema-name>\n\nDo not edit files outside your ownership partition (.claude/scripts/orchestrate.py ownership-check <agent> <files>)."
})
```

`skills_by_agent` is produced by the **skill router** (`scripts/route_skills.py`),
backed by the **skill registry** (`.claude/skills/registry.json`). The router
selects `role primary + domain extras + intent extras + keyword matches +
agentmemory hints`, capped at `registry.max_total_skills` (7), with role/domain/
intent priority stronger than keyword. It is the single source of truth — adaptive
`/team` and `/team --team` both derive their skills from it. Inspect any agent:

```sh
python3 .claude/scripts/route_skills.py --agent unity-dev --domain Unity --intent bug --task "<task>"
```

Example: a Unity bug routes the impl phase to `unity-dev` →
`["unity-classic", "unity-foundation", "codebase-understanding", "agentmemory-codebase-recall", "investigation"]`
(NOT `unity-dots-best-practices`). A DOTS feature routes to `unity-dots-dev` →
`["unity-dots-best-practices", "ecs-job-patterns", "burst-safety", "memory-safety", "codebase-understanding", "agentmemory-codebase-recall"]`.

### Per-agent skill map (registry-driven — see `.claude/skills/INDEX.md`)

| Agent | Primary skills | +bug | +parallel/refactor | DOTS extras? |
|-------|----------------|------|--------------------|--------------|
| `architect` | `architect`, `unity-foundation`, `codebase-understanding`, `agentmemory-codebase-recall` | — | `ownership-partitioning` | no |
| `unity-dots-dev` | `unity-dots-best-practices`, `ecs-job-patterns`, `burst-safety`, `memory-safety`, `codebase-understanding`, `agentmemory-codebase-recall` (`unity-dots` index is keyword-reachable, not forced) | `investigation` | `ownership-partitioning` | yes (DOTS lane) |
| `unity-dev` | `unity-classic`, `unity-foundation`, `codebase-understanding`, `agentmemory-codebase-recall` | `investigation` | `ownership-partitioning` | **no** |
| `tester` / `verifier` / `qa-tester` | `tester`, `qa-validation`, `verifier`, `codebase-understanding`, `agentmemory-codebase-recall` | — | — | **no** |
| `bug-investigation` | `investigation`, `codebase-understanding`, `agentmemory-codebase-recall` | +domain: Unity→`unity-classic`, DOTS→`unity-dots-best-practices`+`ecs-job-patterns`, Hybrid→both+`ownership-partitioning` | — | domain-gated |
| `data-tool` | `data-tool`, `editor-data-tools`, `codebase-understanding`, `agentmemory-codebase-recall` | — | — | **no** |
| `refactor-agent` | `codebase-understanding`, `ownership-partitioning`, `agentmemory-codebase-recall` | — | — | no |

The cap (`max_total_skills` = 7) drops the lowest-priority entry first. Required
intent skills are **must-keep** so the cap can't crowd them out: `investigation` on a
bug and `ownership-partitioning` on refactor/parallel always survive for the roles
that need them, alongside the full DOTS/Unity core. DOTS skills never reach
`unity-dev`, `tester`, `verifier`, `qa-tester`, or `data-tool` — enforced by a hard
guard in the router.

### Per-agent artifact map (mirrors orchestrate.py)

| Agent | Artifact | Schema |
|-------|----------|--------|
| `bug-investigation` | `root_cause.json` | `root_cause` |
| `refactor-agent` | `root_cause.json` (status + evidence reused) | `root_cause` |
| `system-mapper` | (none — informational, updates `repo-knowledge.md`) | — |
| `architect` | `approved_plan.json` (must `status="APPROVED"`) | `approved_plan` |
| `unity-dev` | `impl_result.json` (must `compilation="CLEAN"`) | `impl_result` |
| `data-tool` | `impl_result.json` (appends to changed_files) | `impl_result` |
| `verifier` | `verification_result.json` | `verification_result` |
| `tester` | `verification_result.json` (`method="tester"`) | `verification_result` |

### Architect-specific output

When the pipeline includes `architect` AND `parallel_allowed=true`, the
architect MUST also write `workspace/ownership.lock.json`. The gate for the
implementation phase will fail otherwise.

### Verifier / tester loop

If `verification_result.json.status == "FAIL"`:

- 1st FAIL → re-spawn unity-dev with the `fail_reason` and `regressions[]` in
  the prompt. Then re-spawn verifier.
- 2nd FAIL → escalate to `tester` (if not already), even if triage chose
  `verifier`. Re-spawn unity-dev with tester findings.
- 3rd FAIL → halt and ESCALATE_HUMAN. Print the entire FAIL chain.

`orchestrate.py finalize` returns exit code 4 on any FAIL. That is the
authoritative completion gate.

---

## STEP 4 — Finalize

```sh
python3 .claude/scripts/orchestrate.py finalize
```

Reads `verification_result.json`, computes the completion report, and exits:

- `0` → success
- `2` → gate violation (missing artifact)
- `4` → verification FAIL

On success, print the completion report exactly as the script outputs it. Do
not paraphrase. Do not add a markdown summary on top.

---

## STEP 5 — Commit & push (mandatory on PASS)

After `finalize` exits `0`, commit and push the run:

```sh
python3 .claude/scripts/orchestrate.py commit "<one-line task summary>"
```

Rules enforced by the script (do not reimplement them by hand):

- Only a run whose `verification_result.json.status == "PASS"` may commit. A
  missing/FAIL verification returns exit 2/4 — the run does **not** commit.
- `explore` intent commits nothing (triage-only run).
- Commits on the **current branch** only. Detached HEAD → exit 2 (checkout a
  branch first). The script never auto-creates branches and never force-pushes.
- Stages exactly: the `changed_files` from `impl_result.json` plus the
  persistent knowledge files (`repo-knowledge.md`, `ecs-registry.md`,
  `recent-changes.md`). Nothing else.
- If no remote is configured or `push` is rejected, the commit is retained
  locally and the gate still exits `0` (push failure is non-fatal, surfaced as
  a WARN). Use `--no-push` to commit without pushing.
- The repo committed is the resolved `PROJECT_ROOT` from STEP -1
  (`roots.py` resolution order: explicit arg → `AGENT_TEAM_PROJECT_ROOT` env →
  `project-config.json` → git toplevel — same resolution as `full_team.py`).

Print the `[commit]` output verbatim. Do **not** run a manual `git commit` /
`git push` — always go through this gate so the PASS-only and branch-safety
rules apply.

`--team` / `--worktrees` modes: the same rule applies — the teamlead (or the
worktree merge step) runs `orchestrate.py commit` only after `qa-tester`
posts `APPROVE`.

---

## Codex review (optional, deep depth only)

When `depth == "deep"` OR `intent == "critical"` is plan-derived:

- After `architect` writes `approved_plan.json`: run `/codex:review` against
  the plan. Blocker findings → architect re-issues plan.
- After `verifier` / `tester` writes `verification_result.json` and BEFORE
  `finalize`: run `/codex:review` against the diff. Blocker findings →
  re-spawn unity-dev.

Codex output goes in the completion report under `Codex review:`. If
`/codex:review` is unavailable: state `"Running without codex review"` once
and require tester (not verifier) regardless of triage choice.

---

---

## `/team --team` — Claude Agent Teams Mode

```
/team --team <task description>
/team --full <task description>      # deprecated alias — prints a deprecation notice, then behaves as --team
```

`/team --team` runs the task as a **Claude Agent Teams** team. Read this contract
literally and follow it — it is the behavior of the command:

```
Use Claude Agent Teams backend.
The current Claude Code session is the teamlead.
Create one teammate per role in config teamProfiles.full (from roots.py --json).
Do not use normal subagents.
Do not simulate roles.
Use Sonnet for all teammates.
Use shared task coordination.
Allow teammate-to-teammate communication when useful.
```

This is **not** the adaptive triage/orchestrate flow, **not** in-process one-shot
subagents, **not** markdown role-play, and **not** the manual tmux/worktree path
(that lives under `/team --worktrees`, a separate opt-in mode). `--team` uses the
harness-native Agent Teams primitives only.

### Step 0 — Availability check (FAIL FAST, no fallback)

Agent Teams requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

```sh
grep -q '"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"[[:space:]]*:[[:space:]]*"1"' ~/.claude/settings.json \
  && echo "agent-teams: ON" || echo "agent-teams: OFF"
```

If OFF (or the `TeamCreate` / `Agent(team_name=…)` primitives are unavailable in
this runtime), **STOP** and print exactly:

```
[BLOCK] /team --team requires Claude Agent Teams, which is not enabled.
Enable it:
  1. Add to ~/.claude/settings.json:
       { "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" },
         "preferences": { "tmuxSplitPanes": true } }
  2. Restart Claude Code.
  3. Re-run /team --team <task>.
Do NOT fall back to subagents, single-agent, or simulated roles.
```

Do not continue. Do not degrade. Do not fake a team.

If the invocation was `/team --full …`, first print:

```
[DEPRECATED] /team --full is an alias for /team --team. Prefer /team --team.
```

then proceed identically to `--team`.

### The teammates (from config `teamProfiles.full`, all Sonnet)

The roster is read from `teamProfiles.full` in the STEP -1 `roots.py --json`
output. Spawn exactly the roles it lists — no more, no fewer.

**Default profile for `projectType=unity`** (documented reference, still read
from config at runtime):

| Teammate | Model | Responsibility |
|----------|-------|----------------|
| `architect` | Sonnet | architecture analysis, flow design, ownership, planning, scope control |
| `unity-dots-dev` | Sonnet | Unity DOTS/ECS, Jobs, Burst, Entities, ECB, dependencies, performance |
| `unity-dev` | Sonnet | Unity UI, MonoBehaviour, gameplay, VContainer, Addressables, pooling, DOTween |
| `qa-tester` | Sonnet | testing, regression, reproduction, root-cause validation, final approval |

Other project types use their configured profile (e.g. `architect`,
`backend-dev`, `qa-tester`). For any role with no `.claude/agents/<role>.md`
definition: spawn `subagent_type: "claude"` (generic) and describe the role's
responsibility in the prompt.

Use the exact role names from the profile — no typos, no aliases
(e.g. never `architech`, `unity-dot-dev`, `QA`, or bare `tester` when the
profile says `qa-tester`).

### Execution protocol (teamlead = current session)

1. **Availability check** (Step 0). Fail fast if Agent Teams is off.
2. **Create the team:**
   ```
   TeamCreate({ team_name: "team-<slug>", description: "<task>", agent_type: "orchestrator" })
   ```
3. **Create the shared task list** — one task per role in `teamProfiles.full`,
   with real dependencies so QA cannot approve before the architect + all dev
   roles finish. Capture the returned task IDs. Example for the unity default
   profile (`architect`, `unity-dots-dev`, `unity-dev`, `qa-tester`):
   ```
   tA  = TaskCreate({ subject: "architect: analysis + ownership + plan" })
   tD  = TaskCreate({ subject: "unity-dots-dev: DOTS/ECS analysis + impl notes" })
   tU  = TaskCreate({ subject: "unity-dev: Unity classic (UI/Mono) analysis + impl plan" })
   tQ  = TaskCreate({ subject: "qa-tester: test matrix + regression + APPROVE/BLOCK verdict" })
   # devs blocked by architect; QA blocked by architect AND all devs:
   TaskUpdate({ taskId: tD, addBlockedBy: [tA] })
   TaskUpdate({ taskId: tU, addBlockedBy: [tA] })
   TaskUpdate({ taskId: tQ, addBlockedBy: [tA, tD, tU] })
   ```
   For other profiles, apply the same shape: architect first, dev roles blocked
   by architect, QA blocked by everything else.
4. **Spawn one teammate per profile role** with the Agent tool — `team_name`,
   `name`, `model: "sonnet"`, the matching `subagent_type` (or `"claude"` if no
   agent definition exists for the role), and a `prompt` that loads the role's
   skills.

   **Project context injection (mandatory).** Every teammate prompt MUST embed
   the resolved context from STEP -1, verbatim values, e.g.:
   ```
   PROJECT CONTEXT (resolved — do not re-derive):
   - project: <projectName>  (projectType: <projectType>)
   - PROJECT_ROOT: <PROJECT_ROOT>
   - UNITY_PROJECT_ROOT: <UNITY_PROJECT_ROOT or "none">
   - current branch: <git branch>   default branch: <defaultBranch>
   - workspace dir: <workspaceDir>   reports dir: <reportsDir>
   - your ownership scope / allowed write paths: <from architect's ownership map,
     or the role's default lane>
   ```

   **Skill loading — same registry/router as adaptive mode, Read-first.**
   Per-role skill files come from the skill router so `--team` and adaptive `/team`
   stay in sync. Get the exact list for a role:
   ```sh
   python3 .claude/scripts/route_skills.py --agent <role> --domain <DOTS|Unity|Hybrid|Ambiguous> --intent <intent> --task "<task>"
   ```
   Default `--team` per-role skills (derived from `registry.json`; verify with the
   command above for the actual domain/intent):
   ```
   architect:      architect  unity-foundation  codebase-understanding  agentmemory-codebase-recall
   unity-dots-dev: unity-dots-best-practices  ecs-job-patterns  burst-safety  memory-safety  codebase-understanding  agentmemory-codebase-recall
   unity-dev:      unity-classic  unity-foundation  codebase-understanding  agentmemory-codebase-recall
   qa-tester:      tester  qa-validation  verifier  codebase-understanding  agentmemory-codebase-recall
   ```

   Use BOTH, in this order (tested): `@`-import the skill files at the start of the
   prompt (best-effort), AND an explicit Read-first STEP 0 block. `@`-import
   expansion into a teammate's context is **NOT reliable** (~50% of spawns). The
   explicit Read instruction is the guarantee. Never rely on `@`-import alone or on
   `Reference:` footnotes inside `agents/*.md`.

   **Every teammate prompt MUST embed this verbatim STEP 0 block** (substitute the
   role's skill files):
   ```
   STEP 0 — Required skill loading

   Read the assigned skill files before analysis or editing:
     <one .claude/skills/<m>/SKILL.md path per routed module>

   After reading, report:
   - loaded skill names
   - 3 concrete rules from each required skill
   - any missing skill as [BLOCKED: MISSING SKILL]
   ```

   These are persistent Agent Teams teammates (addressable via `SendMessage`), NOT
   one-shot subagents. Each prompt = `<@-imports>\n\n<STEP 0 block>\n\n<PROJECT
   CONTEXT block>\n\n<role prompt>`. Spawn examples below show the **unity
   default profile** — substitute the actual roles from `teamProfiles.full`:
   ```
   Agent({ team_name: "team-<slug>", name: "architect",      subagent_type: "architect",      model: "sonnet",
           prompt: "@.claude/skills/architect/SKILL.md @.claude/skills/unity-foundation/SKILL.md @.claude/skills/codebase-understanding/SKILL.md @.claude/skills/agentmemory-codebase-recall/SKILL.md\n\nSTEP 0 — Required skill loading: Read those skill files with the Read tool before any work. Then report loaded skill names, 3 concrete rules from each, and any missing skill as [BLOCKED: MISSING SKILL].\n\n<architect role prompt>" })
   Agent({ team_name: "team-<slug>", name: "unity-dots-dev", subagent_type: "unity-dots-dev", model: "sonnet",
           prompt: "@.claude/skills/unity-dots-best-practices/SKILL.md @.claude/skills/ecs-job-patterns/SKILL.md @.claude/skills/burst-safety/SKILL.md @.claude/skills/memory-safety/SKILL.md @.claude/skills/codebase-understanding/SKILL.md @.claude/skills/agentmemory-codebase-recall/SKILL.md\n\nSTEP 0 — Required skill loading: Read those skill files with the Read tool before any work. Then report loaded skill names, 3 concrete rules from each, and any missing skill as [BLOCKED: MISSING SKILL].\n\n<unity-dots-dev role prompt>" })
   Agent({ team_name: "team-<slug>", name: "unity-dev",      subagent_type: "unity-dev",      model: "sonnet",
           prompt: "@.claude/skills/unity-classic/SKILL.md @.claude/skills/unity-foundation/SKILL.md @.claude/skills/codebase-understanding/SKILL.md @.claude/skills/agentmemory-codebase-recall/SKILL.md\n\nSTEP 0 — Required skill loading: Read those skill files with the Read tool before any work. Then report loaded skill names, 3 concrete rules from each, and any missing skill as [BLOCKED: MISSING SKILL].\n\n<unity-dev role prompt>" })
   Agent({ team_name: "team-<slug>", name: "qa-tester",      subagent_type: "qa-tester",      model: "sonnet",
           prompt: "@.claude/skills/tester/SKILL.md @.claude/skills/qa-validation/SKILL.md @.claude/skills/verifier/SKILL.md @.claude/skills/codebase-understanding/SKILL.md @.claude/skills/agentmemory-codebase-recall/SKILL.md\n\nSTEP 0 — Required skill loading: Read those skill files with the Read tool before any work. Then report loaded skill names, 3 concrete rules from each, and any missing skill as [BLOCKED: MISSING SKILL].\n\n<qa-tester role prompt>" })
   ```
5. **architect analyzes first** → publishes ownership map + execution plan +
   acceptance criteria to the shared task / via `SendMessage` to the team.
6. **Dev roles work according to the architect's ownership.**
   Teammate-to-teammate `SendMessage` is allowed (e.g. dev ↔ dev boundary, dev → qa).
7. **qa-tester reviews** outputs + validation evidence and posts `APPROVE` or `BLOCK`.
8. **Teamlead synthesizes** the final result from teammate outputs.
9. **Completion gate:** do NOT mark the task complete if qa-tester has not posted
   `APPROVE` or if validation evidence is missing. On block, report the blocker
   with a clear reason.
10. **Shutdown** the team when done (SendMessage `shutdown_request` to each teammate).

### Inspecting teammates

With `"preferences": { "tmuxSplitPanes": true }` set, each teammate appears in its
own tmux pane. The teamlead should surface, when the runtime provides them:
- the team name (`team-<slug>`),
- any tmux attach hint the runtime prints,
- live status via `TaskList` (shared task list) and teammate idle/active notifications.

Messages from teammates are delivered to the teamlead automatically as new turns —
do not poll an inbox; coordinate with `SendMessage` + `TaskUpdate`.

### Role prompts (unity default profile)

The four role prompts below belong to the documented `projectType=unity`
default profile. For other profiles, reuse the `architect` and `qa-tester`
prompts as-is and write an analogous prompt for each dev role (e.g.
`backend-dev`, `web-dev`, `coder`) describing its lane; roles without a
`.claude/agents/<role>.md` are spawned as generic `claude` teammates with the
role described in the prompt.

### Role prompt — architect

```
You are the architect teammate in Claude Agent Teams.

Responsibilities:
- Analyze the current /team flow.
- Identify V1/V2 conflicts.
- Define ownership and execution order.
- Prevent scope drift.
- Ensure implementation follows the existing project architecture.
- For Unity tasks, require project-first analysis before coding.
- For bugfixes, require root-cause analysis before implementation.
- For refactors, preserve behavior and reduce duplication.
- For implementation, avoid creating parallel architecture or unnecessary abstraction.

Output:
- architecture findings
- ownership map
- execution plan
- risks
- acceptance criteria
```

### Role prompt — unity-dots-dev

```
You are the unity-dots-dev teammate in Claude Agent Teams.

Responsibilities:
- Handle Unity DOTS/ECS, Entities, Systems, Jobs, Burst, ECB, dependencies, physics, and performance.
- For bugfixes, find the core root cause instead of applying temporary patches.
- Implementation must follow existing project patterns and avoid extra logic.

Mandatory DOTS checks (apply every task):
- Job dependency: scheduled JobHandle is assigned back to state.Dependency (dropped handle = race).
- ECB writer mode: parallel job → EntityCommandBuffer.ParallelWriter + sortKey; single-thread → plain ECB.
- ECB playback: correct Begin/End system-group singleton, played back once.
- Enableable components: prefer IEnableableComponent toggling over structural add/remove in hot loops.
- Update order: [UpdateBefore]/[UpdateAfter]/group correct — reader must not run before its writer.
- ComponentLookup/BufferLookup: [ReadOnly] where not written; .Update(ref state) each tick.
- Structural change in a scheduled job → ECB, never EntityManager directly.
- NativeContainer lifetime: disposed / TempJob / DeallocateOnJobCompletion — no leaks.

Output:
- DOTS/ECS analysis
- risk list
- implementation notes
- validation checklist (dependency assigned, ECB writer correct, update order, no leak)
```

### Role prompt — unity-dev

```
You are the unity-dev teammate in Claude Agent Teams.

Responsibilities:
- Handle Unity UI, MonoBehaviour, gameplay logic, VContainer, Addressables, pooling, DOTween, and editor tooling when relevant.
- Inspect existing code patterns before editing.
- For bugfixes, trace lifecycle/data flow and fix the root cause.
- For refactors, preserve behavior, reduce duplication, and avoid unnecessary abstraction.
- For implementation, integrate with existing architecture and do not create duplicate services/controllers/models.

Check:
- Awake/OnEnable/Start/OnDisable lifecycle
- event subscribe/unsubscribe
- GC allocation
- DOTween kill/reuse
- pooling lifecycle
- UI binding duplication
- VContainer injection timing
- async cancellation
- Addressables load/release
- per-frame expensive calls

Output:
- Unity classic analysis
- implementation plan
- changed files summary
- validation steps
```

### Role prompt — qa-tester

```
You are the qa-tester teammate in Claude Agent Teams.

Responsibilities:
- Build a test matrix and regression checklist.
- Verify that the root cause is actually fixed.
- Verify that implementation follows architect ownership.
- Verify no scope drift, no duplicate logic, and no temporary patch.
- For Unity, define validation steps even if the Unity Editor cannot be run.
- For DOTS/ECS, check update order, dependencies, structural changes, allocations, and race risks.
- Block final completion if validation is missing.

Output:
- test matrix
- regression checklist
- QA verdict: APPROVE / BLOCK
- unresolved risks
```

### Quality bars (every teammate, every task)

**Bugfix:** understand symptom → trace data flow / lifecycle / update order →
identify root cause → explain why → fix the correct location → keep diff small →
validate. Forbidden: null check without proving root cause; delay/timer workaround
without proving a lifecycle/ordering issue; suppressing an exception without
understanding the cause; large rewrite when a focused fix suffices.

**Refactor:** preserve behavior; reduce duplication; follow existing architecture;
avoid unnecessary abstraction; keep diff reviewable; provide validation.

**Implementation:** inspect existing project patterns first; follow current
architecture; no parallel architecture; no duplicate models/services/controllers;
consistent naming/style; add only necessary logic; document assumptions.

### Forbidden in `/team --team`

- Simulating a team with markdown-only role descriptions.
- Running as a single agent while pretending teammates exist.
- Normal one-shot subagents.
- Legacy V1 fixed-parallel subagent flow.
- Silent fallback to single-agent or degraded mode.
- Manual tmux/worktree orchestration (that is `/team --worktrees`, a separate mode).
- Marking complete without qa-tester `APPROVE` + validation evidence.

---

## `/team --worktrees` — Manual tmux + git-worktree team (advanced, opt-in)

Separate, explicit mode for isolated parallel branches. NOT `--team`, NOT `--full`.
Uses `full_team.py` to create one real `claude` CLI session (Sonnet) per profile
role in tmux windows, each in its own git worktree+branch, with QA-gated merge.
Use only when you explicitly want branch isolation.

Paths and branches come from the STEP -1 resolution:
- Worktrees are created under `roots.worktree_root()` (the `worktreeRoot` field
  of `roots.py --json`) — never a hardcoded sibling path.
- The base branch for every worktree branch and the merge target is the config
  `defaultBranch` — never an assumed branch name.

```sh
python3 .claude/scripts/full_team.py setup "<task>"      # teammates(standby) → validate → worktrees → assign
# attach to the tmux session name printed by `setup` (derived from projectName)
python3 .claude/scripts/full_team.py status "<task>"
# merge only after <reportsDir>/team/<slug>/qa-report.md = APPROVE, then:
python3 .claude/scripts/full_team.py teardown "<task>"
```

Prerequisites (hard, fail-fast): `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, `tmux`,
`git` worktree support, `claude` CLI. Same roles (from `teamProfiles.full`) and
quality bars as `--team`.

---

## What this command will NOT do

- Spawn a fixed 4-agent team
- Spawn nested subagents inside agents (use skill packs instead)
- Spawn `data-tool` for tasks that do not produce tooling output
- Spawn `tester` for small/medium tasks unless confidence < 0.7
- Spawn agents in parallel before triage emits a partition
- Touch tmux unless `--worktrees` is explicitly requested AND
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set in user settings
- Mark a run complete while `verification_result.json.status != "PASS"`
- Skip schema validation on any artifact

---

## Worked examples

### Example A — small bug

```
/team bug "Damage popup shows 0 when hit lands on enemy with shield"
```

- Triage: complexity=`small`, intent=`bug`, domain=`DOTS`,
  confidence=`0.82`, recommended_pipeline=`[bug-investigation, unity-dev, verifier]`
- Phases: `[bug-investigation] → [unity-dev] → [verifier]`
- Artifacts gated: `root_cause.json` → `impl_result.json` → `verification_result.json`
- No architect. No data-tool. No tmux. ~30% tokens of old `--bug` flow.

### Example B — medium feature

```
/team feature "Add stamina component with regen and sprint cost"
```

- Triage: complexity=`medium`, intent=`feature`, domain=`DOTS`,
  confidence=`0.85`, recommended_pipeline=`[architect, unity-dev, verifier]`,
  skill_packs=`[ecs-job-patterns, burst-safety, memory-safety]`
- Phases: `[architect] → [unity-dev] → [verifier]` (sequential — no second
  writer, so no parallel)
- No tester unless depth=deep.

### Example C — large refactor

```
/team refactor deep "Extract spawn logic into shared SpawnerSystem across zones and dungeons"
```

- Triage: complexity=`large`, intent=`refactor`, domain=`DOTS`,
  confidence=`0.88`,
  recommended_pipeline=`[refactor-agent, architect, unity-dev, tester]`,
  verification_strategy=`stepgated`
- Architect writes `ownership.lock.json` partitioning runtime (`unity-dev`)
  from any tooling touched (`data-tool` if added).
- unity-dev executes migration step-by-step; tester runs behavior-preservation
  tests between steps. FAIL on any step → rollback per `approved_plan.json.migration_plan[N].rollback`.
- Codex review pre-impl AND pre-completion because `depth=deep`.

### Example D — explore

```
/team explore "How does the dungeon POI spawner interact with EnemyTrackerSystem?"
```

- Triage runs full CRG, writes `triage.json` with `intent=explore`.
- `orchestrate.py plan` produces `pipeline.json.phases=[]`.
- `orchestrate.py finalize` reports completion with `risk_level=LOW`.
- The investigation findings are appended to `repo-knowledge.md` by the triage
  agent before exiting.

---

## Anti-patterns (will fail a gate)

- Spawning `architect` for a `tiny` task (`pipeline.json` does not list it)
- Spawning `unity-dev` before `approved_plan.json` exists (when plan requires it)
- Editing files outside `ownership.lock.json` partition
- Returning `verification_result.json` with `status="PASS"` but `regressions[]` non-empty
- Skipping the validate step on any artifact
- Calling `tmux split-window` from this command
- Using "I think it's fine" as a substitute for `orchestrate.py finalize`

---

## Reference

- Skill packs are documented under `.claude/skills/*/SKILL.md`
- Phase gate rules: `.claude/rules/mcp-phase-gates.md`
- Ownership enforcement: `.claude/rules/ownership-boundaries.md`
- Escalation routing: `.claude/rules/escalation-policy.md`
- Migration from v1 fixed-4 flow: `MIGRATION.md`
