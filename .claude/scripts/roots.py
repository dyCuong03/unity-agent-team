#!/usr/bin/env python3
"""Single source of truth for root resolution and project configuration.

Every framework script imports this module instead of computing paths itself.
validate_portability.py fails the build if any other script resolves roots
on its own.

Root concepts
-------------
FRAMEWORK_ROOT     dir containing the installed framework's .claude/
                   (this file lives at <FRAMEWORK_ROOT>/.claude/scripts/roots.py)
CLAUDE_ROOT        the active .claude/ configuration directory
PROJECT_ROOT       the repository being worked on (may differ from
                   FRAMEWORK_ROOT in external/shared and monorepo modes)
UNITY_PROJECT_ROOT dir containing Assets/, Packages/manifest.json and
                   ProjectSettings/ProjectVersion.txt — None for non-Unity
WORKSPACE_ROOT     optional parent dir holding multiple repositories;
                   never guessed, only explicit config/env

Resolution order for PROJECT_ROOT
---------------------------------
1. explicit argument (CLI --project-root passed through by callers)
2. env AGENT_TEAM_PROJECT_ROOT (legacy alias: UNITY_TEAM_PROJECT_ROOT)
3. project-config.json "projectRoot" (relative to CLAUDE_ROOT's parent)
4. `git rev-parse --show-toplevel` from the current working directory
5. walk up from cwd looking for a `.claude/` directory (max 8 levels)
6. fail with RootResolutionError — never guess
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ENV_PROJECT_ROOT = "AGENT_TEAM_PROJECT_ROOT"
ENV_PROJECT_ROOT_LEGACY = "UNITY_TEAM_PROJECT_ROOT"
ENV_WORKSPACE_ROOT = "AGENT_TEAM_WORKSPACE_ROOT"
CONFIG_FILENAME = "project-config.json"

PROJECT_TYPES = ("unity", "cloudcode", "web", "backend", "cocos", "generic")

UNITY_MARKERS = ("Assets", "Packages/manifest.json", "ProjectSettings/ProjectVersion.txt")


class RootResolutionError(RuntimeError):
    """Raised when a root cannot be resolved. Message is always actionable."""


# --------------------------------------------------------------------------
# Structural roots (never configured)
# --------------------------------------------------------------------------

def framework_root() -> Path:
    """Root of the installed framework: parents[2] of this file, validated."""
    root = Path(__file__).resolve().parents[2]
    if not (root / ".claude").is_dir():
        raise RootResolutionError(
            f"Framework structure broken: expected {root}/.claude to exist. "
            "Did you move roots.py out of .claude/scripts/?"
        )
    return root


def claude_root() -> Path:
    """The active .claude/ directory (the one this framework runs from)."""
    return framework_root() / ".claude"


# --------------------------------------------------------------------------
# Project root
# --------------------------------------------------------------------------

def _git_toplevel(start: Path) -> Optional[Path]:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(start), capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip()).resolve()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _walk_up_for_claude(start: Path, max_levels: int = 8) -> Optional[Path]:
    cur = start.resolve()
    for _ in range(max_levels):
        if (cur / ".claude").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def project_root(explicit: Optional[str] = None, cwd: Optional[Path] = None) -> Path:
    """Resolve PROJECT_ROOT using the documented order. Raises on failure."""
    cwd = (cwd or Path.cwd()).resolve()

    # 1. explicit
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.is_dir():
            raise RootResolutionError(
                f"--project-root {explicit!r} does not exist or is not a directory."
            )
        return p

    # 2. environment
    for var in (ENV_PROJECT_ROOT, ENV_PROJECT_ROOT_LEGACY):
        val = os.environ.get(var)
        if val:
            p = Path(val).expanduser().resolve()
            if not p.is_dir():
                raise RootResolutionError(
                    f"{var}={val!r} does not point to an existing directory."
                )
            return p

    # 3. project-config.json next to the active .claude
    try:
        cfg_path = claude_root() / CONFIG_FILENAME
    except RootResolutionError:
        cfg_path = None
    if cfg_path and cfg_path.is_file():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RootResolutionError(
                f"Cannot parse {cfg_path}: {exc}. Fix or delete it, "
                "or run: python .claude/scripts/setup.py --check"
            )
        rel = raw.get("projectRoot")
        if rel and rel != ".":
            p = (framework_root() / rel).resolve()
            if not p.is_dir():
                raise RootResolutionError(
                    f"project-config.json projectRoot={rel!r} resolves to {p}, "
                    "which does not exist."
                )
            return p
        if rel == ".":
            return framework_root()

    # 4. git toplevel from cwd
    git_root = _git_toplevel(cwd)
    if git_root is not None:
        return git_root

    # 5. walk up for .claude
    walked = _walk_up_for_claude(cwd)
    if walked is not None:
        return walked

    # 6. fail
    raise RootResolutionError(
        "Cannot resolve PROJECT_ROOT. Provide one of:\n"
        f"  - env {ENV_PROJECT_ROOT}=<path>\n"
        "  - .claude/project-config.json with \"projectRoot\"\n"
        "  - run from inside a git repository or a directory with .claude/\n"
        "Run: python .claude/scripts/setup.py  to initialize a project."
    )


# --------------------------------------------------------------------------
# Project configuration
# --------------------------------------------------------------------------

def _default_config(proj_root: Path) -> Dict[str, Any]:
    return {
        "projectName": proj_root.name,
        "projectRoot": ".",
        "projectType": "generic",
        "unityProjectRoot": None,
        "defaultBranch": None,           # resolved from git when None
        "allowedBranches": [],            # empty = no restriction
        "devlogPaths": [".claude/devlogs"],
        "workspaceDir": "workspace",
        "reportsDir": "reports",
        "worktreeRoot": None,             # default derived from projectName
        "agentMemoryEnabled": False,
        "agentMemoryIndexPath": ".agentmemory",
        "teamProfiles": {
            "default": ["architect", "coder", "tester"],
            "full": ["architect", "coder", "tester"],
        },
        "ownershipDefaults": {},
        "workspacePaths": [],             # monorepo cross-project allow-list
    }


def load_config(proj_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load project config merged over defaults. Absent file = pure defaults.

    Lookup order: <PROJECT_ROOT>/.claude/project-config.json, then the
    framework's own .claude/project-config.json (external/shared mode).
    """
    proj_root = proj_root or project_root()
    candidates = [proj_root / ".claude" / CONFIG_FILENAME]
    try:
        fw_cfg = claude_root() / CONFIG_FILENAME
        if fw_cfg not in candidates:
            candidates.append(fw_cfg)
    except RootResolutionError:
        pass

    cfg = _default_config(proj_root)
    for path in candidates:
        if path.is_file():
            try:
                user = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RootResolutionError(f"Invalid config {path}: {exc}")
            if not isinstance(user, dict):
                raise RootResolutionError(f"Invalid config {path}: must be a JSON object")
            cfg.update({k: v for k, v in user.items() if v is not None})
            cfg["_config_path"] = str(path)
            break
    return cfg


