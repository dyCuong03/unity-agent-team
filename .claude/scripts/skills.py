#!/usr/bin/env python3
"""
Unified skill management CLI.

Commands:
  skills:list      — list all skills with name/domains/roles/status
  skills:validate  — run full validation suite (errors + warnings)
  skills:doctor    — run validation and auto-suggest fixes (no auto-apply)
  skills:unused    — report dead skills (FAILS on any orphan/unreachable)

Usage:
  python .claude/scripts/skills.py <command> [options]

Options:
  -v, --verbose    show all issues including INFO
  --json           output JSON (skills:list, skills:unused)
  --strict         treat warnings as errors (skills:validate)

Exit codes:
  0  pass
  1  fail (validation errors or dead skills found)
  2  fatal (registry missing / parse error)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure scripts dir is importable
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import skills_validator as _sv


def cmd_list(args: list[str]) -> int:
    """Print a table of all skills with routing metadata."""
    use_json = "--json" in args
    registry = _sv.load_registry()
    skills = registry.get("skills", [])

    if use_json:
        output = []
        for s in skills:
            output.append({
                "name": s.get("name"),
                "domains": s.get("domains", []),
                "roles": s.get("roles", []),
                "keywords": s.get("keywords", []),
                "priority": s.get("priority", 0),
                "mode": s.get("mode"),
                "internal-only": s.get("internal-only", False),
                "task-categories": s.get("task-categories", []),
            })
        print(json.dumps(output, indent=2))
        return 0

    # Table output
    print(f"\n{'NAME':<36} {'DOMAINS':<22} {'ROLES':<55} {'MODE/PRIO'}")
    print("-" * 130)
    for s in sorted(skills, key=lambda x: -x.get("priority", 0)):
        name = s.get("name", "")
        domains = ",".join(s.get("domains", []))
        roles = ",".join(s.get("roles", [])[:4])  # truncate display
        if len(s.get("roles", [])) > 4:
            roles += "…"
        mode = s.get("mode") or f"p{s.get('priority', 0)}"
        internal = " [internal]" if s.get("internal-only") else ""
        print(f"  {name:<34} {domains:<22} {roles:<55} {mode}{internal}")

    print(f"\n  Total: {len(skills)} skills")

    # Summary by status
    meta = [s for s in skills if s.get("mode") in ("meta", "role-brief")]
    routable = [
        s for s in skills
        if s.get("mode") not in ("meta", "role-brief")
        and s.get("roles")
        and (s.get("keywords") or s.get("priority", 0) >= 90)
    ]
    internal = [s for s in skills if s.get("internal-only")]
    print(f"  Routable: {len(routable)}  |  Meta: {len(meta)}  |  Internal-only: {len(internal)}")
    return 0


def cmd_validate(args: list[str]) -> int:
    """Run full validation suite."""
    verbose = "-v" in args or "--verbose" in args
    strict = "--strict" in args

    report = _sv.validate(verbose=verbose)
    _sv.print_report(report, verbose=verbose)

    errors = report.errors()
    warnings = report.warnings()
    failed_zeros = [
        k for k in ("orphans", "unreachable", "unresolved_duplicates")
        if report.counters.get(k, 0) > 0
    ]

    if errors or failed_zeros:
        return 1
    if strict and warnings:
        print("\nFAIL: --strict mode, warnings treated as errors.")
        return 1
    return 0


def cmd_doctor(args: list[str]) -> int:
    """Run validation and suggest concrete fixes for each issue (no auto-apply)."""
    report = _sv.validate(verbose=True)
    errors = report.errors()
    warnings = report.warnings()
    all_issues = errors + warnings

    if not all_issues:
        print("\n✓ No issues found. All skills are healthy.")
        return 0

    print(f"\n=== DOCTOR: {len(all_issues)} issues found ({len(errors)} errors, {len(warnings)} warnings) ===\n")

    FIXES = {
        "disk-vs-registry/orphan": (
            "Add an entry to .claude/skills/registry.json for this skill folder, "
            "or delete the SKILL.md if the skill is deprecated."
        ),
        "disk-vs-registry/missing-path": (
            "Remove this entry from registry.json or create the SKILL.md file at the listed path."
        ),
        "registry/duplicate-name": (
            "Rename one of the duplicate skills. "
            "Skill name must be globally unique — it is the routing key."
        ),
        "registry/missing-field": (
            "Add the missing field to the skill's entry in registry.json. "
            "See registry.json $comment for field documentation."
        ),
        "registry/no-roles": (
            "Add at least one role to the 'roles' array, "
            "or set mode:meta if this skill is for orchestration only."
        ),
        "registry/no-keywords": (
            "Add keywords that describe when this skill should be loaded, "
            "or raise priority to ≥90 if it's a must-have for its role."
        ),
        "registry/dots-guard-violation": (
            "Remove the listed NO_DOTS_ROLES from this skill's 'roles' array. "
            "DOTS-only skills must never be sent to unity-dev, tester, etc."
        ),
        "registry/internal-no-consumer": (
            "Add a 'consumer' field describing who uses this skill, e.g.: "
            '"consumer": "orchestrate.py — loaded for triage agent only"'
        ),
        "registry/corpus-no-source": (
            "Add 'source' field with the Unity documentation URL, e.g.: "
            '"source": "https://docs.unity3d.com/Packages/com.unity.entities@1.3"'
        ),
        "registry/corpus-no-version": (
            "Add 'version' field with the package version this skill was written against, e.g.: "
            '"version": "1.3.8"'
        ),
        "skill-md/no-frontmatter": (
            "Add YAML frontmatter at the top of SKILL.md:\n"
            "  ---\n  name: <folder-name>\n  description: <full description>\n"
            "  use-when: <when to load>\n  do-not-use-when: <when NOT to load>\n"
            "  platforms: [claude-code]\n  ---"
        ),
        "skill-md/name-mismatch": (
            "Set 'name:' in frontmatter to exactly match the folder name. "
            "The folder name is the routing key."
        ),
        "skill-md/description-too-short": (
            "Expand the description to be ≥50 chars. "
            "It should explain what the skill does and why an agent would load it."
        ),
        "skill-md/description-truncated": (
            "Remove the trailing '...' and complete the description fully."
        ),
        "skill-md/missing-field": (
            "Add the missing frontmatter field. Examples:\n"
            "  use-when: |\n    Load when task involves <domain>.\n"
            "  do-not-use-when: |\n    Do not load for <other domain> tasks.\n"
            "  platforms: [claude-code, codex]"
        ),
        "skill-md/possible-secret": (
            "Remove the credential from SKILL.md. "
            "Use placeholders like <YOUR_TOKEN> or environment variable references."
        ),
        "skill-md/personal-path": (
            "Replace the absolute path with a relative path from the repo root, "
            "e.g. .claude/skills/... instead of /home/username/.claude/skills/..."
        ),
        "skill-md/unsafe-exec": (
            "Remove the curl|sh / wget|sh pattern. "
            "If install instructions are needed, use descriptive steps, not piped execution."
        ),
        "dead-skill/no-role": (
            "Add role mappings so agents can receive this skill, "
            "or set mode:meta if this is orchestration-only."
        ),
        "dead-skill/no-trigger": (
            "Add keywords that describe when this skill loads, "
            "or raise priority to ≥90 if it should always load for its roles."
        ),
        "dead-skill/no-routing-rule": (
            "Add a 'routing-rule' field pointing to where this skill's routing is defined, e.g.: "
            '"routing-rule": ".claude/scripts/route_skills.py ROLE_PRIMARY"'
        ),
        "dead-skill/identical-routing": (
            "Differentiate this skill's keywords/roles from its duplicate, "
            "or merge both skills into one and remove the other."
        ),
        "collision/trigger": (
            "Add disambiguation to the routing-rule field of both skills. "
            "Define which keywords make each skill the clear winner."
        ),
        "routing-evidence/no-positive-example": (
            'Add: "positive-example": "Add shop UI popup with button layout"'
        ),
        "routing-evidence/no-negative-example": (
            'Add: "negative-example": "Optimize ECS job scheduling — pure DOTS task"'
        ),
        "routing-evidence/no-routing-rule": (
            'Add: "routing-rule": ".claude/scripts/route_skills.py ROLE_PRIMARY[architect]"'
        ),
        "routing-evidence/no-task-categories": (
            'Add: "task-categories": ["ui", "gameplay", "implementation"]'
        ),
    }

    grouped: dict[str, list] = {}
    for issue in all_issues:
        grouped.setdefault(issue.check, []).append(issue)

    for check, issues in sorted(grouped.items()):
        fix = FIXES.get(check, "Consult skills_validator.py check logic for resolution.")
        print(f"── {check}  ({len(issues)} occurrence{'s' if len(issues)>1 else ''})")
        for issue in issues:
            print(f"   {issue.level:<7} [{issue.skill}] {issue.message}")
        print(f"   FIX: {fix}\n")

    # Summary
    print("=" * 60)
    failed_zeros = [
        k for k in ("orphans", "unreachable", "unresolved_duplicates")
        if report.counters.get(k, 0) > 0
    ]
    if errors or failed_zeros:
        print(f"Doctor complete. {len(errors)} errors must be fixed before skills:validate passes.")
        return 1
    print(f"Doctor complete. No errors. {len(warnings)} warnings are advisory.")
    return 0


def cmd_unused(args: list[str]) -> int:
    """Detect dead/unused skills. FAILS if any orphan or unreachable skill found."""
    use_json = "--json" in args
    report = _sv.validate()

    dead: list[dict] = []
    for issue in report.issues:
        if issue.check.startswith("dead-skill/") or issue.check.startswith("disk-vs-registry/"):
            dead.append({
                "level": issue.level,
                "check": issue.check,
                "skill": issue.skill,
                "message": issue.message,
            })

    counters = {
        "orphans": report.counters.get("orphans", 0),
        "unreachable": report.counters.get("unreachable", 0),
        "duplicate_candidates": report.counters.get("duplicate_candidates", 0),
    }

    if use_json:
        print(json.dumps({"dead_skills": dead, "counters": counters}, indent=2))
    else:
        if dead:
            print(f"\n=== DEAD / UNUSED SKILLS ({len(dead)}) ===\n")
            for item in dead:
                print(f"  {item['level']:<7}  {item['check']:<40}  [{item['skill']}]")
                print(f"           {item['message']}")
        else:
            print("\n✓ No dead or unused skills found.")

        print(f"\n  orphans          : {counters['orphans']}")
        print(f"  unreachable      : {counters['unreachable']}")
        print(f"  duplicate-cands  : {counters['duplicate_candidates']}")

    # FAIL if any must-be-zero is non-zero
    must_zero = counters["orphans"] + counters["unreachable"]
    error_count = sum(1 for d in dead if d["level"] == "ERROR")
    if must_zero > 0 or error_count > 0:
        if not use_json:
            print(f"\nFAIL: {error_count} dead-skill errors. orphans={counters['orphans']}, "
                  f"unreachable={counters['unreachable']}.")
        return 1

    if not use_json:
        print("\nPASS: No orphans or unreachable skills.")
    return 0


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

COMMANDS = {
    "skills:list": cmd_list,
    "skills:validate": cmd_validate,
    "skills:doctor": cmd_doctor,
    "skills:unused": cmd_unused,
    "list": cmd_list,
    "validate": cmd_validate,
    "doctor": cmd_doctor,
    "unused": cmd_unused,
}


def main() -> None:
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        sys.exit(0)

    cmd_name = argv[0]
    cmd_args = argv[1:]

    fn = COMMANDS.get(cmd_name)
    if fn is None:
        print(f"Unknown command: {cmd_name}")
        print(f"Available: {', '.join(sorted(COMMANDS))}")
        sys.exit(2)

    sys.exit(fn(cmd_args))


if __name__ == "__main__":
    main()
