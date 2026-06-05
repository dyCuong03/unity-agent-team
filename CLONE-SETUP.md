# Clone & Setup — use `unity-agent-team` (and `/team --team`) in any Unity project

This package is a portable `.claude/` agent system. You drop it into a Unity
project and get the adaptive `/team` pipeline **and** the real 4-agent
`/team --team` mode (4 Sonnet CLI sessions in tmux, one git worktree each).

---

## 0. Mental model — where the package must live

`/team --team` runs `full_team.py`, which creates **git worktrees of the repo
that contains the installed `.claude/` folder** and lets teammates edit
`Assets/**`. So the package's `.claude/` **must sit at the Unity project root**
(the folder that has `Assets/`, `Packages/`, `ProjectSettings/` and is a git repo).

```
MyUnityGame/                ← git root  ← REPO_ROOT
├── Assets/                 ← teammates edit here
├── Packages/
├── ProjectSettings/
├── .claude/                ← the package (commands, agents, skills, scripts)
├── SETUP.md
└── workspace/              ← runtime artifacts (gitignored mostly)
```

`full_team.py` resolves `REPO_ROOT` as the folder two levels above
`.claude/scripts/`. If you cannot install at the root (e.g. the package is a
nested clone), set an override:

```sh
export UNITY_TEAM_PROJECT_ROOT=/abs/path/to/MyUnityGame
```

Then `REPO_ROOT`, worktrees, and `Assets/**` ownership all resolve to the real
project regardless of where the scripts physically live.

---

## 1. Install into a fresh Unity project

```sh
# from the unity-agent-team package repo
PKG=/path/to/unity-agent-team
DEST=/path/to/MyUnityGame          # the Unity project root (git repo)

cp -r "$PKG/.claude"   "$DEST/.claude"
cp    "$PKG/SETUP.md" "$PKG/README.md" "$PKG/MIGRATION.md" "$PKG/CHANGELOG.md" "$DEST/"
cp    "$PKG/.mcp.json.template" "$DEST/.mcp.json"     # then fill in real MCP endpoints
```

If `$DEST` already has a `.claude/` (e.g. an older v1 install), back it up first:
`mv "$DEST/.claude" "$DEST/.claude.v1.bak"`.

> **This repo (BackpackAdventures) note:** the root `.claude/` is the legacy **v1**
> command (fixed agents, markdown-promise gates). The v2 package lives in
> `unity-agent-team/`. To use `/team --team` here, either (a) copy
> `unity-agent-team/.claude` over the root `.claude`, or (b) run the script
> directly with the override:
> `UNITY_TEAM_PROJECT_ROOT=/mnt/e/BuzzleStudio/BackpackAdventures python3 unity-agent-team/.claude/scripts/full_team.py setup "<task>"`

---

## 2. Enable real team mode (one-time, user-level)

`~/.claude/settings.json`:

```json
{
  "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" },
  "preferences": { "tmuxSplitPanes": true }
}
```

Restart Claude Code. Without the env flag, `/team --team` **fails fast** (by
design — no silent fallback to in-process subagents).

Hard prerequisites (checked by `full_team.py env_check`): `tmux`, `git` with
worktree support, `claude` CLI on PATH, and the env flag.

---

## 3. Verify the install

```sh
cd /path/to/MyUnityGame
python3 .claude/scripts/orchestrate.py preflight
python3 .claude/scripts/orchestrate.py validate .claude/workspace-templates/triage.json triage
python3 .claude/scripts/full_team.py prompts "verify install"   # dry: writes prompt files, no tmux
```

All three should exit 0. (Use `python3`, not `python` — the bare `python`
binary is absent on many systems and returns exit 127.)

---

## 4. Which mode for which task

| Task | Use | Why |
|------|-----|-----|
| Quick, 1–2 file, obvious | `/team bug quick "<symptom>"` or just fix inline | Adaptive triage → 1 agent. No team overhead. |
| Bug, real root cause needed | `/team bug "<symptom>"` | Prepends `bug-investigation` (CRG root-cause) → fix → verify. |
| Refactor with blast radius | `/team refactor deep "<target>"` | `refactor-agent` blast radius → architect approve → step-gated. |
| Feature, medium | `/team feature "<desc>"` | architect → unity-dev → verifier, artifact-gated. |
| **Big / cross-cutting / mixed DOTS + UI** | **`/team --team "<desc>"`** | Claude Agent Teams: 4 Sonnet teammates, shared task list, QA-gated. |
| Want branch isolation | `/team --worktrees "<desc>"` | Manual tmux + git worktree per role (`full_team.py`). Advanced. |
| Just understand something | `/team explore "<question>"` | Triage-only, no code. |

