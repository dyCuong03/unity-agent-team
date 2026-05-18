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
  prompt: "@.claude/docs/setup.md @.claude/skills/architect/SKILL.md @.claude/docs/architecture.md @.claude/docs/mcp-integration.md @.claude/skills/unity-dots-best-practices/SKILL.md\n\nTask: $ARGUMENTS\n\nStart designing immediately. Publish design as soon as it's ready. Pull from ai-game-developer MCP only when a decision depends on it. Pull from agentmemory only if prior work in this area is likely. Save a memory_lesson at handoff for non-obvious risks."
})
```

**Unity Dev** (always)
```
Agent({
  subagent_type: "unity-dev",
  description: "ECS implementation for task",
  prompt: "@.claude/docs/setup.md @.claude/skills/unity-dev/SKILL.md @.claude/docs/architecture.md @.claude/docs/mcp-integration.md @.claude/skills/unity-dots-best-practices/SKILL.md @.claude/skills/qa-validation/SKILL.md\n\nTask: $ARGUMENTS\n\nStart implementing immediately. When Architect's design arrives, reconcile and self-correct. All C# edits via mcp__ai-game-developer__script-update-or-create. Run tests-run before declaring complete."
})
```

**Data Tool** (full mode only)
```
Agent({
  subagent_type: "data-tool",
  description: "Tooling and diagnostics for task",
  prompt: "@.claude/docs/setup.md @.claude/skills/data-tool/SKILL.md @.claude/docs/architecture.md @.claude/docs/mcp-integration.md @.claude/skills/editor-data-tools/SKILL.md @.claude/skills/qa-validation/SKILL.md\n\nTask: $ARGUMENTS\n\nStart building tooling immediately. Do NOT silently change runtime behavior. Anchor inspectors in real data via assets-get-data / object-get-data."
})
```

**Tester** (full mode only)
```
Agent({
  subagent_type: "tester",
  description: "Validation for task",
  prompt: "@.claude/docs/setup.md @.claude/skills/tester/SKILL.md @.claude/docs/architecture.md @.claude/docs/mcp-integration.md @.claude/skills/qa-validation/SKILL.md @.claude/skills/editor-data-tools/SKILL.md\n\nTask: $ARGUMENTS\n\nStart outlining the test matrix immediately. Run tests as soon as code is available. Save a memory_lesson per defect at sign-off."
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

Reuse the existing tmux session — never `tmux kill-session` (it would kill Claude Code).

```sh
TMUX_SESSION=$(tmux display-message -p '#S' 2>/dev/null || true)
TMUX_PANES=$(tmux display-message -p '#{window_panes}' 2>/dev/null || echo 0)
NEED=4  # or 2 in --fast mode
if [ -n "$TMUX_SESSION" ] && [ "$TMUX_PANES" -lt "$NEED" ]; then
  for _ in $(seq 1 $((NEED - TMUX_PANES))); do
    tmux split-window -h -t "$TMUX_SESSION"
  done
  tmux select-layout -t "$TMUX_SESSION" tiled 2>/dev/null || true
fi
```

Spawn 2 or 4 agents in parallel via the Teams API with `mode: "bypassPermissions"` and the same prompts as the Agent-tool backend.

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
