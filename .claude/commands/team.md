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

## STEP 1.5 — Skill routing + hardening checks

Read `@.claude/rules/skill-confidence-routing.md` for the full scoring algorithm.
Read `@.claude/rules/mcp-phase-gates.md` — know which operations are allowed in your phase.
Read `@.claude/rules/escalation-policy.md` — know your mandatory escalation triggers.

**Reset session workspace:**
```sh
mkdir -p workspace/skill-cache
cp .claude/workspace-templates/domain-analysis.md workspace/domain-analysis.md
cp .claude/workspace-templates/escalation-log.md workspace/escalation-log.md
find workspace/skill-cache/ -name "*.cache.md" -mtime +1 -delete 2>/dev/null
```

**1. Check unity-skills server (if installed):**
```
GET http://localhost:8090/health
```
If reachable: note `currentMode`. If unreachable: agents degrade gracefully — no REST calls.

**2. Classify domain using code-aware routing** (`@.claude/rules/code-aware-routing-engine.md`):
The investigation agent (system-mapper/code-tracer/bug-investigation) runs the full pipeline:
CRG → API fingerprinting → pattern detection → domain scoring → write workspace/domain-analysis.md.
Domain classification drives skill loading — not task keywords alone.
Read `workspace/domain-analysis.md` after investigation completes before selecting skills.

**Legacy keyword scoring** (fallback if investigation is skipped):
Score = 0.35×keyword + 0.30×symptom + 0.20×history + 0.10×ECS_penalty + 0.05×issue_type
Load threshold: ≥ 0.70. Max 2 domain + 2 advisory per agent.

**3. Check skill cache** for each selected module:
- If `workspace/skill-cache/<module>.cache.md` exists → use it (150 tokens) instead of full SKILL.md (400 tokens)
- If not → first agent loads full SKILL.md; orchestrator writes cache summary after that agent completes

**4. Write routing decision** (one line, before spawning any agent):
```
[SKILL_ROUTING] domain:[<m1>, <m2>] advisory:[<a1>, <a2>] threshold:0.70 dropped:[<module>(<score>)] cache_hits:[<modules>]
```

**Layer 1 (always, every agent):** `@.claude/skills/unity-dots-best-practices/SKILL.md`
**Layer 2 (architect/unity-dev/data-tool):** `@.claude/skills/unity-foundation/SKILL.md`
**Layer 4 (investigation agents):** `@.claude/skills/investigation/SKILL.md`
**Layer 3 (domain):** add selected module @-imports or cache refs to the relevant agent only

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

**Before Phase 1 — orchestrator resets session workspace:**
```sh
# Clear session-scoped files (preserve persistent files)
cp .claude/workspace-templates/investigation.md workspace/investigation.md
cp .claude/workspace-templates/test-plan.md workspace/test-plan.md
```

**Phase 1 — Spawn and wait:**
```
Agent({
  subagent_type: "bug-investigation",
  description: "Root cause investigation + domain classification",
  prompt: "@.claude/skills/unity-dots-best-practices/SKILL.md @.claude/skills/investigation/SKILL.md @.claude/skills/codebase-understanding/SKILL.md @.claude/rules/GRAPH_FIRST.md @.claude/rules/api-fingerprinting-system.md @.claude/rules/domain-scoring-engine.md @.claude/rules/domain-aware-mcp.md\n\nBug: $ARGUMENTS\n\nRead workspace/repo-knowledge.md, workspace/ecs-registry.md first.\nSearch agentmemory for prior investigations of this symptom area before CRG.\n\nStep 1 — CRG: trace_execution_flow → identify touched files and systems.\nStep 2 — Fingerprint: scan touched files for DOTS/Unity/Hybrid APIs (api-fingerprinting-system.md).\nStep 3 — Score: calculate DOTS_score, Unity_score, Hybrid_score (domain-scoring-engine.md).\nStep 4 — Write workspace/domain-analysis.md (fill all sections).\nIf Ambiguous: write [ESCALATE_ARCHITECT: domain ambiguous] and stop.\n\nStep 5 — MCP: run domain-appropriate queries (domain-aware-mcp.md).\nStep 6 — Root cause: trace writers/readers, get_impact_radius.\n\nWrite root cause to workspace/investigation.md.\nSet STATUS: COMPLETE or STATUS: INCONCLUSIVE with [ESCALATE: reason].\nSave to agentmemory at the end."
})
```