# --------------------------------------------------------------------------
# Derived roots and paths
# --------------------------------------------------------------------------

def is_unity_dir(p: Path) -> bool:
    return all((p / m).exists() for m in UNITY_MARKERS)


def unity_project_root(proj_root: Optional[Path] = None,
                       cfg: Optional[Dict[str, Any]] = None) -> Optional[Path]:
    """UNITY_PROJECT_ROOT or None. Config wins; else scan root + 2 child levels."""
    proj_root = proj_root or project_root()
    cfg = cfg or load_config(proj_root)
    configured = cfg.get("unityProjectRoot")
    if configured:
        p = (proj_root / configured).resolve()
        return p if is_unity_dir(p) else None
    if is_unity_dir(proj_root):
        return proj_root
    # controlled child scan, depth 2, skip hidden/heavy dirs
    skip = {".git", "node_modules", "Library", "Temp", "obj", "bin", ".claude"}
    for child in sorted(d for d in proj_root.iterdir()
                        if d.is_dir() and d.name not in skip and not d.name.startswith(".")):
        if is_unity_dir(child):
            return child
        for grand in sorted(d for d in child.iterdir()
                            if d.is_dir() and d.name not in skip and not d.name.startswith(".")):
            if is_unity_dir(grand):
                return grand
    return None


def workspace_root(cfg: Optional[Dict[str, Any]] = None) -> Optional[Path]:
    env = os.environ.get(ENV_WORKSPACE_ROOT)
    if env:
        return Path(env).expanduser().resolve()
    cfg = cfg or load_config()
    val = cfg.get("workspaceRoot")
    return (project_root() / val).resolve() if val else None


def workspace_dir(proj_root: Optional[Path] = None,
                  cfg: Optional[Dict[str, Any]] = None) -> Path:
    proj_root = proj_root or project_root()
    cfg = cfg or load_config(proj_root)
    return (proj_root / cfg.get("workspaceDir", "workspace")).resolve()


def reports_dir(proj_root: Optional[Path] = None,
                cfg: Optional[Dict[str, Any]] = None) -> Path:
    proj_root = proj_root or project_root()
    cfg = cfg or load_config(proj_root)
    return (proj_root / cfg.get("reportsDir", "reports")).resolve()


def devlog_paths(proj_root: Optional[Path] = None,
                 cfg: Optional[Dict[str, Any]] = None,
                 existing_only: bool = True) -> List[Path]:
    """Configured devlog dirs. Missing dirs are optional, never an error."""
    proj_root = proj_root or project_root()
    cfg = cfg or load_config(proj_root)
    out = []
    for rel in cfg.get("devlogPaths", [".claude/devlogs"]):
        p = (proj_root / rel).resolve()
        if not existing_only or p.is_dir():
            out.append(p)
    return out


