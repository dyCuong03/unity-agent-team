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

