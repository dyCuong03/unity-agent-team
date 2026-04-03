# Unity DOTS Agent Team — SETUP

> **Purpose**: Production-oriented AI Agent Team for Unity DOTS development.
> **Architecture**: 1 top-level team + 4 fixed roles + internal subagents per role.
> **Rule**: No additional top-level roles. No coding before Architect design approval.

---

## Phase 1 — Boot (Team Lead Only)

Phase 1 is executed by the **team lead** (the Claude instance that runs `/team`). It must complete in one pass.

> **⚠️ Critical: Bash Commands Must Use Tool Calls**
>
> Claude Code **cannot** execute bash commands written as plain text in a command file.
> Any shell command (like `tmux new-session`) MUST be wrapped in a **Bash tool call block**.
> Writing `tmux new-session -s claude-work` as plain text in the prompt = **ignored**.
> The command file MUST contain an actual ` ```sh ` fenced block so Claude invokes the Bash tool.
>
> **Correct pattern:**
> ```sh
> tmux kill-session -t claude-work 2>/dev/null
> tmux new-session -d -s claude-work
> echo "Tmux session 'claude-work' created ✓"
> ```

### Phase 1 Steps (In Order)

```
STEP 1 → Verify preflight
STEP 2 → Create tmux session (claude-work)
STEP 3 → Create Agent Team
STEP 4 → Spawn 4 agents with mode: bypassPermissions
         Each agent prompt contains its role + skill files.
