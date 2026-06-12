#!/usr/bin/env python3
"""
full_team.py — Real multi-agent team orchestrator for /team --full.

STARTUP ORDER (mandatory):
  1. Parse task → slug
  2. Fail fast if tools missing
  3. Create tmux session + 4 windows FIRST
  4. Launch Claude in standby in each window FIRST
  5. Validate all 4 teammate sessions are alive
  6. ONLY THEN: analyze task, create worktrees, assign work

This is NOT a simulated plan — it creates real infrastructure for parallel
agent work. Teammate sessions must exist before any analysis begins.

Subcommands:
  setup <task>              — full two-phase setup (teammates first, then assign)
  spawn-teammates <task>    — phase 1 only: tmux + standby Claude sessions
  assign <task>             — phase 2 only: worktrees + prompts + dispatch
  verify <task>             — print verification table
  teardown <task>           — remove worktrees and tmux session
  status <task>             — check report files and branch state

Environment:
  CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS must be set to "1" for real team mode.

Exit codes:
  0   ok
  1   internal error
  2   precondition failed (dirty tree, missing tool, env not set)
  3   setup failed (teammate sessions not alive, worktree creation failed)
  5   teammate validation failed (sessions not running)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Root resolution is owned by roots.py — the single allowed mechanism.
# REPO_ROOT = the project repository the team works on. Env overrides
# (roots.ENV_PROJECT_ROOT and its legacy alias) and project-config.json
# are all honoured inside roots.py.
_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import roots  # noqa: E402


def _resolve_project_root() -> Path:
    try:
        return roots.project_root()
    except roots.RootResolutionError:
        return roots.framework_root()


REPO_ROOT = _resolve_project_root()
try:
    CONFIG: dict[str, Any] = roots.load_config(REPO_ROOT)
except roots.RootResolutionError:
    CONFIG = {}

# Per-project worktree base (configurable via project-config "worktreeRoot").
WORKTREE_BASE = roots.worktree_root(REPO_ROOT, CONFIG or {})

# PROJECT-scoped dirs come from roots helpers.
WORKSPACE_DIR = roots.workspace_dir(REPO_ROOT, CONFIG or {})
REPORTS_DIR = roots.reports_dir(REPO_ROOT, CONFIG or {})


def _rel_to_repo(p: Path) -> str:
    """Repo-relative posix path for prompt text; absolute string if outside."""
    try:
        return p.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return p.as_posix()


REPORTS_REL = _rel_to_repo(REPORTS_DIR)
WORKSPACE_REL = _rel_to_repo(WORKSPACE_DIR)

# Model used for every spawned teammate session. Sonnet by default (fast, cheap,
# strong enough for role-scoped Unity work). Override with --model on any subcommand.
DEFAULT_MODEL = "sonnet"

# ---------------------------------------------------------------------------
# Agent role definitions
# ---------------------------------------------------------------------------

# Built-in 4-agent Unity profile — used when project-config.json defines no
# usable teamProfiles.full. AGENTS itself is resolved after AGENT_ROLES below.
_DEFAULT_AGENTS = ["architect", "unity-dev", "unity-dots-dev", "qa-tester"]

AGENT_ROLES = {
    "architect": {
        "title": "System Architect / Task Planner",
        "focus": [
            "Analyze user task and split work by role",
            "Define file ownership per agent",
            "Define worktree/branch plan",
            "Define merge order and QA checklist",
            "Must not directly implement unless necessary",
        ],
        "skills": [
            ".claude/skills/architect/SKILL.md",
            ".claude/skills/unity-dots-best-practices/SKILL.md",
            ".claude/skills/unity-foundation/SKILL.md",
        ],
        "allowed_files": ["workspace/*", "reports/*", ".claude/*"],
        "forbidden_files": [],
    },
    "unity-dev": {
        "title": "Senior Unity Developer (Non-DOTS)",
        "focus": [
            "MonoBehaviour / ScriptableObject / Addressables",
            "VContainer / UniTask / DOTween / UI",
            "Gameplay code / non-DOTS Unity code",
            "Must avoid DOTS/ECS files unless architect explicitly allows",
        ],
        "skills": [
            ".claude/skills/unity-classic/SKILL.md",
            ".claude/skills/unity-foundation/SKILL.md",
        ],
        "allowed_files": [
            "Assets/**/*.cs",
            "!Assets/**/Systems/**",
            "!Assets/**/DOTS/**",
            "!Assets/**/ECS/**",
        ],
        "forbidden_files": [],
    },
    "unity-dots-dev": {
        "title": "Senior Unity DOTS/ECS Developer",
        "focus": [
            "Entities / ISystem / SystemBase / Jobs / Burst",
            "ECS components / buffers / physics / performance",
            "Baker / authoring / blob assets / native containers",
            "Must avoid pure Unity/UI files unless architect explicitly allows",
        ],
        "skills": [
            ".claude/skills/unity-dev/SKILL.md",
            ".claude/skills/unity-dots-best-practices/SKILL.md",
            ".claude/skills/burst-safety/SKILL.md",
            ".claude/skills/ecs-job-patterns/SKILL.md",
            ".claude/skills/memory-safety/SKILL.md",
        ],
        "allowed_files": [
            "Assets/**/Systems/**",
            "Assets/**/DOTS/**",
            "Assets/**/ECS/**",
            "Assets/**/DOTSFoundation/**",
            "Assets/**/*System*.cs",
            "Assets/**/*Component*.cs",
            "Assets/**/*Baker*.cs",
            "Assets/**/*Authoring*.cs",
            "Assets/**/*Job*.cs",
            "Assets/**/*Aspect*.cs",
        ],
        "forbidden_files": [],
    },
    "qa-tester": {
        "title": "QA Tester / Reviewer",
        "focus": [
            "Review diffs from all agent branches",
            "Run or describe compile/test/manual verification",
            "Check behavior risks, performance risks, race conditions",
            "Check merge conflicts between agent branches",
            "Must not change implementation files unless explicitly asked",
        ],
        "skills": [
            ".claude/skills/tester/SKILL.md",
            ".claude/skills/qa-validation/SKILL.md",
        ],
        "allowed_files": ["reports/*", "workspace/*"],
        "forbidden_files": ["Assets/**/*.cs"],
    },
}


def _resolve_agents() -> list[str]:
    """Team composition: project-config teamProfiles.full when every member maps
    onto a known AGENT_ROLES role; otherwise the built-in 4-agent profile.

    Only an explicitly written config file counts — roots.load_config() merges
    generic defaults ("architect", "coder", "tester") that do not match the
    roles this orchestrator can prompt for.
    """
    cfg_path = (CONFIG or {}).get("_config_path")
    if cfg_path:
        try:
            raw = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}
        profile = (raw.get("teamProfiles") or {}).get("full")
        if profile and all(a in AGENT_ROLES for a in profile):
            return list(profile)
        if profile:
            print(
                f"[full-team] teamProfiles.full {profile} contains roles without "
                f"AGENT_ROLES definitions — falling back to {_DEFAULT_AGENTS}",
                file=sys.stderr,
            )
    return list(_DEFAULT_AGENTS)


AGENTS = _resolve_agents()

_OWNERSHIP_APPLIED = False


def _apply_ownership_defaults() -> None:
    """Resolve per-agent file ownership globs once, lazily (before prompts).

    Priority:
      1. project-config "ownershipDefaults" {agent: [globs]} when present
      2. built-in Unity globs (Assets/** …) — fallback for projectType=="unity"
      3. neutral ["**/*"] partition for implementation roles on non-unity
         projects (logged)
    """
    global _OWNERSHIP_APPLIED
    if _OWNERSHIP_APPLIED:
        return
    _OWNERSHIP_APPLIED = True
    cfg = CONFIG or {}
    overrides = cfg.get("ownershipDefaults") or {}
    if overrides:
        for agent, globs in overrides.items():
            if agent in AGENT_ROLES and globs:
                AGENT_ROLES[agent]["allowed_files"] = list(globs)
        return
    ptype = cfg.get("projectType")
    if not cfg.get("_config_path"):
        # No project-config.json written yet — detect, so unconfigured installs
        # at a Unity project root keep the built-in Unity globs.
        try:
            ptype = roots.detect_project_type(REPO_ROOT)
        except Exception:
            ptype = "generic"
    if ptype != "unity":
        print(
            f"[full-team] projectType={ptype}: no ownershipDefaults configured — "
            "using neutral '**/*' ownership for implementation roles"
        )
        for agent, role in AGENT_ROLES.items():
            if agent not in ("architect", "qa-tester"):
                role["allowed_files"] = ["**/*"]
                role["forbidden_files"] = []


# ---------------------------------------------------------------------------
# Standby bootstrap prompt (sent to each teammate before real assignment)
# ---------------------------------------------------------------------------

STANDBY_PROMPT = """You are the {role} teammate in a real tmux-based Unity DOTS agent team.

STANDBY MODE — do not act yet.

- Do NOT analyze the project.
- Do NOT edit any files.
- Do NOT run implementation commands.
- Do NOT explore the codebase.

Wait for the main lead to send your assignment, which will include:
- Your worktree path
- Your branch name
- Your file ownership map
- Your task assignment
- Skills to load
- MCP instructions
- Report path

Acknowledge this message and wait."""


# Non-negotiable quality bars injected into EVERY teammate assignment.
# These encode the project owner's hard rules for all /team --team work.
QUALITY_BARS = """## Non-Negotiable Quality Bars (apply to ALL work)

1. ROOT CAUSE, NOT BAND-AID. For any bug, find the core defect — the system/
   component that actually writes the wrong state. Use CRG (code-review-graph)
   first: trace_execution_flow → identify writers/readers → get_impact_radius.
   A fix that hides the symptom (clamp, null-guard, try/catch swallow, re-init)
   without naming the root cause is REJECTED. State the root cause explicitly in
   your report before proposing the fix.

2. STICK TO THE PROJECT — NO DRIFT. Match existing patterns, naming, folder
   layout, and architecture. Before adding anything, search for an existing
   system/component/util that already does it. Do NOT introduce a parallel
   architecture when one exists. Extend the established extension points.

3. NO DUPLICATE CODE / NO REDUNDANT LOGIC. Reuse existing systems, helpers, and
   components. If you would copy-paste logic, extract or call the existing one
   instead. Do not add a second code path for behavior the project already has.
   Flag any duplication you are forced to create and explain why in your report.

If a task cannot be done without violating one of these, STOP and write the
conflict to your report + message the architect — do not work around it."""


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def slugify(text: str) -> str:
    """Convert task description to a filesystem-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower().strip())
    slug = slug.strip("-")[:60]
    return slug or "task"


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return result."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd or REPO_ROOT,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result


