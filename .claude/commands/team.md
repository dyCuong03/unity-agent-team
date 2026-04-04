---
description: Boot the Unity DOTS agent team — parallel execution with self-correction. No blocking. All agents spawn immediately.
argument-hint: "<task> [--fast]"
---

# `/team` — Parallel Unity DOTS Agent Team

**Philosophy:** Spawn all agents immediately. Each agent loads its role and reports ready. No agent starts any work until the user explicitly approves.

**Modes:**
- `fast` (default): Architect + Unity Dev only.
- `full`: All 4 agents — parallel spawn.

---

## STEP 1: Preflight

```sh
if ! grep -q "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS.*1" ~/.claude/settings.json 2>/dev/null; then
  echo "Agent Team mode not enabled. Run:"
  echo 'mkdir -p ~/.claude && cat > ~/.claude/settings.json << '\''EOF'\'''
  echo '{"env":{"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS":"1"},"preferences":{"tmuxSplitPanes":true}}'
  echo "'EOF'"
  echo "Restart Claude Code, then run /team again."
  exit 1
fi
echo "Preflight: Agent Team mode enabled ✓"
```

---

## STEP 2: Tmux — Reuse Existing Session (Do Not Kill)

Claude Code is already running inside a tmux session. **Do NOT kill or recreate it.**

```sh
# Detect current tmux session state
TMUX_SESSION=$(tmux display-message -p '#S' 2>/dev/null)
TMUX_PANES=$(tmux display-message -p '#{window_panes}' 2>/dev/null)

if [ -n "$TMUX_SESSION" ]; then
  echo "Tmux: reusing existing session '$TMUX_SESSION' with $TMUX_PANES pane(s)"

  # Ensure we have exactly 4 panes for the 4 agents
  if [ "$TMUX_PANES" -lt 4 ]; then
    SPLITS_NEEDED=$((4 - TMUX_PANES))
    echo "Tmux: splitting $SPLITS_NEEDED additional pane(s)..."
    for i in $(seq 1 $SPLITS_NEEDED); do
      tmux split-window -h -t "$TMUX_SESSION"
    done
    # Re-layout to 2x2 grid
    tmux select-layout -t "$TMUX_SESSION" tiled 2>/dev/null || true
  else
    echo "Tmux: 4+ panes already available — using existing panes"
  fi
else
  echo "Tmux: not detected — running without session (degraded mode)"
fi
```

**Rules:**
- Never `tmux kill-session` — it would kill Claude Code itself.
- Never `tmux new-session` — create panes inside the existing session instead.
- Each agent pane is mapped: pane 0 = architect, pane 1 = unity-dev, pane 2 = data-tool, pane 3 = tester.

---

## STEP 3: Create Team

```
TeamCreate:
  team_name:    unity-dots-team
  description:  Unity DOTS — architect, unity-dev, data-tool, tester (parallel)
  agent_type:    orchestrator
```

---

## STEP 3: Spawn All Agents in Parallel (Single Wave)

All agents load their role files and report ready. **No agent starts any work until the user explicitly approves.**

### Architect

```json
{
  "name": "architect",
  "team_name": "unity-dots-team",
  "subagent_type": "architect",
  "mode": "bypassPermissions",
  "prompt": [
    "@SETUP.md",
    "@skills/architect/role.md",
    "@skills/architect/skills.md",
    "@skills/architect/rules.md",
    "@architecture.md",
    "@mcp-integration.md",
    "@.claude/skills/unity-dots-best-practices/SKILL.md",
    "\nTask context: $ARGUMENTS\n\nLoad all files listed above. Then send a ready message to the team lead: 'architect ready'.",
    "Do NOT begin any work, analysis, planning, or design until the team lead explicitly assigns you a task via SendMessage.",
    "When assigned, confirm the task back to the team lead before starting.",
    "After publishing a design, remain active to answer follow-up questions and review deviations flagged by other agents.",
    "When work is complete, send results to the team lead and wait for the next assignment."
  ]
}
```

### Unity Dev

```json
{
  "name": "unity-dev",
  "team_name": "unity-dots-team",
  "subagent_type": "unity-dev",
  "mode": "bypassPermissions",
  "prompt": [
    "@SETUP.md",
    "@skills/unity-dev/role.md",
    "@skills/unity-dev/skills.md",
    "@skills/unity-dev/rules.md",
    "@architecture.md",
    "@mcp-integration.md",
    "@.claude/skills/unity-dots-best-practices/SKILL.md",
    "@.claude/skills/qa-validation/SKILL.md",
    "\nTask context: $ARGUMENTS\n\nLoad all files listed above. Then send a ready message to the team lead: 'unity-dev ready'.",
    "Do NOT begin any work, analysis, planning, or implementation until the team lead explicitly assigns you a task via SendMessage.",
    "When assigned, confirm the task back to the team lead before starting.",
    "Surface blockers and performance risks via SendMessage to team lead.",
    "When work is complete, send results to the team lead and wait for the next assignment."
  ]
}
```

### Data Tool (full mode only)

