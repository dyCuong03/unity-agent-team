# Unity DOTS Agent Team — SETUP

> **Purpose**: Adaptive AI Agent Team for Unity DOTS development.
> **Architecture**: Triage-driven adaptive pipeline (1–4 agents) + optional full
> multi-agent mode with real tmux/worktrees.
> **Philosophy**: Agents start work immediately. No blocking preflight.
> Pull MCP / memory only when needed.

---

## Quick Start

```
# Adaptive mode (default) — spawns minimum agents needed
/team bug "enemy stuck after teleport"
/team feature "add stamina component with regen"
/team refactor deep "extract spawn logic into shared system"

# Full team mode — real 4-agent parallel team with tmux + git worktrees
/team --full "implement inventory system with ECS backend and UI"
```

---

## Setting Up in a New Project

Copy the `.claude/` directory structure to your target project. Here's what
you need and what each piece does.

### Required Files

```
your-project/
├── .claude/
│   ├── CLAUDE.md                    # Project philosophy + pipeline rules
│   ├── commands/
│   │   └── team.md                  # The /team command definition
│   ├── agents/                      # Agent role definitions
│   │   ├── architect.md
│   │   ├── unity-dev.md
│   │   ├── unity-dot-dev.md         # DOTS specialist (--full mode)
│   │   ├── qa-tester.md             # QA reviewer (--full mode)
│   │   ├── tester.md
│   │   ├── verifier.md
│   │   ├── data-tool.md
│   │   ├── bug-investigation.md
│   │   ├── refactor-agent.md
│   │   ├── system-mapper.md
│   │   ├── code-tracer.md
│   │   └── triage.md
│   ├── scripts/
│   │   ├── orchestrate.py           # Pipeline enforcer (adaptive mode)
│   │   ├── full_team.py             # Full team orchestrator (--full mode)
│   │   ├── triage.py                # Task classifier
│   │   ├── preflight.py             # Environment checker
│   │   ├── dots_scan.py             # DOTS anti-pattern scanner
│   │   └── validate_skill_pack.py   # Schema validator
│   ├── schemas/                     # JSON schemas for artifact validation
│   │   ├── triage.schema.json
│   │   ├── approved_plan.schema.json
│   │   ├── root_cause.schema.json
│   │   ├── impl_result.schema.json
│   │   ├── verification_result.schema.json
│   │   └── ownership.schema.json
│   ├── skills/                      # Skill packs (loaded per domain)
│   │   ├── architect/SKILL.md
│   │   ├── unity-dev/SKILL.md
│   │   ├── tester/SKILL.md
│   │   ├── unity-dots-best-practices/SKILL.md
│   │   ├── unity-foundation/SKILL.md
│   │   ├── burst-safety/SKILL.md
│   │   ├── ecs-job-patterns/SKILL.md
│   │   ├── memory-safety/SKILL.md
│   │   ├── qa-validation/SKILL.md
│   │   └── ... (see skills/ for full list)
│   ├── rules/                       # Policy/enforcement rules
│   │   ├── GRAPH_FIRST.md
│   │   ├── mcp-phase-gates.md
│   │   ├── ownership-boundaries.md
│   │   ├── escalation-policy.md
│   │   ├── dual-stack-domain-system.md
│   │   └── ... (see rules/ for full list)
│   ├── workspace-templates/         # Artifact templates
│   └── docs/
│       ├── setup.md                 # This file
│       ├── architecture.md
│       └── mcp-integration.md
└── workspace/                       # Runtime workspace (gitignore session files)
    ├── repo-knowledge.md            # PERSISTENT — commit
    ├── ecs-registry.md              # PERSISTENT — commit
    └── recent-changes.md            # PERSISTENT — commit
```

### Step-by-Step for New Project

1. **Copy `.claude/` directory**

   ```bash
   cp -r /path/to/source/.claude/ /path/to/new-project/.claude/
   ```

2. **Create workspace directory**

   ```bash
   mkdir -p /path/to/new-project/workspace
   ```

