# Unity DOTS Agent Team — Installer

**You (Claude) were invoked with this file as input.** Treat the rest of this document as an executable install task for the user's Unity project. Do not just summarize it — perform the install.

## Context

The user cloned this repo into their Unity project root, so the layout is:

```
<project-root>/                          ← user's Unity project; this is your CWD
├── Assets/                              ← may or may not exist; do not touch
├── ProjectSettings/                     ← may or may not exist; do not touch
├── unity-agent-team-publish/            ← this repo (clone target)
│   ├── .claude/                         ← source of truth for the install
│   │   ├── agents/
│   │   ├── commands/
│   │   ├── docs/
│   │   ├── scripts/
│   │   ├── skills/
│   │   └── CLAUDE.md
│   ├── SETUP.md                         ← this file
│   ├── README.md
│   └── LICENSE
└── .claude/                             ← target (may or may not exist yet)
```

Your job: copy `unity-agent-team-publish/.claude/` into `<project-root>/.claude/`, merging cleanly with anything already there.

## Steps

### 1. Verify you are in the right place

Confirm both of these exist:
- `unity-agent-team-publish/.claude/commands/team.md`
- `unity-agent-team-publish/.claude/agents/architect.md`

If either is missing, stop and tell the user the clone is incomplete or they are running from the wrong directory.

### 2. Audit the source pack

Run the bundled validator if Python is available:
```
python unity-agent-team-publish/.claude/scripts/validate_skill_pack.py
```
Report any issues to the user before proceeding. If Python is not available, skip and note it.

### 3. Detect existing `.claude/` in the target

Check whether `<project-root>/.claude/` already exists.

- **If no:** safe full copy in step 4.
- **If yes:** list what's already inside (`agents/`, `commands/`, `skills/`, `CLAUDE.md`, etc.) and ask the user one question with `AskUserQuestion`:
  - **Merge** — copy only files that don't exist; skip conflicts and list them for the user to resolve manually. *(Recommended; preserves user's work.)*
  - **Overwrite** — overwrite conflicting files with this pack's versions.
  - **Abort** — don't install; let the user resolve manually.

### 4. Copy `.claude/` contents

Choose the platform-appropriate command. The user's shell is reported in the session context — check `$env:OS` or the platform info.

**Windows / PowerShell:**
```powershell
Copy-Item -Path "unity-agent-team-publish/.claude/*" -Destination ".claude/" -Recurse -Force
```
(use `-Force` only if user chose "Overwrite" in step 3; omit it for "Merge")

**macOS / Linux / Git-Bash:**
```sh
mkdir -p .claude && cp -rn unity-agent-team-publish/.claude/. .claude/   # merge (no clobber)
# or
mkdir -p .claude && cp -rf unity-agent-team-publish/.claude/. .claude/   # overwrite
```

Copy these subdirectories: `agents/`, `commands/`, `docs/`, `scripts/`, `skills/`, plus the top-level `CLAUDE.md`.

If `<project-root>/.claude/CLAUDE.md` already exists and differs, **never silently overwrite it** — ask the user whether to merge content (append a "## Unity DOTS Agent Team" section) or skip. The CLAUDE.md is the user's project-wide instruction file; corrupting it can break their other workflows.

### 5. Verify the install

Check that the target now contains:

**Core team agents:**
- `<project-root>/.claude/agents/architect.md`
- `<project-root>/.claude/agents/unity-dev.md`
- `<project-root>/.claude/agents/data-tool.md`
- `<project-root>/.claude/agents/tester.md`

**CRG-first investigation agents:**
- `<project-root>/.claude/agents/architecture-agent.md`
- `<project-root>/.claude/agents/codebase-reader.md`
- `<project-root>/.claude/agents/bug-investigation.md`
- `<project-root>/.claude/agents/refactor-agent.md`
- `<project-root>/.claude/agents/feature-dev-agent.md`

**Commands and skills:**
- `<project-root>/.claude/commands/team.md`
- `<project-root>/.claude/skills/architect/SKILL.md`
- `<project-root>/.claude/skills/unity-dev/SKILL.md`
- `<project-root>/.claude/skills/data-tool/SKILL.md`
- `<project-root>/.claude/skills/tester/SKILL.md`
- `<project-root>/.claude/skills/unity-dots-best-practices/SKILL.md`
- `<project-root>/.claude/skills/editor-data-tools/SKILL.md`
- `<project-root>/.claude/skills/qa-validation/SKILL.md`
- `<project-root>/.claude/skills/start-unity-dots-team/SKILL.md`
- `<project-root>/.claude/skills/codebase-understanding/SKILL.md`