def get_current_branch() -> str:
    result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip()


def get_base_branch() -> str:
    """Base branch for agent worktrees.

    Configured project default (roots/project-config "defaultBranch") wins;
    otherwise the currently checked-out branch (legacy behavior preserved).
    """
    configured = (CONFIG or {}).get("defaultBranch")
    if configured:
        return str(configured)
    return get_current_branch()


def is_worktree_dirty() -> bool:
    result = run(["git", "status", "--porcelain"], check=False)
    return bool(result.stdout.strip())


def tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def env_check() -> list[str]:
    """Check required environment. Returns list of errors.

    STRICT: /team --full must fail fast if any prerequisite is missing.
    No fallback to internal subagents. No partial setup.
    """
    errors = []
    if os.environ.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") != "1":
        errors.append(
            "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS is not set to '1'. "
            "Add to ~/.claude/settings.json: "
            '{"env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}}. '
            "Then restart Claude Code."
        )
    if not tool_available("tmux"):
        errors.append(
            "tmux is not installed or not in PATH. "
            "/team --full requires real tmux sessions — no fallback to internal subagents."
        )
    if not tool_available("git"):
        errors.append("git is not installed or not in PATH")
    else:
        result = run(["git", "worktree", "list"], check=False)
        if result.returncode != 0:
            errors.append(
                "git worktree not supported. "
                "/team --full requires real git worktrees — no fallback."
            )
    if not tool_available("claude"):
        errors.append(
            "claude CLI is not installed or not in PATH. "
            "/team --full requires claude CLI in each tmux window."
        )
    return errors


