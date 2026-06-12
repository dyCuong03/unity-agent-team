#!/usr/bin/env python3
"""Idempotent project setup for the agent-team framework.

Usage:
    python .claude/scripts/setup.py                 # interactive-ish, safe defaults
    python .claude/scripts/setup.py --check         # dry run, change nothing, exit 1 if work needed
    python .claude/scripts/setup.py --yes           # non-interactive, accept all defaults
    python .claude/scripts/setup.py --project-root <path>
    python .claude/scripts/setup.py --force         # required to overwrite existing config values

Behavior:
- Detects the target repository and its project type
  (unity / cloudcode / web / backend / cocos / generic).
- Creates required directories (workspace/, reports/, devlogs when configured).
- Writes .claude/project-config.json with detected defaults — never
  overwrites existing user values without --force.
- Seeds only the knowledge files the selected architecture uses:
  workspace/repo-knowledge.md + recent-changes.md (all types),
  workspace/ecs-registry.md (unity only).
- Validates dependencies (python version, git, optional MCP config).
- Configures agentmemory .mcp.json from template when enabled.
- Safe to run any number of times.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import roots  # noqa: E402

MIN_PYTHON = (3, 8)

KNOWLEDGE_SEEDS = {
    "repo-knowledge.md": (
        "# Repo Knowledge\n\n"
        "Stable architecture facts for this project. Section format:\n\n"
        "```\n## [tag:<tags>] <Title>\n<fact>\n"
        "<!-- confidence:1.00 verified:<YYYY-MM-DD> source:<agent> -->\n```\n\n"
        "(Seeded by setup.py — agents append via the learning loop.)\n"
    ),
    "recent-changes.md": (
        "# Recent Changes\n\n"
        "Rolling 14-day architectural mutations. Entry format:\n\n"
        "```\n[DATE] domain:<d> impact:<high|medium|low> affects:<agents>\n"
        "change: <one line>\nrisk: <one line>\n```\n\n"
        "(Seeded by setup.py.)\n"
    ),
    "ecs-registry.md": (
        "# ECS Registry\n\n"
        "Component and system ownership for this Unity project.\n\n"
        "| Component/System | Owner system | Writers | Readers | Notes |\n"
        "|---|---|---|---|---|\n\n"
        "(Seeded by setup.py — Unity/DOTS projects only.)\n"
    ),
}

TEAM_PROFILE_DEFAULTS = {
    "unity": {
        "default": ["architect", "unity-dev", "tester"],
        "dots": ["architect", "unity-dots-dev", "tester"],
        "full": ["architect", "unity-dots-dev", "unity-dev", "qa-tester"],
    },
    "cloudcode": {
        "default": ["architect", "backend-dev", "tester"],
        "full": ["architect", "backend-dev", "qa-tester"],
    },
    "web": {
        "default": ["architect", "web-dev", "tester"],
        "full": ["architect", "web-dev", "qa-tester"],
    },
    "backend": {
        "default": ["architect", "backend-dev", "tester"],
        "full": ["architect", "backend-dev", "qa-tester"],
    },
    "cocos": {
        "default": ["architect", "coder", "tester"],
        "full": ["architect", "coder", "qa-tester"],
    },
    "generic": {
        "default": ["architect", "coder", "tester"],
        "full": ["architect", "coder", "qa-tester"],
    },
}


class Plan:
    """Accumulates planned actions; --check prints them without applying."""

    def __init__(self) -> None:
        self.actions: List[Tuple[str, str]] = []   # (kind, description)
        self.errors: List[str] = []
        self.notes: List[str] = []

    def add(self, kind: str, desc: str) -> None:
        self.actions.append((kind, desc))

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def note(self, msg: str) -> None:
        self.notes.append(msg)


def check_dependencies(plan: Plan, proj_root: Path) -> None:
    if sys.version_info < MIN_PYTHON:
        plan.error(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required, "
                   f"found {sys.version.split()[0]}")
    if shutil.which("git") is None:
        plan.error("git not found on PATH — required for worktrees and branch resolution")
    else:
        try:
            r = subprocess.run(["git", "rev-parse", "--git-dir"], cwd=str(proj_root),
                               capture_output=True, text=True, timeout=10)
            if r.returncode != 0:
                plan.note(f"{proj_root} is not a git repository — worktree features disabled "
                          "until `git init` is run")
        except (OSError, subprocess.TimeoutExpired):
            plan.note("git check timed out — continuing")


def build_config(proj_root: Path, existing: Dict[str, Any]) -> Dict[str, Any]:
    ptype = existing.get("projectType") or roots.detect_project_type(proj_root)
    unity = roots.unity_project_root(proj_root, dict(existing, unityProjectRoot=existing.get("unityProjectRoot")))
    cfg: Dict[str, Any] = {
        "projectName": existing.get("projectName") or proj_root.name,
        "projectRoot": existing.get("projectRoot") or ".",
        "projectType": ptype,
        "defaultBranch": existing.get("defaultBranch") or roots.default_branch(proj_root, {}),
        "allowedBranches": existing.get("allowedBranches", []),
        "devlogPaths": existing.get("devlogPaths") or [".claude/devlogs"],
        "workspaceDir": existing.get("workspaceDir") or "workspace",
        "reportsDir": existing.get("reportsDir") or "reports",
        "agentMemoryEnabled": existing.get("agentMemoryEnabled", False),
        "agentMemoryIndexPath": existing.get("agentMemoryIndexPath") or ".agentmemory",
        "teamProfiles": existing.get("teamProfiles") or TEAM_PROFILE_DEFAULTS[ptype],
    }
    if unity is not None:
        try:
            cfg["unityProjectRoot"] = str(unity.relative_to(proj_root)) or "."
        except ValueError:
            cfg["unityProjectRoot"] = str(unity)
    if existing.get("worktreeRoot"):
        cfg["worktreeRoot"] = existing["worktreeRoot"]
    if existing.get("ownershipDefaults"):
        cfg["ownershipDefaults"] = existing["ownershipDefaults"]
    if existing.get("workspacePaths"):
        cfg["workspacePaths"] = existing["workspacePaths"]
    return cfg


def run_setup(args: argparse.Namespace) -> int:
    plan = Plan()
    try:
        proj_root = roots.project_root(args.project_root)
    except roots.RootResolutionError as exc:
        # setup may be the very first command: fall back to cwd if it's a repo-ish dir
        proj_root = Path.cwd().resolve()
        plan.note(f"Root resolver had no signal ({exc}); using cwd {proj_root}")

    check_dependencies(plan, proj_root)

    claude_dir = proj_root / ".claude"
    cfg_path = claude_dir / roots.CONFIG_FILENAME

    existing: Dict[str, Any] = {}
    if cfg_path.is_file():
        try:
            existing = json.loads(cfg_path.read_text(encoding="utf-8"))
            plan.note(f"Existing config found at {cfg_path} — values preserved "
                      "(use --force to regenerate)")
        except (OSError, json.JSONDecodeError) as exc:
            plan.error(f"Existing {cfg_path} is invalid JSON: {exc}. "
                       "Fix it or delete it, then re-run setup.")
            existing = {}

    if plan.errors:
        _print_summary(plan, applied=False)
        return 2

    cfg = build_config(proj_root, {} if args.force else existing)
    ptype = cfg["projectType"]

    # planned directory creation
    dirs = [
        proj_root / cfg["workspaceDir"],
        proj_root / cfg["workspaceDir"] / "skill-cache",
        proj_root / cfg["reportsDir"],
        claude_dir,
    ]
    for rel in cfg["devlogPaths"]:
        dirs.append(proj_root / rel)
    for d in dirs:
        if not d.is_dir():
            plan.add("mkdir", str(d))

    # planned config write
    if not cfg_path.is_file() or args.force or (existing and existing != {**existing, **cfg} and not existing):
        pass
    write_config = (not cfg_path.is_file()) or args.force
    if not write_config and existing:
        # additive merge: add missing keys only
        merged = dict(cfg)
        merged.update(existing)
        if merged != existing:
            write_config = True
            cfg = merged
            plan.note("Adding missing config keys (existing values untouched)")
        else:
            cfg = merged
    if write_config:
        plan.add("write", f"{cfg_path} (projectType={ptype})")

    # planned knowledge seeds
    ws = proj_root / cfg["workspaceDir"]
    seeds = ["repo-knowledge.md", "recent-changes.md"]
    if ptype == "unity":
        seeds.append("ecs-registry.md")
    for name in seeds:
        target = ws / name
        if not target.is_file():
            plan.add("seed", str(target))

    # agentmemory
    if cfg.get("agentMemoryEnabled"):
        mcp = proj_root / ".mcp.json"
        if not mcp.is_file():
            tmpl = roots.framework_root() / ".mcp.json.template"
            if tmpl.is_file():
                plan.add("mcp", f"{mcp} from template (repo={proj_root})")
            else:
                plan.note("agentMemoryEnabled but .mcp.json.template missing — "
                          "configure agentmemory MCP manually")
        idx = proj_root / cfg["agentMemoryIndexPath"]
        if not idx.exists():
            plan.note(f"agentmemory index dir {idx} will be created on first index run")

    if args.check:
        _print_summary(plan, applied=False)
        return 1 if plan.actions else 0

    # ---- apply ----
    for kind, desc in plan.actions:
        if kind == "mkdir":
            Path(desc).mkdir(parents=True, exist_ok=True)
        elif kind == "write":
            cfg_out = {k: v for k, v in cfg.items() if not k.startswith("_")}
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            cfg_path.write_text(json.dumps(cfg_out, indent=2) + "\n", encoding="utf-8")
        elif kind == "seed":
            p = Path(desc)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(KNOWLEDGE_SEEDS[p.name], encoding="utf-8")
        elif kind == "mcp":
            tmpl = roots.framework_root() / ".mcp.json.template"
            content = tmpl.read_text(encoding="utf-8").replace(
                "<ABSOLUTE_PATH_TO_REPO_ROOT>", str(proj_root))
            (proj_root / ".mcp.json").write_text(content, encoding="utf-8")

    _print_summary(plan, applied=True, proj_root=proj_root, ptype=ptype)
    return 0


def _print_summary(plan: Plan, applied: bool, proj_root: Path = None, ptype: str = None) -> None:
    hdr = "SETUP SUMMARY" if applied else "SETUP CHECK (dry run — nothing changed)"
    print(f"=== {hdr} ===")
    if proj_root:
        print(f"project root : {proj_root}")
        print(f"project type : {ptype}")
    for kind, desc in plan.actions:
        verb = {"mkdir": "created dir", "write": "wrote", "seed": "seeded",
                "mcp": "configured"}[kind] if applied else \
               {"mkdir": "would create", "write": "would write", "seed": "would seed",
                "mcp": "would configure"}[kind]
        print(f"  [{verb}] {desc}")
    if not plan.actions:
        print("  nothing to do — already set up")
    for n in plan.notes:
        print(f"  note: {n}")
    for e in plan.errors:
        print(f"  ERROR: {e}")
    if applied and not plan.errors:
        print("Next steps: python .claude/scripts/orchestrate.py preflight ; then /team <intent> <task>")


def main() -> int:
    ap = argparse.ArgumentParser(description="Idempotent agent-team project setup")
    ap.add_argument("--check", action="store_true", help="dry run; exit 1 if changes needed")
    ap.add_argument("--yes", "--non-interactive", action="store_true", dest="yes",
                    help="accept all defaults (setup never prompts; flag reserved for automation)")
    ap.add_argument("--force", action="store_true",
                    help="regenerate config, overwriting existing values")
    ap.add_argument("--project-root", default=None)
    args = ap.parse_args()
    try:
        return run_setup(args)
    except Exception as exc:  # actionable top-level error, no tracebacks for users
        print(f"[setup] ERROR: {exc}", file=sys.stderr)
        if "--debug" in sys.argv:
            raise
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
