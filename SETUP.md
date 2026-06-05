# Unity DOTS Agent Team — SETUP

> **What this is.** A Claude Code package that runs an adaptive Unity DOTS
> agent pipeline. Triage classifies the task; the orchestrator derives the
> minimum viable agent composition; every phase is artifact-gated by Python.
>
> **What it is not.** A fixed-4-agent template. No always-on tester. No nested
> subagent fan-out. No tmux dependency.

---

## Install

1. Copy the `.claude/` folder into your Unity project root (or root of any
   repo you want to use it from).
2. Copy `SETUP.md`, `README.md`, `CHANGELOG.md`, `MIGRATION.md`, and `LICENSE`
   alongside (optional but recommended).
3. Open Claude Code in the project. The `/team` slash command is now
   available.

That is the whole install. There is no global config to enable.

### Optional: tmux pane-per-agent UI

Only if you want one tmux pane per spawned agent. Add to `~/.claude/settings.json`:

```json
{
  "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" },
  "preferences": { "tmuxSplitPanes": true }
}
```

Restart Claude Code. Then invoke `/team` as usual — the orchestrator detects
the env flag and uses panes. **Without this**, the system runs identically via
the standard `Agent` tool. No degraded mode, no missing features.

---

## Required runtime

- **Python 3.8+** on PATH. The orchestrator (`.claude/scripts/orchestrate.py`)
  is the runtime enforcer. It uses only the standard library — no pip install.
- **`code-review-graph` MCP** is strongly recommended. The triage agent and
  every investigator use it. Without it, agents fall back to targeted grep and
  reduce their confidence scores; the pipeline still runs.
- **`ai-game-developer` MCP** is recommended for any Unity-side inspection or
  script writes.

That is the entire dependency list. No npm, no Docker, no node modules.

---

## Verify install

From the project root:

```sh
python .claude/scripts/orchestrate.py preflight
```

Expected:

```
[preflight]
  repo_root        : <your repo>
  workspace        : <repo>/workspace
  schemas          : present
  templates        : present
  agent-team-mode  : off (default)
  tmux             : available | unavailable
  result           : informational — never blocks
```

Then validate the schemas + templates round-trip:

```sh
python .claude/scripts/orchestrate.py validate .claude/workspace-templates/triage.json triage
```

Expected: `[validate] OK — triage.json matches triage`.

If both pass, you are installed.

---

## Run your first task

```
/team explore "What does the spawner system do?"
```

Triage runs alone (CRG + fingerprinting), writes
`workspace/triage.json`, and `orchestrate.py finalize` reports completion.
No design, no implementation — `explore` intent is triage-only.

For real work:

```
/team bug "Health bar shows 0 after respawn"
/team feature "Add stamina component + regen system"
/team refactor deep "Extract zone spawn logic into shared SpawnerSystem"
```

The orchestrator picks the agent composition. You do not pre-select agents.

---

## Using `/team --team`

`/team --team <task>` runs the task as a **Claude Agent Teams** team instead of the
adaptive single-session pipeline. The current Claude Code session becomes the
**teamlead** and spawns exactly **4 persistent teammates on Sonnet** via the
harness-native `TeamCreate` + `Agent(team_name=…)` primitives, coordinating them
through a shared task list. This is **not** normal subagents, **not** simulated
markdown roles, and **not** the manual worktree mode.

**1. Enable Agent Teams** (one-time). In `~/.claude/settings.json`:
```json
{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" },
  "preferences": { "tmuxSplitPanes": true } }
```
Restart Claude Code. (`tmuxSplitPanes` gives one tmux pane per teammate.)

**2. Verify availability:**
```sh
grep -q '"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"[[:space:]]*:[[:space:]]*"1"' ~/.claude/settings.json \
  && echo "agent-teams: ON" || echo "agent-teams: OFF"
```

**3. Run:**
```
/team --team analyze the /team flow and improve Unity task support
```

**4. The 4 required teammates** (all Sonnet):