# ---------------------------------------------------------------------------
# Worktree management
# ---------------------------------------------------------------------------


def worktree_path(task_slug: str, agent: str) -> Path:
    return WORKTREE_BASE / task_slug / agent


def branch_name(task_slug: str, agent: str) -> str:
    return f"agent/{agent}/{task_slug}"


def create_worktrees(task_slug: str, base_branch: str) -> dict[str, Path]:
    """Create git worktrees for all agents. Returns {agent: path}."""
    paths = {}
    for agent in AGENTS:
        wt = worktree_path(task_slug, agent)
        br = branch_name(task_slug, agent)

        if wt.exists():
            print(f"  [worktree] {agent}: already exists at {wt}")
            paths[agent] = wt
            continue

        wt.parent.mkdir(parents=True, exist_ok=True)
        try:
            run(["git", "worktree", "add", str(wt), "-b", br, base_branch])
            print(f"  [worktree] {agent}: created {wt} on branch {br}")
            paths[agent] = wt
        except RuntimeError as e:
            if "already exists" in str(e):
                try:
                    run(["git", "worktree", "add", str(wt), br])
                    print(f"  [worktree] {agent}: attached to existing branch {br}")
                    paths[agent] = wt
                except RuntimeError as e2:
                    print(f"  [worktree] {agent}: FAILED — {e2}", file=sys.stderr)
            else:
                print(f"  [worktree] {agent}: FAILED — {e}", file=sys.stderr)
    return paths


def remove_worktrees(task_slug: str) -> None:
    for agent in AGENTS:
        wt = worktree_path(task_slug, agent)
        br = branch_name(task_slug, agent)
        if wt.exists():
            run(["git", "worktree", "remove", str(wt), "--force"], check=False)
            print(f"  [teardown] removed worktree: {wt}")
        run(["git", "branch", "-D", br], check=False)


# ---------------------------------------------------------------------------
# tmux management
# ---------------------------------------------------------------------------


def tmux_session_name(task_slug: str) -> str:
    return f"unity-agent-team-{task_slug}"


def create_tmux_session(task_slug: str) -> str:
    """Create tmux session with one window per agent. Returns session name.

    Does NOT require worktrees — this runs BEFORE worktree creation.
    """
    session = tmux_session_name(task_slug)

    # Kill existing session if present
    run(["tmux", "kill-session", "-t", session], check=False)

    # Create session with first agent window
    first_agent = AGENTS[0]
    run([
        "tmux", "new-session", "-d",
        "-s", session,
        "-n", first_agent,
        "-x", "200", "-y", "50",
    ])
    print(f"  [tmux] created session: {session}")

    # Create remaining windows
    for agent in AGENTS[1:]:
        run(["tmux", "new-window", "-t", session, "-n", agent])
        print(f"  [tmux] created window: {agent}")

    return session


def launch_standby_claude(task_slug: str, model: str = DEFAULT_MODEL) -> None:
    """Launch Claude in standby mode in each tmux window.

    Each teammate gets a bootstrap prompt telling them to wait.
    This runs BEFORE any task analysis or worktree creation.
    Every teammate runs on `model` (Sonnet by default).
    """
    session = tmux_session_name(task_slug)

    for agent in AGENTS:
        role_title = AGENT_ROLES[agent]["title"]

        # Launch claude CLI in the tmux window on the chosen model
        launch_cmd = (
            "export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 && "
            f"claude --model {model}"
        )
        run([
            "tmux", "send-keys",
            "-t", f"{session}:{agent}",
            launch_cmd,
            "C-m",
        ])
        print(f"  [standby] {agent}: launched Claude in tmux window")

    # Give Claude processes time to start
    print("  [standby] waiting 5s for Claude processes to initialize...")
    time.sleep(5)

    # Send standby bootstrap prompt to each
    for agent in AGENTS:
        role_title = AGENT_ROLES[agent]["title"]
        prompt = STANDBY_PROMPT.format(role=role_title)

        # Escape the prompt for tmux send-keys
        # Send it line by line to avoid issues
        run([
            "tmux", "send-keys",
            "-t", f"{session}:{agent}",
            prompt,
            "C-m",
        ])
        print(f"  [standby] {agent}: sent standby bootstrap prompt")