**Orchestrator: read workspace/investigation.md. If STATUS is INCONCLUSIVE or starts with [ESCALATE], stop and report. Otherwise Phase 2:**

```
Agent({
  subagent_type: "unity-dev",
  description: "Implement bug fix",
  prompt: "@.claude/skills/unity-dev/SKILL.md @.claude/skills/unity-dots-best-practices/SKILL.md\n\nBug: $ARGUMENTS\n\nRead workspace/investigation.md for root cause and fix strategy.\nRead workspace/ecs-registry.md before touching any component or system.\n\nFix only the identified root cause — no refactor. Minimal change, maximum precision.\nAll C# edits via mcp__ai-game-developer__script-update-or-create.\n\nBefore signaling tester:\n1. Complete ECS Safety Checklist from your SKILL.md.\n2. mcp__ai-game-developer__console-get-logs — confirm ZERO compile errors.\nIf compilation fails: fix it. Do NOT signal tester with broken compilation.\n\nSignal: write 'Fix applied. Compilation: CLEAN. Changed: <list>' to workspace/investigation.md under '## Fix Applied'."
})

Agent({
  subagent_type: "tester",
  description: "Regression test for bug fix",
  prompt: "@.claude/skills/tester/SKILL.md @.claude/skills/qa-validation/SKILL.md\n\nBug: $ARGUMENTS\n\nRead workspace/investigation.md for root cause and regression test guidance.\nWrite your test plan to workspace/test-plan.md.\n\nBASELINE FIRST: Run regression test NOW (pre-fix state). Record 'Baseline: FAIL' in workspace/test-plan.md.\nIf test passes pre-fix — assertion is wrong. Write [BLOCKED: baseline test passes pre-fix] to test-plan.md STATUS and stop.\n\nPoll workspace/investigation.md for '## Fix Applied' section. When present: run same test.\nRecord both baseline and post-fix results in workspace/test-plan.md.\nSet STATUS: PASSED or STATUS: FAILED with [BLOCKED: reason]."
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

**Before Phase 1 — orchestrator resets session workspace:**
```sh
cp .claude/workspace-templates/design.md workspace/design.md
cp .claude/workspace-templates/test-plan.md workspace/test-plan.md
```

**Phase 1 — Map existing system (system-mapper, not architect):**
```
Agent({
  subagent_type: "system-mapper",
  description: "Map existing systems + domain classification for feature area",
  prompt: "@.claude/skills/unity-dots-best-practices/SKILL.md @.claude/skills/unity-foundation/SKILL.md @.claude/skills/investigation/SKILL.md @.claude/skills/codebase-understanding/SKILL.md @.claude/rules/GRAPH_FIRST.md @.claude/rules/api-fingerprinting-system.md @.claude/rules/domain-scoring-engine.md @.claude/rules/architecture-pattern-detection.md @.claude/rules/domain-aware-mcp.md\n\nFeature: $ARGUMENTS\n\nRead workspace/repo-knowledge.md and workspace/ecs-registry.md first.\nIf repo-knowledge.md is empty or stale: call project_stack_detect to detect tech stack, then run get_architecture_overview and update repo-knowledge.md.\n\nStep 1 — CRG: get_architecture_overview → trace_execution_flow → identify_extension_points.\nStep 2 — Fingerprint: scan touched files for DOTS/Unity/Hybrid APIs (api-fingerprinting-system.md).\nStep 3 — Patterns: detect architecture patterns in touched code (architecture-pattern-detection.md).\nStep 4 — Score: calculate domain scores (domain-scoring-engine.md).\nStep 5 — Write workspace/domain-analysis.md (all sections including Touched Files, API Scan, Patterns, Domain Classification).\nIf Ambiguous: write [ESCALATE_ARCHITECT: domain ambiguous] — architect must classify before architect designs.\n\nStep 6 — Update workspace/repo-knowledge.md (Extension Points, tech stack, session history).\nStep 7 — Write feature-specific System Map to workspace/design.md '## System Map' section.\nIf CRG reveals ecs-registry.md conflict: write [ESCALATE: conflict description]."
})
```

**Orchestrator: check workspace/design.md for [ESCALATE]. Then Phase 2:**
```
Agent({
  subagent_type: "architect",
  description: "Design feature extension",
  prompt: "@.claude/skills/architect/SKILL.md @.claude/docs/architecture.md @.claude/skills/unity-dots-best-practices/SKILL.md\n\nFeature: $ARGUMENTS\n\nRead workspace/design.md (system map section) and workspace/ecs-registry.md.\nDesign the feature extension from the mapped extension points — do not redesign existing systems.\nCheck ecs-registry.md before adding any component — avoid duplicates.\n\nWrite the complete design to workspace/design.md (fill all sections).\nUpdate workspace/ecs-registry.md with any new components and systems.\nSet design.md STATUS: APPROVED when done, or STATUS: REJECTED with [REJECTED: reason] if requirements are underspecified."
})
```

**Orchestrator: check workspace/design.md STATUS. If REJECTED → stop. If APPROVED → Phase 3:**
**Add domain @-imports from STEP 1.5 routing to unity-dev prompt only if relevant to this agent's work.**
```
Agent({
  subagent_type: "unity-dev",
  description: "Implement feature",
  prompt: "@.claude/skills/unity-dots-best-practices/SKILL.md @.claude/skills/unity-foundation/SKILL.md @.claude/skills/unity-dev/SKILL.md [+ domain module @-imports from STEP 1.5 for unity-dev]\n\nFeature: $ARGUMENTS\n\nRead workspace/design.md for architecture. Read workspace/ecs-registry.md before touching any component.\nCheck DOTS Conflict Resolution Policy (CLAUDE.md) for any MonoBehaviour-first modules loaded — confirm boundary.\nSpawn `code-tracer` to confirm extension points before writing any code.\n\nImplement strictly from workspace/design.md. All C# edits via mcp__ai-game-developer__script-update-or-create.\nIf unity-skills server is reachable and module is FullAuto or SemiAuto-cleared: use REST skills for scene/prefab inspection only — never for mutation without ECS Safety Checklist completed.\nIf design is ambiguous: write [ESCALATE: question] to workspace/design.md open risks — do not guess.\nComplete ECS Safety Checklist from SKILL.md before signaling tester.\nUpdate workspace/ecs-registry.md if implementation differs from design (with reason)."
})