STEP 5 → Done. Agents self-configure (Phase 2).
```

### Phase 1 — Preflight

1. **Agent Team mode not enabled** → STOP. Instruct user with exact command.
2. **tmux unavailable** → Continue in degraded mode (no session).
3. **Always operate as multi-agent** when possible.

### Phase 1 — Tmux Session (Execute via Bash Tool)

> **CRITICAL**: The team lead MUST run the tmux command as an actual Bash tool call.
> Writing it as plain text in the prompt is NOT enough — it will be ignored by Claude Code.
> Insert a Bash tool call block to execute it immediately.

```sh
# Execute via Bash tool (not plain text)
# Claude Code runs INSIDE this tmux session named claude-work
tmux kill-session -t claude-work 2>/dev/null
tmux new-session -s claude-work
```

- Session name: `claude-work`
- If tmux is available → run the Bash block above.
- If tmux is unavailable → log "tmux unavailable — continuing without session."

### Phase 1 — Enable Agent Team Mode

Required `~/.claude/settings.json`:

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

### Phase 1 — Create Team

```json
{
  "team_name": "unity-dots-team",
  "description": "Unity DOTS agent team — architect, unity-dev, data-tool, tester"
}
```

### Phase 1 — Spawn 4 Agents

Spawn **all 4 agents in parallel** with `mode: "bypassPermissions"`.

Each agent prompt contains:
- Phase 1 completion confirmation
- Role definition file (`@skills/<role>/role.md`)
- Skills file (`@skills/<role>/skills.md`)
- Rules file (`@skills/<role>/rules.md`)
- Subagents file (`@skills/<role>/subagents.md`)
- `@SETUP.md` reference (so agent can load additional files)

```
┌─────────────────────────────────────────────┐
│  team-lead (you)                            │
│  STEP 1–5: preflight → tmux → team → spawn  │
│                                             │
│    ┌───────────┐  ┌───────────┐             │
│    │ Architect │  │ Unity Dev │             │
│    └───────────┘  └───────────┘             │
│    ┌───────────────┐  ┌───────────┐         │
│    │ Data Tool Eng │  │  Tester   │         │
│    └───────────────┘  └───────────┘         │
│         Phase 2: self-configure              │
└─────────────────────────────────────────────┘
```

### Phase 1 — Agent Spawn Template

```json
{
  "name": "<role-name>",
  "team_name": "unity-dots-team",
  "subagent_type": "general-purpose",
  "mode": "bypassPermissions",
  "prompt": [
    "@SETUP.md",
    "@skills/<role>/role.md",
    "@skills/<role>/skills.md",
    "@skills/<role>/rules.md",
    "@skills/<role>/subagents.md",
    "<task description>",
    "Phase 1 complete. You are now in Phase 2: self-configure.",
    "Load all referenced files in your prompt. Then begin your role."
  ]
}
```

---

## Phase 2 — Self-Configure (Each Agent, Parallel)

Once spawned, **each agent independently**:

1. Reads all files in its prompt.
2. Loads `@architecture.md` and `@mcp-integration.md` if not already loaded.
3. Loads runtime skills from `@.claude/skills/*` applicable to its role.
4. Sets up internal subagents from `@skills/<role>/subagents.md`.
5. Confirms readiness to team lead via message.
6. Awaits Architect design → begins work.

### Phase 2 — Per-Role Skill Loading

| Role | Additional Files to Load |
|------|--------------------------|
| **Architect** | `@.claude/skills/unity-dots-best-practices/SKILL.md` |
| **Unity Dev** | `@.claude/skills/unity-dots-best-practices/SKILL.md`, `@.claude/skills/qa-validation/SKILL.md` |
| **Data Tool Engineer** | `@.claude/skills/editor-data-tools/SKILL.md`, `@.claude/skills/qa-validation/SKILL.md` |
| **Tester** | `@.claude/skills/qa-validation/SKILL.md`, `@.claude/skills/editor-data-tools/SKILL.md` |

---

## Shared Architecture (Phase 2 Reference)

These files are shared across all roles after team creation:

| File | Purpose |
|------|---------|
| `@architecture.md` | ECS architecture patterns and templates |
| `@mcp-integration.md` | Unity MCP operating procedures |

---

## Non-Negotiable Rules Summary

| # | Rule |
|---|------|
| 1 | **Phase 1 is team-lead only.** Agents do NOT exist yet. |
| 2 | **Bash commands MUST use Bash tool calls** — plain text in prompts is ignored. |
| 3 | Spawn all 4 agents **in parallel** with `mode: "bypassPermissions"`. |
| 4 | Each agent self-loads its skills — team lead does NOT pre-load them. |
| 5 | Architect approval is **required** before implementation begins. |
| 6 | No extra top-level agents. |
| 7 | **Always prefer MCP over guessing.** |
| 8 | Each role delegates complex work to internal subagents. |

---

## Top-Level Roles (Fixed)

| # | Role | Core Responsibility |
|---|------|---------------------|
| 1 | **Architect** | ECS design, boundaries, update order, acceptance criteria, risks |
| 2 | **Unity Developer** | DOTS/ECS implementation, jobs, bakers, runtime logic |
| 3 | **Data Tool Engineer** | Data pipelines, editor tools, inspectors, debug/diagnostics utilities |
| 4 | **Tester / QA** | Functional, regression, determinism, stress, and performance validation |

---

## Agent Execution Environment Rules

This section defines the mandatory execution environment for all agent operations. Any setup that violates these rules is **invalid** and must be corrected before any task can proceed.

### Mandatory tmux Layout

The system **MUST** use `tmux` for all agent execution. This is a **hard requirement** — no exceptions.

- The terminal **MUST** be split into a **2×2 grid layout** (4 panes total).
- Each agent **MUST** run in its own dedicated pane as follows:

| Pane | Agent |
|------|-------|
| Top-Left | `architect` |
| Top-Right | `unity-dev` |
| Bottom-Left | `data-tool` |
| Bottom-Right | `tester` |

### Parallel Execution Requirement

- Agents **MUST** run in **parallel**, not sequentially.
- **No two agents** are allowed to share the same pane.
- Logs for **all 4 agents must remain visible simultaneously** at all times.
- The system **MUST NOT** fall back to single-pane or sequential execution under any circumstance.

### tmux Session Management

- If a `tmux` session does not already exist, it **MUST** be created automatically before any agent spawns.
- The session **MUST** be named `claude-work` (or equivalent, consistent name).
- The team lead is responsible for ensuring the session and layout exist prior to agent spawning.

### Example tmux Commands

The following commands create the required layout. These **MUST** be executed via Bash tool calls before spawning agents:

```sh
# Create a new tmux session (run in background)
tmux new-session -d -s claude-work

# Split the window into a 2x2 grid
# Split the main pane horizontally
tmux split-window -h -t claude-work

# Split the left pane vertically
tmux split-window -v -t claude-work:0.0

# Split the right pane vertically
tmux split-window -v -t claude-work:0.1
```

After these commands, the session `claude-work` will have 4 panes arranged in a 2×2 grid, ready for agent assignment.

### Layout Validation

Before spawning agents, the team lead **MUST** verify:

1. The `tmux` session exists and is named correctly.
2. Exactly **4 panes** are active.
3. Each pane is **assigned to a unique agent**.
4. All panes are **visible simultaneously** in a 2×2 grid.
5. No pane is shared between multiple agents.

### Enforcement

- This layout is **mandatory** and **non-negotiable**.
- Any execution environment that does not conform to these rules is considered **invalid**.
- The team lead **MUST NOT** proceed to Phase 2 (agent spawning) until the layout requirements are satisfied.
- If `tmux` is unavailable and the layout cannot be created, the team lead **MUST** halt execution and report the failure — do **not** fall back to an alternative setup.
