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

### Use `/team` in another project (cross-project)

`/team` is **self-contained in `.claude/`**. To use it in any other repo, copy that
folder into the target repo root — nothing else is global, and it works for Unity
classic, Unity DOTS/ECS, and plain C# / non-Unity repos alike (irrelevant skills
just score low and never load).

```sh
# from this package repo into a target project:
cp -R .claude /path/to/other-project/.claude
cp SETUP.md README.md CHANGELOG.md MIGRATION.md LICENSE /path/to/other-project/   # optional but recommended

cd /path/to/other-project
python3 .claude/scripts/orchestrate.py preflight         # env / MCP / tmux sanity
python3 .claude/scripts/build_skill_registry.py check    # registry intact (22/22 skills)
python3 .claude/scripts/validate_skill_routing.py        # routing lanes correct (4/4)
```

Then open Claude Code in that project and run `/team <intent> [depth] <task>`.

What carries over and is enforced per-project, with **no global config**:

- **Skill registry + router** (`.claude/skills/registry.json` + `scripts/route_skills.py`):
  each agent loads a curated, role-correct subset (`role + domain + intent + keyword
  + memory hint`, capped at `max_total_skills=7`). DOTS skills never reach
  `unity-dev` / `tester` / `verifier` / `qa-tester` / `data-tool`. Dry-run any route:
  ```sh
  python3 .claude/scripts/route_skills.py --agent unity-dots-dev --domain DOTS --intent bug --task "ISystem race"
  ```
- **Both modes**: adaptive `/team` (writes `pipeline.json.skills_by_agent` from the
  router) and `/team --team` (4 Sonnet teammates, Read-first skill loading) use the
  same registry — see [`CLONE-SETUP.md`](./CLONE-SETUP.md) for the full `--team` walkthrough.
- **agentmemory recall** is optional and per-project (see "Using agentmemory with
  /team" below). When absent, the pipeline still runs — agents report
  `[MEMORY UNAVAILABLE]` and use targeted search.

> If the target repo is not a Unity project, `/team` still works — domain scoring
> classifies the task and only loads relevant skills. Memory is never the source of
> truth; the target repo's current files always win.

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

## Using agentmemory with /team

`agentmemory` is an **optional** MCP server that lets `/team` agents recall
cross-session engineering knowledge — failure patterns, architecture decisions,
and performance findings accumulated from past runs. Every feature works without it.

> **Source:** https://github.com/rohitg00/agentmemory
> Verify the install steps and MCP entry shape against the current agentmemory docs
> before following the steps below — they reflect a typical stdio setup but may not
> match the latest release.

### 1. Install agentmemory

Follow the install instructions at https://github.com/rohitg00/agentmemory.
The server is typically installed as a Python package:

```sh
pip install agentmemory
# or, without a global install:
# uvx agentmemory   (used directly in .mcp.json — see step 2)
```

You do not need to start it manually. Claude Code launches it as a stdio process
when the project is opened (once `.mcp.json` is configured).

### 2. Connect to Claude Code via `.mcp.json`

Add an `agentmemory` entry to your project's `.mcp.json` alongside the other servers.
The typical stdio shape (verify against https://github.com/rohitg00/agentmemory):

```json
{
  "mcpServers": {
    "ai-game-developer": { "...": "..." },
    "code-review-graph":  { "...": "..." },
    "agentmemory": {
      "type": "stdio",
      "command": "uvx",
      "args": ["agentmemory"]
    }
  }
}
```

> **Verify this shape** against the current docs before committing — the command
> name and args may differ across versions.

Restart Claude Code after editing `.mcp.json`.

### 3. Verify the memory tools are present

After restarting, confirm the `mcp__agentmemory__*` tools are available:

```
/mcp
```

You should see `agentmemory` listed with tools including
`mcp__agentmemory__memory_smart_search`, `mcp__agentmemory__memory_lesson_save`,
`mcp__agentmemory__memory_recall`, and others.

### 4. Behavior when agentmemory is unavailable

If the server is not running or the tools are absent, `/team` agents continue
normally — no session is blocked:

- Agents print `[MEMORY UNAVAILABLE]` **once** (not repeated).
- Investigation agents (`bug-investigation`, `system-mapper`) fall back to targeted
  `Grep` + `code-review-graph` queries against the current codebase.
- No `/team` features are disabled; memory only enriches the initial hypothesis.

### 5. Disable the memory requirement

Memory is opt-in by design. To ensure no agent ever attempts a memory call, remove
the `agentmemory` entry from `.mcp.json`. The `[MEMORY UNAVAILABLE]` fallback
activates automatically — no other config change needed.

### ⚠ WARNING: memory is NOT the source of truth

> **Current repo files always win over memory.**
>
> Agents use memory only to seed an initial hypothesis (known failure patterns,
> prior architecture decisions). They **verify every recalled fact against the
> live codebase** before acting. A memory entry that contradicts current source
> code or `workspace/repo-knowledge.md` is treated as stale and ignored. Never
> act on a memory recall without confirming it against the actual files.

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
