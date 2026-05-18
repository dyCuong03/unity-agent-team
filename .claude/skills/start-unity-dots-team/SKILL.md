---
name: start-unity-dots-team
description: Reference notes for the /team command. Documents how the 4-role Unity DOTS agent team (architect, unity-dev, data-tool, tester) boots with ai-game-developer MCP and agentmemory integration. The runnable entrypoint is the /team command — this skill is loaded by it.
---

# Start Unity DOTS Team

This skill is reference material for the `/team` command. The full execution logic lives in `@.claude/commands/team.md`.

## Preflight Order

1. Run `python .claude/scripts/preflight.py --verbose` (cross-platform check for Agent Team mode, MCP availability, tmux).
2. If preflight reports `agent-team-mode: missing` → ask user to enable per `~/.claude/settings.json` block in `@.claude/docs/setup.md`. Continue in single-session fallback if not enabled.
3. If preflight reports `mcp:ai-game-developer: missing` → state "Running without MCP evidence"; continue with code-only reasoning.
4. If preflight reports `mcp:agentmemory: missing` → state "Running without memory recall"; continue without cross-session memory.

## Execution

Delegate the rest to `@.claude/commands/team.md` with `$ARGUMENTS` forwarded as the task description.

```
Task: $ARGUMENTS
```

## Required Skill Loading (forwarded to each role)

| Role | Skill Files |
|---|---|
| Architect | `@.claude/skills/architect/SKILL.md`, `@.claude/skills/unity-dots-best-practices/SKILL.md` |
| Unity Dev | `@.claude/skills/unity-dev/SKILL.md`, `@.claude/skills/unity-dots-best-practices/SKILL.md`, `@.claude/skills/qa-validation/SKILL.md` |
| Data Tool | `@.claude/skills/data-tool/SKILL.md`, `@.claude/skills/editor-data-tools/SKILL.md`, `@.claude/skills/qa-validation/SKILL.md` |
| Tester | `@.claude/skills/tester/SKILL.md`, `@.claude/skills/qa-validation/SKILL.md`, `@.claude/skills/editor-data-tools/SKILL.md` |

All roles additionally load:
- `@.claude/docs/setup.md`
- `@.claude/docs/architecture.md`
- `@.claude/docs/mcp-integration.md`

## MCP & Memory Rules (forwarded)

- **Always prefer `ai-game-developer` MCP over guessing project state.**
- **Every agent calls `mcp__agentmemory__memory_recall` at start and `mcp__agentmemory__memory_lesson_save` at completion.**
- Team lead calls `mcp__agentmemory__memory_reflect` once per `/team` run.

## Completion Output

Each agent reports back to team lead via SendMessage (Teams mode) or final return (Agent-tool mode):

```
[<role>]
  Implemented / Designed / Tested:
  Open risks:
  Lessons saved to memory:
  Next steps:
```

Fallback: if Agent Teams mode is unavailable, `/team` runs the same 4-role flow sequentially in a single session — gates, skills, subagents, and MCP/memory calls are preserved.
