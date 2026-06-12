#!/usr/bin/env python3
"""Migrate an existing old-style (hardcoded) install to the portable layout.

Usage:
    python3 .claude/scripts/migrate.py --check          # report only, change nothing
    python3 .claude/scripts/migrate.py                  # detect + apply (runs setup.py --yes)
    python3 .claude/scripts/migrate.py --allow-dirty    # apply even with uncommitted .claude/ changes
    python3 .claude/scripts/migrate.py --project-root <path>

What "old-style" means (any of these signals):
- no .claude/project-config.json (pre-portable install)
- env UNITY_TEAM_PROJECT_ROOT set (legacy variable; AGENT_TEAM_PROJECT_ROOT  # portability-allow: documents resolver contract
  is the current name — the legacy alias keeps working, but should be renamed)
- absolute filesystem paths baked into .claude/**/*.md or .mcp.json
- an old un-namespaced worktrees dir at <parent-of-repo>/worktrees
  (the portable layout uses <parent>/<projectName>-worktrees)

What apply does:
- runs `setup.py --yes` (idempotent; NEVER overwrites existing user config
  values — same semantics as running setup.py by hand)
- writes a report of everything it found/changed to workspace/migration-report.md
- does NOT edit your .md files or .mcp.json for you — absolute paths are
  reported with file:line so you can fix them deliberately
- does NOT move or delete the old worktrees dir — it reports it

Safety:
- refuses to apply if `git status` shows uncommitted changes under .claude/
  (override with --allow-dirty)
- nothing destructive anywhere; revert with: git checkout -- .claude/
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import roots  # noqa: E402

ABS_PATH_RE = re.compile(
    r"(/mnt/[a-z]/[^\s\"'`)\]]+"                          # WSL drive mounts
    # Windows drive paths: not part of a longer word (rejects "https://",
    # "log:\n") and not a URL scheme ("x://")
    r"|(?<![A-Za-z0-9])[A-Za-z]:(?!//)[/\\][^\s\"'`)\]]+"
    r"|(?<![\w./-])/home/[^\s\"'`)\]]+"                   # Linux home dirs
    r"|(?<![\w./-])/Users/[^\s\"'`)\]]+)"                 # macOS home dirs
)

SCAN_SKIP_DIRS = {"skill-cache", "__pycache__", "node_modules"}


class Finding:
    def __init__(self, kind: str, detail: str, fix: str) -> None:
        self.kind = kind
        self.detail = detail
        self.fix = fix

    def __str__(self) -> str:
        return f"[{self.kind}] {self.detail}\n    fix: {self.fix}"


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------

def detect_missing_config(claude_dir: Path) -> Optional[Finding]:
    cfg = claude_dir / roots.CONFIG_FILENAME
    if not cfg.is_file():
        return Finding(
            "missing-config",
            f"{cfg} does not exist (pre-portable install)",
            "apply mode runs setup.py --yes to generate it with detected defaults",
        )
    return None


def detect_legacy_env() -> Optional[Finding]:
    val = os.environ.get(roots.ENV_PROJECT_ROOT_LEGACY)
    if val:
        return Finding(
            "legacy-env",
            f"{roots.ENV_PROJECT_ROOT_LEGACY}={val!r} is set (legacy name)",
            f"rename to {roots.ENV_PROJECT_ROOT} in your shell profile "
            "(the legacy alias still works, but is deprecated)",
        )
    return None


def detect_absolute_paths(claude_dir: Path, proj_root: Path) -> List[Finding]:
    findings: List[Finding] = []
    targets: List[Path] = []
    for p in sorted(claude_dir.rglob("*.md")):
        if any(part in SCAN_SKIP_DIRS for part in p.parts):
            continue
        targets.append(p)
    mcp = proj_root / ".mcp.json"
    if mcp.is_file():
        targets.append(mcp)
    for path in targets:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            m = ABS_PATH_RE.search(line)
            if m:
                findings.append(Finding(
                    "absolute-path",
                    f"{path.relative_to(proj_root)}:{lineno}: {m.group(0)[:80]}",
                    "replace with a path relative to the project root, or a "
                    "roots.py-resolved placeholder; not auto-edited",
                ))
    return findings


def detect_old_worktrees(proj_root: Path) -> Optional[Finding]:
    old = proj_root.parent / "worktrees"
    if old.is_dir():
        try:
            new = roots.worktree_root(proj_root)
        except Exception:
            new = proj_root.parent / f"{proj_root.name}-worktrees"
        return Finding(
            "old-worktrees-dir",
            f"un-namespaced worktrees dir found: {old}",
            f"portable layout uses {new}; remove the old dir after confirming "
            "no live worktrees (`git worktree list`), or set worktreeRoot in "
            "project-config.json to keep the old location",
        )
    return None


def git_dirty_claude(proj_root: Path) -> List[str]:
    """Lines of `git status --porcelain` that touch .claude/."""
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain", "--", ".claude"],
            cwd=str(proj_root), capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0:
        return []  # not a git repo — nothing to protect
    return [l for l in r.stdout.splitlines() if l.strip()]


# --------------------------------------------------------------------------
# Apply
# --------------------------------------------------------------------------

def run_setup(proj_root: Path) -> Tuple[int, str]:
    cmd = [sys.executable, str(SCRIPTS / "setup.py"), "--yes",
           "--project-root", str(proj_root)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout + r.stderr).strip()


def write_report(proj_root: Path, findings: List[Finding],
                 setup_output: Optional[str], applied: bool) -> Path:
    try:
        ws = roots.workspace_dir(proj_root)
    except Exception:
        ws = proj_root / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    report = ws / "migration-report.md"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Migration Report",
        "",
        f"- Date: {now}",
        f"- Project root: {proj_root}",
        f"- Mode: {'apply' if applied else 'check (no changes made)'}",
        "",
        "## Findings",
        "",
    ]
    if findings:
        for f in findings:
            lines.append(f"- **{f.kind}** — {f.detail}")
            lines.append(f"  - fix: {f.fix}")
    else:
        lines.append("- none — install already matches the portable layout")
    if setup_output is not None:
        lines += ["", "## setup.py output", "", "```", setup_output, "```"]
    lines += [
        "",
        "## Revert",
        "",
        "Migration only adds files (config, knowledge seeds, directories).",
        "To revert framework files: `git checkout -- .claude/`",
        "To remove generated config: delete `.claude/project-config.json`.",
        "",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")
    return report


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Migrate an old-style install to the portable layout")
    ap.add_argument("--check", action="store_true",
                    help="report only; change nothing; exit 1 if migration needed")
    ap.add_argument("--allow-dirty", action="store_true",
                    help="apply even if .claude/ has uncommitted git changes")
    ap.add_argument("--project-root", default=None)
    args = ap.parse_args()

    try:
        proj_root = roots.project_root(args.project_root)
    except roots.RootResolutionError:
        proj_root = Path.cwd().resolve()  # portability-allow: last-resort fallback, mirrors setup.py
        print(f"[migrate] note: root resolver had no signal; using cwd {proj_root}")

    claude_dir = proj_root / ".claude"
    if not claude_dir.is_dir():
        print(f"[migrate] ERROR: {claude_dir} does not exist — nothing to migrate. "
              "Install the framework first (copy .claude/ in, then run setup.py).",
              file=sys.stderr)
        return 2

    findings: List[Finding] = []
    for f in (detect_missing_config(claude_dir),
              detect_legacy_env(),
              detect_old_worktrees(proj_root)):
        if f:
            findings.append(f)
    findings.extend(detect_absolute_paths(claude_dir, proj_root))

    print(f"[migrate] project root: {proj_root}")
    if not findings:
        print("[migrate] no old-style configuration detected — already portable.")
        if not args.check:
            write_report(proj_root, findings, None, applied=False)
        return 0

    MAX_PRINT = 40
    print(f"[migrate] {len(findings)} finding(s):")
    for f in findings[:MAX_PRINT]:
        print(f"  {f}")
    if len(findings) > MAX_PRINT:
        print(f"  … {len(findings) - MAX_PRINT} more "
              "(full list is written to workspace/migration-report.md on apply)")

    if args.check:
        print("[migrate] check mode — nothing changed. Run without --check to apply.")
        return 1

    # git-safety gate
    dirty = git_dirty_claude(proj_root)
    if dirty and not args.allow_dirty:
        print("[migrate] BLOCK: uncommitted changes in .claude/ — commit or stash "
              "them first, or re-run with --allow-dirty.", file=sys.stderr)
        for l in dirty[:20]:
            print(f"    {l}", file=sys.stderr)
        print("  revert instructions: git checkout -- .claude/", file=sys.stderr)
        return 3

    # apply: setup.py --yes (idempotent; never overwrites user config values)
    code, out = run_setup(proj_root)
    print(out)
    if code != 0:
        print(f"[migrate] setup.py exited {code} — migration incomplete. "
              "Fix the errors above and re-run.", file=sys.stderr)
        write_report(proj_root, findings, out, applied=False)
        return code

    report = write_report(proj_root, findings, out, applied=True)
    print(f"[migrate] done. Report: {report}")
    print("[migrate] revert (if needed): git checkout -- .claude/ "
          "and delete .claude/project-config.json")
    remaining = [f for f in findings if f.kind in ("absolute-path", "legacy-env",
                                                   "old-worktrees-dir")]
    if remaining:
        print(f"[migrate] {len(remaining)} finding(s) need manual follow-up — "
              "see the report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
