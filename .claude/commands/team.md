---
description: Boot the Unity DOTS agent team. Pass a task mode flag to select the right agent composition and sequencing for the work.
argument-hint: "<task> [--bug | --feature | --refactor] [--fast | --full] [--teams]"
---

# `/team` — Unity DOTS Agent Team

**Task mode flags** — pick the one that matches the work. Wrong flag = wrong agent composition = slower decisions.

| Flag | Task type | First agent | Agent composition |
|------|-----------|-------------|-------------------|
| `--bug` | Bug fix | `bug-investigation` (sequential) | investigation → unity-dev + tester |
| `--feature` | New feature | `system-mapper` (sequential) | CRG map → architect → unity-dev + tester (`--with-tooling` adds data-tool) |
| `--refactor` | Refactor / restructure | `refactor-agent` (sequential) | blast-radius → architect → unity-dev + tester |
| `--fast-fix` | 1-3 line fix | unity-dev directly | unity-dev + tester, scope-limited |
| *(none)* | General / unknown | `architect` (parallel) | all 4 in parallel (same as `--full`) |

**Agent naming:** `system-mapper` = reads existing ECS systems (CRG). `architect` = designs new ECS systems. Never swap these.

**Size flags** (only apply to general mode — task modes set their own composition):
- `--fast` — architect + unity-dev only.
- `--full` — all four agents.

**Execution backends:**
- *Default:* standard `Agent` tool. Works everywhere.
- `--teams` — experimental tmux-pane backend. Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `~/.claude/settings.json`.

---

## STEP 1 — Non-blocking preflight (informational only)

Run once. Agents proceed regardless of result.

```sh
python .claude/scripts/preflight.py
```

Reports `agent-team-mode`, `tmux`, `mcp:ai-game-developer`, `mcp:agentmemory`. Note any missing capability and continue.

---

## STEP 2 — Route by task mode

Read the flags, then jump to the matching section below.

---

### Mode: `--bug` (Bug fix)

```
Investigation-first. Root cause proven before any code changes.

Phase 1 (sequential — WAIT for result):
  bug-investigation → root cause + evidence + safe fix strategy

Phase 2 (parallel — single message):
  unity-dev  → implements the fix strategy exactly
  tester     → prepares regression test from evidence chain, waits for fix signal

Phase 3 (sequential — WAIT):
  tester verifies fix (must fail-before / pass-after)
  Sign off or loop back to Phase 2
```

**Phase 1 — Spawn and wait:**
```
Agent({
  subagent_type: "bug-investigation",
  description: "Root cause investigation",
  prompt: "@.claude/skills/codebase-understanding/SKILL.md @.claude/rules/GRAPH_FIRST.md\n\nBug: $ARGUMENTS\n\nTrace root cause using code-review-graph:\n1. Define symptom precisely — what state is wrong, when, under what condition.\n2. trace_execution_flow from symptom to entry point.\n3. Identify writers and readers of the mutated state.\n4. get_impact_radius — what else could be affected by a fix?\n5. Inspect only systems identified by graph evidence.\n\nDeliver:\n- Root cause with evidence chain\n- Impacted systems\n- Safe fix strategy (minimal blast radius, behavior-preserving)\n- Regression test guidance (what to assert, under what condition)"
})
```

**Read the output fully. Then Phase 2 — spawn both in a single message, embedding `<INVESTIGATION_OUTPUT>`:**

```
Agent({
  subagent_type: "unity-dev",
  description: "Implement bug fix",
  prompt: "@.claude/skills/unity-dev/SKILL.md @.claude/skills/unity-dots-best-practices/SKILL.md\n\nBug: $ARGUMENTS\n\nInvestigation findings:\n<INVESTIGATION_OUTPUT>\n\nFix only the identified root cause — no refactor. Minimal change, maximum precision. All C# edits via mcp__ai-game-developer__script-update-or-create.\n\nBefore signaling tester:\n1. Complete the ECS Safety Checklist in your SKILL.md.\n2. Run mcp__ai-game-developer__console-get-logs — confirm ZERO compile errors.\nIf compilation fails: fix it before signaling. Never signal tester with broken compilation.\n\nOnly after both: SendMessage to tester: 'Fix applied. Compilation: CLEAN. Systems changed: <list>.'"
})

Agent({
  subagent_type: "tester",
  description: "Regression test for bug fix",
  prompt: "@.claude/skills/tester/SKILL.md @.claude/skills/qa-validation/SKILL.md\n\nBug: $ARGUMENTS\n\nInvestigation findings:\n<INVESTIGATION_OUTPUT>\n\nBASELINE FIRST: Run the regression test NOW in the pre-fix state. Record 'Baseline: FAIL'. If the test passes pre-fix — the assertion is wrong. Stop and report to orchestrator.\n\nThen wait for unity-dev's 'Fix applied. Compilation: CLEAN' message. Run same test. Report: Baseline result + post-fix result + adjacent regression check. No sign-off without both evidence entries."
})
```

