#!/usr/bin/env python3
"""
validate_skill_registry.py — validate .claude/skills/registry.json structure
and behavioral routing assertions via route_skills.route().

Exit 0: all checks pass
Exit 1: one or more issues found

Usage:
    python .claude/scripts/validate_skill_registry.py
    python .claude/scripts/validate_skill_registry.py --json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import roots  # noqa: E402

ROOT = roots.framework_root()
REGISTRY_PATH = roots.claude_root() / "skills" / "registry.json"
ROUTE_SKILLS_PATH = roots.claude_root() / "scripts" / "route_skills.py"

DOTS_ONLY_SKILLS = {
    "unity-dots-best-practices",
    "unity-dots",
    "ecs-job-patterns",
    "burst-safety",
    "memory-safety",
}

# Roles that must NEVER receive DOTS skills.
NO_DOTS_ROLES = {"tester", "verifier", "qa-tester", "data-tool", "unity-dev"}

# Roles that must always receive agentmemory-codebase-recall (code-reading roles).
CODE_READING_ROLES = {
    "architect",
    "unity-dots-dev",
    "unity-dev",
    "bug-investigation",
    "data-tool",
    "tester",
    "verifier",
    "qa-tester",
    "refactor-agent",
    "system-mapper",
}

# All roles defined in the registry — no skill should target ALL of them.
ALL_REGISTRY_ROLES = {
    "architect",
    "unity-dots-dev",
    "unity-dev",
    "tester",
    "verifier",
    "qa-tester",
    "bug-investigation",
    "refactor-agent",
    "data-tool",
    "system-mapper",
    "triage",
}


def _load_route_module():
    """Load route_skills.py via importlib. Returns module or None on failure."""
    if not ROUTE_SKILLS_PATH.exists():
        return None, f"route_skills.py not found: {ROUTE_SKILLS_PATH}"
    spec = importlib.util.spec_from_file_location("route_skills", ROUTE_SKILLS_PATH)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        return mod, None
    except Exception as exc:
        return None, f"route_skills.py import error: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate skill registry and routing behaviour")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    issues: list[str] = []
    summary: dict[str, int] = {
        "structural_checks": 0,
        "routing_checks": 0,
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
    # STRUCTURAL CHECKS                                                    #
    # ------------------------------------------------------------------ #

    # 1. Registry file exists
    if not REGISTRY_PATH.exists():
        fail("structural_checks", f"Registry missing: {REGISTRY_PATH}")
        _report(args.json, summary, issues)
        return 1
    ok("structural_checks")

    # 2. Parse registry
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        fail("structural_checks", f"Registry JSON parse error: {exc}")
        _report(args.json, summary, issues)
        return 1

    skills_list: list[dict] = registry.get("skills", [])
    max_total: int = registry.get("max_total_skills", 6)
    by_name: dict[str, dict] = {e["name"]: e for e in skills_list}

    # 3. All skill paths exist on disk
    for entry in skills_list:
        skill_path = ROOT / entry.get("path", "")
        if not skill_path.exists():
            fail("structural_checks",
                 f"Skill path missing: '{entry['name']}' → {entry.get('path')}")
        else:
            ok("structural_checks")

    # 4. No non-meta skill entry targets ALL registry roles
    non_meta = [
        e for e in skills_list
        if e.get("mode") != "meta" and e.get("load_by_default", True) is not False
    ]
    for entry in non_meta:
        entry_roles = set(entry.get("roles", []))
        if entry_roles >= ALL_REGISTRY_ROLES:
            fail("structural_checks",
                 f"Skill '{entry['name']}' lists ALL registry roles — "
                 "no single skill should be universally loaded for every role")
        else:
            ok("structural_checks")

    # 5. agentmemory-codebase-recall entry exists
    am_entry = by_name.get("agentmemory-codebase-recall")
    if am_entry is None:
        fail("structural_checks", "agentmemory-codebase-recall entry missing from registry")
    else:
        ok("structural_checks")
        # 5a. It includes all code-reading roles
        am_roles = set(am_entry.get("roles", []))
        missing = CODE_READING_ROLES - am_roles
        if missing:
            fail("structural_checks",
                 f"agentmemory-codebase-recall missing code-reading roles: {sorted(missing)}")
        else:
            ok("structural_checks")

    # 6. DOTS-only skills must NOT include any no-DOTS role
    for skill_name in sorted(DOTS_ONLY_SKILLS):
        entry = by_name.get(skill_name)
        if entry is None:
            continue  # missing path already flagged above
        entry_roles = set(entry.get("roles", []))
        bad = entry_roles & NO_DOTS_ROLES
        if bad:
            fail("structural_checks",
                 f"DOTS skill '{skill_name}' has no-DOTS roles in registry: {sorted(bad)}")
        else:
            ok("structural_checks")

    # 7. unity-classic must include unity-dev and must NOT include unity-dots-dev
    uc = by_name.get("unity-classic")
    if uc is not None:
        uc_roles = set(uc.get("roles", []))
        if "unity-dev" not in uc_roles:
            fail("structural_checks", "unity-classic missing unity-dev in roles")
        else:
            ok("structural_checks")
        if "unity-dots-dev" in uc_roles:
            fail("structural_checks",
                 "unity-classic has unity-dots-dev in roles — DOTS lane must not load Unity Classic")
        else:
            ok("structural_checks")

    # ------------------------------------------------------------------ #
    # ROUTING BEHAVIOURAL CHECKS                                          #
    # ------------------------------------------------------------------ #

    mod, load_err = _load_route_module()
    if mod is None:
        fail("routing_checks",
             f"route_skills.py not loadable — routing checks skipped: {load_err}")
        _report(args.json, summary, issues)
        return 1

    route = mod.route  # function is `route`, NOT `route_skills`

    def assert_present(label: str, result: list[str], skills: list[str]) -> None:
        for skill in skills:
            if skill in result:
                ok("routing_checks")
            else:
                fail("routing_checks",
                     f"[routing] {label}: expected '{skill}' in result {result}")

    def assert_absent(label: str, result: list[str], skills: list[str]) -> None:
        for skill in skills:
            if skill not in result:
                ok("routing_checks")
            else:
                fail("routing_checks",
                     f"[routing] {label}: DOTS skill '{skill}' must NOT appear in result {result}")

    def assert_cap(label: str, result: list[str]) -> None:
        if len(result) <= max_total:
            ok("routing_checks")
        else:
            fail("routing_checks",
                 f"[routing] {label}: result length {len(result)} exceeds cap {max_total}")

    dots_list = sorted(DOTS_ONLY_SKILLS)

    # Unity task → unity-dev must get unity-classic, no DOTS skills
    r = route(agent="unity-dev", domain="Unity", intent="feature", task_text="popup not showing")
    assert_present("unity-dev/Unity/feature", r, ["unity-classic", "agentmemory-codebase-recall"])
    assert_absent("unity-dev/Unity/feature", r, dots_list)
    assert_cap("unity-dev/Unity/feature", r)

    r = route(agent="unity-dev", domain="Unity", intent="bug", task_text="button not responding")
    assert_present("unity-dev/Unity/bug", r, ["unity-classic", "agentmemory-codebase-recall"])
    assert_absent("unity-dev/Unity/bug", r, dots_list)
    assert_cap("unity-dev/Unity/bug", r)

    # DOTS task → unity-dots-dev must get DOTS skills
    r = route(agent="unity-dots-dev", domain="DOTS", intent="feature", task_text="ISystem entity movement")
    assert_present("unity-dots-dev/DOTS/feature", r,
                   ["unity-dots-best-practices", "agentmemory-codebase-recall"])
    assert_cap("unity-dots-dev/DOTS/feature", r)
    # At least one DOTS skill present
    if any(s in r for s in DOTS_ONLY_SKILLS):
        ok("routing_checks")
    else:
        fail("routing_checks",
             f"[routing] unity-dots-dev/DOTS/feature: no DOTS skill in result {r}")

    # No-DOTS roles — none should receive DOTS skills
    for no_dots_role in sorted(NO_DOTS_ROLES):
        r = route(agent=no_dots_role, domain="Any", intent="feature", task_text="implement feature")
        assert_absent(f"{no_dots_role}/Any/feature", r, dots_list)
        assert_cap(f"{no_dots_role}/Any/feature", r)

    # unity-dev with DOTS domain/task — DOTS guard must still hold
    r = route(agent="unity-dev", domain="DOTS", intent="feature", task_text="ISystem entity ECS")
    assert_absent("unity-dev/DOTS/feature (DOTS guard)", r, dots_list)

    # All code-reading roles must receive agentmemory-codebase-recall
    for role in sorted(CODE_READING_ROLES):
        r = route(agent=role, domain="Any", intent="feature", task_text="investigate code")
        assert_present(f"{role}/agentmemory-recall", r, ["agentmemory-codebase-recall"])

    _report(args.json, summary, issues)
    return 1 if issues else 0


def _report(use_json: bool, summary: dict, issues: list[str]) -> None:
    if use_json:
        print(json.dumps({"summary": summary, "issues": issues}, indent=2))
    else:
        total = summary["passed"] + summary["failed"]
        print(f"validate_skill_registry: {summary['passed']}/{total} checks passed")
        for issue in issues:
            print(f"  FAIL: {issue}")
        if not issues:
            print("  All checks passed.")


if __name__ == "__main__":
    sys.exit(main())
