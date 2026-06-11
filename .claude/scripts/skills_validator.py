#!/usr/bin/env python3
"""
Comprehensive skill registry + SKILL.md validator.
Checks structural integrity, description quality, routing coverage,
dead-skill detection, and trigger-collision detection.

Exit codes:
  0  all checks pass
  1  validation errors found (see output)
  2  fatal error (registry missing, JSON parse failure, etc.)
"""

from __future__ import annotations

import json
import os
import re
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
REGISTRY_PATH = SKILLS_DIR / "registry.json"
SCRIPTS_DIR = REPO_ROOT / ".claude" / "scripts"

# Minimum description length (chars)
MIN_DESC_LEN = 50
# Must not end with these (indicates truncation)
TRUNCATION_SUFFIXES = ("...", "…", "etc.")

# Platforms that agents may run on
VALID_PLATFORMS = {"claude-code", "codex", "copilot", "cursor", "windsurf"}

# Required frontmatter fields for non-meta skills
REQUIRED_FM_FIELDS = ["name", "description", "use-when", "do-not-use-when", "platforms"]

# Patterns that indicate secrets/tokens in SKILL.md
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret[_-]?key|password|token|auth[_-]?token)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9\-_]+"),
    re.compile(r"(?=[A-Za-z0-9+/]*[0-9])[A-Za-z0-9+/]{40,}={0,2}"),  # base64-like (must contain digit; excludes class names)
]

# Patterns that indicate personal machine paths
PERSONAL_PATH_PATTERNS = [
    re.compile(r"/home/[a-zA-Z0-9_]+/"),
    re.compile(r"C:\\Users\\[a-zA-Z0-9_]+\\"),
    re.compile(r"/Users/[a-zA-Z0-9_]+/"),
]

# Patterns that indicate unsafe auto-execution
UNSAFE_EXEC_PATTERNS = [
    re.compile(r"curl\s+.*\|\s*(sh|bash)"),
    re.compile(r"wget\s+.*\|\s*(sh|bash)"),
    re.compile(r"eval\s+\$\(curl"),
    re.compile(r"eval\s+\$\(wget"),
]

# Roles that must NEVER receive DOTS-only skills
NO_DOTS_ROLES = {"tester", "verifier", "qa-tester", "data-tool", "unity-dev"}

# Skills that are DOTS-only (must not appear in NO_DOTS_ROLES)
DOTS_ONLY_SKILLS = {"unity-dots-best-practices", "unity-dots", "ecs-job-patterns", "burst-safety", "memory-safety"}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    level: str          # "ERROR" | "WARNING" | "INFO"
    check: str          # check category
    skill: str          # skill name or ""
    message: str

    def __str__(self) -> str:
        loc = f"[{self.skill}] " if self.skill else ""
        return f"  {self.level:7s}  {self.check:35s}  {loc}{self.message}"


@dataclass
class CollisionReport:
    skill_a: str
    skill_b: str
    shared_keywords: list[str]
    shared_roles: list[str]
    winner: str
    resolution: str


@dataclass
class ValidationReport:
    issues: list[Issue] = field(default_factory=list)
    collisions: list[CollisionReport] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)

    def add(self, level: str, check: str, skill: str, message: str) -> None:
        self.issues.append(Issue(level, check, skill, message))

    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "ERROR"]

    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "WARNING"]


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------

def load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        print(f"FATAL: registry not found at {REGISTRY_PATH}", file=sys.stderr)
        sys.exit(2)
    try:
        with open(REGISTRY_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"FATAL: registry JSON parse error: {exc}", file=sys.stderr)
        sys.exit(2)


