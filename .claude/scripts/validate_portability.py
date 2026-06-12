#!/usr/bin/env python3
"""Deterministic portability validator for the agent-team framework.

Exit codes: 0 = PASS, 1 = FAIL (findings printed), 2 = internal error.

Checks
------
a. banned-name      Hardcoded project/host names in framework files
                    (.claude/**/*.{py,md,json} + root docs). A line may carry
                    an inline waiver:  portability-allow: <reason>
b. root-resolver    Root resolution logic (parents[2] / parent.parent.parent /
                    *_PROJECT_ROOT env reads) anywhere except roots.py.
c. broken-reference Every literal `.claude/...` path mentioned in
                    .claude/commands/*.md and .claude/agents/*.md must exist
                    (placeholders, globs and template vars are tolerated).
d. config           project-config.json (when present): field types,
                    projectType membership, and relative paths must not escape
                    PROJECT_ROOT — except worktreeRoot, which may be a direct
                    sibling ("../<name>").
e. cwd-dependence   os.getcwd() / Path.cwd() in .claude/scripts/*.py outside
                    roots.py and setup.py.

Usage:
    python .claude/scripts/validate_portability.py [--root <dir>] [--json]
"""
from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

SELF_NAME = "validate_portability.py"
WAIVER_MARK = "portability-allow:"

# Note: tokens below are the *banned* strings; this file is excluded from its
# own scan (SELF_NAME), so listing them here is safe.
BANNED_TOKENS = [
    "UnityBackpackAdventures",
    "BackpackAdventures",
    "UnityCloudCode",
    "BuzzleStudio",
    "/mnt/e/",
    "E:/Buzzle",
]

ROOT_DOCS = ["CLAUDE.md", "README.md", "SETUP.md", "CLONE-SETUP.md",
             "MIGRATION.md", "AGENTS.md"]

SCAN_SUFFIXES = {".py", ".md", ".json"}

RESOLVER_PATTERNS = [
    (re.compile(r"\.parents\[2\]"), "parents[2]"),
    (re.compile(r"\.parent\.parent\.parent\b"), "parent.parent.parent"),
    (re.compile(r"UNITY_TEAM_PROJECT_ROOT"), "UNITY_TEAM_PROJECT_ROOT"),
    (re.compile(r"AGENT_TEAM_PROJECT_ROOT"), "AGENT_TEAM_PROJECT_ROOT"),
]
# A relative-import shim is always fine (it is not root resolution).
SHIM_RE = re.compile(
    r"sys\.path\.insert\(\s*0\s*,\s*str\(Path\(__file__\)\.resolve\(\)\.parent\)\s*\)"
)

CWD_RE = re.compile(r"\bos\.getcwd\(\)|\bPath\.cwd\(\)")

CLAUDE_PATH_RE = re.compile(r"\.claude/[\w\-./<>{}$*?\[\]]+")
PLACEHOLDER_RE = re.compile(r"[<>{}$*?\[\]]")

# Well-known user-created / generated files: referenced in docs by design,
# legitimately absent from a fresh checkout.
ALLOWED_MISSING_REFS = {
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".claude/project-config.json",
}

ALLOWED_PROJECT_TYPES = ("unity", "cloudcode", "web", "backend", "cocos", "generic")

# field name -> (allowed python types, allow None)
CONFIG_FIELD_TYPES: Dict[str, tuple] = {
    "projectName": ((str,), False),
    "projectRoot": ((str,), False),
    "projectType": ((str,), False),
    "unityProjectRoot": ((str,), True),
    "defaultBranch": ((str,), True),
    "allowedBranches": ((list,), False),
    "devlogPaths": ((list,), False),
    "workspaceDir": ((str,), False),
    "reportsDir": ((str,), False),
    "worktreeRoot": ((str,), True),
    "agentMemoryEnabled": ((bool,), False),
    "agentMemoryIndexPath": ((str,), False),
    "teamProfiles": ((dict,), False),
    "ownershipDefaults": ((dict,), False),
    "workspacePaths": ((list,), False),
    "workspaceRoot": ((str,), True),
}

# relative-path fields that must stay inside PROJECT_ROOT
CONFIG_PATH_FIELDS = ["unityProjectRoot", "workspaceDir", "reportsDir",
                      "agentMemoryIndexPath"]
CONFIG_PATH_LIST_FIELDS = ["devlogPaths", "workspacePaths"]

# directories (relative to scan root) never scanned
EXCLUDED_REL_PREFIXES = ("workspace/", "reports/", "docs/research/",
                         "tests/fixtures/")
EXCLUDED_DIR_NAMES = {".git", "node_modules", "Library", "Temp", "__pycache__"}


class Finding:
    def __init__(self, category: str, path: str, line: Optional[int], message: str):
        self.category = category
        self.path = path
        self.line = line
        self.message = message

    def as_dict(self) -> Dict[str, Any]:
        return {"category": self.category, "path": self.path,
                "line": self.line, "message": self.message}

    def render(self) -> str:
        loc = f"{self.path}:{self.line}" if self.line else self.path
        return f"[{self.category}] {loc}: {self.message}"


