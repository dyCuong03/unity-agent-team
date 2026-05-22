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

## Codex Review Gate (MANDATORY for every team task)

Every task executed by the team **must pass a `/codex:review` pass after the Architect publishes the design and again before final sign-off.**

1. **Plan review** — As soon as the Architect publishes a design, the orchestrator (or the agent acting as team lead) invokes `/codex:review` with the design plus the relevant recon facts. Architect must address every blocker / high-severity comment before unity-dev starts irreversible work.
2. **Implementation review** — Before Tester sign-off, run `/codex:review` again over the final diff. Any blocker found returns the task to the responsible role and the loop continues.
3. **Evidence** — Capture the `/codex:review` verdict (pass / changes-requested / block) plus a one-line summary in the completion output under a `Codex review:` field. Never declare a task complete without it.
4. **Fallback** — If `/codex:review` is unavailable, state `"Running without codex review"` once, escalate, and require an extra Architect + Tester review pass to compensate.

This rule applies to bug fixes, features, refactors, and tooling work alike. It is non-optional.

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

## CRG-First Codebase Understanding

Five specialized agents handle codebase investigation. All query `code-review-graph` MCP before reading any files.

| Agent | Use Case |
|-------|----------|
| `architecture-agent` | System architecture mapping, domain boundaries, execution flow |
| `codebase-reader` | Feature reading, entry point discovery, behavior summary |
| `bug-investigation` | Root cause tracing, write conflict detection, fix validation |
| `refactor-agent` | Blast radius analysis, safe migration planning |
| `feature-dev-agent` | Pattern discovery, extension point identification, consistent implementation |

### CRG Rules (apply to all 5 agents)

- Query `code-review-graph` before opening any file
- Never grep the repository blindly
- Never infer architecture from filenames
- Never open more than 8 files without graph justification
- If CRG is unavailable: state "Running without CRG evidence" once, then use targeted Grep

Full rules: `@.claude/rules/GRAPH_FIRST.md`