# ---------------------------------------------------------------------------
# SKILL.md frontmatter parsing (handles BOM)
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"^﻿?---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(skill_path: Path) -> dict[str, Any] | None:
    """Return parsed YAML frontmatter dict, or None if not found."""
    try:
        text = skill_path.read_text(encoding="utf-8-sig")
    except OSError:
        return None

    m = FRONTMATTER_RE.match(text)
    if not m:
        return None

    # Minimal YAML parser for flat key: value (no deps required)
    result: dict[str, Any] = {}
    block = m.group(1)
    current_key: str | None = None
    current_multiline: list[str] = []

    for line in block.splitlines():
        # Detect continuation of block scalar (indented)
        if current_multiline is not None and line.startswith("  "):
            current_multiline.append(line.strip())
            continue
        # Flush multiline
        if current_multiline and current_key:
            result[current_key] = "\n".join(current_multiline).strip()
            current_multiline = []
            current_key = None

        kv_match = re.match(r"^(\S[^:]*?)\s*:\s*(.*)", line)
        if kv_match:
            k = kv_match.group(1).strip()
            v = kv_match.group(2).strip()
            if v in ("|", ">", ">-", "|-", ">+", "|+"):
                current_key = k
                current_multiline = []
            elif v.startswith("[") and v.endswith("]"):
                # Inline list
                items = [i.strip().strip('"\'') for i in v[1:-1].split(",") if i.strip()]
                result[k] = items
            elif not v:
                result[k] = None
            else:
                # Handle YAML boolean
                if v.lower() == "true":
                    result[k] = True
                elif v.lower() == "false":
                    result[k] = False
                else:
                    result[k] = v

    # Flush trailing multiline
    if current_multiline and current_key:
        result[current_key] = "\n".join(current_multiline).strip()

    return result


# ---------------------------------------------------------------------------
# Check: disk vs registry consistency
# ---------------------------------------------------------------------------

def check_disk_vs_registry(report: ValidationReport, registry: dict) -> None:
    skills = registry.get("skills", [])
    registry_names = {s["name"] for s in skills}

    # Collect all top-level skill folders (each has a SKILL.md)
    disk_folders: set[str] = set()
    for item in SKILLS_DIR.iterdir():
        if item.is_dir() and (item / "SKILL.md").exists():
            disk_folders.add(item.name)

    for folder in sorted(disk_folders - registry_names):
        report.add("ERROR", "disk-vs-registry/orphan",
                   folder, "Folder has SKILL.md but is MISSING from registry. Add it or remove it.")

    for name in sorted(registry_names - disk_folders):
        entry = next((s for s in skills if s["name"] == name), {})
        path = Path(entry.get("path", ""))
        if not path.exists():
            report.add("ERROR", "disk-vs-registry/missing-path",
                       name, f"Registry path '{path}' does not exist on disk.")


# ---------------------------------------------------------------------------
# Check: registry entry structural completeness
# ---------------------------------------------------------------------------

REQUIRED_REGISTRY_FIELDS = ["name", "path", "domains", "roles", "intents", "keywords", "priority"]
RECOMMENDED_REGISTRY_FIELDS_NONMETA = ["task-categories", "positive-example", "negative-example", "routing-rule"]


def check_registry_entries(report: ValidationReport, registry: dict) -> None:
    skills = registry.get("skills", [])
    names_seen: dict[str, int] = {}

    for entry in skills:
        name = entry.get("name", "<unnamed>")
        is_meta = entry.get("mode") in ("meta",)

        # Duplicate names
        if name in names_seen:
            report.add("ERROR", "registry/duplicate-name", name,
                       f"Duplicate skill name. Also appears at index {names_seen[name]}.")
        names_seen[name] = skills.index(entry)

        # Required fields
        for f in REQUIRED_REGISTRY_FIELDS:
            if f not in entry:
                report.add("ERROR", "registry/missing-field", name, f"Required field '{f}' missing.")

        # Domains must be valid
        valid_domains = set(registry.get("domains", ["DOTS", "Unity", "Hybrid", "Any"]))
        for d in entry.get("domains", []):
            if d not in valid_domains:
                report.add("ERROR", "registry/invalid-domain", name, f"Domain '{d}' not in schema domains list.")

        # Roles must be valid
        valid_roles = set(registry.get("roles", []))
        for r in entry.get("roles", []):
            if valid_roles and r not in valid_roles:
                report.add("WARNING", "registry/unknown-role", name, f"Role '{r}' not in schema roles list.")

        # Non-meta skills must have non-empty roles + keywords
        if not is_meta:
            if not entry.get("roles"):
                report.add("ERROR", "registry/no-roles", name,
                           "Non-meta skill has empty roles. No agent will ever load it. Add roles or set mode:meta.")
            if not entry.get("keywords") and entry.get("priority", 0) < 90:
                report.add("WARNING", "registry/no-keywords", name,
                           "No keywords and priority < 90. Skill unreachable via keyword routing.")

        # Recommended fields for non-meta
        if not is_meta:
            for f in RECOMMENDED_REGISTRY_FIELDS_NONMETA:
                if f not in entry:
                    report.add("WARNING", "registry/missing-recommended", name,
                               f"Recommended field '{f}' missing. Add for routing evidence.")

        # DOTS guard: DOTS-only skills must not list NO_DOTS_ROLES
        if name in DOTS_ONLY_SKILLS:
            overlap = set(entry.get("roles", [])) & NO_DOTS_ROLES
            if overlap:
                report.add("ERROR", "registry/dots-guard-violation", name,
                           f"DOTS-only skill lists NO_DOTS_ROLES: {sorted(overlap)}. Remove them.")

        # internal-only: if set, consumer must be documented
        if entry.get("internal-only"):
            if not entry.get("consumer"):
                report.add("WARNING", "registry/internal-no-consumer", name,
                           "internal-only=true but no 'consumer' field. Document who uses this.")

        # Unity corpus skills: must have source + version
        is_unity_corpus = entry.get("source") or any(
            kw in name for kw in ["unity-dots", "unity-classic", "unity-foundation", "unity-skills"]
        )
        if is_unity_corpus and "unity-skills" not in (entry.get("mode") or ""):
            if not entry.get("source"):
                report.add("WARNING", "registry/corpus-no-source", name,
                           "Unity corpus skill missing 'source' field. Add per architect rule-extraction schema.")
            if not entry.get("version"):
                report.add("WARNING", "registry/corpus-no-version", name,
                           "Unity corpus skill missing 'version' field. Add per architect rule-extraction schema.")


