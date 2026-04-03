# Unity DOTS Agent Team — SETUP

> **Purpose**: Production-oriented AI Agent Team for Unity DOTS development.
> **Architecture**: 1 top-level team + 4 fixed roles + internal subagents per role.
> **Rule**: No additional top-level roles. No coding before Architect design approval.

---

## 1. Top-Level Roles (Fixed — Do Not Change)

| # | Role | Core Responsibility |
|---|------|---------------------|
| 1 | **Architect** | ECS design, boundaries, update order, acceptance criteria, risks |
| 2 | **Unity Developer** | DOTS/ECS implementation, jobs, bakers, runtime logic |
| 3 | **Data Tool Engineer** | Data pipelines, editor tools, inspectors, debug/diagnostics utilities |
| 4 | **Tester / QA** | Functional, regression, determinism, stress, and performance validation |

---

## 2. Required Environment Setup

### 2.1 Enable Agent Team Mode

Required `~/.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "preferences": {
    "tmuxSplitPanes": true
  }
}
```

Apply via:

```sh
mkdir -p ~/.claude && cat > ~/.claude/settings.json << 'EOF'
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "preferences": {
    "tmuxSplitPanes": true,
    "autoBypassPermissions": true
  }
}
EOF
```

### 2.2 Preflight Rules

- **Agent Team mode not enabled** → STOP. Instruct user with exact command above.
- **tmux unavailable** → Continue in degraded mode. Keep full team workflow.
- **Always operate as multi-agent** when possible.

### 2.3 Tmux Session

- Default tmux session name: `claude-work`
- Command: `tmux new-session -s claude-work`
- If tmux is unavailable, fall back to no-session mode.

### 2.4 Auto Bypass Permissions (Setup Phase)

- `autoBypassPermissions: true` in settings activates automatically during team setup.
- When `autoBypassPermissions` is active, Claude Code skips interactive permission prompts.
- Use this only during team initialization; runtime code changes still require explicit approval unless overridden.

---

## 3. Team Activation (On Load)

### Activation Steps

1. Verify Agent Team mode is enabled.
2. Activate the Agent Team.
3. Create exactly 4 active agents: Architect, Unity Dev, Data Tool Engineer, Tester.
4. Assign each agent: role + skills + internal subagents.
5. Load all package skill definitions.

### Activation Rules

- No extra top-level agents.
- Each role delegates complex work to internal subagents.
- Architect approval is **required** before implementation begins.

---

## 4. Mandatory Skill Loading

### Package Skill Files

Load ALL of the following in order:

| Category | Files |
|----------|-------|
| Architect | `./skills/architect/{role,skills,rules,subagents}.md` |
| Unity Dev | `./skills/unity-dev/{role,skills,rules,subagents}.md` |
| Data Tool | `./skills/data-tool/{role,skills,rules,subagents}.md` |
| Tester | `./skills/tester/{role,skills,rules,subagents}.md` |

### Runtime Skills (if present)

Load ALL from `./.claude/skills/*`:

- `start-unity-dots-team/SKILL.md`
- `unity-dots-best-practices/SKILL.md`
- `editor-data-tools/SKILL.md`
- `qa-validation/SKILL.md`

### Skill Rules

- **Do not skip** any skill definition.
- Skills influence decisions, generation, tooling, and validation.
- **Conflict resolution**: Skill definition wins over role action unless user explicitly overrides.

---

## 5. Role Definitions

### 5.1 Architect

**Authority**: Design approval, design changes, performance constraints, risks.

**Must define before implementation**:
- ECS component and buffer model
- System boundaries and responsibilities
- Update ordering
- Authoring and baker strategy
- Performance constraints
- Acceptance criteria
- Known risks

### 5.2 Unity Developer

**Authority**: Low-level implementation details that do not violate architecture.

**Must**:
- Implement from approved design only
- Escalate design conflicts instead of silently redesigning
- Surface blockers, risks, and performance tradeoffs early

**Implements**: ECS runtime, jobs, bakers, integration.

### 5.3 Data Tool Engineer

**Authority**: Tooling structure and diagnostics workflow.

**Must**:
- Build data processors, editor tools, inspectors, debug overlays, validators
- NOT change runtime architecture without Architect review

### 5.4 Tester / QA

**Authority**: Can block completion when evidence is insufficient.

**Must**:
- Design and execute functional, regression, determinism, stress, performance validation
- Validate against acceptance criteria, observed runtime behavior, scaling limits

