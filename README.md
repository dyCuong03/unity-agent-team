# Unity DOTS Agent Team

A reusable, multi-agent Claude Code workflow for Unity DOTS development — coordinating Architect, Unity Developer, Data Tool Engineer, and Tester roles with enforced quality gates.

## What Is This?

This package turns Claude Code into a structured DOTS development team. Four specialized agents work in sequence — each with a defined role, skill set, and subagents — to design, implement, instrument, and validate ECS systems.

It is designed for **production DOTS projects**, not toy examples. The framework enforces role isolation, MCP-backed evidence, and explicit validation before any work is marked complete.

---

## Quick Start

### 1. Enable Agent Team Mode

Before running the team, add this to your Claude Code settings:

```sh
mkdir -p ~/.claude && cat > ~/.claude/settings.json << 'EOF'
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

Restart Claude Code, then run:

```
/team <your task description>
```

Example:

```
/team Add a health system with damage, healing, and death states
```

---

## Team Roles

### Architect
Designs the ECS architecture before any code is written. Owns:
- Component, buffer, and blob asset design
- System boundaries and update order
- Baker and authoring conversion strategy
- Performance constraints and acceptance criteria

**Gate:** No implementation starts until the Architect publishes a design.

### Unity Developer
Implements the approved ECS design. Owns:
- Systems, jobs, bakers, and data plumbing
- Burst validation and memory-conscious code
- Early surfacing of blockers and performance risks

**Gate:** Must follow the Architect's design exactly; deviations require Architect review.

### Data Tool Engineer
Adds tooling and observability. Owns:
- Editor utilities and inspection helpers
- Validators and data pipelines
- Debug visualizations and logging channels

**Gate:** Must not silently change runtime architecture.

### Tester / QA
Validates correctness and stability. Owns:
- Functional and stress test cases
- Determinism and race-risk checks
- Regression protection and benchmark evidence

**Gate:** Must block completion if correctness or stability is unverified.

---

## Execution Flow

```
Architect  →  Unity Dev  →  Data Tool  →  Tester
   Design        Implement      Tooling      Validate
                 ↕ escalate if needed
              Architect
```

1. **Architect** publishes an approved ECS design with acceptance criteria.
2. **Unity Developer** implements from the design.
3. **Data Tool Engineer** adds tooling, validators, and diagnostics.
4. **Tester** runs validation and stress testing.
5. **Loop** on defects until stable.

---

## Skill Files

Each role has its own skill definitions:

| Role | Skill Path |
|------|-----------|
| Architect | `skills/architect/` |
| Unity Developer | `skills/unity-dev/` |
| Data Tool Engineer | `skills/data-tool/` |
| Tester | `skills/tester/` |

Universal skills:
- `.claude/skills/unity-dots-best-practices/SKILL.md`
- `.claude/skills/editor-data-tools/SKILL.md`
- `.claude/skills/qa-validation/SKILL.md`

---

## Unity MCP Integration

This framework is designed to use **Unity MCP** ([IvanMurzak/Unity-MCP](https://github.com/IvanMurzak/Unity-MCP)) as the primary evidence source for all Unity project state.

**Core rule:** Always prefer MCP over guessing project state.

Use MCP for:
- Project structure and asset inspection
- Scene, prefab, and GameObject inspection
- Serialized data and authoring output
- Console logs and editor state
- Running tests and capturing evidence

If Unity MCP is unavailable, the team falls back to source code reading and states that MCP evidence is unavailable.

---

## Team Entry Points

| Command | Description |
|---------|-------------|
| `/team <task>` | Full 4-agent team boot sequence |
| `/start-unity-dots-team <task>` | Alias via skill system |

Both commands trigger the same workflow: preflight → team creation → parallel agent spawn → Phase 2 autonomous execution.

---

## Quality Gates Summary

| # | Gate | Enforcer |
|---|------|----------|
| 1 | No implementation before Architect-approved design | Architect |
| 2 | No runtime design changes without Architect review | Unity Dev |
| 3 | No tooling that silently changes runtime behavior | Data Tool |
| 4 | No sign-off without correctness + stress evidence | Tester |
| 5 | No completion while regressions are open | Tester |

---

## File Structure

```
unity-agent-team-publish/
├── .claude/
│   ├── agents/           # Role agent definitions
│   ├── commands/         # /team command entrypoint
│   ├── skills/           # Runtime skills (MCP, team boot)
│   └── CLAUDE.md         # Project-level constraints
├── skills/
│   ├── architect/        # Architect role skills
│   ├── unity-dev/        # Unity Dev role skills
│   ├── data-tool/        # Data Tool role skills
│   └── tester/           # Tester role skills
├── architecture.md       # System architecture reference
├── mcp-integration.md    # Unity MCP usage policy
└── README.md             # This file
```

---

## Customizing for Your Project

1. **Point the team at your Unity project** by describing its location in the task prompt:
   ```
   /team Add a stamina system to Assets/Games/Units
   ```

2. **Extend a role** by adding skill files to its `skills/` directory.

3. **Add subagents** to a role by editing its `skills/<role>/subagents.md`.

4. **Integrate Unity MCP** by ensuring the Unity MCP server is running before starting the team. See [Unity-MCP](https://github.com/IvanMurzak/Unity-MCP) for setup.

---

## Requirements

- Claude Code with Agent Team mode enabled (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`)
- Unity project with DOTS packages (Entities, Jobs, Burst)
- Unity MCP server (optional but strongly recommended)
- tmux (optional — team runs in degraded mode without it)
