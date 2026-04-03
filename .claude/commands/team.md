---
description: Run the full Unity DOTS agent team package from SETUP.md with all roles, skills, subagents, MCP rules, and activation gates.
argument-hint: "<task>"
---

Load and fully apply this package before doing any real work:

@SETUP.md
@architecture.md
@mcp-integration.md

Role package files:

@skills/architect/role.md
@skills/architect/skills.md
@skills/architect/rules.md
@skills/architect/subagents.md

@skills/unity-dev/role.md
@skills/unity-dev/skills.md
@skills/unity-dev/rules.md
@skills/unity-dev/subagents.md

@skills/data-tool/role.md
@skills/data-tool/skills.md
@skills/data-tool/rules.md
@skills/data-tool/subagents.md

@skills/tester/role.md
@skills/tester/skills.md
@skills/tester/rules.md
@skills/tester/subagents.md

Runtime skill package:

@.claude/skills/start-unity-dots-team/SKILL.md
@.claude/skills/unity-dots-best-practices/SKILL.md
@.claude/skills/editor-data-tools/SKILL.md
@.claude/skills/qa-validation/SKILL.md

Task:

$ARGUMENTS

---

## Execution Requirements

### Preflight

1. **Agent Team mode not enabled** → STOP. Instruct user with the exact `~/.claude/settings.json` command from SETUP.md Section 2.
2. **tmux unavailable** → Continue in degraded mode. Keep full team workflow.
3. **Always operate as multi-agent** when possible.

### Tmux Session

- Session name: `clude-work` (set via `tmux new-session -s claude-work`)
- If tmux is available, create/use this named session for the team run.
- If tmux is unavailable, proceed without a session (degraded mode is acceptable).

### Auto Bypass Permissions (Setup Phase)

- `autoBypassPermissions: true` is set in `~/.claude/settings.json` preferences.
- When active, Claude Code automatically skips interactive permission prompts during team initialization.
- **Scope**: Applies only to team setup operations (agent spawning, file writes during activation).
- **Runtime safety**: Code implementation, file writes, and destructive operations still require explicit approval unless `mode: "bypassPermissions"` is explicitly passed to the agent spawn call.
- **Rule**: Use `mode: "bypassPermissions"` on Agent spawn calls during team setup to enable the auto bypass behavior.

### Team Agents

Activate exactly 4 top-level agents:

| Agent | Role |
|-------|------|
| `Architect` | Design, ECS boundaries, acceptance criteria |
| `Unity Dev` | DOTS/ECS implementation, jobs, bakers |
| `Data Tool Engineer` | Data pipelines, editor tools, diagnostics |
| `Tester` | Validation, stress testing, regression coverage |

### Agent Spawning Rule

Spawn each agent with `mode: "bypassPermissions"` during team initialization:

```json
{
  "name": "<agent-name>",
  "team_name": "<team-name>",
  "mode": "bypassPermissions"
}
```

This ensures the `autoBypassPermissions` setting takes effect for all setup-phase agent spawns.

### Skill Assignment

Assign each role its internal subagents and apply ALL loaded skill definitions from the skill files above.

### Workflow Order

1. **Architect** → Analyze requirements + MCP evidence → Publish approved design (component model, system boundaries, update order, baker strategy, performance constraints, risks, acceptance criteria)
2. **Unity Dev** → Implement from approved design only → Surface blockers early
3. **Data Tool Engineer** → Build tooling, diagnostics, debug utilities, data pipelines
4. **Tester** → Validate correctness, determinism, stress, performance → Block if evidence insufficient
5. **Iterate** → Loop until production-ready

### MCP Rule

- **Always prefer Unity MCP** over guessing project state.
- If MCP is unavailable: state *"Running without MCP evidence"* and fall back to code reasoning.
- Use MCP to inspect: scenes, prefabs, assets, scripts, GameObjects, components, authoring data, runtime state, console logs, test output.

### Quality Gates

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
[Architect]
<design and decisions>

[Unity Dev]
<implementation and ECS details>

[Data Tool]
<tools, diagnostics, and support utilities>

[Tester]
<tests, stress results, and validation>
```