def send_assignment_to_teammate(
    task_slug: str,
    agent: str,
    prompt_file: Path,
    worktree: Path,
) -> None:
    """Send the real role assignment to an already-running teammate."""
    session = tmux_session_name(task_slug)

    # First: cd into the worktree
    cd_cmd = f"cd {worktree}"
    run([
        "tmux", "send-keys",
        "-t", f"{session}:{agent}",
        cd_cmd,
        "C-m",
    ])

    # Then: send the assignment prompt by reading the file content
    # Use claude's ability to read file by sending a prompt referencing it
    assignment_cmd = f'Read the file {prompt_file} — that is your full assignment. Begin work immediately.'
    run([
        "tmux", "send-keys",
        "-t", f"{session}:{agent}",
        assignment_cmd,
        "C-m",
    ])
    print(f"  [assign] {agent}: sent assignment, worktree={worktree}")


def kill_tmux_session(task_slug: str) -> None:
    session = tmux_session_name(task_slug)
    run(["tmux", "kill-session", "-t", session], check=False)
    print(f"  [teardown] killed tmux session: {session}")


# ---------------------------------------------------------------------------
# Teammate session validation (MUST pass before any analysis)
# ---------------------------------------------------------------------------


def validate_teammate_sessions_first(task_slug: str) -> tuple[bool, str]:
    """Validate that all 4 teammate tmux windows exist with running Claude.

    This MUST pass BEFORE:
    - any task analysis
    - any worktree creation
    - any prompt generation
    - any assignment dispatch

    No fallback to internal subagents if this fails.
    """
    lines = []
    passed = True
    session = tmux_session_name(task_slug)

    # --- tmux ls ---
    lines.append("## tmux ls")
    result = run(["tmux", "ls"], check=False)
    tmux_output = result.stdout.strip() if result.stdout else ""
    lines.append(tmux_output or "(no sessions)")
    if session not in tmux_output:
        lines.append(f"  FAIL: session '{session}' not found")
        passed = False
    else:
        lines.append(f"  OK: session '{session}' exists")

    # --- tmux list-windows ---
    lines.append(f"\n## tmux list-windows -t {session}")
    result = run(["tmux", "list-windows", "-t", session], check=False)
    if result.returncode == 0:
        lines.append(result.stdout.strip())
        window_lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        window_count = len(window_lines)
        lines.append(f"  Windows: {window_count}/{len(AGENTS)}")
        if window_count != len(AGENTS):
            lines.append(f"  FAIL: expected {len(AGENTS)} windows, got {window_count}")
            passed = False
        else:
            lines.append("  OK: all 4 windows exist")

        # Check each required role name exists as a window
        for agent in AGENTS:
            found = any(agent in line for line in window_lines)
            if not found:
                lines.append(f"  FAIL: window '{agent}' not found")
                passed = False
            else:
                lines.append(f"  OK: window '{agent}' exists")
    else:
        lines.append(f"  FAIL: session '{session}' not found for list-windows")
        passed = False

    # --- tmux list-panes ---
    lines.append(f"\n## tmux list-panes -a")
    result = run(
        ["tmux", "list-panes", "-a", "-F",
         "#{session_name}:#{window_name}.#{pane_index} #{pane_current_path} #{pane_pid}"],
        check=False,
    )
    if result.returncode == 0:
        relevant = [l for l in result.stdout.strip().split("\n") if session in l]
        for l in relevant:
            lines.append(f"  {l}")
        pane_count = len(relevant)
        lines.append(f"  Panes in session: {pane_count}/{len(AGENTS)}")
        if pane_count < len(AGENTS):
            lines.append(f"  FAIL: expected at least {len(AGENTS)} panes, got {pane_count}")
            passed = False
        else:
            lines.append("  OK: all panes present")
    else:
        lines.append("  FAIL: could not list panes")
        passed = False

    # --- Check for running claude processes ---
    lines.append("\n## Claude process check (ps aux | grep claude)")
    result = run(["bash", "-c", "ps aux | grep '[c]laude' | grep -v grep || true"], check=False)
    claude_procs = result.stdout.strip()
    if claude_procs:
        proc_lines = claude_procs.split("\n")
        lines.append(f"  Claude processes found: {len(proc_lines)}")
        for p in proc_lines[:8]:
            # Truncate long lines
            lines.append(f"  {p[:120]}")
        if len(proc_lines) < len(AGENTS):
            lines.append(f"  WARNING: only {len(proc_lines)} claude processes, expected {len(AGENTS)}")
            # Not failing here — claude may show as a single process managing multiple sessions
    else:
        lines.append("  WARNING: no claude processes detected via ps")
        lines.append("  (Claude may use a different process name or be starting up)")

    # --- CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS check ---
    lines.append("\n## Environment check")
    if os.environ.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1":
        lines.append("  OK: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1")
    else:
        lines.append("  FAIL: CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS not set to '1'")
        passed = False

    # --- Verdict ---
    lines.append("")
    if passed:
        lines.append("TEAMMATE SESSION VALIDATION PASSED")
        lines.append("All 4 teammate tmux windows exist with required role names.")
        lines.append("Safe to proceed with task analysis and worktree creation.")
    else:
        lines.append("TEAMMATE SESSION VALIDATION FAILED")
        lines.append("Cannot proceed with task analysis or worktree creation.")
        lines.append("Do NOT fall back to internal subagents.")
        lines.append("Do NOT simulate the team.")
        lines.append("Fix issues above and re-run.")

    return passed, "\n".join(lines)