# ---------------------------------------------------------------------------
# Check: SKILL.md content
# ---------------------------------------------------------------------------

def check_skill_md(report: ValidationReport, registry: dict) -> None:
    skills = registry.get("skills", [])

    for entry in skills:
        name = entry.get("name", "<unnamed>")
        skill_path_str = entry.get("path", "")
        if not skill_path_str:
            continue
        skill_path = REPO_ROOT / skill_path_str
        if not skill_path.exists():
            continue  # already caught in disk-vs-registry

        fm = parse_frontmatter(skill_path)
        is_meta = entry.get("mode") in ("meta",)

        # Frontmatter must parse
        if fm is None:
            report.add("ERROR", "skill-md/no-frontmatter", name,
                       f"SKILL.md has no valid YAML frontmatter block. Add '---\\nname: {name}\\n...\\n---'.")
            continue

        # name field
        fm_name = fm.get("name")
        if not fm_name:
            report.add("ERROR", "skill-md/no-name", name, "Frontmatter missing 'name' field.")
        elif str(fm_name) != name:
            report.add("ERROR", "skill-md/name-mismatch", name,
                       f"Frontmatter name '{fm_name}' != folder name '{name}'. They must match.")

        # description field
        desc = fm.get("description") or ""
        if not desc:
            report.add("ERROR", "skill-md/no-description", name, "Frontmatter missing 'description' field.")
        else:
            if len(str(desc)) < MIN_DESC_LEN:
                report.add("ERROR", "skill-md/description-too-short", name,
                           f"Description only {len(str(desc))} chars (min {MIN_DESC_LEN}). Expand it.")
            for suffix in TRUNCATION_SUFFIXES:
                if str(desc).rstrip().endswith(suffix):
                    report.add("ERROR", "skill-md/description-truncated", name,
                               f"Description ends with '{suffix}' — looks truncated. Complete it.")

        # New required fields for non-meta skills
        if not is_meta:
            for field_name in ["use-when", "do-not-use-when", "platforms"]:
                if field_name not in fm or not fm[field_name]:
                    report.add("WARNING", "skill-md/missing-field", name,
                               f"Frontmatter missing '{field_name}'. Required for machine-readable routing.")

            # platforms must be valid values
            platforms = fm.get("platforms") or []
            if isinstance(platforms, list):
                for p in platforms:
                    if p not in VALID_PLATFORMS:
                        report.add("WARNING", "skill-md/invalid-platform", name,
                                   f"Platform '{p}' not in valid set {sorted(VALID_PLATFORMS)}.")
            elif platforms:
                report.add("WARNING", "skill-md/platforms-not-list", name,
                           "platforms field should be a YAML list e.g. [claude-code, codex].")

        # Security checks
        content = skill_path.read_text(encoding="utf-8-sig")
        for pattern in SECRET_PATTERNS:
            m = pattern.search(content)
            if m:
                # Skip if it's clearly a placeholder like "YOUR_TOKEN_HERE"
                match_text = m.group(0)
                if not re.search(r"(?i)(your|example|placeholder|xxx|<[^>]+>)", match_text):
                    report.add("ERROR", "skill-md/possible-secret", name,
                               f"Possible secret/token detected: '{match_text[:60]}'. Remove credentials.")

        for pattern in PERSONAL_PATH_PATTERNS:
            m = pattern.search(content)
            if m:
                report.add("ERROR", "skill-md/personal-path", name,
                           f"Personal machine path detected: '{m.group(0)}'. Use relative paths.")

        for pattern in UNSAFE_EXEC_PATTERNS:
            m = pattern.search(content)
            if m:
                report.add("ERROR", "skill-md/unsafe-exec", name,
                           f"Unsafe auto-execution pattern: '{m.group(0)[:60]}'. Remove it.")