```json
{
  "name": "data-tool",
  "team_name": "unity-dots-team",
  "subagent_type": "data-tool",
  "mode": "bypassPermissions",
  "prompt": [
    "@SETUP.md",
    "@skills/data-tool/role.md",
    "@skills/data-tool/skills.md",
    "@skills/data-tool/rules.md",
    "@architecture.md",
    "@mcp-integration.md",
    "@.claude/skills/editor-data-tools/SKILL.md",
    "@.claude/skills/qa-validation/SKILL.md",
    "\nTask context: $ARGUMENTS\n\nLoad all files listed above. Then send a ready message to the team lead: 'data-tool ready'.",
    "Do NOT begin any work, analysis, planning, or tooling until the team lead explicitly assigns you a task via SendMessage.",
    "When assigned, confirm the task back to the team lead before starting.",
    "Do NOT silently change runtime behavior. Any tooling that touches runtime logic must be reviewed.",
    "When work is complete, send results to the team lead and wait for the next assignment."
  ]
}
```

### Tester (full mode only)

```json
{
  "name": "tester",
  "team_name": "unity-dots-team",
  "subagent_type": "tester",
  "mode": "bypassPermissions",
  "prompt": [
    "@SETUP.md",
    "@skills/tester/role.md",
    "@skills/tester/skills.md",
    "@skills/tester/rules.md",
    "@architecture.md",
    "@mcp-integration.md",
    "@.claude/skills/qa-validation/SKILL.md",
    "@.claude/skills/editor-data-tools/SKILL.md",
    "\nTask context: $ARGUMENTS\n\nLoad all files listed above. Then send a ready message to the team lead: 'tester ready'.",
    "Do NOT begin any work, analysis, planning, or testing until the team lead explicitly assigns you a task via SendMessage.",
    "When assigned, confirm the task back to the team lead before starting.",
    "Block completion if correctness or stability gates fail. Return issues to the responsible agent.",
    "When work is complete, send results to the team lead and wait for the next assignment."
  ]
}
```

---

## STEP 4: Create Tasks (Pending — No Auto-Assignment)

Tasks are created as pending. No task is assigned or started until the user approves.

```json
TaskCreate: { "subject": "ECS architecture design",        "description": "Architect: ECS boundaries, data model, update order, baker plan, acceptance criteria" }
TaskCreate: { "subject": "ECS implementation",             "description": "Unity Dev: components, systems, jobs, bakers from approved design" }
TaskCreate: { "subject": "Tooling and diagnostics",        "description": "Data Tool: authoring pipeline, editor tools, validators, debug helpers" }
TaskCreate: { "subject": "Validation and QA",              "description": "Tester: functional tests, stress, regression, acceptance sign-off" }
```

---

## STEP 5: Report to User and Wait for Approval

Once all 4 agents report ready and tasks are created, report to the user:

```
Team ready. 4 agents standing by — no work has started.

Task queue:
  [1] ECS architecture design      → architect
  [2] ECS implementation           → unity-dev
  [3] Tooling and diagnostics      → data-tool
  [4] Validation and QA            → tester

Tell me which task(s) to start, or say 'go' to start task 1 (architecture).
No agent will do anything until you approve.
```

**Do not assign any task or send any agent a start signal until the user responds.**

---

## Agent Self-Correction Protocol

When an agent receives upstream data (design, implementation, tooling), it must:

1. **Compare** incoming data against its current working assumptions.
2. **Identify** conflicts, gaps, or scope changes.
3. **Self-correct** — update its own plan, code, or test matrix.
4. **Log** what changed and why via SendMessage to team lead.
5. **Flag** any unresolved conflicts to the responsible upstream agent.

No agent is blocked waiting. No agent waits for a perfect upstream signal before starting.

---

## MCP Rule

**Always prefer Unity MCP** over guessing project state.
- Available: use for project inspection, ECS authoring checks, logs, and test execution.
- Unavailable: state *"Running without MCP evidence"* and fall back to source code reasoning.

---

## Quality Gates

| Gate | Rule | Enforcer |
|------|------|----------|
| G1 | Implementation matches Architect's published design; deviations escalate | Unity Dev → Architect |
| G2 | Tooling does not silently change runtime behavior | Data Tool |
| G3 | Correctness + stress evidence required for sign-off | Tester |
| G4 | No completion while regressions remain open | Tester |

---

## Completion Output Format

```
[Team: unity-dots-team] — Done

[Architect]
  <design decisions, acceptance criteria>

[Unity Dev]
  <implemented systems, self-corrections made, known risks>

[Data Tool]  ← full mode
  <tools added, validators, diagnostics>

[Tester]     ← full mode
  <test results, stress outcomes, open defects, sign-off>

Self-corrections: <list of updates made when upstream data arrived>
Open risks: <list>
Next steps: <list>
```

---

## Usage

```sh
# Fast mode — Architect + Unity Dev in parallel
/team Add a health system with damage and death states --fast

# Full mode — All 4 agents in parallel
/team Add stamina regeneration with cooldowns
```
