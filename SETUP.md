# Unity DOTS Agent Team — SETUP

> **Purpose**: Production-oriented AI Agent Team for Unity DOTS development.
> **Architecture**: 1 top-level team + 4 fixed roles + internal subagents per role.
> **Rule**: No additional top-level roles. No coding before Architect design approval.

---

## Hard Constraints — Non-Negotiable

| Constraint | Rule |
|---|---|
| **1 role = 1 agent = 1 pane** | Each of the 4 roles spawns exactly ONE agent instance. |
| **No duplicate agents** | No "-2", "-3", etc. under any condition. No retry-based duplication. |
| **No dynamic agent spawning** | The 4-agent team is fixed at boot. No additional top-level agents. |
| **Subagents are internal only** | Subagents run within the parent agent. They MUST NOT create panes, tabs, or top-level agents. |
| **Team lead = coordination only** | The team lead (Claude instance running `/team`) does NOT execute tasks, does NOT appear in agent panes, creates NO panes. |
| **Pane count = agent count** | Total panes MUST equal exactly 4 (one per role). No extra panes. |
| **No UI creation from subagents** | Subagents must never open tmux panes, windows, or tabs. All UI belongs to the 4 main agents. |

**Violation of any constraint = STOP and escalate.**

---

## Phase 1 — Boot (Team Lead Only)

Phase 1 is executed by the **team lead** (the Claude instance that runs `/team`). It must complete in one pass.

```
STEP 1 → Verify preflight
STEP 2 → Create tmux session (claude-work)  [optional; degrade gracefully if unavailable]
STEP 3 → Create Agent Team
STEP 4 → Spawn exactly 4 agents, one per role, with mode: bypassPermissions
         Each agent prompt contains its role + skill files.
STEP 5 → Done. Agents self-configure (Phase 2).
```

### Phase 1 — Preflight

1. **Agent Team mode not enabled** → STOP. Instruct user with exact command.
2. **tmux unavailable** → Continue in degraded mode (no session).
3. **Always operate as multi-agent** when possible.

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

### Phase 1 — Spawn 4 Agents (Fixed Structure)

Spawn **exactly 4 agents in parallel**, one per role. Each role must appear **once and only once**. No duplicates.

Spawn all 4 using this template:

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

#### Roles and Names (exactly one each)

| Role | Agent Name |
|------|-----------|
| ECS Architect | `architect` |
| Unity Developer | `unity-dev` |
| Data Tool Engineer | `data-tool` |
| Tester / QA | `tester` |

**Do not spawn any additional agents.** The team is fixed.

---

## Phase 2 — Self-Configure (Each Agent, Parallel)

Once spawned, **each agent independently**:

1. Reads all files in its prompt.
2. Loads `@architecture.md` and `@mcp-integration.md` if not already loaded.
3. Loads runtime skills from `@.claude/skills/*` applicable to its role.
4. Sets up internal subagents from `@skills/<role>/subagents.md`. Subagents run **inside the agent's context only** — no pane creation, no top-level promotion.
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

| File | Purpose |
|------|---------|
| `@architecture.md` | ECS architecture patterns and templates |
| `@mcp-integration.md` | Unity MCP operating procedures |

---

## Non-Negotiable Rules Summary

| # | Rule |
|---|------|
| 1 | **Phase 1 is team-lead only.** Agents do NOT exist yet. |
| 2 | **1 role = 1 agent = 1 pane.** Exact match always. |
| 3 | **No duplicate agents** under any condition. |
| 4 | **Subagents are internal.** No panes, no top-level promotion. |
| 5 | **Team lead = coordination only.** No task execution, no panes. |
| 6 | Spawn all 4 agents **in parallel** with `mode: "bypassPermissions"`. |
| 7 | Each agent self-loads its skills — team lead does NOT pre-load them. |
| 8 | Architect approval is **required** before implementation begins. |
| 9 | No extra top-level agents. |
| 10 | **Always prefer MCP over guessing.** |
| 11 | Each role delegates complex work to internal subagents. |

---

## Top-Level Roles (Fixed — One Per Role)

| # | Role | Agent Name | Core Responsibility |
|---|------|-------------|---------------------|
| 1 | **Architect** | `architect` | ECS design, boundaries, update order, acceptance criteria, risks |
| 2 | **Unity Developer** | `unity-dev` | DOTS/ECS implementation, jobs, bakers, runtime logic |
| 3 | **Data Tool Engineer** | `data-tool` | Data pipelines, editor tools, inspectors, debug/diagnostics utilities |
| 4 | **Tester / QA** | `tester` | Functional, regression, determinism, stress, and performance validation |

**No other top-level roles exist. No agents beyond these 4.**