---

### Mode: `--feature` (New feature)

```
Architecture-first. Existing system mapped before design starts.
data-tool is opt-in: add --with-tooling if the feature needs new editor tooling.

Phase 1 (sequential — WAIT for result):
  system-mapper → maps existing ECS systems, boundaries, extension points
  NOTE: system-mapper ≠ architect. system-mapper READS. architect DESIGNS.

Phase 2 (sequential — WAIT for result):
  architect → designs the feature extension from the map

Phase 3 (parallel — single message):
  unity-dev   → implements from design + code-tracer for extension points
  tester      → prepares test matrix from acceptance criteria
  data-tool   → ONLY if --with-tooling flag present
```

**Phase 1 — Map existing system (system-mapper, not architect):**
```
Agent({
  subagent_type: "system-mapper",
  description: "Map existing ECS systems for feature area",
  prompt: "@.claude/skills/codebase-understanding/SKILL.md @.claude/rules/GRAPH_FIRST.md\n\nFeature: $ARGUMENTS\n\nMap what already exists — do not suggest a design.\n1. get_architecture_overview — full system map.\n2. trace_execution_flow — how does the closest existing feature flow?\n3. identify_extension_points — where does new code attach without parallel architecture?\n4. map_dependency_graph — what would this feature depend on?\n\nDeliver: system map, execution path, extension points (file:line), dependencies, infrastructure gaps."
})
```

**Read output. Phase 2 — Architect designs the extension:**
```
Agent({
  subagent_type: "architect",
  description: "Design feature extension",
  prompt: "@.claude/skills/architect/SKILL.md @.claude/docs/architecture.md @.claude/skills/unity-dots-best-practices/SKILL.md\n\nFeature: $ARGUMENTS\n\nExisting system map:\n<ARCHITECTURE_AGENT_OUTPUT>\n\nDesign the feature extension. Work from the existing extension points — do not redesign existing systems. Deliver the full handoff: scope, ECS data model, system map, update order, baker plan, performance constraints, acceptance criteria, open risks, implementation task list for unity-dev / data-tool / tester."
})
```

**Read output. Phase 3 — spawn all three in a single message, embedding `<ARCHITECT_OUTPUT>`:**
```
Agent({
  subagent_type: "unity-dev",
  description: "Implement feature",
  prompt: "@.claude/skills/unity-dev/SKILL.md @.claude/docs/architecture.md @.claude/skills/unity-dots-best-practices/SKILL.md\n\nFeature: $ARGUMENTS\n\nArchitect design:\n<ARCHITECT_OUTPUT>\n\nBefore implementing: spawn `code-tracer` once to confirm extension points and existing patterns (replaces both codebase-reader and feature-dev-agent — one call, not two). Implement strictly from the design. All C# edits via mcp__ai-game-developer__script-update-or-create. Complete ECS Safety Checklist before signaling tester. Surface any design deviation immediately to architect."
})

# --with-tooling only:
Agent({
  subagent_type: "data-tool",
  description: "Feature tooling",
  prompt: "@.claude/skills/data-tool/SKILL.md @.claude/skills/editor-data-tools/SKILL.md\n\nFeature: $ARGUMENTS\n\nArchitect design:\n<ARCHITECT_OUTPUT>\n\nBefore building tooling: spawn `code-tracer` to map real component state. Build inspectors, validators, diagnostics anchored in the architect's data model. Do NOT silently change runtime behavior."
})

Agent({
  subagent_type: "tester",
  description: "Feature validation",
  prompt: "@.claude/skills/tester/SKILL.md @.claude/skills/qa-validation/SKILL.md\n\nFeature: $ARGUMENTS\n\nArchitect design:\n<ARCHITECT_OUTPUT>\n\nDerive test matrix from acceptance criteria above. Cover correctness, scale, determinism, regression. When a test fails: spawn `bug-investigation` to trace root cause — return fix strategy to unity-dev. Block sign-off until all acceptance criteria pass with evidence."
})
```

---

### Mode: `--refactor` (Refactor / restructure)

