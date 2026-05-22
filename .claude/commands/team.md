---
description: Boot the Unity DOTS agent team — parallel execution, agents start immediately. No blocking preflight.
argument-hint: "<task> [--fast | --full] [--teams]"
---

# `/team` — Unity DOTS Agent Team (fast-spawn)

**Philosophy:** Agents start work the moment they're spawned. No preflight checklists. No waiting on other agents. Pull MCP / memory when actually needed.

**Modes:**
- `--fast` *(default)* — Architect + Unity Dev only. Two-agent parallel spawn.
- `--full` — All four (architect, unity-dev, data-tool, tester) in parallel.

**Execution backends:**
- *Default:* standard `Agent` tool with `subagent_type`, in this session. Works everywhere.
- `--teams` flag: experimental `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` flow with `TeamCreate` and tmux panes. Only if the flag is set in `~/.claude/settings.json`.

---

## STEP 1 — Non-blocking preflight (informational only)

Run once. Agents proceed regardless of result.

```sh
python .claude/scripts/preflight.py
```

The script reports `agent-team-mode`, `tmux`, `mcp:ai-game-developer`, `mcp:agentmemory`. Note any missing capability and continue. Agents will state their own fallback if a tool fails.

---

## STEP 2 — Spawn agents in parallel (single wave)

### Default backend: `Agent` tool

Spawn 2 (fast) or 4 (full) agents in **one message, multiple Agent calls in parallel**. Each agent receives the task immediately and begins work.

**Architect** (always)
```
Agent({
  subagent_type: "architect",
  description: "ECS design for task",
  prompt: "@.claude/docs/setup.md @.claude/skills/architect/SKILL.md @.claude/docs/architecture.md @.claude/docs/mcp-integration.md @.claude/skills/unity-dots-best-practices/SKILL.md @.claude/skills/codebase-understanding/SKILL.md\n\nTask: $ARGUMENTS\n\nBefore locking the design: spawn `architecture-agent` to map existing ECS systems, boundaries, and extension points for this feature area. Feed its system map and dependency summary into your design — do not design against guessed state.\n\nThen design and publish. Pull from ai-game-developer MCP only when a decision depends on it. Pull from agentmemory only if prior work in this area is likely. Save a memory_lesson at handoff for non-obvious risks."
})
```

**Unity Dev** (always)
```
Agent({
  subagent_type: "unity-dev",
  description: "ECS implementation for task",
  prompt: "@.claude/docs/setup.md @.claude/skills/unity-dev/SKILL.md @.claude/docs/architecture.md @.claude/docs/mcp-integration.md @.claude/skills/unity-dots-best-practices/SKILL.md @.claude/skills/qa-validation/SKILL.md @.claude/skills/codebase-understanding/SKILL.md\n\nTask: $ARGUMENTS\n\nBefore implementing: (1) spawn `codebase-reader` to find the entry point and execution chain for this feature, (2) spawn `feature-dev-agent` to locate the existing pattern and extension points. Implement from those findings — do not introduce parallel architecture if one already exists.\n\nWhen Architect's design arrives, reconcile and self-correct. All C# edits via mcp__ai-game-developer__script-update-or-create. Run tests-run before declaring complete."
})
```

**Data Tool** (full mode only)
```
Agent({
  subagent_type: "data-tool",
  description: "Tooling and diagnostics for task",
  prompt: "@.claude/docs/setup.md @.claude/skills/data-tool/SKILL.md @.claude/docs/architecture.md @.claude/docs/mcp-integration.md @.claude/skills/editor-data-tools/SKILL.md @.claude/skills/qa-validation/SKILL.md @.claude/skills/codebase-understanding/SKILL.md\n\nTask: $ARGUMENTS\n\nBefore building tooling: spawn `codebase-reader` to understand what runtime state and ECS components already exist for this feature area and what needs exposing. Anchor inspectors in real components and buffers found by the reader — do not build tooling for state that doesn't exist.\n\nDo NOT silently change runtime behavior."
})
```

**Tester** (full mode only)
```
Agent({
  subagent_type: "tester",
  description: "Validation for task",
  prompt: "@.claude/docs/setup.md @.claude/skills/tester/SKILL.md @.claude/docs/architecture.md @.claude/docs/mcp-integration.md @.claude/skills/qa-validation/SKILL.md @.claude/skills/editor-data-tools/SKILL.md @.claude/skills/codebase-understanding/SKILL.md\n\nTask: $ARGUMENTS\n\nStart outlining the test matrix immediately. When a test fails: spawn `bug-investigation` to trace root cause with graph evidence before proposing a fix — return the safe fix strategy to unity-dev, do not patch it yourself. Run tests as soon as code is available. Save a memory_lesson per defect at sign-off."
})
```

All agent calls must go in **a single assistant turn with multiple Agent tool uses** so they run in parallel. Do not await one before starting the next.

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

Create one task per agent so progress is visible in the task list:

```
TaskCreate { subject: "ECS architecture design",   owner: "architect" }
TaskCreate { subject: "ECS implementation",        owner: "unity-dev" }
TaskCreate { subject: "Tooling and diagnostics",   owner: "data-tool" }   # --full
TaskCreate { subject: "Validation and QA",         owner: "tester" }      # --full
```

---

## Self-correction protocol

When upstream data (design, implementation, tooling) lands in an agent's context, it must:

1. Compare against current working assumptions.
2. Identify conflicts / gaps.
3. Self-correct its plan, code, or test matrix.
4. State what changed and why.
5. Flag unresolved conflicts to the upstream agent.

No agent waits on another. No agent runs a checklist before starting.

---

## Quality gates

| # | Rule | Enforcer |
|---|---|---|
| G1 | Implementation matches Architect's design; deviations escalate | unity-dev → architect |
| G2 | Tooling does not silently change runtime behavior | data-tool |
| G3 | Correctness + stress evidence required for sign-off | tester |
| G4 | No completion while regressions remain open | tester |
| G5 | `/codex:review` recorded for design AND final diff (see CLAUDE.md → "Codex Review Gate") | orchestrator |

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
# Two-agent fast mode (default)
/team Add a health system with damage and death states

# Four-agent full mode
/team Add stamina regeneration with cooldowns --full

# Force experimental Teams backend (requires the env flag)
/team Refactor inventory --full --teams
```