| Teammate | Responsibility |
|----------|----------------|
| `architect` | architecture analysis, ownership, execution plan, scope control |
| `unity-dots-dev` | Unity DOTS/ECS, Jobs, Burst, Entities, ECB, dependencies, performance |
| `unity-dev` | Unity UI, MonoBehaviour, gameplay, VContainer, Addressables, pooling, DOTween |
| `qa-tester` | test matrix, regression, root-cause validation, final APPROVE/BLOCK |

**5. Inspect teammates:** with `tmuxSplitPanes: true`, each teammate is a tmux pane.
The teamlead surfaces the team name (`team-<slug>`) and any attach hint the runtime
prints. Track progress via the shared task list (`TaskList`); teammate messages are
delivered to the teamlead automatically.

**6. If Agent Teams is unavailable:** the command **fails fast** with a `[BLOCK]`
message explaining how to enable it. It does **not** fall back to subagents,
single-agent, or simulated roles.

**7–9. `/team --team` is NOT:** normal subagent mode · simulated markdown roleplay ·
manual worktree mode. (For git-worktree isolation use the separate `/team --worktrees`.)

`/team --full` is a **deprecated alias** for `--team` (prints a deprecation notice,
then behaves identically).

---

## File layout reference

```
.claude/
├── CLAUDE.md                       — project memory loaded on every run
├── commands/
│   └── team.md                     — the adaptive /team command
├── agents/                         — subagent_type definitions
│   ├── triage.md                   — always runs first
│   ├── verifier.md                 — default verification for tiny/small/medium
│   ├── architect.md, unity-dev.md, …
├── skills/                         — skill packs (loaded into agents, never spawned)
│   ├── triage/SKILL.md
│   ├── verifier/SKILL.md
│   ├── burst-safety/SKILL.md
│   ├── ecs-job-patterns/SKILL.md
│   ├── memory-safety/SKILL.md
│   ├── ownership-partitioning/SKILL.md
│   ├── unity-dots-best-practices/SKILL.md
│   └── …
├── scripts/                        — runtime enforcement (Python stdlib only)
│   ├── orchestrate.py              — preflight, reset, plan, gate, ownership-check, finalize
│   ├── triage.py                   — helper for the triage agent
│   ├── preflight.py, dots_scan.py, validate_skill_pack.py (legacy utilities, retained)
├── schemas/                        — JSON-schema for every artifact
│   ├── triage.schema.json
│   ├── root_cause.schema.json
│   ├── approved_plan.schema.json
│   ├── impl_result.schema.json
│   ├── verification_result.schema.json
│   └── ownership.schema.json
├── workspace-templates/            — canonical empty artifacts (copied by reset/agents)
├── rules/                          — operational policy (Phase gates, escalation, …)
└── docs/                           — design references (architecture, MCP, setup deep dive)

workspace/                          — runtime artifacts (mostly session-scoped, gitignored)
├── triage.json                     — emitted by triage agent
├── pipeline.json                   — emitted by orchestrate.py plan
├── root_cause.json                 — bug-investigation / refactor-agent
├── approved_plan.json              — architect (medium and above)
├── impl_result.json                — unity-dev / data-tool
├── verification_result.json        — verifier / tester
├── ownership.lock.json             — architect or triage (when partitioning)
├── escalation-log.md               — session-scoped escalations
├── repo-knowledge.md               — PERSISTENT, commit to repo
├── ecs-registry.md                 — PERSISTENT, commit to repo
└── recent-changes.md               — PERSISTENT, commit to repo (14-day rolling)
```

---

## Updating

The package has no auto-update. To update:

1. Pull the latest `.claude/` from the package repo.
2. Run `python .claude/scripts/orchestrate.py preflight`.
3. Run `python .claude/scripts/orchestrate.py validate .claude/workspace-templates/triage.json triage`
   to confirm schemas still round-trip.
4. Read `CHANGELOG.md` for any breaking schema changes (you will need to
   manually update any persisted `workspace/repo-knowledge.md` or
   `ecs-registry.md` content that depends on them — these files are not
   migrated automatically).

---

## Uninstall

Delete the `.claude/` folder. The `workspace/` folder can stay (it is yours).
There is no global state to clean up.