def validate_full_setup(task_slug: str) -> tuple[bool, str]:
    """Post-assignment validation. Checks teammates + worktrees + branches.

    Called after phase 2 (assign) to confirm everything is wired up.
    """
    lines = []
    passed = True
    session = tmux_session_name(task_slug)

    # First run teammate session validation
    teammate_passed, teammate_report = validate_teammate_sessions_first(task_slug)
    lines.append(teammate_report)
    if not teammate_passed:
        passed = False

    # --- Git worktree validation ---
    lines.append("\n## git worktree list")
    result = run(["git", "worktree", "list"], check=False)
    lines.append(result.stdout.strip() if result.stdout else "(empty)")

    worktree_count = 0
    for agent in AGENTS:
        wt = worktree_path(task_slug, agent)
        if wt.exists():
            worktree_count += 1
        else:
            lines.append(f"  MISSING: {agent} worktree at {wt}")
            passed = False
    lines.append(f"  Agent worktrees: {worktree_count}/{len(AGENTS)}")
    if worktree_count != len(AGENTS):
        passed = False

    # --- Mapping table ---
    lines.append("\n## Agent Mapping Table")
    lines.append(f"{'Agent':<16} {'tmux Window':<35} {'Worktree':<55} {'Branch':<45} {'Status'}")
    lines.append("-" * 155)
    for agent in AGENTS:
        wt = worktree_path(task_slug, agent)
        br = branch_name(task_slug, agent)
        wt_ok = "OK" if wt.exists() else "MISSING"
        lines.append(f"{agent:<16} {session}:{agent:<25} {str(wt):<55} {br:<45} {wt_ok}")

    lines.append("")
    if passed:
        lines.append("FULL SETUP VALIDATION PASSED — Real full team mode confirmed.")
    else:
        lines.append("FULL SETUP VALIDATION FAILED — Cannot claim real team mode.")

    return passed, "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt generation
# ---------------------------------------------------------------------------


def generate_prompts(
    task_slug: str,
    task: str,
    base_branch: str,
    worktrees: dict[str, Path],
    ownership: dict[str, Any] | None = None,
) -> Path:
    """Generate per-agent prompt files. Returns prompt directory."""
    _apply_ownership_defaults()
    prompt_dir = WORKSPACE_DIR / "full-team" / task_slug
    prompt_dir.mkdir(parents=True, exist_ok=True)

    report_dir = f"{REPORTS_REL}/team/{task_slug}"

    for agent in AGENTS:
        role = AGENT_ROLES[agent]
        wt = worktrees.get(agent, worktree_path(task_slug, agent))
        br = branch_name(task_slug, agent)

        # Build ownership section
        if ownership and agent in ownership:
            ownership_lines = "\n".join(f"- {p}" for p in ownership[agent])
            ownership_section = (
                "## File Ownership (from Architect)\n"
                "You own these files/patterns:\n"
                f"{ownership_lines}\n\n"
                "Do NOT edit files outside your ownership. Check with architect first."
            )
        else:
            allowed_lines = "\n".join(f"- {p}" for p in role["allowed_files"])
            ownership_section = (
                "## Default File Ownership\n"
                "Allowed patterns:\n"
                f"{allowed_lines}\n\n"
                "This is default ownership. Architect may override."
            )

        skill_refs = "\n".join(f"- @{s}" for s in role["skills"])
        focus_lines = "\n".join(f"- {f}" for f in role["focus"])

        sections = [
            f"# {role['title']} — Full Team Mode Assignment",
            "",
            "You are now leaving STANDBY mode. This is your real assignment.",
            "",
            "## Your Identity",
            f"- **Role:** {agent}",
            f"- **Worktree:** {wt}",
            f"- **Branch:** {br}",
            f"- **Base branch:** {base_branch}",
            "",
            "## Original Task",
            task,
            "",
            "## Your Focus",
            focus_lines,
            "",
            QUALITY_BARS,
            "",
            ownership_section,
            "",
            "## Skills to Load",
            skill_refs,
            "",
            "## MCP Tools",
            "You have access to all configured MCP tools:",
            "- `ai-game-developer` — Unity Editor introspection and mutation",
            "- `agentmemory` — Prior session memory (optional)",
            "Use them when needed for your role.",
            "",
            "## Git Workflow",
            f"- You are working in your own worktree at: `{wt}`",
            f"- Your branch is: `{br}`",
            f"- Base branch is: `{base_branch}`",
            "- Commit your work to YOUR branch only",
            "- Do NOT merge into base branch — the integrator handles merges",
            "- Do NOT push to remote unless explicitly told to",
            "",
            "## Report",
            f"When done, write your report to: `{report_dir}/{agent}.md`",
            "",
            "Your report MUST include:",
            "1. **Summary** — what you did",
            "2. **Files changed** — list with one-line purpose each",
            "3. **Tests/checks performed** — what you verified",
            "4. **Risks** — anything the team should know",
            "5. **Follow-up notes** — remaining work or suggestions",
        ]

        if agent == "architect":
            sections.extend([
                "",
                "## Architect-Specific Instructions",
                f"Write the master plan to: `{report_dir}/architect-plan.md`",
                "",
                "The plan MUST include:",
                "- Task decomposition by role (what each agent should do)",
                "- File ownership map (which agent owns which files/directories)",
                "- Merge order (which branch merges into base first)",
                "- QA checklist for qa-tester",
                "- Acceptance criteria (how to know the task is done)",
                "- Risk assessment",
            ])
        elif agent == "qa-tester":
            sections.extend([
                "",
                "## QA-Specific Instructions",
                f"Write your QA report to: `{report_dir}/qa-report.md`",
                "",
                "Review ALL agent branches before approving:",
                *[
                    f"- `git diff {base_branch}..{branch_name(task_slug, a)}`"
                    for a in AGENTS
                    if a != "qa-tester"
                ],
                "",
                "Check for: compile errors, behavior risks, performance risks,",
                "race conditions, merge conflicts.",
                "",
                "Do NOT approve if any branch has issues.",
                "Verdict must be APPROVE or REJECT with specific reasons.",
            ])

        sections.extend([
            "",
            "## Communication",
            f"- If you need input from another agent, write to: `{WORKSPACE_REL}/full-team/{task_slug}/messages/{agent}-outbox.md`",
            f"- Check for messages at: `{WORKSPACE_REL}/full-team/{task_slug}/messages/{agent}-inbox.md`",
            "",
            "## BEGIN WORK NOW",
            "You have left standby mode. Start working on your assignment immediately.",
        ])

        prompt = "\n".join(sections) + "\n"
        prompt_file = prompt_dir / f"{agent}.md"
        prompt_file.write_text(prompt, encoding="utf-8")
        print(f"  [prompt] wrote {prompt_file}")

    return prompt_dir


