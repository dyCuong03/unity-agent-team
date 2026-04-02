---
name: start-unity-dots-team
description: Start a 4-role Unity DOTS agent team using architect, unity-dev, data-tool, and tester. Invoke manually for feature work that benefits from coordinated design, implementation, tooling, and QA.
argument-hint: "[task]"
disable-model-invocation: true
---

Before doing any real work, enforce this preflight:

1. Confirm Agent Team mode is enabled through `~/.claude/settings.json`.
2. Required user-level configuration:

```sh
cat > ~/.claude/settings.json << 'EOF'
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "preferences": {
    "tmuxSplitPanes": true
  }
}
EOF
```

3. If Agent Team mode is not enabled, stop and instruct the user to run the exact command above.
4. If tmux panes are unavailable, continue in degraded mode.

Create a Unity DOTS agent team for this task:

$ARGUMENTS

Team creation rules:

1. Activate Agent Team mode and create exactly 4 active agents:
   - `architect`
   - `unity-dev`
   - `data-tool`
   - `tester`
2. Assign each agent:
   - its role
   - its full skill set
   - its internal subagents
3. Load all package skill definitions before task execution:
   - `./skills/architect/*`
   - `./skills/unity-dev/*`
   - `./skills/data-tool/*`
   - `./skills/tester/*`
   - `./.claude/skills/*`
4. Do not ignore any skill definition in the package.
5. Each role must internally delegate complex work to subagents instead of solving everything directly.

Execution requirements:

1. Architect goes first and publishes a design before any implementation starts.
2. Unity Developer follows the approved design strictly.
3. Data Tool Engineer provides data processing, editor tools, validators, and debugging helpers as needed.
4. Tester validates behavior, race risk, stress limits, regressions, and acceptance criteria before sign-off.
5. ALWAYS prefer MCP over guessing project state.
6. If Unity MCP is available, use it for project inspection, ECS-related authoring inspection, buffers, logs, tests, and runtime-facing state.
7. If Unity MCP is unavailable, fall back to code reading and reasoning and state that MCP evidence is unavailable.
8. Loop on defects until stable.

Completion requirements:

- Summarize architecture decisions, implementation status, tooling added, validation results, open risks, and next steps.
- Keep the output structured by role.
- Clean up the team only after all teammate work is complete.

Fallback:

- If agent teams are unavailable, emulate the same 4-role workflow in a single session while preserving the same gates, skill loading, and subagent behavior.
