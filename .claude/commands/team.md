---
description: Adaptive Unity DOTS agent pipeline. Triage classifies the task; orchestrate.py derives the minimum viable agent composition; each phase is artifact-gated by Python, not by markdown promises. Use --full for real multi-agent teams with tmux + git worktrees.
argument-hint: "[--full] <intent: bug | feature | refactor | explore> [depth: quick | normal | deep] <task description>"
---

# `/team` — Adaptive Unity DOTS Pipeline

```
/team <intent> [depth] <task description>
/team --full <task description>

intent  ∈ { bug, feature, refactor, explore }
depth   ∈ { quick, normal, deep }   default: normal
```

Two modes:

| Mode | Command | Behavior |
|------|---------|----------|
| **Adaptive** (default) | `/team <intent> [depth] <task>` | Triage → minimum agents → artifact-gated |
| **Full Team** | `/team --full <task>` | Real 4-agent team with tmux + git worktrees |

This command **always** runs `triage` first, **always** calls
`orchestrate.py plan` to derive the pipeline, and **never** spawns agents that
the plan does not list. Every phase boundary is a Python gate; if the gate
exits non-zero, you halt — no exceptions, no markdown promises.

**Exception:** `/team --full` bypasses adaptive triage and always spawns exactly
4 agents in separate tmux windows with separate git worktrees. See the
`--full` section below.

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

## STEP 0 — Bootstrap (informational, never blocks)

```sh
python .claude/scripts/orchestrate.py preflight
python .claude/scripts/orchestrate.py reset
```

`preflight` reports env, MCP, tmux state. `reset` clears session artifacts:
`triage.json`, `pipeline.json`, `root_cause.json`, `approved_plan.json`,
`impl_result.json`, `verification_result.json`, `ownership.lock.json`,
`escalation-log.md`. Persistent files (`repo-knowledge.md`,
`ecs-registry.md`, `recent-changes.md`) are preserved.

---

## STEP 1 — Triage (ALWAYS, exactly once)

Spawn one `triage` agent. Wait for its artifact. No exceptions.

```
Agent({
  subagent_type: "triage",
  description: "Adaptive pipeline triage",
  prompt: "@.claude/agents/triage.md @.claude/skills/triage/SKILL.md @.claude/rules/GRAPH_FIRST.md @.claude/rules/api-fingerprinting-system.md @.claude/rules/domain-scoring-engine.md\n\nIntent: <INTENT>\nDepth: <DEPTH>\nTask: <TASK>\n\nProduce workspace/triage.json via .claude/scripts/triage.py and validate it. Return only the rationale paragraph and the artifact path."
})
```

After triage returns, validate (script does this too but be explicit):

```sh
python .claude/scripts/orchestrate.py validate workspace/triage.json triage
```

If validation fails → halt and report the error. Do not spawn anything else.

---

## STEP 2 — Plan (deterministic mapping)

```sh
python .claude/scripts/orchestrate.py plan workspace/triage.json
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
   python .claude/scripts/orchestrate.py gate <phase-id>
   ```

   Non-zero exit means a prior phase's artifact is missing, malformed, or has
   the wrong status. **Halt and surface the gate output** — do not patch around
   it, do not retry the spawn, do not "just try anyway".

2. **Spawn** the agents listed in `phase.agents`:
   - `mode == "sequential"` → one agent at a time, wait for each artifact
   - `mode == "parallel"` → spawn all in one message
   - Each agent prompt MUST include the skill packs from
     `pipeline.json.skill_packs` and its required artifact from
     `pipeline.json.artifacts_required`
   - Each agent prompt MUST instruct it to validate its artifact before
     returning:
     `python .claude/scripts/orchestrate.py validate workspace/<artifact> <schema>`

3. **After all agents in the phase finish**, gate again before the next phase.

### Phase template