# ---------------------------------------------------------------------------
# Verification / status (read-only)
# ---------------------------------------------------------------------------


def verify(task_slug: str) -> int:
    """Print verification table. Returns 0 if all good, 2 if issues."""
    print("=" * 70)
    print("FULL TEAM VERIFICATION")
    print("=" * 70)

    print("\n## Git Worktrees")
    result = run(["git", "worktree", "list"], check=False)
    print(result.stdout)

    session = tmux_session_name(task_slug)
    print("## tmux Session")
    result = run(["tmux", "ls"], check=False)
    print(result.stdout if result.returncode == 0 else "  No tmux sessions found")

    print("## tmux Windows")
    result = run(["tmux", "list-windows", "-t", session], check=False)
    print(result.stdout if result.returncode == 0 else f"  Session {session} not found")

    print("## tmux Panes")
    result = run(["tmux", "list-panes", "-a", "-F",
                   "#{session_name}:#{window_name}.#{pane_index} #{pane_current_path}"],
                  check=False)
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if task_slug in line or "agent-team" in line:
                print(f"  {line}")
    else:
        print("  No panes found")

    print("\n## Claude Processes")
    result = run(["bash", "-c", "ps aux | grep '[c]laude' | head -10 || true"], check=False)
    print(result.stdout.strip() if result.stdout.strip() else "  No claude processes found")

    # Agent mapping table
    print("\n## Agent Mapping Table")
    print(f"{'Agent':<16} {'tmux Window':<30} {'Worktree Path':<50} {'Branch':<40}")
    print("-" * 136)
    issues = 0
    for agent in AGENTS:
        wt = worktree_path(task_slug, agent)
        br = branch_name(task_slug, agent)
        wt_exists = wt.exists()
        tmux_win = f"{session}:{agent}"
        status_wt = "OK" if wt_exists else "MISSING"
        if not wt_exists:
            issues += 1
        print(f"{agent:<16} {tmux_win:<30} {str(wt):<50} {br:<40} [{status_wt}]")

    # Report files
    print("\n## Report Files")
    report_dir = REPORTS_DIR / "team" / task_slug
    for agent in AGENTS:
        report = report_dir / f"{agent}.md"
        st = "EXISTS" if report.exists() else "pending"
        print(f"  {agent}: {report} [{st}]")
    for name in ["architect-plan.md", "qa-report.md", "final-integration-report.md"]:
        report = report_dir / name
        st = "EXISTS" if report.exists() else "pending"
        print(f"  {name}: {report} [{st}]")

    print("\n" + "=" * 70)
    if issues:
        print(f"ISSUES: {issues} worktree(s) missing")
        return 2
    print("ALL CHECKS PASSED")
    return 0