```
Blast-radius-first. Full impact known before a single line changes.

Phase 1 (sequential — WAIT for result):
  refactor-agent → blast radius, dependency map, migration plan, rollback strategy

Phase 2 (sequential — WAIT for result):
  architect → approves or rejects migration plan; resolves any design conflicts

Phase 3 (parallel — single message):
  unity-dev   → executes migration plan step by step
  tester      → validates behavior is preserved after each step
```

**Phase 1 — Map blast radius:**
```
Agent({
  subagent_type: "refactor-agent",
  description: "Blast radius and migration plan",
  prompt: "@.claude/skills/codebase-understanding/SKILL.md @.claude/rules/GRAPH_FIRST.md\n\nRefactor: $ARGUMENTS\n\nBefore touching anything:\n1. get_impact_radius — full blast radius of the target symbol/system.\n2. trace_dependencies — what depends on what is changing?\n3. identify_shared_symbols — what is used by many callers?\n4. Map all affected systems.\n\nDeliver:\n- Risk assessment (blast radius, breaking changes)\n- Affected files and systems\n- Step-by-step migration plan (safe order)\n- Rollback strategy\n- Behavior preservation checklist (what must be identical after refactor)"
})
```

**Read output. Phase 2 — Architect approves:**
```
Agent({
  subagent_type: "architect",
  description: "Approve refactor migration plan",
  prompt: "@.claude/skills/architect/SKILL.md @.claude/docs/architecture.md\n\nRefactor: $ARGUMENTS\n\nRefactor agent findings:\n<REFACTOR_AGENT_OUTPUT>\n\nReview the migration plan:\n- Does it preserve all existing behavior?\n- Does it reduce coupling without breaking ECS scheduling or system order?\n- Are the rollback strategy and step order safe?\n\nApprove with any modifications, or reject with clear reasoning. If approved, publish the final migration plan for unity-dev."
})
```

**Read output. Phase 3 — spawn both in a single message, embedding `<APPROVED_PLAN>`:**
```
Agent({
  subagent_type: "unity-dev",
  description: "Execute refactor migration",
  prompt: "@.claude/skills/unity-dev/SKILL.md @.claude/skills/unity-dots-best-practices/SKILL.md\n\nRefactor: $ARGUMENTS\n\nApproved migration plan:\n<APPROVED_PLAN>\n\nExecute the migration steps in order. Do not deviate from the plan. After each step, SendMessage to tester: 'Step <N> complete: <what changed>. Ready to verify.' Wait for tester's OK before next step. All C# edits via mcp__ai-game-developer__script-update-or-create."
})

Agent({
  subagent_type: "tester",
  description: "Behavior preservation validation",
  prompt: "@.claude/skills/tester/SKILL.md @.claude/skills/qa-validation/SKILL.md\n\nRefactor: $ARGUMENTS\n\nApproved migration plan:\n<APPROVED_PLAN>\n\nBehavior preservation checklist above is your test target. After each 'Step N complete' message from unity-dev: run the relevant tests, verify behavior is identical. Reply 'Step N OK' or 'Step N FAIL: <what broke>'.\n\nDEADLOCK PREVENTION: If you cannot verify a step (compilation failure, test infra broken), do NOT leave unity-dev waiting. Reply immediately: 'Step N BLOCKED: <reason>'. Unity-dev must roll back that step and escalate to architect — never leave migration half-done."
})
```

---

### Mode: `--fast-fix` (1-3 line fix, no investigation)

```
For small, obvious fixes only. Skip investigation.
Scope limit: if change exceeds 20 lines or 2 files — STOP, escalate to --bug.
```

Spawn both in a single message:

```
Agent({
  subagent_type: "unity-dev",
  description: "Fast fix",
  prompt: "@.claude/skills/unity-dev/SKILL.md @.claude/skills/unity-dots-best-practices/SKILL.md\n\nFix: $ARGUMENTS\n\nSCOPE LIMIT: If this fix requires changing more than 20 lines or touching more than 2 files, STOP immediately and report: 'Scope exceeded --fast-fix limit. Re-run with --bug.' Do not proceed with a large change in fast-fix mode.\n\nOtherwise: apply the minimal fix. Complete ECS Safety Checklist. Verify compilation clean. Signal tester."
})

Agent({
  subagent_type: "tester",
  description: "Fast fix verification",
  prompt: "@.claude/skills/tester/SKILL.md\n\nFix: $ARGUMENTS\n\nVerify the fix works and no regressions introduced. Run EditMode tests for touched assemblies. Report: pass/fail + list of tests run."
})
```

