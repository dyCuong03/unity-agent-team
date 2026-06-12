#!/usr/bin/env python3
"""
validate_agentmemory_rule.py — verify that the agentmemory "recall layer, not source of
truth" rule is correctly stated in:
  - .claude/skills/agentmemory-codebase-recall/SKILL.md
  - .claude/CLAUDE.md
  - .claude/commands/team.md

Exit 0: all checks pass
Exit 1: one or more issues found

Usage:
    python .claude/scripts/validate_agentmemory_rule.py
    python .claude/scripts/validate_agentmemory_rule.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import roots  # noqa: E402

ROOT = roots.framework_root()

SKILL_MD   = ROOT / ".claude" / "skills" / "agentmemory-codebase-recall" / "SKILL.md"
CLAUDE_MD  = ROOT / ".claude" / "CLAUDE.md"
TEAM_MD    = ROOT / ".claude" / "commands" / "team.md"


def _read(path: Path) -> str | None:
    """Return file text or None if missing."""
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _contains(text: str, pattern: str, flags: int = re.IGNORECASE) -> bool:
    return bool(re.search(pattern, text, flags))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate agentmemory recall-layer rule in SKILL.md, CLAUDE.md, team.md"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    issues: list[str] = []
    summary: dict[str, int] = {
        "skill_md_checks": 0,
        "claude_md_checks": 0,
        "team_md_checks": 0,
        "passed": 0,
        "failed": 0,
    }

    def ok(section: str) -> None:
        summary[section] += 1
        summary["passed"] += 1

    def fail(section: str, msg: str) -> None:
        summary[section] += 1
        summary["failed"] += 1
        issues.append(msg)

    # ------------------------------------------------------------------ #
    # SKILL.md checks                                                     #
    # ------------------------------------------------------------------ #

    skill_text = _read(SKILL_MD)
    if skill_text is None:
        fail("skill_md_checks", f"SKILL.md missing: {SKILL_MD}")
    else:
        ok("skill_md_checks")

        # "recall layer" + "NOT the source of truth"
        if _contains(skill_text, r"recall layer") and _contains(skill_text, r"NOT the source of truth"):
            ok("skill_md_checks")
        else:
            fail("skill_md_checks",
                 "SKILL.md: missing 'recall layer' or 'NOT the source of truth' statement")

        # "Current repo files always win" or "files always win"
        if _contains(skill_text, r"files always win"):
            ok("skill_md_checks")
        else:
            fail("skill_md_checks",
                 "SKILL.md: missing 'files always win' (or 'Current repo files always win') statement")

        # "Never edit from memory alone"
        if _contains(skill_text, r"Never edit from memory alone"):
            ok("skill_md_checks")
        else:
            fail("skill_md_checks",
                 "SKILL.md: missing 'Never edit from memory alone' in Core Contract table")

        # "[MEMORY UNAVAILABLE]" fallback text
        if _contains(skill_text, r"\[MEMORY UNAVAILABLE\]"):
            ok("skill_md_checks")
        else:
            fail("skill_md_checks",
                 "SKILL.md: missing '[MEMORY UNAVAILABLE]' fallback text")

    # ------------------------------------------------------------------ #
    # CLAUDE.md checks                                                    #
    # ------------------------------------------------------------------ #

    claude_text = _read(CLAUDE_MD)
    if claude_text is None:
        fail("claude_md_checks", f"CLAUDE.md missing: {CLAUDE_MD}")
    else:
        ok("claude_md_checks")

        # "Memory is not the source of truth" / "not.*source of truth"
        if _contains(claude_text, r"memory.*not.*source of truth|not.*source of truth.*memory|Memory is \*\*not\*\* the source"):
            ok("claude_md_checks")
        else:
            fail("claude_md_checks",
                 "CLAUDE.md: missing 'Memory is not the source of truth' statement")

    # ------------------------------------------------------------------ #
    # team.md checks                                                      #
    # ------------------------------------------------------------------ #

    team_text = _read(TEAM_MD)
    if team_text is None:
        fail("team_md_checks", f"team.md missing: {TEAM_MD}")
    else:
        ok("team_md_checks")

        # STEP 0 "Required skill loading" block present
        if _contains(team_text, r"STEP 0[^:]*:?\s*[—\-]?\s*Required skill loading", re.IGNORECASE):
            ok("team_md_checks")
        else:
            fail("team_md_checks",
                 "team.md: missing 'STEP 0 — Required skill loading' block in agent spawn prompts")

        # "[BLOCKED: MISSING SKILL]" present
        if _contains(team_text, r"\[BLOCKED: MISSING SKILL\]"):
            ok("team_md_checks")
        else:
            fail("team_md_checks",
                 "team.md: missing '[BLOCKED: MISSING SKILL]' in STEP 0 block")

        # "[MEMORY UNAVAILABLE]" present
        if _contains(team_text, r"\[MEMORY UNAVAILABLE\]"):
            ok("team_md_checks")
        else:
            fail("team_md_checks",
                 "team.md: missing '[MEMORY UNAVAILABLE]' fallback instruction")

        # "do not edit based only on memory" / "not edit.*memory" prohibition
        if _contains(team_text, r"do not edit based only on memory|not edit.*memory.*alone|Do not edit based only on memory"):
            ok("team_md_checks")
        else:
            fail("team_md_checks",
                 "team.md: missing 'Do not edit based only on memory' prohibition")

        # "query agentmemory when available" / "agentmemory.*available" rule
        if _contains(team_text, r"query agentmemory when available|agentmemory when available"):
            ok("team_md_checks")
        else:
            fail("team_md_checks",
                 "team.md: missing 'query agentmemory when available' usage rule")

    _report(args.json, summary, issues)
    return 1 if issues else 0


def _report(use_json: bool, summary: dict, issues: list[str]) -> None:
    if use_json:
        print(json.dumps({"summary": summary, "issues": issues}, indent=2))
    else:
        total = summary["passed"] + summary["failed"]
        print(f"validate_agentmemory_rule: {summary['passed']}/{total} checks passed")
        for issue in issues:
            print(f"  FAIL: {issue}")
        if not issues:
            print("  All checks passed.")


if __name__ == "__main__":
    sys.exit(main())