3. **Update `.gitignore`**

   Add to your project's `.gitignore`:

   ```gitignore
   # Session-scoped workspace files — do not commit
   workspace/domain-analysis.md
   workspace/design.md
   workspace/investigation.md
   workspace/test-plan.md
   workspace/migration-plan.md
   workspace/escalation-log.md
   workspace/skill-cache/
   workspace/full-team/
   workspace/triage.json
   workspace/pipeline.json
   workspace/root_cause.json
   workspace/approved_plan.json
   workspace/impl_result.json
   workspace/verification_result.json
   workspace/ownership.lock.json

   # Persistent workspace files — DO commit these
   # workspace/repo-knowledge.md
   # workspace/ecs-registry.md
   # workspace/recent-changes.md

   # Reports
   # reports/  ← commit or gitignore per your preference
   ```

4. **Initialize persistent knowledge files**

   ```bash
   touch workspace/repo-knowledge.md
   touch workspace/ecs-registry.md
   touch workspace/recent-changes.md
   ```

5. **Verify scripts work**

   ```bash
   python .claude/scripts/orchestrate.py preflight
   python .claude/scripts/full_team.py verify "test"
   ```

---

## Required MCP Servers

| Server | Purpose | Required? |
|---|---|---|
| `ai-game-developer` | Unity Editor introspection and mutation | Required for Phase 2+ |
| `agentmemory` | Cross-session memory (recall, save) | Optional |
| `code-review-graph` | CRG-first codebase understanding | Required for triage |

If a server is unavailable, agents state the fallback once and keep working.
See `@.claude/docs/mcp-integration.md` for the full tool map.

### MCP Configuration

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "ai-game-developer": {
      "type": "http",
      "url": "http://localhost:YOUR_PORT"
    },
    "agentmemory": {
      "type": "http",
      "url": "http://localhost:YOUR_PORT"
    }
  }
}
```

---

## Adaptive Mode (Default)

The default `/team` runs agents via the standard `Agent` tool. No special
configuration needed.

```
/team <intent> [depth] <task>
```

| Intent | Behavior |
|--------|----------|
| `bug` | Prepends `bug-investigation` agent |
| `feature` | Standard triage → pipeline |
| `refactor` | Prepends `refactor-agent`, forces architect + stepgated |
| `explore` | Triage-only, no implementation |

| Depth | Effect |
|-------|--------|
| `quick` | Downgrades complexity one tier |
| `normal` | Default |
| `deep` | Upgrades one tier, always uses tester, requires Codex review |

Pipeline is derived by `orchestrate.py plan` from triage classification.
See `team.md` for full documentation.

---

## Full Team Mode (`--full`)

Real multi-agent team with tmux windows + git worktrees.

### Prerequisites

All are HARD requirements — no fallback if missing:

1. **tmux** installed: `sudo apt install tmux` (Linux) or `brew install tmux` (macOS)

2. **Claude CLI** in PATH: `claude --version` should work

3. **Experimental agent teams enabled** — add to `~/.claude/settings.json`:

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

   **Restart Claude Code after adding.**

4. **Git worktree support**: `git worktree list` should work

### Usage

```
/team --full <task description>
```

This runs a two-phase startup:

**Phase 1 (Teammates First):**
- Creates tmux session with 4 windows
- Launches Claude in STANDBY in each window
- Validates all 4 teammate sessions are alive
- ABORTS if validation fails — no worktrees, no analysis

**Phase 2 (Assign — only after Phase 1 passes):**
- Creates 4 git worktrees at `../worktrees/<task-slug>/<agent>`
- Creates 4 git branches: `agent/<role>/<task-slug>`
- Generates per-agent assignment prompts
- Sends assignments to running teammate sessions

### Agents in Full Mode

| Agent | Role | Domain |
|-------|------|--------|
| `architect` | System architect / task planner | Planning, ownership, merge order |
| `unity-dev` | Senior Unity developer (non-DOTS) | MonoBehaviour, SO, UI, Addressables, VContainer |
| `unity-dot-dev` | Senior DOTS/ECS developer | Entities, ISystem, Jobs, Burst, components |
| `qa-tester` | QA tester / reviewer | Diff review, compile check, risk assessment |

### Worktree Layout

```
../worktrees/<task-slug>/
├── architect/      → branch: agent/architect/<task-slug>
├── unity-dev/      → branch: agent/unity-dev/<task-slug>
├── unity-dot-dev/  → branch: agent/unity-dot-dev/<task-slug>
└── qa-tester/      → branch: agent/qa-tester/<task-slug>
```

### tmux Session

```
Session: unity-agent-team-<task-slug>
├── Window 0: architect    (cd ../worktrees/<slug>/architect)
├── Window 1: unity-dev    (cd ../worktrees/<slug>/unity-dev)
├── Window 2: unity-dot-dev (cd ../worktrees/<slug>/unity-dot-dev)
└── Window 3: qa-tester    (cd ../worktrees/<slug>/qa-tester)
```

### Management Commands

```bash
# Full two-phase setup (teammates first → assign)
python .claude/scripts/full_team.py setup "<task>"

