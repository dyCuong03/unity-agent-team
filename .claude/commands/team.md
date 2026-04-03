---
description: Boot the Unity DOTS agent team — Phase 1 creates tmux, team, and agents; Phase 2 agents self-configure.
argument-hint: "<task>"
---

# `/team` — Unity DOTS Agent Team Boot Sequence

This command executes **Phase 1 only**: tmux session → preflight → team creation → parallel agent spawn.
Phase 2 (skill loading, subagent setup, work) runs autonomously inside each agent.

---

## Phase 1 — Team Lead Execution

Execute all steps in order. Do not spawn agents until tmux + preflight are done.

### STEP 1: Preflight

```
IF Agent Team mode is NOT enabled:
  → STOP. Output the exact ~/.claude/settings.json command from SETUP.md Section "Enable Agent Team Mode".
  → Do not continue.

IF tmux is unavailable:
  → Log "tmux unavailable — continuing in degraded mode."
  → Continue without tmux session.
```

### STEP 2: Tmux Session

```
IF tmux IS available:
  → Run: tmux new-session -s claude-work
  → Log "tmux session 'claude-work' created."
ELSE:
  → Log "tmux unavailable — no session created."
```

### STEP 3: Create Agent Team

```json
{
  "team_name": "unity-dots-team",
  "description": "Unity DOTS agent team — architect, unity-dev, data-tool, tester",
  "agent_type": "orchestrator"
}
```

### STEP 4: Spawn 4 Agents in Parallel

Spawn **all 4 agents simultaneously** (parallel, not sequential) with `mode: "bypassPermissions"`.

#### Agent: architect

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
    "@skills/architect/subagents.md",
    "@architecture.md",
    "@mcp-integration.md",
    "@.claude/skills/unity-dots-best-practices/SKILL.md",
    "\nTask: $ARGUMENTS\n\nPhase 1 complete (team lead). You are now in Phase 2.",
    "Load all files above. Set up your internal subagents. Confirm readiness to team lead.",
    "Then await task assignment and begin with ECS architecture design."
  ]
}
```

#### Agent: unity-dev

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
    "@skills/unity-dev/subagents.md",
    "@architecture.md",
    "@mcp-integration.md",
    "@.claude/skills/unity-dots-best-practices/SKILL.md",
    "@.claude/skills/qa-validation/SKILL.md",
    "\nTask: $ARGUMENTS\n\nPhase 1 complete (team lead). You are now in Phase 2.",
    "Load all files above. Set up your internal subagents. Confirm readiness to team lead.",
    "Then await Architect's approved design before implementing anything."
  ]
}
```

#### Agent: data-tool

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
    "@skills/data-tool/subagents.md",
    "@architecture.md",
    "@mcp-integration.md",
    "@.claude/skills/editor-data-tools/SKILL.md",
    "@.claude/skills/qa-validation/SKILL.md",
    "\nTask: $ARGUMENTS\n\nPhase 1 complete (team lead). You are now in Phase 2.",
    "Load all files above. Set up your internal subagents. Confirm readiness to team lead.",
    "Then await Unity Dev's handoff to begin building tooling and diagnostics."
  ]
}
```

#### Agent: tester

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
    "@skills/tester/subagents.md",
    "@architecture.md",
    "@mcp-integration.md",
    "@.claude/skills/qa-validation/SKILL.md",
    "@.claude/skills/editor-data-tools/SKILL.md",
    "\nTask: $ARGUMENTS\n\nPhase 1 complete (team lead). You are now in Phase 2.",
    "Load all files above. Set up your internal subagents. Confirm readiness to team lead.",
    "Then await Data Tool Engineer's handoff to begin validation and stress testing."
  ]
}
```

### STEP 5: Confirm Boot

After all 4 agents are spawned:

```
Log "Team boot complete. 4 agents active in Phase 2."
Log "Architect → design. Unity Dev → implement after approval."
Log "Data Tool → tooling after Unity Dev handoff."
Log "Tester → validation after Data Tool handoff."
```

---

## Phase 2 — Agent Behavior (Reference)

Each agent, upon spawning, runs independently:

1. Load all files in its prompt (already injected — no network/IO needed).
2. Confirm readiness to team lead via SendMessage.
3. Set up internal subagents from subagents.md.
4. Enter role-specific workflow:

```
Architect   → Analyze task → Publish approved ECS design → await implementation
Unity Dev   → Wait for Architect design → Implement → handoff to data-tool
Data Tool   → Wait for Unity Dev handoff → Build tooling → handoff to tester
Tester      → Wait for Data Tool handoff → Validate → loop or sign off
```

---

## MCP Rule

- **Always prefer Unity MCP** over guessing project state.
- If MCP is unavailable: state *"Running without MCP evidence"* and fall back to code reasoning.

---

## Quality Gates

| Gate | Rule |
|------|------|
| Architect | No implementation before design exists |
| Implementation | No completion if runtime violates approved design |
| Tooling | No sign-off if state cannot be inspected/reproduced |
| Validation | No completion without correctness + stress evidence |
| Validation | No completion while regressions remain open |

---

## Output Format

```
[Team Lead]
Phase 1: preflight ✓ | tmux ✓ | team created ✓ | 4 agents spawned ✓

[Architect]
<design and decisions>

[Unity Dev]
<implementation and ECS details>

[Data Tool]
<tools, diagnostics, and support utilities>

[Tester]
<tests, stress results, and validation>
```