def _rel(root: Path, p: Path) -> str:
    try:
        return p.resolve().relative_to(root).as_posix()
    except ValueError:
        return p.as_posix()


def _excluded(root: Path, p: Path) -> bool:
    rel = _rel(root, p)
    if any(rel.startswith(pref) for pref in EXCLUDED_REL_PREFIXES):
        return True
    parts = rel.split("/")
    if any(part in EXCLUDED_DIR_NAMES for part in parts):
        return True
    return p.name == SELF_NAME


def _read_lines(p: Path) -> List[str]:
    try:
        return p.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []


# --------------------------------------------------------------------------
# Check a — banned hardcoded names
# --------------------------------------------------------------------------

def check_banned_names(root: Path, include_docs: bool = False) -> List[Finding]:
    """Scan framework-shipped files for banned names.

    Top-level docs (README.md etc.) are scanned only with include_docs=True —
    in an installed/embedded copy those files belong to the TARGET project and
    may legitimately contain its own name. Same reason `*.original.md` backups
    and the `projectName`/`worktreeRoot` values in project-config.json are
    exempt: they are project data, not framework hardcoding.
    """
    findings: List[Finding] = []
    targets: List[Path] = []
    claude = root / ".claude"
    if claude.is_dir():
        targets.extend(f for f in claude.rglob("*")
                       if f.is_file() and f.suffix in SCAN_SUFFIXES)
    if include_docs:
        for doc in ROOT_DOCS:
            p = root / doc
            if p.is_file():
                targets.append(p)

    for f in sorted(set(targets)):
        if _excluded(root, f):
            continue
        if f.name.endswith(".original.md"):
            continue  # pre-compression backup of project-local skill edits
        is_project_config = f.name == "project-config.json"
        for i, line in enumerate(_read_lines(f), 1):
            if WAIVER_MARK in line:
                continue
            if is_project_config and ('"projectName"' in line
                                      or '"worktreeRoot"' in line):
                continue  # project data, not framework hardcoding
            hits = [t for t in BANNED_TOKENS if t in line]
            # drop the bare token when a longer banned token covers the hit
            if "UnityBackpackAdventures" in hits and "BackpackAdventures" in hits:
                if line.count("BackpackAdventures") == line.count("UnityBackpackAdventures"):
                    hits.remove("BackpackAdventures")
            for t in hits:
                findings.append(Finding(
                    "banned-name", _rel(root, f), i,
                    f"hardcoded name {t!r} (waive with '{WAIVER_MARK} <reason>')"))
    return findings


# --------------------------------------------------------------------------
# Check b — single root resolver
# --------------------------------------------------------------------------