---

### Mode: general (no task mode flag)

```
All agents start immediately in parallel. Use when task type is unclear.
Agents self-correct as upstream data arrives.
```

Spawn 2 (`--fast`) or 4 (`--full`) agents in **one message**:

```
Agent({
  subagent_type: "architect",
  description: "ECS design for task",
  prompt: "@.claude/docs/setup.md @.claude/skills/architect/SKILL.md @.claude/docs/architecture.md @.claude/docs/mcp-integration.md @.claude/skills/unity-dots-best-practices/SKILL.md\n\nTask: $ARGUMENTS\n\nBefore locking the design: spawn `system-mapper` to map existing ECS systems, boundaries, and extension points. Feed its output into your design — do not design against guessed state. Then design and publish. Save a memory_lesson at handoff for non-obvious risks."
})

Agent({
  subagent_type: "unity-dev",
  description: "ECS implementation for task",
  prompt: "@.claude/docs/setup.md @.claude/skills/unity-dev/SKILL.md @.claude/docs/architecture.md @.claude/docs/mcp-integration.md @.claude/skills/unity-dots-best-practices/SKILL.md @.claude/skills/qa-validation/SKILL.md\n\nTask: $ARGUMENTS\n\nBefore implementing: spawn `code-tracer` to find entry point, execution chain, existing pattern, and extension point in one pass. Implement from those findings. When Architect's design arrives, reconcile and self-correct. All C# edits via mcp__ai-game-developer__script-update-or-create. Complete ECS Safety Checklist before signaling tester."
})

# --full only:
Agent({
  subagent_type: "data-tool",
  description: "Tooling and diagnostics",
  prompt: "@.claude/docs/setup.md @.claude/skills/data-tool/SKILL.md @.claude/docs/architecture.md @.claude/docs/mcp-integration.md @.claude/skills/editor-data-tools/SKILL.md\n\nTask: $ARGUMENTS\n\nBefore building tooling: spawn `code-tracer` to understand what runtime state already exists. Anchor inspectors in real components. Do NOT silently change runtime behavior."
})

Agent({
  subagent_type: "tester",
  description: "Validation",
  prompt: "@.claude/docs/setup.md @.claude/skills/tester/SKILL.md @.claude/docs/architecture.md @.claude/docs/mcp-integration.md @.claude/skills/qa-validation/SKILL.md\n\nTask: $ARGUMENTS\n\nStart outlining the test matrix immediately. When a test fails: spawn `bug-investigation` to trace root cause before proposing a fix — return fix strategy to unity-dev. Run tests as soon as code is available. Save a memory_lesson per defect at sign-off."
})
```

---

## STEP 2 (alt) — Teams backend (`--teams` only)

Only use when `--teams` is passed *and* `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set.

```
TeamCreate:
  team_name:   unity-dots-team
  description: Unity DOTS — architect, unity-dev[, data-tool, tester] (parallel)
```

### Tmux pane rule — DO NOT pre-create panes

**Never run `tmux split-window` manually before spawning agents.** The harness creates exactly one pane per spawned agent automatically when `tmuxSplitPanes: true` is set in `~/.claude/settings.json`. Pre-splitting leaves empty bash panes lying around and can race with the harness's pane-renumbering, accidentally killing live agents.

Rules:
- **Reuse** the existing tmux session — never `tmux kill-session` (it would kill Claude Code itself).
- **Never** call `tmux split-window` / `tmux new-window` from this command.
- **Do not** count panes or pre-allocate them. If the orchestrator session has 1 pane at start, leave it at 1 pane. The harness adds one pane per agent at spawn time and only as many as are actually needed (2 in `--fast`, 4 in `--full`).
- **Never** call `tmux kill-pane` to "clean up" empty panes. If the harness reports a leftover pane, ask the user before killing — pane indices renumber after every kill and a wrong index will terminate an active agent.
- If `tmuxSplitPanes` is disabled or tmux is unavailable, agents run inline in the orchestrator's pane. That is acceptable; do not try to compensate by manually splitting.

Spawn 2 or 4 agents in parallel via the Teams API with `mode: "bypassPermissions"` and the same prompts as the Agent-tool backend. Send all spawn calls in a single assistant turn so the harness allocates panes in one batch.

---

## STEP 3 — Tasks (optional, for visibility)

Create tasks matching the mode:

```
# --bug
TaskCreate { subject: "Root cause investigation",  owner: "bug-investigation" }
TaskCreate { subject: "Fix implementation",        owner: "unity-dev" }
TaskCreate { subject: "Regression verification",   owner: "tester" }