**Rule of thumb:** use **Adaptive** for focused work (cheaper, gated, sequential);
use **`--team`** when the work genuinely splits across roles (architecture +
non-DOTS Unity + DOTS/ECS + QA). Use **`--worktrees`** only when you specifically
need each role on an isolated git branch.

---

## 5. Using `/team --team`

`/team --team` runs the task as a **Claude Agent Teams** team — the current Claude
Code session is the **teamlead** and spawns exactly 4 persistent teammates on
**Sonnet** (`architect`, `unity-dots-dev`, `unity-dev`, `qa-tester`) via the
harness-native `TeamCreate` + `Agent(team_name=…)` primitives with a shared task
list. It is **not** normal subagents, **not** simulated markdown roles, and **not**
the manual worktree mode.

**1. Enable Agent Teams** (one-time, see §2): set
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (+ `tmuxSplitPanes: true` to get a pane per
teammate) in `~/.claude/settings.json`, then restart Claude Code.

**2. Verify availability:**
```sh
grep -q '"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"[[:space:]]*:[[:space:]]*"1"' ~/.claude/settings.json \
  && echo "agent-teams: ON" || echo "agent-teams: OFF"
```

**3. Run:**
```
/team --team analyze the /team flow and improve Unity task support
```

**4. The 4 required teammates** (all Sonnet): `architect` (analysis/ownership/plan),
`unity-dots-dev` (DOTS/ECS), `unity-dev` (UI/MonoBehaviour/gameplay), `qa-tester`
(test matrix + final APPROVE/BLOCK).

**5. Inspect teammates:** with `tmuxSplitPanes: true`, each teammate is a tmux pane;
the teamlead surfaces the team name (`team-<slug>`) and any attach hint the runtime
prints. Live status via the shared task list (`TaskList`) and automatic teammate
messages — no inbox polling.

**6. If Agent Teams is unavailable:** the command **fails fast** with a `[BLOCK]`
message explaining how to enable it. It does **not** fall back to subagents,
single-agent, or simulated roles.

**7–9. What `--team` is NOT:** not normal subagent mode, not simulated markdown
role-play, not manual worktree mode. (For worktrees, use `/team --worktrees`.)

The 4 roles:

| Teammate | Owns | Avoids |
|----------|------|--------|
| `architect` | analysis, ownership map, execution plan, acceptance criteria, scope control | implementing |
| `unity-dots-dev` | ISystem, Jobs, Burst, ECS components, ECB, bakers, blob assets, performance | pure UI/Mono files |
| `unity-dev` | MonoBehaviour, UI, gameplay, VContainer, Addressables, pooling, DOTween | DOTS/ECS files |
| `qa-tester` | test matrix, regression, root-cause validation, APPROVE/BLOCK | editing impl files |

---

## 5b. `/team --worktrees` (advanced, opt-in)

Separate mode for isolated git branches. 4 real `claude` CLI sessions (Sonnet) in
tmux windows, one worktree+branch each, QA-gated merge. NOT `--team`/`--full`.

```sh
python3 .claude/scripts/full_team.py setup "<task>"     # standby → validate → worktrees → assign
tmux attach -t unity-agent-team-<slug>
python3 .claude/scripts/full_team.py status "<task>"
# merge only after reports/team/<slug>/qa-report.md = APPROVE; then:
python3 .claude/scripts/full_team.py teardown "<task>"
```

---

## 6. Effective-use tips

- **`--team` (Agent Teams)** is the default for multi-role work — no git worktrees,
  the teamlead coordinates the shared task list and synthesizes the result.
- **Completion is gated on QA.** The teamlead must not mark done until `qa-tester`
  posts `APPROVE` with validation evidence.
- **`--worktrees`** only when you need branch isolation; keep the working tree clean
  first (worktrees branch from HEAD).
- **Adaptive mode still has the real Python gates.** Prefer it for focused work — it
  enforces root-cause (`root_cause.json`, confidence ≥ 0.6) and plan-adherence
  (`approved_plan.json`, no unreconciled `deviations_from_plan`).
