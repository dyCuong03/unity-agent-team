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

Execution requirements:

1. Enforce the preflight defined in `SETUP.md`.
2. If Agent Team mode is not enabled, stop and instruct the user to enable it with the exact required `~/.claude/settings.json` command.
3. If tmux panes are not active, continue in degraded mode.
4. Activate and run exactly 4 top-level agents:
   - Architect
   - Unity Dev
   - Data Tool Engineer
   - Tester
5. Assign each role its internal subagents and apply all loaded skill definitions.
6. Architect must design first and approve before implementation begins.
7. Unity Dev implements from the approved design.
8. Data Tool Engineer builds support tooling, diagnostics, and data workflows.
9. Tester validates correctness, stress behavior, race risk, and performance.
10. Always prefer Unity MCP over guessing project state.
11. If MCP is unavailable, state that execution is running without MCP evidence and fall back to code reasoning.
12. Iterate until the result is production-ready.

Output format:

[Architect]
<design and decisions>

[Unity Dev]
<implementation and ECS details>

[Data Tool]
<tools, diagnostics, and support utilities>

[Tester]
<tests, stress results, and validation>