# --feature
TaskCreate { subject: "Existing system map",       owner: "architecture-agent" }
TaskCreate { subject: "Feature design",            owner: "architect" }
TaskCreate { subject: "Feature implementation",    owner: "unity-dev" }
TaskCreate { subject: "Feature tooling",           owner: "data-tool" }
TaskCreate { subject: "Feature validation",        owner: "tester" }

# --refactor
TaskCreate { subject: "Blast radius analysis",     owner: "refactor-agent" }
TaskCreate { subject: "Migration plan approval",   owner: "architect" }
TaskCreate { subject: "Migration execution",       owner: "unity-dev" }
TaskCreate { subject: "Behavior preservation",     owner: "tester" }

# general
TaskCreate { subject: "ECS architecture design",   owner: "architect" }
TaskCreate { subject: "ECS implementation",        owner: "unity-dev" }
TaskCreate { subject: "Tooling and diagnostics",   owner: "data-tool" }
TaskCreate { subject: "Validation and QA",         owner: "tester" }
```

---

## Self-correction protocol

When upstream data lands in an agent's context:

1. Compare against current working assumptions.
2. Identify conflicts / gaps.
3. Self-correct plan, code, or test matrix.
4. State what changed and why.
5. Flag unresolved conflicts to the upstream agent.

In sequential-phase modes (`--bug`, `--feature`, `--refactor`): each phase waits for upstream output before spawning downstream agents. This is intentional — do not collapse phases into parallel.

---

## Quality gates

| # | Rule | Mode | Enforcer |
|---|---|---|---|
| G1 | Root cause proven by graph evidence before fix starts | --bug | bug-investigation |
| G2 | Fix is minimal — root cause only, no refactor | --bug | unity-dev |
| G3 | Regression test fail-before / pass-after | --bug | tester |
| G4 | Existing system mapped before design starts | --feature | architecture-agent |
| G5 | Design locked before implementation starts | --feature | architect |
| G6 | Blast radius documented before any code changes | --refactor | refactor-agent |
| G7 | Migration plan approved by architect before execution | --refactor | architect |
| G8 | Behavior verified step-by-step during migration | --refactor | tester |
| G9 | Implementation matches design; deviations escalate | all | unity-dev → architect |
| G10 | No sign-off without correctness + stress evidence | all | tester |
| G11 | `/codex:review` after design AND before final sign-off | all | orchestrator |

---

## Codex review checkpoints (MANDATORY)

Every `/team` run **must** invoke `/codex:review` twice — failure to do so is a process violation.

1. **After Architect publishes the design** — the orchestrator runs `/codex:review` against the design (plus recon facts and the user request). Architect addresses every blocker / high-severity finding before unity-dev makes irreversible edits.
2. **Before final sign-off** — orchestrator runs `/codex:review` over the final diff. Any blocker returns the task to its owner.

Record both verdicts under `Codex review:` in the completion output. If `/codex:review` is unavailable, state `"Running without codex review"` once and require an extra Architect + Tester pass.

---

## Completion output

```
[Team] Done

[Architect]
  <design decisions, acceptance criteria>

[Unity Dev]
  <implemented systems, self-corrections, known risks>

[Data Tool]     ← --full only
  <tools added, validators, diagnostics>

[Tester]        ← --full only
  <test results, stress outcomes, open defects, sign-off>

Lessons saved to memory: <count>
Open risks: <list>
Next steps: <list>
```

---

## Usage

```sh
# 1-3 line fix — no investigation
/team Fix off-by-one in damage calculation --fast-fix

# Bug fix — investigation-first
/team Enemies stop chasing after teleport --bug
/team Health bar shows wrong value when two damage sources apply same frame --bug

# New feature — architecture-first
/team Add a stamina system with regeneration and cooldown --feature
/team Add expedition reward screen with new inspector tooling --feature --with-tooling

# Refactor — blast-radius-first
/team Extract zone spawner logic into a shared SpawnerSystem --refactor
/team Replace MonoBehaviour health tracking with ECS component --refactor

# General / unknown
/team Add stamina regeneration with cooldowns --full
```

**Quick rule:**
- 1-3 lines, obvious → `--fast-fix`
- Known bug → `--bug`
- New feature → `--feature`
- Restructuring existing code → `--refactor`
- Not sure → omit flag (general mode)

**Never use `--fast-fix` for anything touching system execution order, Burst jobs, or structural changes.**