def status(task_slug: str) -> int:
    print(f"Status for task: {task_slug}\n")

    print("## Branch Status")
    base = get_current_branch()
    for agent in AGENTS:
        br = branch_name(task_slug, agent)
        result = run(["git", "log", f"{base}..{br}", "--oneline"], check=False)
        if result.returncode == 0:
            commits = result.stdout.strip().split("\n") if result.stdout.strip() else []
            print(f"  {agent}: {len(commits)} commit(s) ahead of {base}")
            for c in commits[:5]:
                print(f"    {c}")
        else:
            print(f"  {agent}: branch not found or no commits")

    print("\n## Reports")
    report_dir = REPORTS_DIR / "team" / task_slug
    all_done = True
    for agent in AGENTS:
        report = report_dir / f"{agent}.md"
        if report.exists():
            print(f"  {agent}: {report.name} ({report.stat().st_size} bytes)")
        else:
            print(f"  {agent}: NOT YET WRITTEN")
            all_done = False

    print("\nAll agent reports complete. Ready for integration." if all_done
          else "\nSome reports still pending.")
    return 0


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_setup(args: argparse.Namespace) -> int:
    """Full two-phase setup.

    PHASE 1: Spawn teammate sessions (tmux + Claude in standby)
    PHASE 2: Analyze task, create worktrees, assign work

    Teammates MUST be alive before any analysis begins.
    """
    task = args.task
    task_slug = slugify(task)

    print(f"[full-team setup] task: {task}")
    print(f"[full-team setup] slug: {task_slug}")
    print()

    # =====================================================================
    # PHASE 1: SPAWN TEAMMATES FIRST
    # =====================================================================
    print("=" * 70)
    print("PHASE 1: SPAWN TEAMMATE SESSIONS")
    print("=" * 70)

    # Step 1.1: Environment check (fail fast)
    print("\nStep 1.1: Environment check")
    errors = env_check()
    if errors:
        print("BLOCKED — environment not ready:", file=sys.stderr)
        for e in errors:
            print(f"  • {e}", file=sys.stderr)
        print("\nDo NOT fall back to internal subagents.", file=sys.stderr)
        return 2
    print("  Environment OK")

    # Step 1.2: Create tmux session with 4 windows
    print("\nStep 1.2: Create tmux session")
    session = create_tmux_session(task_slug)
    print(f"  Session: {session}")

    # Step 1.3: Launch Claude in standby in each window
    model = getattr(args, "model", DEFAULT_MODEL)
    print(f"\nStep 1.3: Launch Claude in standby mode (model={model})")
    launch_standby_claude(task_slug, model)

    # Step 1.4: VALIDATE teammate sessions are alive
    print("\nStep 1.4: Validate teammate sessions (MANDATORY)")
    teammate_ok, teammate_report = validate_teammate_sessions_first(task_slug)
    print(teammate_report)

    if not teammate_ok:
        print("\n[ABORT] Teammate session validation FAILED.", file=sys.stderr)
        print("Cannot proceed to task analysis or worktree creation.", file=sys.stderr)
        print("Do NOT fall back to internal subagents.", file=sys.stderr)
        print("Do NOT simulate the team.", file=sys.stderr)
        print(f"\nTo retry: python3 .claude/scripts/full_team.py setup \"{task}\"", file=sys.stderr)
        print(f"To teardown: python3 .claude/scripts/full_team.py teardown \"{task}\"", file=sys.stderr)
        return 5

    print("\n✓ All 4 teammate sessions verified. Proceeding to Phase 2.")

    # =====================================================================
    # PHASE 2: ANALYZE TASK, CREATE WORKTREES, ASSIGN WORK
    # =====================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: ANALYZE + ASSIGN")
    print("=" * 70)

    # Step 2.1: Detect base branch
    print("\nStep 2.1: Detect base branch")
    base_branch = get_base_branch()
    print(f"  Base branch: {base_branch}")

    # Step 2.2: Dirty check
    print("\nStep 2.2: Working tree cleanliness")
    if is_worktree_dirty():
        print("  WARNING: Working tree is dirty.", file=sys.stderr)
        print("  Worktrees will be created from current HEAD regardless.", file=sys.stderr)
        print("  Consider: git stash, git commit, or proceed with caution.", file=sys.stderr)

    # Step 2.3: Create worktrees
    print("\nStep 2.3: Create git worktrees")
    worktrees = create_worktrees(task_slug, base_branch)
    if len(worktrees) != len(AGENTS):
        print(f"  FAILED: only {len(worktrees)}/{len(AGENTS)} worktrees created", file=sys.stderr)
        return 3
    print(f"  All {len(worktrees)} worktrees created")

    # Step 2.4: Create report directories
    print("\nStep 2.4: Create report directories")
    report_dir = REPORTS_DIR / "team" / task_slug
    report_dir.mkdir(parents=True, exist_ok=True)
    for agent, wt in worktrees.items():
        (wt / REPORTS_REL / "team" / task_slug).mkdir(parents=True, exist_ok=True)
    print(f"  Report dir: {report_dir}")

    # Step 2.5: Create message directories for inter-agent communication
    msg_dir = WORKSPACE_DIR / "full-team" / task_slug / "messages"
    msg_dir.mkdir(parents=True, exist_ok=True)

    # Step 2.6: Generate assignment prompts
    print("\nStep 2.6: Generate agent assignment prompts")
    prompt_dir = generate_prompts(task_slug, task, base_branch, worktrees)
    print(f"  Prompt dir: {prompt_dir}")

    # Step 2.7: Send assignments to running teammates
    print("\nStep 2.7: Send assignments to teammate sessions")
    for agent in AGENTS:
        wt = worktrees[agent]
        prompt_file = prompt_dir / f"{agent}.md"
        send_assignment_to_teammate(task_slug, agent, prompt_file, wt)

    # Step 2.8: Full setup validation
    print("\nStep 2.8: Full setup validation")
    setup_ok, setup_report = validate_full_setup(task_slug)
    print(setup_report)

    if not setup_ok:
        print("\n[WARNING] Full setup validation has issues.", file=sys.stderr)
        print("Teammates are running but some infrastructure may be incomplete.", file=sys.stderr)

    # Summary
    print(f"""
================================================================================
FULL TEAM LAUNCHED — REAL MULTI-AGENT MODE
================================================================================
Task:       {task}
Slug:       {task_slug}
Base:       {base_branch}
Session:    {session}
Agents:     {', '.join(AGENTS)}

Startup order verified:
  Phase 1: tmux session created → Claude launched in standby → validated
  Phase 2: worktrees created → prompts generated → assignments sent

Attach to session:
  tmux attach -t {session}

Switch between agents:
  Ctrl-B then window number (0-3), or Ctrl-B n/p

Check status:
  python3 .claude/scripts/full_team.py status "{task}"

Re-verify setup:
  python3 .claude/scripts/full_team.py verify "{task}"

Teardown when done:
  python3 .claude/scripts/full_team.py teardown "{task}"
================================================================================
""")
    return 0