```
Agent({
  subagent_type: "<agent name from phase.agents>",
  description: "<role> — phase <id>",
  prompt: "@.claude/agents/<agent>.md @.claude/skills/unity-dots-best-practices/SKILL.md [+ skill_packs from pipeline.json]\n\nIntent: <INTENT>\nTask: <TASK>\nRead workspace/triage.json and any prior artifacts listed in pipeline.json.artifacts_required for upstream agents.\n\nProduce workspace/<your-artifact>.json. Validate before returning:\n  python .claude/scripts/orchestrate.py validate workspace/<your-artifact>.json <schema-name>\n\nDo not edit files outside your ownership partition (.claude/scripts/orchestrate.py ownership-check <agent> <files>)."
})
```

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
python .claude/scripts/orchestrate.py finalize
```

Reads `verification_result.json`, computes the completion report, and exits:

- `0` → success
- `2` → gate violation (missing artifact)
- `4` → verification FAIL

On success, print the completion report exactly as the script outputs it. Do
not paraphrase. Do not add a markdown summary on top.

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

## `/team --full` — Real Multi-Agent Team Mode

```
/team --full <task description>
```

This mode creates a **real parallel agent team** with:
- 4 separate git worktrees (one per agent)
- 4 tmux windows (one per agent)
- 4 Claude Code instances with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- Strict file ownership per role
- QA gate before any merge

### Prerequisites (HARD — no fallback)

1. `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` set in `~/.claude/settings.json`
2. `tmux` installed and available
3. `git` with worktree support
4. `claude` CLI available in PATH

If ANY prerequisite is missing, `/team --full` **fails fast** and reports what's
missing. It does NOT fall back to internal subagents. "Full" means real
infrastructure or nothing.

### Agents (exactly 4, always)

| Agent | Role | Domain |
|-------|------|--------|
| `architect` | System architect / task planner | Planning, ownership, merge order |
| `unity-dev` | Senior Unity developer (non-DOTS) | MonoBehaviour, SO, UI, Addressables, VContainer, DOTween |
| `unity-dot-dev` | Senior DOTS/ECS developer | Entities, ISystem, Jobs, Burst, ECS components, physics |
| `qa-tester` | QA tester / reviewer | Diff review, compile check, behavior/performance risk |

### Execution Flow (Teammates First, Then Assign)

```
/team --full <task>
    │
    ▼ PHASE 1: SPAWN TEAMMATES FIRST
    │
    ├─ Step 1.1: Parse task → generate slug
    │
    ├─ Step 1.2: Environment check (fail fast if missing)
    │            tmux, git, claude, CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
    │            ↳ ABORT immediately if any missing. No fallback.
    │
    ├─ Step 1.3: Create tmux session with 4 windows
    │            unity-agent-team-<slug>:architect
    │            unity-agent-team-<slug>:unity-dev
    │            unity-agent-team-<slug>:unity-dot-dev
    │            unity-agent-team-<slug>:qa-tester
    │
    ├─ Step 1.4: Launch Claude in STANDBY in each window
    │            Each teammate gets a bootstrap prompt:
    │            "You are <role>. Wait for assignment. Do not act."
    │
    ├─ Step 1.5: VALIDATE teammate sessions (MANDATORY)
    │            - Verify exactly 4 tmux windows exist
    │            - Verify each role name exists as a window
    │            - Verify panes are present
    │            - Check for running claude processes
    │            - Print: tmux ls, list-windows, list-panes -a, ps aux | grep claude
    │            ↳ ABORT if validation fails. No worktrees. No analysis.
    │
    ▼ PHASE 2: ANALYZE + ASSIGN (only after Phase 1 passes)
    │
    ├─ Step 2.1: Detect base branch
    │
    ├─ Step 2.2: Working tree dirty check
    │
    ├─ Step 2.3: Create 4 git worktrees + branches
    │            ../worktrees/<slug>/architect    → agent/architect/<slug>
    │            ../worktrees/<slug>/unity-dev    → agent/unity-dev/<slug>
    │            ../worktrees/<slug>/unity-dot-dev → agent/unity-dot-dev/<slug>
    │            ../worktrees/<slug>/qa-tester    → agent/qa-tester/<slug>
    │
    ├─ Step 2.4: Create report + message directories
    │
    ├─ Step 2.5: Generate per-agent assignment prompts
    │
    ├─ Step 2.6: Send assignments to running teammate sessions
    │            Each teammate: cd into worktree → receive full role prompt
    │
    ├─ Step 2.7: Full setup validation
    │            Teammates + worktrees + branches all verified
    │
    └─ Step 2.8: Print summary with attach/status/teardown commands