# Phase 1 only: spawn teammates in standby
python .claude/scripts/full_team.py spawn-teammates "<task>"

# Phase 2 only: assign work (teammates must be running)
python .claude/scripts/full_team.py assign "<task>"

# Check status
python .claude/scripts/full_team.py status "<task>"

# Verify infrastructure
python .claude/scripts/full_team.py verify "<task>"

# Regenerate prompts (after architect updates ownership)
python .claude/scripts/full_team.py prompts "<task>"

# Teardown (remove worktrees + kill tmux)
python .claude/scripts/full_team.py teardown "<task>"
```

### Reports

Each agent writes to `reports/team/<task-slug>/`:

| File | Author |
|------|--------|
| `architect-plan.md` | architect |
| `architect.md` | architect |
| `unity-dev.md` | unity-dev |
| `unity-dot-dev.md` | unity-dot-dev |
| `qa-tester.md` | qa-tester |
| `qa-report.md` | qa-tester |
| `final-integration-report.md` | integrator (main session) |

### Validation (Two Stages)

**Phase 1 validation** (`validate_teammate_sessions_first`) — runs BEFORE
any task analysis or worktree creation:
- Checks exactly 4 tmux windows exist with correct role names
- Checks panes are present
- Checks for running Claude processes (`ps aux | grep claude`)
- Checks `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- Prints: `tmux ls`, `tmux list-windows`, `tmux list-panes -a`
- ABORTS if fails — no worktrees created, no task analysis

**Phase 2 validation** (`validate_full_setup`) — runs AFTER worktrees + assignment:
- Re-runs Phase 1 checks
- Additionally checks exactly 4 worktrees exist
- Prints `git worktree list` + full mapping table
- Warns if any infrastructure is incomplete

---

## Hard Constraints

| # | Rule |
|---|---|
| 1 | Adaptive mode: triage determines pipeline. No fixed team. |
| 2 | Full mode: exactly 4 agents, always. No more, no less. |
| 3 | Full mode: real worktrees + tmux or fail. No internal subagent fallback. |
| 4 | Agents start work immediately when spawned. No checklist preflight. |
| 5 | Every phase boundary is a Python gate (`orchestrate.py gate`). |
| 6 | No merge without verification (`verification_result.json.status == "PASS"`). |
| 7 | Full mode: no merge without QA approval (`qa-report.md` says APPROVE). |
| 8 | Skill packs loaded per domain, not nested subagents. |
| 9 | Never commit user-level settings (`~/.claude/settings.json`) to repo. |

---

## Customizing for Your Project

### Adjust File Ownership Patterns

Edit `AGENT_ROLES` in `.claude/scripts/full_team.py` to match your project's
directory structure. The default patterns assume:

- DOTS code lives in `Assets/**/Systems/`, `Assets/**/DOTS/`, `Assets/**/ECS/`
- Unity code is everything else under `Assets/`
- QA only touches `reports/` and `workspace/`

### Add Project-Specific Skills

Create new skill files under `.claude/skills/<your-skill>/SKILL.md`.
Reference them in agent definitions under `.claude/agents/`.

### Modify Agent Roles

For projects without DOTS, you can:
- Replace `unity-dot-dev` with a second domain specialist
- Adjust ownership patterns in `full_team.py`
- Update agent definitions in `.claude/agents/`

---

## Troubleshooting

### "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS is not set"

Add to `~/.claude/settings.json` and restart Claude Code:
```json
{"env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}}
```

### "tmux is not installed"

```bash
# Ubuntu/Debian
sudo apt install tmux

# macOS
brew install tmux

# Windows (WSL required)
sudo apt install tmux
```

### "git worktree not supported"

Update git: `git --version` should be 2.5+.

### Worktree creation fails

Check for existing branches:
```bash
git branch --list "agent/*"
```

Remove stale worktrees:
```bash
git worktree prune
```

### tmux session already exists

```bash
tmux kill-session -t unity-agent-team-<slug>
```

Or use teardown:
```bash
python .claude/scripts/full_team.py teardown "<task>"
```