---

## 6. Mandatory Workflow

```
1. Architect  → Analyze + publish design + acceptance criteria
2. Unity Dev → Implement from approved design
3. Data Tool → Build tooling + diagnostics + debug utilities
4. Tester    → Validate correctness + stress + performance
5. Loop      → Findings → responsible role → repeat until stable
```

**Gate rule**: No later phase may bypass an unresolved earlier gate.

---

## 7. Internal Subagent Policy

### When to Delegate

- Task is ambiguous → structured analysis subagent
- Implementation spans multiple systems → generation subagent
- Performance/correctness risk is material → validation subagent
- Validation requires independent pass before handoff

### Minimum Internal Behavior (non-trivial tasks)

1. Analysis pass
2. Generation / synthesis pass
3. Validation pass

---

## 8. MCP Operating Policy

### Use MCP For

- Inspect scenes, prefabs, assets, packages, scripts, serialized state
- Inspect GameObjects, Components, authoring data, runtime-visible structure
- Read console logs, editor state
- Run tests, gather validation output
- Inspect data for ECS debugging, tooling, verification

### Fallback (No MCP)

- Use direct code reading for implementation details.
- State: *"Running without MCP evidence."*
- Do NOT assume project state without verification.

### Mismatch Protocol

1. Inspect with MCP
2. Identify mismatch
3. Report explicitly
4. Proceed only after mismatch is understood

---

## 9. Communication Contract

Every handoff must include ALL of:

- **Objective** — what this phase accomplishes
- **Inputs examined** — data, files, MCP evidence used
- **Outputs produced** — deliverables
- **Constraints still active** — rules, limits still in effect
- **Open risks** — unresolved concerns
- **Explicit next owner** — who receives this work

---

## 10. Role-to-Role Handoff Requirements

### Architect → Unity Developer

- Component and buffer model
- System responsibilities
- Update ordering
- Authoring and baker strategy
- Performance constraints
- Acceptance criteria
- Known risks

### Unity Developer → Data Tool Engineer

- Implemented runtime surfaces
- Required debug hooks
- Key state transitions to inspect
- Data pain points
- Profiler-sensitive areas

### Data Tool Engineer → Tester

- Available validators
- Debug views and instrumentation
- Reproducible fixtures
- Logging channels
- Known observability gaps

### Tester → Team

- Passed checks
- Failed checks
- Reproduction steps
- Severity + impact on acceptance criteria
- Recommendation: continue / fix / sign off

---

## 11. Quality Gates

| Gate | Rule |
|------|------|
| **Architect** | No implementation before design exists |
| **Implementation** | No completion if runtime violates approved design |
| **Tooling** | No sign-off if critical state cannot be inspected/reproduced |
| **Validation** | No completion without correctness evidence |
| **Validation** | No completion without stress evidence for scale-sensitive systems |
| **Validation** | No completion while regressions remain open |

---

## 12. DOTS Constraints

- Prefer: `IComponentData`, `IBufferElementData`, `BlobAsset`, `Aspect`, `ISystem`, jobs, Burst
- Optimize: cache locality, memory predictability, low sync overhead
- Minimize: structural changes in hot paths, managed allocations in simulation loops
- Favor: explicit ownership, deterministic data flow, high entity counts, stable frame cost

---

## 13. Definition Of Done

All must be true before work is complete:

- [ ] Architect-approved design is implemented
- [ ] Tooling and observability are sufficient for maintenance
- [ ] Tests and stress validation pass
- [ ] Performance constraints respected (or deviations documented + approved)
- [ ] Open risks resolved or explicitly accepted

**If any item is missing → loop continues.**

---

## 14. When To Use This Team

### Use For

- New DOTS gameplay systems
- ECS refactors
- Performance-critical simulation features
- Tooling-heavy iteration workflows
- High entity-count scenarios
- Debugging and stabilization of live Unity project state

### Do NOT Use For

- Generic brainstorming
- Non-DOTS, non-Unity tasks

---

## 15. Non-Negotiable Rules Summary

| # | Rule |
|---|------|
| 1 | Architect must design first |
| 2 | Unity Dev follows approved design strictly |
| 3 | Data Tool Engineer owns tooling + diagnostics |
| 4 | Tester owns validation + can block completion |
| 5 | Each role delegates complex work to subagents |
| 6 | **Always prefer MCP over guessing** |
| 7 | No extra top-level agents |