# ---------------------------------------------------------------------------
# Check: dead-skill detection
# ---------------------------------------------------------------------------

def check_dead_skills(report: ValidationReport, registry: dict) -> None:
    skills = registry.get("skills", [])

    for entry in skills:
        name = entry.get("name", "<unnamed>")
        is_meta = entry.get("mode") in ("meta",)
        is_role_brief = entry.get("mode") == "role-brief"

        if is_meta or is_role_brief:
            continue  # meta/role-brief: expected to have no normal routing

        roles = entry.get("roles", [])
        keywords = entry.get("keywords", [])
        intents = entry.get("intents", [])

        # No role mapping
        if not roles:
            report.add("ERROR", "dead-skill/no-role", name,
                       "No role mapping. No agent can ever receive this skill. Set roles or mode:meta.")

        # No trigger (no keywords and no intents and priority < 90)
        if not keywords and not intents and entry.get("priority", 0) < 90:
            report.add("ERROR", "dead-skill/no-trigger", name,
                       "No keywords, no intents, and low priority. Skill is unreachable. Add keywords or intents.")

        # No routing rule
        if not entry.get("routing-rule") and not entry.get("conditional"):
            report.add("WARNING", "dead-skill/no-routing-rule", name,
                       "No 'routing-rule' field. Document where this skill's routing is defined.")

    # Detect identical effective routing (same keywords + same roles + same domains)
    non_meta = [e for e in skills if e.get("mode") not in ("meta", "role-brief")]
    seen_signatures: dict[str, str] = {}
    for entry in non_meta:
        sig = (
            frozenset(entry.get("keywords", [])),
            frozenset(entry.get("roles", [])),
            frozenset(entry.get("domains", [])),
        )
        sig_key = str(sig)
        if sig_key in seen_signatures:
            report.add("WARNING", "dead-skill/identical-routing", entry.get("name", ""),
                       f"Identical effective routing as '{seen_signatures[sig_key]}'. "
                       "One is a dead duplicate. Differentiate triggers or merge.")
        else:
            seen_signatures[sig_key] = entry.get("name", "")


# ---------------------------------------------------------------------------
# Check: trigger-collision detection
# ---------------------------------------------------------------------------

PRIORITY_TIERS = [
    "specific-local",
    "domain-specific",
    "project-specific",
    "general-unity",
    "external-skillhub",
]


def _get_priority_tier(entry: dict) -> str:
    """Classify entry into priority tier for collision resolution."""
    if entry.get("conditional"):
        return "specific-local"
    domains = entry.get("domains", [])
    if domains and "Any" not in domains:
        return "domain-specific"
    if entry.get("priority", 0) >= 90:
        return "project-specific"
    return "general-unity"


