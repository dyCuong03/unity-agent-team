# Unity DOTS Agent Team

A reusable, multi-agent Claude Code workflow for Unity DOTS development — Architect, Unity Developer, Data Tool Engineer, and Tester roles spawned in parallel and wired to `ai-game-developer` (Unity MCP) and `agentmemory`.

## Philosophy

**Agents start work the moment they're spawned.** No blocking preflight. Pull MCP and memory tools only when actually needed.

---

## Install in another Unity project

Everything ships under `.claude/`. Recommended install (Claude does the work):

```sh
# from your Unity project root:
git clone git@github.com:dyCuong03/unity-agent-team.git unity-agent-team-publish
claude unity-agent-team-publish/SETUP.md
```

Claude reads `SETUP.md` and runs the installer end-to-end: it audits the source pack, detects any existing `.claude/` in your project, asks before overwriting, copies the pack under `<project>/.claude/`, verifies the install, and reports MCP server status.

### Manual install (if you prefer)

1. Copy this package's `.claude/` directory into your project root.
   - If your project already has a `.claude/` folder, **merge** rather than overwrite. The skill, agent, and command names here don't collide with Claude Code defaults.
   - Result: `<your-project>/.claude/agents/`, `<your-project>/.claude/skills/`, `<your-project>/.claude/commands/team.md`, `<your-project>/.claude/docs/`, `<your-project>/.claude/scripts/`.
2. Register the required MCP servers (see below).
3. From your project root, run `/team <task>` in Claude Code.

All `@-imports` inside this pack are written as `@.claude/...` so they resolve from the project root regardless of where you install Claude Code.

---

## Required MCP servers

| Server | Purpose |
|---|---|
| `ai-game-developer` | Unity Editor introspection and mutation |
| `agentmemory` | Cross-session memory |

If either is unavailable, agents state the fallback ("Running without MCP evidence" / "Running without memory recall") and continue.

---

## Optional: experimental Agent Teams mode

The default `/team` uses the standard `Agent` tool — works everywhere, zero config. For tmux panes per agent, opt in by adding this to your **user-level** `~/.claude/settings.json` (not project-level — do not commit this):

```json
{
  "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" },
  "preferences": { "tmuxSplitPanes": true }
}
```

Then run `/team <task> --teams`. Without the flag and env var, `--teams` is ignored.

---

## Usage

```sh
# Fast mode — Architect + Unity Dev (default)
/team Add a health system with damage and death states

# Full mode — all 4 agents
/team Add stamina regeneration with cooldowns --full

# Force experimental Teams backend (requires the env flag above)
/team Refactor inventory --full --teams
```

---

## Team roles

### Core DOTS team (4 roles)

#### Architect
Designs the ECS architecture: components, buffers, blob assets, system boundaries, update order, baker strategy, acceptance criteria. **Gate:** unity-dev must reconcile to the design before completion.

#### Unity Developer
Implements the ECS design: systems, jobs, bakers, runtime logic. All C# edits via `mcp__ai-game-developer__script-update-or-create` to keep Unity's AssetDatabase coherent.

#### Data Tool Engineer
Builds editor tooling, validators, inspectors, diagnostics. **Gate:** must not silently change runtime behavior.

#### Tester / QA
Validates correctness, scale, determinism. **Gate:** sign-off requires `tests-run` + log evidence.

---

### CRG-first investigation agents (5 roles)

All five use `code-review-graph` MCP before reading any files. Never grep blindly; never open files without graph evidence.

#### Architecture Agent (`architecture-agent`)
Maps high-level system architecture: domain boundaries, feature ownership, execution flow, dependency chains. Uses `get_architecture_overview` → `trace_execution_flow` → `map_dependency_graph`. Max 8 files, each justified.

#### Codebase Reader (`codebase-reader`)
Reads unfamiliar features quickly: entry points, execution chains, hidden dependencies. Uses `get_minimal_context` → `find_entry_points` → `trace_callers_callees`. Max 8 files.

#### Bug Investigation Agent (`bug-investigation`)
Traces symptom to root cause: finds component writers, competing systems, unintended mutations. Uses `trace_execution_flow` → `get_impact_radius`. Never assumes first suspicious file is root cause.

#### Refactor Agent (`refactor-agent`)
Safe refactoring with documented blast radius: dependency tracing, coupling reduction, migration plan + rollback. Uses `get_impact_radius` → `trace_dependencies` → `identify_shared_symbols`. No refactor without blast radius.

#### Feature Development Agent (`feature-dev-agent`)
Consistent feature implementation: finds existing patterns before writing new code. Uses CRG to locate extension points and trace similar features. Never introduces parallel architecture when one already exists.