**Rules and docs:**
- `<project-root>/.claude/rules/GRAPH_FIRST.md`
- `<project-root>/.claude/docs/setup.md`
- `<project-root>/.claude/docs/architecture.md`
- `<project-root>/.claude/docs/mcp-integration.md`
- `<project-root>/.claude/scripts/preflight.py`

Run the validator again against the installed copy if Python is available:
```
python .claude/scripts/validate_skill_pack.py
```

### 6. Check MCP servers

Look in `~/.claude/settings.json` (or `~/.claude/mcp.json`) for these two server registrations:
- `ai-game-developer`
- `agentmemory`

If either is missing, **do not register it for the user** — instead tell them which is missing and link them to the relevant install docs. The agent team will still boot without them but in degraded mode (agents will say "Running without MCP evidence" / "Running without memory recall").

### 6b. Project-scoped MCP (`.mcp.json`) — `code-review-graph`

In addition to the user-level servers above, this pack ships a **project-scoped** MCP template at `unity-agent-team-publish/.mcp.json.template`. It registers two servers Claude Code loads automatically when present at the project root:

| Server | Purpose | Required? |
|---|---|---|
| `ai-game-developer` | Same Unity Editor MCP as above, but pinned per-project (port + token) | Optional — only if you want per-project overrides |
| `code-review-graph` | Code graph for fast structural search (callers/callees, impact radius, semantic search). See `@.claude/rules/GRAPH_FIRST.md` if present. | Optional but **strongly recommended** |

**To install for a new project:**

1. Copy `unity-agent-team-publish/.mcp.json.template` to `<project-root>/.mcp.json`.
2. Replace `<ABSOLUTE_PATH_TO_REPO_ROOT>` with the absolute path to the Git repo root (the folder containing `.git/`, **not** the Unity sub-folder if your repo has one).
3. Replace `<YOUR_AI_GAME_DEVELOPER_TOKEN>` with the bearer token from your Unity MCP server config (or delete the `ai-game-developer` block to inherit from user-level settings).
4. Install the `code-review-graph` CLI so the `command` resolves on PATH. If the user doesn't have it, **tell them which install step is missing** — do not silently invent an install command.
5. Reload Claude Code (`/mcp`) and verify both servers report connected.

Ask before overwriting an existing `<project-root>/.mcp.json` — merge entries instead of clobbering.

### 7. Decide whether to keep `unity-agent-team-publish/`

Ask the user with `AskUserQuestion`:
- **Keep the clone in the project** — future updates are a single `git pull` inside it. *(Recommended for teams that want to track upstream.)*
- **Delete the clone** — the installed copy under `.claude/` is self-sufficient; the clone was only a delivery vehicle.

If they pick delete, remove `unity-agent-team-publish/` (Windows: `Remove-Item -Recurse -Force unity-agent-team-publish`; POSIX: `rm -rf unity-agent-team-publish`). Confirm with the user before removing.

### 8. Report

Print a short report:
```
Installed:
  agents:   <count>      (architect, unity-dev, data-tool, tester,
                          architecture-agent, codebase-reader,
                          bug-investigation, refactor-agent, feature-dev-agent)
  commands: <count>      (/team)
  skills:   <count>      (architect, unity-dev, data-tool, tester,
                          unity-dots-best-practices, editor-data-tools,
                          qa-validation, start-unity-dots-team,
                          codebase-understanding)
  rules:    <count>      (GRAPH_FIRST)
  docs:     <count>      (setup, architecture, mcp-integration)
  scripts:  <count>      (preflight, dots_scan, validate_skill_pack)

MCP servers:
  ai-game-developer: <present | MISSING>
  agentmemory:       <present | MISSING>

Conflicts resolved: <count>  (list if any)
Files skipped:      <count>  (list if any)

Next: from this project root, run
  /team <your-task>          # fast mode (architect + unity-dev)
  /team <your-task> --full   # all four agents
```

---

## What this installer does NOT do

- It does not modify `~/.claude/settings.json` (user-level config — owned by the user).
- It does not register MCP servers (the user manages those).
- It does not enable the experimental `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` flag (opt-in only — see `README.md`).
- It does not touch Unity project files (`Assets/`, `ProjectSettings/`, `Packages/`).

## If something goes wrong

- Source files missing → re-clone the repo.
- Permission errors copying → user lacks write access to project root; have them fix permissions and re-run.
- Validator reports frontmatter errors → check `.claude/scripts/validate_skill_pack.py` output; report verbatim to the user. Do not attempt auto-repair.

After install, the user should be able to run `/team <task>` from the project root.