def check_trigger_collisions(report: ValidationReport, registry: dict) -> list[CollisionReport]:
    skills = registry.get("skills", [])
    non_meta = [e for e in skills if e.get("mode") not in ("meta", "role-brief")]
    collisions: list[CollisionReport] = []

    for i, a in enumerate(non_meta):
        for b in non_meta[i + 1:]:
            shared_kw = sorted(set(a.get("keywords", [])) & set(b.get("keywords", [])))
            shared_roles = sorted(set(a.get("roles", [])) & set(b.get("roles", [])))

            if shared_kw and shared_roles:
                tier_a = _get_priority_tier(a)
                tier_b = _get_priority_tier(b)
                idx_a = PRIORITY_TIERS.index(tier_a) if tier_a in PRIORITY_TIERS else 99
                idx_b = PRIORITY_TIERS.index(tier_b) if tier_b in PRIORITY_TIERS else 99

                if idx_a <= idx_b:
                    winner = a["name"]
                    resolution = (
                        f"Route {a['name']} first ({tier_a}). "
                        f"Load {b['name']} only when '{b.get('name')}' keywords dominate without shared overlap."
                    )
                else:
                    winner = b["name"]
                    resolution = (
                        f"Route {b['name']} first ({tier_b}). "
                        f"Load {a['name']} only when '{a.get('name')}' keywords dominate without shared overlap."
                    )

                c = CollisionReport(
                    skill_a=a["name"],
                    skill_b=b["name"],
                    shared_keywords=shared_kw,
                    shared_roles=shared_roles,
                    winner=winner,
                    resolution=resolution,
                )
                collisions.append(c)

                # DOTS skills colliding with Unity skills across NO_DOTS_ROLES is an error
                a_is_dots = a["name"] in DOTS_ONLY_SKILLS
                b_is_dots = b["name"] in DOTS_ONLY_SKILLS
                mixed_dots = (a_is_dots and not b_is_dots) or (not a_is_dots and b_is_dots)
                roles_include_no_dots = bool(set(shared_roles) & NO_DOTS_ROLES)
                if mixed_dots and roles_include_no_dots:
                    report.add("ERROR", "collision/dots-unity-role-overlap",
                               f"{a['name']} vs {b['name']}",
                               f"DOTS skill and non-DOTS skill share roles in NO_DOTS_ROLES: {shared_roles}. "
                               "Remove the DOTS-only skill from those roles.")
                else:
                    report.add("WARNING", "collision/trigger",
                               f"{a['name']} vs {b['name']}",
                               f"Shared keywords {shared_kw} × shared roles {shared_roles}. "
                               f"Priority winner: {winner}. Add disambiguation to routing-rule.")

    return collisions


# ---------------------------------------------------------------------------
# Check: routing evidence completeness
# ---------------------------------------------------------------------------

def check_routing_evidence(report: ValidationReport, registry: dict) -> None:
    skills = registry.get("skills", [])
    for entry in skills:
        name = entry.get("name", "<unnamed>")
        is_meta = entry.get("mode") in ("meta", "role-brief")
        if is_meta:
            continue

        if not entry.get("positive-example"):
            report.add("WARNING", "routing-evidence/no-positive-example", name,
                       "Missing 'positive-example'. Add a sample task that SHOULD load this skill.")
        if not entry.get("negative-example"):
            report.add("WARNING", "routing-evidence/no-negative-example", name,
                       "Missing 'negative-example'. Add a sample task that must NOT load this skill.")
        if not entry.get("routing-rule"):
            report.add("WARNING", "routing-evidence/no-routing-rule", name,
                       "Missing 'routing-rule'. Document which file/function controls routing.")
        # internal-only skills are excluded from SkillHub — task-categories not required
        if not entry.get("internal-only") and not entry.get("task-categories"):
            report.add("WARNING", "routing-evidence/no-task-categories", name,
                       "Missing 'task-categories'. Add category tags for SkillHub discovery.")

        # External-skillhub skills must have routing-eligible: false until human approval.
        # Skills with origin="external-skillhub" indicate they were discovered via external
        # discovery flow (AGENTS.md §Required Workflow). Until a human sets routing-eligible: true,
        # the skill must not be routed.
        if entry.get("origin") == "external-skillhub":
            if entry.get("routing-eligible", True) is not False:
                report.add("WARNING", "routing-eligible/external-not-gated", name,
                           "External-skillhub skill missing 'routing-eligible: false'. "
                           "External skills must be gated until human approves routing. "
                           "Set routing-eligible: false + $routing-gate in registry entry.")

        # Any skill with routing-eligible: false should document WHY via $routing-gate.
        if entry.get("routing-eligible") is False:
            if not entry.get("$routing-gate"):
                report.add("WARNING", "routing-eligible/missing-gate-note", name,
                           "Skill has 'routing-eligible: false' but no '$routing-gate' explanation. "
                           "Add '$routing-gate': 'HOLD: <reason>' to document why routing is blocked.")


# ---------------------------------------------------------------------------
# Build final report counters
# ---------------------------------------------------------------------------

