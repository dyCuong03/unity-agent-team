# Unity DOTS Agent Team — SETUP

> **Purpose**: Production-oriented AI Agent Team for Unity DOTS development.
> **Architecture**: 1 top-level team + 4 fixed roles + internal subagents per role.
> **Philosophy**: Agents start work the moment they're spawned. No blocking preflight. Pull MCP / memory only when needed.

---

## Required MCP Servers

The package is designed around two MCP servers:

| Server | Purpose |
|---|---|
| `ai-game-developer` | Unity Editor introspection and mutation (the package's "Unity MCP") |
| `agentmemory` | Cross-session memory (recall, save, consolidate, reflect) |

If either is unavailable, agents proceed in fallback mode (state once, keep working). See `@.claude/docs/mcp-integration.md` for the full tool map.

---

## Optional: Experimental Agent Teams Mode

The default `/team` runs the four agents via the standard `Agent` tool — works everywhere, no configuration needed. To use Anthropic's experimental teams mode with tmux panes, add to `~/.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "preferences": {
    "tmuxSplitPanes": true,
    "autoBypassPermissions": true
  }
}
```

Then invoke `/team <task> --teams` to opt in.

---

## Hard Constraints

| # | Rule |
|---|---|
| 1 | **1 role = 1 agent.** No duplicates, no "-2"/"-3" suffixes. |
| 2 | **No dynamic agent spawning.** The team is fixed at boot. |
| 3 | **Subagents are internal.** They run inside the parent agent — no panes, no top-level promotion. |
| 4 | **Agents start work immediately** when spawned. No checklist preflight. |
| 5 | **Architect approval is required before unity-dev commits** — but unity-dev can start work in parallel and reconcile when the design lands. |
| 6 | **Tester evidence is required for completion.** No sign-off without `tests-run` + logs. |

---

## Phase 1 — Boot (Team Lead)

Executed by the Claude instance running `/team`. One pass.

```
STEP 1 → python .claude/scripts/preflight.py  (non-blocking, informational only)
STEP 2 → Spawn 2 (--fast) or 4 (--full) agents in parallel
         Each agent prompt contains its role + skill files (@-imports)
STEP 3 → (Optional) TaskCreate one task per agent for visibility
STEP 4 → Done. Agents self-configure and start work in Phase 2.
```

### Spawn templates

See `@.claude/commands/team.md`. Every spawn is parallel (one assistant turn, multiple Agent calls).

### Required skill imports per role

| Role | Files imported |
|---|---|
| Architect | `@.claude/docs/setup.md`, `@.claude/skills/architect/SKILL.md`, `@.claude/docs/architecture.md`, `@.claude/docs/mcp-integration.md`, `@.claude/skills/unity-dots-best-practices/SKILL.md` |
| Unity Dev | `@.claude/docs/setup.md`, `@.claude/skills/unity-dev/SKILL.md`, `@.claude/docs/architecture.md`, `@.claude/docs/mcp-integration.md`, `@.claude/skills/unity-dots-best-practices/SKILL.md`, `@.claude/skills/qa-validation/SKILL.md` |
| Data Tool | `@.claude/docs/setup.md`, `@.claude/skills/data-tool/SKILL.md`, `@.claude/docs/architecture.md`, `@.claude/docs/mcp-integration.md`, `@.claude/skills/editor-data-tools/SKILL.md`, `@.claude/skills/qa-validation/SKILL.md` |
| Tester | `@.claude/docs/setup.md`, `@.claude/skills/tester/SKILL.md`, `@.claude/docs/architecture.md`, `@.claude/docs/mcp-integration.md`, `@.claude/skills/qa-validation/SKILL.md`, `@.claude/skills/editor-data-tools/SKILL.md` |

---

## Phase 2 — Work (Each Agent, Parallel)

Each agent independently:

1. Begins work on the task **immediately** from its best understanding.
2. Self-corrects when upstream data (design, implementation, tooling) arrives.
3. Pulls `ai-game-developer` MCP **only when a decision needs Unity-side info**.
4. Pulls `agentmemory` **only when prior work in this area is likely**.
5. Saves a `memory_lesson_save` at handoff **only for non-obvious lessons**.

---

## Top-Level Roles (Fixed)

| # | Role | Agent | Core Responsibility |
|---|---|---|---|
| 1 | Architect | `architect` | ECS design, boundaries, update order, acceptance criteria, risks |
| 2 | Unity Developer | `unity-dev` | DOTS/ECS implementation, jobs, bakers, runtime logic |
| 3 | Data Tool Engineer | `data-tool` | Data pipelines, editor tools, inspectors, diagnostics |
| 4 | Tester / QA | `tester` | Functional, regression, determinism, stress, performance validation |

No additional top-level agents.

---

## Internal Subagents (Per Role)

Each role delegates internally — these never escape into top-level panes:

| Role | Subagents |
|---|---|
| Architect | `design-analyzer`, `dependency-mapper`, `architecture-validator` |
| Unity Dev | `code-generator`, `job-optimizer`, `burst-validator`, `memory-checker` |
| Data Tool | `debug-tool-builder`, `data-inspector`, `logging-analyzer`, `pipeline-builder` |
| Tester | `test-generator`, `stress-tester`, `race-condition-detector`, `performance-analyzer` |

---

## Communication

Every handoff must include:

- **Objective** — what this stage accomplished
- **Inputs consumed** — design / implementation / data passed in
- **Outputs produced** — files, decisions, evidence
- **Constraints** — what bounded the result
- **Open risks** — what's deferred or uncertain

Keep updates concise and technical. If implementation conflicts with design, escalate to Architect. If tests fail, return to the responsible role and continue the loop.