def worktree_root(proj_root: Optional[Path] = None,
                  cfg: Optional[Dict[str, Any]] = None) -> Path:
    """Per-project worktree base. Default: sibling '<projectName>-worktrees'.

    Project name in the default prevents two projects sharing one dir.
    """
    proj_root = proj_root or project_root()
    cfg = cfg or load_config(proj_root)
    configured = cfg.get("worktreeRoot")
    if configured:
        return (proj_root / configured).resolve()
    name = cfg.get("projectName") or proj_root.name
    return (proj_root.parent / f"{name}-worktrees").resolve()


def default_branch(proj_root: Optional[Path] = None,
                   cfg: Optional[Dict[str, Any]] = None) -> str:
    """Configured default branch, else origin/HEAD, else current branch."""
    proj_root = proj_root or project_root()
    cfg = cfg or load_config(proj_root)
    if cfg.get("defaultBranch"):
        return cfg["defaultBranch"]
    try:
        out = subprocess.run(
            ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
            cwd=str(proj_root), capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip().split("/", 1)[-1]
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        out = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(proj_root), capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "main"


def team_profile(name: str = "default",
                 cfg: Optional[Dict[str, Any]] = None) -> List[str]:
    cfg = cfg or load_config()
    profiles = cfg.get("teamProfiles") or {}
    if name in profiles:
        return list(profiles[name])
    if "default" in profiles:
        return list(profiles["default"])
    return ["architect", "coder", "tester"]


def detect_project_type(proj_root: Path) -> str:
    """Best-effort project type detection for setup defaults."""
    if is_unity_dir(proj_root) or unity_search_hit(proj_root):
        return "unity"
    if (proj_root / "cloudcode").is_dir() or _glob_any(proj_root, "*.cc.js"):
        return "cloudcode"
    pkg = proj_root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if any(k in deps for k in ("react", "vue", "next", "svelte", "angular")):
                return "web"
            if "cc" in deps or (proj_root / "assets").is_dir() and (proj_root / "settings").is_dir():
                return "cocos"
            return "backend" if deps else "generic"
        except (OSError, json.JSONDecodeError):
            pass
    if any((proj_root / f).is_file() for f in ("pyproject.toml", "go.mod", "Cargo.toml", "pom.xml")):
        return "backend"
    return "generic"


def unity_search_hit(proj_root: Path) -> bool:
    try:
        return unity_project_root(proj_root, _default_config(proj_root)) is not None
    except Exception:
        return False


def _glob_any(root: Path, pattern: str) -> bool:
    try:
        next(root.glob(pattern))
        return True
    except StopIteration:
        return False


# --------------------------------------------------------------------------
# CLI: print resolved context (used by commands, agents, smoke tests)
# --------------------------------------------------------------------------

def resolve_all(explicit: Optional[str] = None) -> Dict[str, Any]:
    proj = project_root(explicit)
    cfg = load_config(proj)
    unity = unity_project_root(proj, cfg)
    return {
        "FRAMEWORK_ROOT": str(framework_root()),
        "CLAUDE_ROOT": str(claude_root()),
        "PROJECT_ROOT": str(proj),
        "UNITY_PROJECT_ROOT": str(unity) if unity else None,
        "WORKSPACE_ROOT": str(workspace_root(cfg)) if workspace_root(cfg) else None,
        "projectName": cfg.get("projectName"),
        "projectType": cfg.get("projectType"),
        "defaultBranch": default_branch(proj, cfg),
        "workspaceDir": str(workspace_dir(proj, cfg)),
        "reportsDir": str(reports_dir(proj, cfg)),
        "worktreeRoot": str(worktree_root(proj, cfg)),
        "devlogPaths": [str(p) for p in devlog_paths(proj, cfg, existing_only=False)],
        "devlogPathsExisting": [str(p) for p in devlog_paths(proj, cfg)],
        "agentMemoryEnabled": bool(cfg.get("agentMemoryEnabled")),
        "teamProfiles": cfg.get("teamProfiles"),
        "configPath": cfg.get("_config_path"),
    }


def main(argv: List[str]) -> int:
    explicit = None
    as_json = "--json" in argv
    for i, a in enumerate(argv):
        if a == "--project-root" and i + 1 < len(argv):
            explicit = argv[i + 1]
    try:
        ctx = resolve_all(explicit)
    except RootResolutionError as exc:
        print(f"[roots] ERROR: {exc}", file=sys.stderr)
        return 2
    if ctx.get("configPath") is None:
        print("[roots] note: no project-config.json found — using built-in "
              "defaults. Run: python3 .claude/scripts/setup.py", file=sys.stderr)
    if as_json:
        print(json.dumps(ctx, indent=2))
    else:
        for k, v in ctx.items():
            print(f"{k}={v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