def check_root_resolver(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    scripts = root / ".claude" / "scripts"
    if not scripts.is_dir():
        return findings
    for f in sorted(scripts.glob("*.py")):
        if f.name in ("roots.py", SELF_NAME):
            continue
        for i, line in enumerate(_read_lines(f), 1):
            if WAIVER_MARK in line or SHIM_RE.search(line):
                continue
            for pat, label in RESOLVER_PATTERNS:
                if pat.search(line):
                    findings.append(Finding(
                        "root-resolver", _rel(root, f), i,
                        f"{label} outside roots.py — import roots instead"))
    return findings


# --------------------------------------------------------------------------
# Check c — broken internal references
# --------------------------------------------------------------------------

def check_internal_references(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    seen = set()
    for sub in ("commands", "agents"):
        d = root / ".claude" / sub
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            for i, line in enumerate(_read_lines(f), 1):
                if WAIVER_MARK in line:
                    continue
                for m in CLAUDE_PATH_RE.finditer(line):
                    ref = m.group(0).rstrip(".,:;!").rstrip("/")
                    if PLACEHOLDER_RE.search(ref):
                        continue  # placeholder / glob / template var
                    if ref in ALLOWED_MISSING_REFS:
                        continue  # user-created / generated file
                    key = (f, ref)
                    if key in seen:
                        continue
                    seen.add(key)
                    if not (root / ref).exists():
                        findings.append(Finding(
                            "broken-reference", _rel(root, f), i,
                            f"referenced path {ref!r} does not exist"))
    return findings


# --------------------------------------------------------------------------
# Check d — project-config.json sanity
# --------------------------------------------------------------------------

def _escapes_root(rel_path: str) -> bool:
    norm = posixpath.normpath(rel_path)
    return norm == ".." or norm.startswith("../")


def _is_direct_sibling(rel_path: str) -> bool:
    parts = posixpath.normpath(rel_path).split("/")
    return len(parts) >= 2 and parts[0] == ".." and ".." not in parts[1:]


def check_project_config(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    cfg_path = root / ".claude" / "project-config.json"
    if not cfg_path.is_file():
        return findings
    rel = _rel(root, cfg_path)
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(Finding("config", rel, None, f"invalid JSON: {exc}"))
        return findings
    if not isinstance(cfg, dict):
        findings.append(Finding("config", rel, None, "must be a JSON object"))
        return findings

    for key, value in cfg.items():
        if key.startswith("_") or key not in CONFIG_FIELD_TYPES:
            continue
        types, nullable = CONFIG_FIELD_TYPES[key]
        if value is None:
            if not nullable:
                findings.append(Finding("config", rel, None,
                                        f"field {key!r} must not be null"))
            continue
        # bool is a subclass of int; explicit check keeps types honest
        if not isinstance(value, types) or (isinstance(value, bool) and bool not in types):
            findings.append(Finding(
                "config", rel, None,
                f"field {key!r} has type {type(value).__name__}, "
                f"expected {'/'.join(t.__name__ for t in types)}"))

    ptype = cfg.get("projectType")
    if isinstance(ptype, str) and ptype not in ALLOWED_PROJECT_TYPES:
        findings.append(Finding(
            "config", rel, None,
            f"projectType {ptype!r} not in {ALLOWED_PROJECT_TYPES}"))

    def _check_escape(field: str, value: str) -> None:
        if not isinstance(value, str) or not value:
            return
        if posixpath.isabs(value) or re.match(r"^[A-Za-z]:[/\\]", value):
            findings.append(Finding(
                "config", rel, None,
                f"{field} must be a relative path, got absolute {value!r}"))
            return
        if _escapes_root(value):
            findings.append(Finding(
                "config", rel, None,
                f"{field} {value!r} escapes PROJECT_ROOT"))

    for field in CONFIG_PATH_FIELDS:
        val = cfg.get(field)
        if isinstance(val, str):
            _check_escape(field, val)
    for field in CONFIG_PATH_LIST_FIELDS:
        val = cfg.get(field)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    _check_escape(f"{field}[]", item)

    wt = cfg.get("worktreeRoot")
    if isinstance(wt, str) and wt:
        if posixpath.isabs(wt) or re.match(r"^[A-Za-z]:[/\\]", wt):
            findings.append(Finding(
                "config", rel, None,
                f"worktreeRoot must be relative, got absolute {wt!r}"))
        elif _escapes_root(wt) and not _is_direct_sibling(wt):
            findings.append(Finding(
                "config", rel, None,
                f"worktreeRoot {wt!r} escapes beyond a direct sibling "
                "('../<name>' is the only allowed escape)"))
    return findings


# --------------------------------------------------------------------------
# Check e — no caller-cwd dependence
# --------------------------------------------------------------------------

def check_cwd_dependence(root: Path) -> List[Finding]:
    findings: List[Finding] = []
    scripts = root / ".claude" / "scripts"
    if not scripts.is_dir():
        return findings
    for f in sorted(scripts.glob("*.py")):
        if f.name in ("roots.py", "setup.py", SELF_NAME):
            continue
        for i, line in enumerate(_read_lines(f), 1):
            if WAIVER_MARK in line:
                continue
            m = CWD_RE.search(line)
            if m:
                findings.append(Finding(
                    "cwd-dependence", _rel(root, f), i,
                    f"{m.group(0)} outside roots.py/setup.py — "
                    "resolve paths via roots instead"))
    return findings


# --------------------------------------------------------------------------
# Entry
# --------------------------------------------------------------------------

def run_all(root: Path, include_docs: bool = False) -> List[Finding]:
    findings: List[Finding] = []
    findings.extend(check_banned_names(root, include_docs=include_docs))
    findings.extend(check_root_resolver(root))
    findings.extend(check_internal_references(root))
    findings.extend(check_project_config(root))
    findings.extend(check_cwd_dependence(root))
    return findings


def _default_root() -> Path:
    import roots  # sibling module — sanctioned root resolver
    return roots.framework_root()


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="Framework portability validator")
    ap.add_argument("--root", default=None,
                    help="directory to validate (default: framework root)")
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--include-docs", action="store_true", dest="include_docs",
                    help="also scan top-level docs (framework repo CI; skip in "
                         "installed copies where README etc. belong to the target project)")
    args = ap.parse_args(argv)

    try:
        root = Path(args.root).resolve() if args.root else _default_root()
    except Exception as exc:
        print(f"[validate_portability] ERROR: cannot resolve root: {exc}",
              file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"[validate_portability] ERROR: {root} is not a directory",
              file=sys.stderr)
        return 2

    findings = run_all(root, include_docs=args.include_docs)
    status = "PASS" if not findings else "FAIL"

    if args.as_json:
        print(json.dumps({
            "status": status,
            "root": str(root),
            "finding_count": len(findings),
            "findings": [f.as_dict() for f in findings],
        }, indent=2))
    else:
        for f in findings:
            print(f.render())
        print(f"portability: {status} ({len(findings)} finding(s)) root={root}")

    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