def cmd_spawn_teammates(args: argparse.Namespace) -> int:
    """Phase 1 only: create tmux session + launch Claude in standby.

    Use this when you want to spawn teammates first, then manually
    run 'assign' later after preparing worktrees.
    """
    task = args.task
    task_slug = slugify(task)

    print(f"[spawn-teammates] task: {task}")
    print(f"[spawn-teammates] slug: {task_slug}")

    errors = env_check()
    if errors:
        print("BLOCKED:", file=sys.stderr)
        for e in errors:
            print(f"  • {e}", file=sys.stderr)
        return 2

    session = create_tmux_session(task_slug)
    launch_standby_claude(task_slug, getattr(args, "model", DEFAULT_MODEL))

    ok, report = validate_teammate_sessions_first(task_slug)
    print(report)

    if not ok:
        print("\n[ABORT] Teammate validation failed.", file=sys.stderr)
        return 5

    print(f"\nTeammates spawned in session: {session}")
    print(f"Run 'assign' to create worktrees and send assignments:")
    print(f'  python3 .claude/scripts/full_team.py assign "{task}"')
    return 0


def cmd_assign(args: argparse.Namespace) -> int:
    """Phase 2 only: create worktrees + generate prompts + send assignments.

    Requires teammates to already be running (from spawn-teammates or setup).
    """
    task = args.task
    task_slug = slugify(task)

    print(f"[assign] task: {task}")
    print(f"[assign] slug: {task_slug}")

    # Validate teammates first
    ok, report = validate_teammate_sessions_first(task_slug)
    if not ok:
        print(report)
        print("\n[ABORT] Teammates not running. Run spawn-teammates first.", file=sys.stderr)
        return 5

    base_branch = get_base_branch()
    worktrees = create_worktrees(task_slug, base_branch)
    if len(worktrees) != len(AGENTS):
        print(f"FAILED: only {len(worktrees)}/{len(AGENTS)} worktrees", file=sys.stderr)
        return 3

    report_dir = REPORTS_DIR / "team" / task_slug
    report_dir.mkdir(parents=True, exist_ok=True)
    for agent, wt in worktrees.items():
        (wt / REPORTS_REL / "team" / task_slug).mkdir(parents=True, exist_ok=True)

    msg_dir = WORKSPACE_DIR / "full-team" / task_slug / "messages"
    msg_dir.mkdir(parents=True, exist_ok=True)

    prompt_dir = generate_prompts(task_slug, task, base_branch, worktrees)

    for agent in AGENTS:
        send_assignment_to_teammate(task_slug, agent, prompt_dir / f"{agent}.md", worktrees[agent])

    print("\nAssignments sent to all teammates.")
    return 0


def cmd_worktrees(args: argparse.Namespace) -> int:
    task_slug = slugify(args.task)
    base_branch = get_base_branch()
    print(f"Creating worktrees for: {task_slug}")
    worktrees = create_worktrees(task_slug, base_branch)
    return 0 if len(worktrees) == len(AGENTS) else 3


def cmd_prompts(args: argparse.Namespace) -> int:
    task_slug = slugify(args.task)
    base_branch = get_base_branch()
    worktrees = {a: worktree_path(task_slug, a) for a in AGENTS}
    generate_prompts(task_slug, args.task, base_branch, worktrees)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    task_slug = slugify(args.task)
    verify(task_slug)
    print()
    passed, report = validate_full_setup(task_slug)
    print(report)
    return 0 if passed else 2


def cmd_teardown(args: argparse.Namespace) -> int:
    task_slug = slugify(args.task)
    print(f"Tearing down: {task_slug}")
    kill_tmux_session(task_slug)
    remove_worktrees(task_slug)
    print("Teardown complete.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    task_slug = slugify(args.task)
    return status(task_slug)


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="full_team.py",
        description="Real multi-agent team orchestrator for /team --full",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name, func in [
        ("setup", cmd_setup),
        ("spawn-teammates", cmd_spawn_teammates),
        ("assign", cmd_assign),
        ("worktrees", cmd_worktrees),
        ("prompts", cmd_prompts),
        ("teardown", cmd_teardown),
        ("status", cmd_status),
    ]:
        p = sub.add_parser(name)
        p.add_argument("task", help="Task description")
        p.add_argument(
            "--model",
            default=DEFAULT_MODEL,
            help=f"Model for spawned teammate sessions (default: {DEFAULT_MODEL})",
        )
        p.set_defaults(func=func)

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("task", help="Task description (for slug)")
    p_verify.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:
        print(f"[full-team] internal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
