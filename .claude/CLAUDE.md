# Unity DOTS Agent Team

This project packages a reusable Claude Code team for Unity DOTS development.

## Philosophy

**Agents start work the moment they're spawned.** No blocking preflight, no checklist before doing the task. MCP and memory tools are pulled when actually needed, not as ceremony.

## Required MCP Servers

| Server | Purpose |
|---|---|
| `ai-game-developer` | Unity Editor introspection and mutation |
| `agentmemory` | Cross-session memory (recall, save, consolidate, reflect) |

If either is unavailable, agents state the fallback once and keep working. See `@.claude/docs/mcp-integration.md`.

## Optional: Experimental Agent Teams Mode

The default `/team` uses the standard `Agent` tool — no setup required. To opt in to the experimental teams mode with tmux panes, add to `~/.claude/settings.json`:

```json
{
  "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" },
  "preferences": { "tmuxSplitPanes": true }
}
```

Then run `/team <task> --teams`.

## Team Activation

When this package handles a task:

1. Run `python .claude/scripts/preflight.py` (informational, never blocks).
2. Spawn the 4 fixed roles in parallel — `architect`, `unity-dev`, `data-tool`, `tester` (or just 2 in `--fast` mode).
3. Each agent self-loads its skills via `@`-imports and starts work immediately.

Entrypoints:
- `/team <task>` (default — fast, 2 agents)
- `/team <task> --full` (all 4 agents)

## Skill Files

| Location | Purpose |
|---|---|
| `.claude/skills/<role>/SKILL.md` | Per-role brief (architect, unity-dev, data-tool, tester) |
| `.claude/skills/unity-dots-best-practices/SKILL.md` | Shared DOTS guidance |
| `.claude/skills/editor-data-tools/SKILL.md` | Shared editor tooling guidance |
| `.claude/skills/qa-validation/SKILL.md` | Shared QA guidance |
| `.claude/skills/start-unity-dots-team/SKILL.md` | Reference notes for `/team` |

## Execution Order

1. **Architect** publishes a design. Other agents may have already started in parallel and reconcile when it arrives.
2. **Unity Dev** implements, escalating any design conflict.
3. **Data Tool** adds tooling, validators, diagnostics.
4. **Tester** validates and blocks completion until evidence supports sign-off.
5. Loop on defects.

## Architect Gate

The design must cover:
- Feature scope
- ECS data model
- Entity / component ownership
- System responsibilities and update order
- Baker / authoring conversion plan
- Performance constraints
- Acceptance criteria
- Known risks

Once published, unity-dev / data-tool / tester self-correct against it.

## Subagent Rule

Each role delegates non-trivial work to its internal subagents (listed in `.claude/skills/<role>/SKILL.md`). Subagents stay inside the parent agent — no panes, no top-level promotion.

## MCP & Memory Rule

- **Prefer `ai-game-developer` MCP over guessing Unity-side state** — but only when you actually need to verify or mutate Unity state. Don't pull tools as ceremony.
- **Use `agentmemory` when prior work likely exists** — recall and search. Save a lesson at handoff only when it's non-obvious.
- If a tool is unavailable, state "Running without MCP evidence" / "Running without memory recall" once and continue.

## Unity DOTS Rules

- Prefer `IComponentData`, `IBufferElementData`, `BlobAssetReference<T>`, `IAspect`, `ISystem`, jobs, and Burst.
- Optimize for data layout, cache locality, predictable frame cost.
- No managed allocations in hot paths.
- Minimize structural changes in tight loops (ECB or enableable components).
- Keep authoring/editor code separate from runtime (asmdef boundaries).
- Sync points, main-thread work, and archetype churn are explicit costs.

## Role Boundaries

| Role | Owns | Must not |
|---|---|---|
| Architect | Design, ECS boundaries, update flow, acceptance criteria | Code |
| Unity Dev | Runtime implementation | Change architecture without approval |
| Data Tool | Editor tools, validators, diagnostics | Silently change runtime behavior |
| Tester | Test cases, stress, regression, sign-off | Approve without evidence |

## Communication

Every handoff: objective, inputs, outputs, constraints, open risks. Concise and technical. Conflicts escalate; tests-fail returns to the responsible role; loop continues.