```

**Critical ordering rule:** Worktrees do NOT exist before teammate sessions.
Task analysis does NOT happen before teammate sessions. No exceptions.

### How to invoke

When the user runs `/team --full <task>`, execute:

```sh
# Full two-phase setup (teammates first, then assign)
python .claude/scripts/full_team.py setup "<task>"
```

Or run the two phases separately:

```sh
# Phase 1 only: spawn teammates in standby
python .claude/scripts/full_team.py spawn-teammates "<task>"

# Phase 2 only: create worktrees + send assignments (teammates must be running)
python .claude/scripts/full_team.py assign "<task>"
```

**If the script exits non-zero**, report the exact error and stop. Do NOT
attempt to work around it with internal subagents.

**If the script exits 0**, read and print the output. The team is running.
Provide the user with:
- tmux attach command
- Status check command
- Teardown command

### Post-launch workflow

After all 4 agents have received their assignments:

1. **Architect** creates the plan first (`reports/team/<slug>/architect-plan.md`)
2. **unity-dev** and **unity-dot-dev** implement their areas (may run in parallel)
3. **qa-tester** reviews all branches after implementation
4. **Integrator** (you, the main session) merges ONLY after QA approves

### Integration (after QA approval)

When `reports/team/<slug>/qa-report.md` exists and says APPROVE:

```sh
# Check merge readiness
python .claude/scripts/full_team.py status "<task>"

# Merge in safe order (architect first, then devs, verify after each)
git merge agent/architect/<slug>
git merge agent/unity-dev/<slug>
git merge agent/unity-dot-dev/<slug>

# Final verification
python .claude/scripts/full_team.py verify "<task>"
```

Do NOT merge if QA report says REJECT. Fix issues first.

### Reports

Each agent writes to `reports/team/<slug>/`:

| File | Author |
|------|--------|
| `architect.md` | architect |
| `architect-plan.md` | architect |
| `unity-dev.md` | unity-dev |
| `unity-dot-dev.md` | unity-dot-dev |
| `qa-tester.md` | qa-tester |
| `qa-report.md` | qa-tester |
| `final-integration-report.md` | integrator (main session) |

### Teardown

```sh
python .claude/scripts/full_team.py teardown "<task>"
```

Removes worktrees, kills tmux session, deletes branches.

### Management commands

```sh
# Phase 1 only: spawn teammates in standby
python .claude/scripts/full_team.py spawn-teammates "<task>"

# Phase 2 only: assign work to running teammates
python .claude/scripts/full_team.py assign "<task>"

# Check status of all agents
python .claude/scripts/full_team.py status "<task>"

# Re-verify infrastructure (teammates + worktrees)
python .claude/scripts/full_team.py verify "<task>"

# Generate new prompts (e.g., after architect updates ownership)
python .claude/scripts/full_team.py prompts "<task>"
```

### Strict Rules

1. **Teammates first.** tmux sessions with Claude in standby MUST be created
   and validated BEFORE any task analysis, worktree creation, or implementation
2. `/team --full` MUST create real git worktrees — not simulated
3. `/team --full` MUST create real tmux windows — not internal subagents
4. Each agent MUST work in its own worktree only
5. Each agent MUST have `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
6. No merge without QA approval
7. Fail fast on any missing prerequisite — no partial setup, no fallback
8. `validate_teammate_sessions_first()` MUST pass before Phase 2 begins
9. Post-setup validation MUST confirm exactly 4 worktrees + 4 tmux windows
10. Print `tmux ls`, `tmux list-windows`, `tmux list-panes -a`,
    `ps aux | grep claude`, `git worktree list` as proof
11. If teammate validation fails: ABORT. Do NOT create worktrees.
    Do NOT analyze the task. Do NOT fall back to internal subagents.

---

## What this command will NOT do

- Spawn a fixed 4-agent team
- Spawn nested subagents inside agents (use skill packs instead)
- Spawn `data-tool` for tasks that do not produce tooling output
- Spawn `tester` for small/medium tasks unless confidence < 0.7
- Spawn agents in parallel before triage emits a partition
- Touch tmux unless `--teams` is explicitly requested AND
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