def build_counters(registry: dict, report: ValidationReport,
                   collisions: list[CollisionReport]) -> dict[str, int]:
    skills = registry.get("skills", [])
    total = len(skills)

    meta_names = {s["name"] for s in skills if s.get("mode") in ("meta", "role-brief")}
    internal_only = sum(1 for s in skills if s.get("internal-only"))

    # Routable = not meta, has roles, has keywords or priority >= 90
    routable = sum(
        1 for s in skills
        if s.get("mode") not in ("meta", "role-brief")
        and s.get("roles")
        and (s.get("keywords") or s.get("priority", 0) >= 90)
    )

    # Orphans = on disk but not in registry
    registry_names = {s["name"] for s in skills}
    orphans = sum(
        1 for item in SKILLS_DIR.iterdir()
        if item.is_dir() and (item / "SKILL.md").exists() and item.name not in registry_names
    )

    # Unreachable = in registry, not meta, no roles OR (no keywords AND priority < 90)
    unreachable = sum(
        1 for s in skills
        if s.get("mode") not in ("meta", "role-brief")
        and (not s.get("roles") or (not s.get("keywords") and s.get("priority", 0) < 90))
    )

    # Duplicate candidates (from identical routing collisions)
    dup_candidates = sum(
        1 for i in report.issues
        if i.check == "dead-skill/identical-routing"
    )

    # Unresolved duplicates = collisions flagged as ERROR
    unresolved = sum(
        1 for i in report.issues
        if "collision" in i.check and i.level == "ERROR"
    )

    # Gated = routing-eligible: false (awaiting ACK before routing)
    gated = sum(1 for s in skills if s.get("routing-eligible") is False)

    return {
        "total_skills": total,
        "routable": routable,
        "internal_only": internal_only,
        "gated": gated,
        "duplicate_candidates": dup_candidates,
        "orphans": orphans,
        "unreachable": unreachable,
        "merged": 0,
        "removed": 0,
        "newly_created": 0,
        "unresolved_duplicates": unresolved,
        "collision_warnings": len(collisions),
    }


# ---------------------------------------------------------------------------
# Main validation runner
# ---------------------------------------------------------------------------

def validate(verbose: bool = False) -> ValidationReport:
    registry = load_registry()
    report = ValidationReport()

    check_disk_vs_registry(report, registry)
    check_registry_entries(report, registry)
    check_skill_md(report, registry)
    check_dead_skills(report, registry)
    collisions = check_trigger_collisions(report, registry)
    check_routing_evidence(report, registry)

    report.collisions = collisions
    report.counters = build_counters(registry, report, collisions)
    return report


# ---------------------------------------------------------------------------
# CLI entry (also importable)
# ---------------------------------------------------------------------------

def print_report(report: ValidationReport, verbose: bool = True) -> None:
    errors = report.errors()
    warnings = report.warnings()

    if errors or verbose:
        print("\n=== ERRORS ===")
        for issue in errors:
            print(str(issue))

    if warnings or verbose:
        print("\n=== WARNINGS ===")
        for issue in warnings:
            print(str(issue))

    if report.collisions:
        print(f"\n=== TRIGGER COLLISIONS ({len(report.collisions)}) ===")
        for c in report.collisions:
            print(f"\n  {c.skill_a}  vs  {c.skill_b}")
            print(f"    Shared keywords : {c.shared_keywords}")
            print(f"    Shared roles    : {c.shared_roles}")
            print(f"    Priority winner : {c.winner}")
            print(f"    Resolution      : {c.resolution}")

    print("\n=== FINAL REPORT COUNTERS ===")
    for k, v in sorted(report.counters.items()):
        flag = " ← MUST BE ZERO" if k in ("orphans", "unreachable", "unresolved_duplicates") and v > 0 else ""
        print(f"  {k:<30s} {v}{flag}")

    required_zeros = ["orphans", "unreachable", "unresolved_duplicates"]
    failed_zeros = [k for k in required_zeros if report.counters.get(k, 0) > 0]

    print()
    if errors:
        print(f"RESULT: FAIL  ({len(errors)} errors, {len(warnings)} warnings)")
        if failed_zeros:
            print(f"        REQUIRED-ZERO VIOLATIONS: {failed_zeros}")
    elif failed_zeros:
        print(f"RESULT: FAIL  (0 errors, {len(warnings)} warnings — required-zero violated: {failed_zeros})")
    elif warnings:
        print(f"RESULT: PASS (with {len(warnings)} warnings)")
    else:
        print("RESULT: PASS (clean)")


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    report = validate(verbose=verbose)
    print_report(report, verbose=verbose)

    errors = report.errors()
    failed_zeros = [
        k for k in ("orphans", "unreachable", "unresolved_duplicates")
        if report.counters.get(k, 0) > 0
    ]
    sys.exit(1 if (errors or failed_zeros) else 0)