# --with-tooling only:
Agent({
  subagent_type: "data-tool",
  description: "Feature tooling",
  prompt: "@.claude/skills/data-tool/SKILL.md @.claude/skills/editor-data-tools/SKILL.md\n\nFeature: $ARGUMENTS\n\nRead workspace/design.md for component and system shapes before building any tooling.\nRead workspace/ecs-registry.md for real field names and types.\nSpawn `code-tracer` only if workspace files are insufficient for real component state.\nDo NOT silently change runtime behavior. Write [ESCALATE: reason] if tooling requires runtime architecture change."
})

Agent({
  subagent_type: "tester",
  description: "Feature validation",
  prompt: "@.claude/skills/tester/SKILL.md @.claude/skills/qa-validation/SKILL.md\n\nFeature: $ARGUMENTS\n\nRead workspace/design.md Acceptance Criteria section. Derive test matrix from it.\nWrite test plan to workspace/test-plan.md.\n\nWhen a test fails: spawn `bug-investigation` — it will read workspace/investigation.md. Return fix strategy to unity-dev.\nBlock sign-off until all P0 acceptance criteria pass with evidence.\nWrite final result to workspace/test-plan.md STATUS and sign-off section."
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

**Before Phase 1 — orchestrator resets session workspace:**
```sh
cp .claude/workspace-templates/migration-plan.md workspace/migration-plan.md
cp .claude/workspace-templates/test-plan.md workspace/test-plan.md
```

**Phase 1 — Map blast radius:**
```
Agent({
  subagent_type: "refactor-agent",
  description: "Blast radius and migration plan",
  prompt: "@.claude/skills/codebase-understanding/SKILL.md @.claude/rules/GRAPH_FIRST.md\n\nRefactor: $ARGUMENTS\n\nRead workspace/ecs-registry.md and workspace/repo-knowledge.md first.\n\nBefore touching anything:\n1. get_impact_radius — full blast radius.\n2. trace_dependencies — what depends on what is changing?\n3. identify_shared_symbols — what is used by many callers?\n4. Map all affected systems.\n\nWrite complete output to workspace/migration-plan.md (all sections).\nIf blast radius affects more than 10 files or 3 system groups: write [ESCALATE: high blast radius — consider phased approach]."
})
```

**Orchestrator: check migration-plan.md for [ESCALATE]. Then Phase 2:**
```
Agent({
  subagent_type: "architect",
  description: "Approve refactor migration plan",
  prompt: "@.claude/skills/architect/SKILL.md @.claude/docs/architecture.md\n\nRefactor: $ARGUMENTS\n\nRead workspace/migration-plan.md fully.\n\nReview:\n- Does plan preserve all existing ECS behavior?\n- Is system update order preserved?\n- Is rollback strategy safe and complete?\n- Is step order correct?\n\nWrite approval decision to workspace/migration-plan.md 'Architect Approval Notes' section.\nSet STATUS: APPROVED or STATUS: REJECTED with [REJECTED: reason].\nIf APPROVED with changes: modify the migration steps directly in the file."
})
```

**Orchestrator: check migration-plan.md STATUS. If REJECTED → stop, report. If APPROVED → Phase 3:**
```
Agent({
  subagent_type: "unity-dev",
  description: "Execute refactor migration",
  prompt: "@.claude/skills/unity-dev/SKILL.md @.claude/skills/unity-dots-best-practices/SKILL.md\n\nRefactor: $ARGUMENTS\n\nRead workspace/migration-plan.md for approved steps and rollback strategy.\n\nExecute steps IN ORDER. After each step:\n1. Complete ECS Safety Checklist.\n2. Verify compilation clean.\n3. Update workspace/migration-plan.md Step Execution Log with your result.\n4. WAIT — poll migration-plan.md for tester's 'Step N OK' before continuing.\n\nIf tester writes 'Step N BLOCKED' or 'Step N FAIL': roll back that step using the rollback strategy, write [ESCALATE: step N failed] to migration-plan.md, and stop."
})

Agent({
  subagent_type: "tester",
  description: "Behavior preservation validation",
  prompt: "@.claude/skills/tester/SKILL.md @.claude/skills/qa-validation/SKILL.md\n\nRefactor: $ARGUMENTS\n\nRead workspace/migration-plan.md for behavior preservation checklist and steps.\nWrite your test plan to workspace/test-plan.md.\n\nAfter each unity-dev step (poll migration-plan.md Step Execution Log):\n- Run behavior preservation tests for changed systems.\n- Write 'Step N OK' or 'Step N FAIL: <what broke>' to migration-plan.md.\n- DEADLOCK PREVENTION: If you cannot verify (compilation broken, test infra broken), write 'Step N BLOCKED: <reason>' immediately — never leave unity-dev waiting."
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