---

## Execution flow

```
[architect]  [unity-dev]  [data-tool]  [tester]
     ↘            ↓            ↓           ↙
        all spawn simultaneously, self-correct as upstream data arrives
```

1. All agents spawn in **one parallel wave**.
2. Architect publishes design; others reconcile in-place.
3. Tester blocks completion until evidence passes.
4. Loop until stable.

---

## File structure

```
unity-agent-team-publish/
├── .claude/
│   ├── agents/                       # Role agent definitions (Claude Code agents)
│   │   ├── architect.md              # Core DOTS team
│   │   ├── unity-dev.md
│   │   ├── data-tool.md
│   │   ├── tester.md
│   │   ├── architecture-agent.md     # CRG-first investigation agents
│   │   ├── codebase-reader.md
│   │   ├── bug-investigation.md
│   │   ├── refactor-agent.md
│   │   └── feature-dev-agent.md
│   ├── commands/
│   │   └── team.md                   # /team slash command
│   ├── rules/
│   │   └── GRAPH_FIRST.md            # CRG-first rules for all investigation agents
│   ├── skills/                       # Claude Code skills (auto-discovered)
│   │   ├── architect/SKILL.md
│   │   ├── unity-dev/SKILL.md
│   │   ├── data-tool/SKILL.md
│   │   ├── tester/SKILL.md
│   │   ├── unity-dots-best-practices/SKILL.md
│   │   ├── editor-data-tools/SKILL.md
│   │   ├── qa-validation/SKILL.md
│   │   ├── start-unity-dots-team/SKILL.md
│   │   └── codebase-understanding/SKILL.md  # CRG-first navigation skill
│   ├── docs/                         # Reference docs imported via @-imports
│   │   ├── setup.md
│   │   ├── architecture.md
│   │   └── mcp-integration.md
│   ├── scripts/                      # Bundled helpers
│   │   ├── preflight.py
│   │   ├── dots_scan.py
│   │   └── validate_skill_pack.py
│   └── CLAUDE.md                     # Always-loaded project context
├── SETUP.md                          # Installer Claude reads via `claude unity-agent-team-publish/SETUP.md`
├── .gitignore
├── README.md                         # This file
└── LICENSE
```

Everything Claude Code needs lives under `.claude/`. The package root only carries `README.md`, `LICENSE`, and `.gitignore`.

---

## MCP integration

`ai-game-developer` is the primary evidence source for Unity-side state. Agents pull from it **when a decision actually depends on it** — not as a checklist.

Tool families used by the team (see `.claude/docs/mcp-integration.md` for the full map):

- Assets / scene / prefab introspection
- GameObject + Component get/modify
- Scripts (read, update-or-create, execute, delete)
- Console logs (get, clear)
- Editor state, selection
- Tests (run, capture)
- Screenshots (game view, scene view, camera, isolated)
- Reflection (method find, call)

`agentmemory` provides cross-session continuity. Agents recall when prior work likely exists and save a `memory_lesson` at handoff for non-obvious findings.

---

## Quality gates

| # | Gate | Enforcer |
|---|---|---|
| 1 | No silent architecture drift in implementation | unity-dev → architect |
| 2 | No tooling that silently changes runtime behavior | data-tool |
| 3 | No sign-off without `tests-run` + log evidence | tester |
| 4 | No completion while regressions remain open | tester |

---

## Bundled scripts

| Script | Purpose |
|---|---|
| `.claude/scripts/preflight.py` | Cross-platform check for Agent Team mode, tmux, MCP availability. Never blocks. |
| `.claude/scripts/dots_scan.py` | Fast first-pass DOTS anti-pattern scan over C# files. |
| `.claude/scripts/validate_skill_pack.py` | Validates frontmatter on every SKILL.md and agent file in this package. |

Run any of them with `python .claude/scripts/<name>.py --help`.

---

## Customizing

1. **Point the team at your Unity project** by describing its location in the task prompt:
   ```
   /team Add a stamina system to Assets/Games/Units
   ```
2. **Extend a role** by editing its `.claude/skills/<role>/SKILL.md`.
3. **Add subagents** to a role by editing the "Internal Subagents" section of its SKILL.md.
4. **Tighten or relax MCP enforcement** in each agent file under `.claude/agents/`.

---

## Requirements

- Claude Code with the `Agent` tool (or `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` for `--teams` mode)
- Unity project with DOTS packages (Entities, Jobs, Burst)
- `ai-game-developer` MCP server (strongly recommended)
- `agentmemory` MCP server (strongly recommended)
- Python 3.8+ (only for the bundled `scripts/`)
- tmux (optional — only for `--teams` mode panes)
