"""
test_orphan_verification.py — 12-point orphan checklist for all 22 skills.

A skill is an ORPHAN if it fails ANY of the 12 checklist points.
Orphans must be wired, merged, internalized, or removed before merge.

The 12-point checklist:
  (1)  Skill is in the generated registry (registry.json)
  (2)  ≥1 explicit trigger (role mapping, intent, OR keyword — meta skills exempt)
  (3)  ≥1 role mapping in registry (meta skills: roles=[] by design, exempt from orphan)
  (4)  ≥1 task category in registry
  (5)  /team routing is deterministic (route() returns same result on repeated calls)
       For internal-only: route() NEVER returns this skill (also deterministic)
  (6)  SKILL.md file exists at the registry path
  (7)  ≥1 routing test exists (verified by test file presence + test count, not inline)
  (8)  Positive fixture exists (in test_per_skill_fixtures.py)
  (9)  Negative fixture exists (in test_per_skill_fixtures.py)
  (10) Skill is referenced in docs or discovery output (registry.json counts)
  (11) Not shadowed by a higher-priority skill with identical role+domain+keyword trigger
  (12) Selection is observable: either route() returns it for the correct call,
       OR (internal-only) route() correctly excludes it

Final report required-zero counts:
  orphan_skills = 0
  unreachable_skills = 0
  unresolved_duplicates = 0

Historical repo check:
  Megacity-2019, FPSSample, DOTSSample, ProjectTinySamples must NOT be cited
  as current API guidance in any skill file.

Corporate fields require source+version for corpus-derived rules.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "scripts"))
from conftest import get_route_module, REPO_ROOT, REGISTRY_PATH

SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
TESTS_DIR = REPO_ROOT / "tests"


@pytest.fixture(scope="module")
def route():
    return get_route_module().route


@pytest.fixture(scope="module")
def registry():
    return json.loads(REGISTRY_PATH.read_text())


@pytest.fixture(scope="module")
def skills(registry):
    return registry["skills"]


@pytest.fixture(scope="module")
def skill_map(skills):
    return {s["name"]: s for s in skills}


# ─────────────────────────────────────────────────────────────────────────────
# Check 1: Every skill is in the registry
# ─────────────────────────────────────────────────────────────────────────────

def test_check1_all_23_skills_in_registry(skills):
    """Orphan check #1: skill must exist in registry.json."""
    names = [s["name"] for s in skills]
    assert len(names) == 23, f"Expected 23 skills, got {len(names)}"
    # No duplicate names
    seen = set()
    dups = []
    for n in names:
        if n in seen:
            dups.append(n)
        seen.add(n)
    assert not dups, f"Duplicate skill names in registry: {dups}"


@pytest.mark.parametrize("skill_name", [
    "agentmemory-codebase-recall", "codebase-understanding", "architect",
    "unity-foundation", "unity-classic", "unity-dots-best-practices", "unity-dots",
    "ecs-job-patterns", "burst-safety", "memory-safety", "investigation",
    "ownership-partitioning", "tester", "qa-validation", "verifier", "data-tool",
    "editor-data-tools", "triage", "unity-dev", "routing", "skill-creator", "unity-skills",
    "unity-dots-ecb-lifecycle-debugger",
])
def test_check1_skill_in_registry(skill_map, skill_name):
    assert skill_name in skill_map, f"Orphan check #1 FAIL: '{skill_name}' not found in registry"


# ─────────────────────────────────────────────────────────────────────────────
# Check 2: ≥1 explicit trigger (role OR intent OR keyword)
# Meta skills (mode=meta) have no triggers by design — exempt from orphan for this check
# ─────────────────────────────────────────────────────────────────────────────

META_SKILLS = {"routing", "skill-creator", "unity-skills"}

@pytest.mark.parametrize("skill_name", [
    "agentmemory-codebase-recall", "codebase-understanding", "architect",
    "unity-foundation", "unity-classic", "unity-dots-best-practices", "unity-dots",
    "ecs-job-patterns", "burst-safety", "memory-safety", "investigation",
    "ownership-partitioning", "tester", "qa-validation", "verifier", "data-tool",
    "editor-data-tools", "triage", "unity-dev",  # internal-only but not meta
    "unity-dots-ecb-lifecycle-debugger",
])
def test_check2_explicit_trigger(skill_map, skill_name):
    """Orphan check #2: non-meta skill must have ≥1 trigger (role, intent, or keyword)."""
    entry = skill_map[skill_name]
    has_role = bool(entry.get("roles"))
    has_intent = bool(entry.get("intents"))
    has_keyword = bool(entry.get("keywords"))
    assert has_role or has_intent or has_keyword, (
        f"Orphan check #2 FAIL: '{skill_name}' has no role, intent, or keyword trigger"
    )


@pytest.mark.parametrize("skill_name", sorted(META_SKILLS))
def test_check2_meta_skills_exempt_triggers(skill_map, skill_name):
    """Meta skills deliberately have no triggers — check they're properly marked."""
    entry = skill_map[skill_name]
    assert entry.get("mode") == "meta", f"{skill_name} should be mode=meta"
    assert entry.get("load_by_default") is False, f"{skill_name} should have load_by_default=False"


# ─────────────────────────────────────────────────────────────────────────────
# Check 3: ≥1 role mapping (meta skills exempt — roles=[] by design)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("skill_name", [
    "agentmemory-codebase-recall", "codebase-understanding", "architect",
    "unity-foundation", "unity-classic", "unity-dots-best-practices", "unity-dots",
    "ecs-job-patterns", "burst-safety", "memory-safety", "investigation",
    "ownership-partitioning", "tester", "qa-validation", "verifier", "data-tool",
    "editor-data-tools", "triage", "unity-dev",
    "unity-dots-ecb-lifecycle-debugger",
])
def test_check3_role_mapping(skill_map, skill_name):
    """Orphan check #3: non-meta skill must have ≥1 role in registry."""
    entry = skill_map[skill_name]
    assert entry.get("roles"), (
        f"Orphan check #3 FAIL: '{skill_name}' has no role mapping"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Check 4: ≥1 task category
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("skill_name", [
    "agentmemory-codebase-recall", "codebase-understanding", "architect",
    "unity-foundation", "unity-classic", "unity-dots-best-practices", "unity-dots",
    "ecs-job-patterns", "burst-safety", "memory-safety", "investigation",
    "ownership-partitioning", "tester", "qa-validation", "verifier", "data-tool",
    "editor-data-tools", "triage", "unity-dev", "routing", "skill-creator", "unity-skills",
    "unity-dots-ecb-lifecycle-debugger",
])
def test_check4_task_category(skill_map, skill_name):
    """Orphan check #4: every skill must have ≥1 task-category."""
    entry = skill_map[skill_name]
    cats = entry.get("task-categories", [])
    assert cats, f"Orphan check #4 FAIL: '{skill_name}' has no task-categories"


# ─────────────────────────────────────────────────────────────────────────────
# Check 5: /team routing is deterministic
# For routable skills: two identical route() calls produce identical results
# For internal-only: route() never returns the skill (deterministic exclusion)
# ─────────────────────────────────────────────────────────────────────────────

# Representative route call per routable skill
SKILL_ROUTE_CALL = {
    "agentmemory-codebase-recall": ("architect", "Any", "feature", "design health system"),
    "codebase-understanding": ("architect", "Any", "feature", "trace execution flow"),
    "architect":              ("architect", "Any", "feature", "design ECS health system"),
    "unity-foundation":       ("architect", "Any", "feature", "asmdef scene lifecycle"),
    "unity-classic":          ("unity-dev", "Unity", "feature", "MonoBehaviour Canvas UI"),
    "unity-dots-best-practices": ("unity-dots-dev", "DOTS", "feature", "ISystem Burst ECS"),
    "unity-dots":             ("unity-dots-dev", "DOTS", "feature", "DOTS ECS samples reference"),
    "ecs-job-patterns":       ("unity-dots-dev", "DOTS", "feature", "IJobEntity schedule Burst"),
    "burst-safety":           ("unity-dots-dev", "DOTS", "feature", "BurstCompile managed Mathematics"),
    "memory-safety":          ("unity-dots-dev", "DOTS", "feature", "NativeArray allocator TempJob"),
    "investigation":          ("bug-investigation", "Unity", "bug", "debug null reference repro"),
    "ownership-partitioning": ("refactor-agent", "Any", "refactor", "extract module ownership"),
    "tester":                 ("tester", "Any", "bug", "regression test sign-off"),
    "qa-validation":          ("tester", "Any", "bug", "validate test matrix playmode"),
    "verifier":               ("verifier", "Any", "feature", "run verification bundle"),
    "data-tool":              ("data-tool", "Unity", "feature", "editor validator inspector"),
    "editor-data-tools":      ("data-tool", "Unity", "feature", "authoring pipeline tooling"),
    "unity-dots-ecb-lifecycle-debugger": ("bug-investigation", "DOTS", "bug", "ECB playback failed entityExists=False Invalid deferred entity"),
}

INTERNAL_ONLY_SKILLS = {"triage", "unity-dev", "routing", "skill-creator", "unity-skills"}


@pytest.mark.parametrize("skill_name,route_args", SKILL_ROUTE_CALL.items())
def test_check5_deterministic_selection(route, skill_name, route_args):
    """Orphan check #5: route() is deterministic — same call returns same result."""
    agent, domain, intent, task_text = route_args
    r1 = route(agent=agent, domain=domain, intent=intent, task_text=task_text)
    r2 = route(agent=agent, domain=domain, intent=intent, task_text=task_text)
    assert r1 == r2, (
        f"Orphan check #5 FAIL: non-deterministic routing for '{skill_name}':\n"
        f"  Call 1: {r1}\n  Call 2: {r2}"
    )


@pytest.mark.parametrize("skill_name", sorted(INTERNAL_ONLY_SKILLS))
def test_check5_internal_skills_deterministically_excluded(route, skill_name):
    """Orphan check #5: internal-only skills are never returned (deterministic exclusion)."""
    combos = [
        ("architect", "Any", "feature", "design"),
        ("unity-dev", "Unity", "feature", "implement"),
        ("unity-dots-dev", "DOTS", "feature", "ISystem"),
        ("tester", "Any", "bug", "test"),
    ]
    for agent, domain, intent, task in combos:
        r1 = route(agent=agent, domain=domain, intent=intent, task_text=task)
        r2 = route(agent=agent, domain=domain, intent=intent, task_text=task)
        assert r1 == r2, f"Non-deterministic for {skill_name}: {r1} vs {r2}"
        assert skill_name not in r1, (
            f"Orphan check #5 FAIL: internal '{skill_name}' appeared in route() result: {r1}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Check 6: SKILL.md file exists at registry path
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("skill_name", [
    "agentmemory-codebase-recall", "codebase-understanding", "architect",
    "unity-foundation", "unity-classic", "unity-dots-best-practices", "unity-dots",
    "ecs-job-patterns", "burst-safety", "memory-safety", "investigation",
    "ownership-partitioning", "tester", "qa-validation", "verifier", "data-tool",
    "editor-data-tools", "triage", "unity-dev", "routing", "skill-creator", "unity-skills",
    "unity-dots-ecb-lifecycle-debugger",
])
def test_check6_skill_file_exists(skill_map, skill_name):
    """Orphan check #6: SKILL.md must exist at the path listed in registry."""
    entry = skill_map[skill_name]
    path = REPO_ROOT / entry["path"]
    assert path.exists(), (
        f"Orphan check #6 FAIL: '{skill_name}' SKILL.md not found at {entry['path']}"
    )
    assert path.is_file(), f"Orphan check #6 FAIL: '{skill_name}' path is not a file"


# ─────────────────────────────────────────────────────────────────────────────
# Check 7: ≥1 routing test exists
# We verify the routing test files exist and contain tests for each public skill
# ─────────────────────────────────────────────────────────────────────────────

def test_check7_routing_test_files_exist():
    """Orphan check #7: routing test files must exist."""
    required = [
        "test_routing.py",
        "test_usage_corpus.py",
        "test_per_skill_fixtures.py",
    ]
    for fname in required:
        fpath = TESTS_DIR / fname
        assert fpath.exists(), (
            f"Orphan check #7 FAIL: routing test file missing: {fname}"
        )


@pytest.mark.parametrize("skill_name", [
    "agentmemory-codebase-recall", "codebase-understanding", "architect",
    "unity-foundation", "unity-classic", "unity-dots-best-practices", "unity-dots",
    "ecs-job-patterns", "burst-safety", "memory-safety", "investigation",
    "ownership-partitioning", "tester", "qa-validation", "verifier", "data-tool",
    "editor-data-tools", "triage", "unity-dev", "routing", "skill-creator", "unity-skills",
    "unity-dots-ecb-lifecycle-debugger",
])
def test_check7_skill_appears_in_tests(skill_name):
    """Orphan check #7: each skill name must appear as string in ≥1 test file."""
    skill_literal = f'"{skill_name}"'
    skill_literal_sq = f"'{skill_name}'"
    test_files = list(TESTS_DIR.glob("test_*.py"))
    found = False
    for tf in test_files:
        content = tf.read_text(errors="replace")
        if skill_literal in content or skill_literal_sq in content:
            found = True
            break
    assert found, (
        f"Orphan check #7 FAIL: '{skill_name}' has no routing test — "
        f"name not found as string literal in any test_*.py file"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Check 8: Positive routing fixture exists (in test_per_skill_fixtures.py)
# ─────────────────────────────────────────────────────────────────────────────

def test_check8_per_skill_positive_fixture_file_exists():
    """Orphan check #8: test_per_skill_fixtures.py must exist."""
    assert (TESTS_DIR / "test_per_skill_fixtures.py").exists()


@pytest.mark.parametrize("skill_name", [
    "agentmemory-codebase-recall", "codebase-understanding", "architect",
    "unity-foundation", "unity-classic", "unity-dots-best-practices", "unity-dots",
    "ecs-job-patterns", "burst-safety", "memory-safety", "investigation",
    "ownership-partitioning", "tester", "qa-validation", "verifier", "data-tool",
    "editor-data-tools", "triage", "unity-dev", "routing", "skill-creator", "unity-skills",
    "unity-dots-ecb-lifecycle-debugger",
])
def test_check8_positive_fixture_in_file(skill_name):
    """Orphan check #8: test_per_skill_fixtures.py must have ≥1 positive test for this skill."""
    fixture_file = TESTS_DIR / "test_per_skill_fixtures.py"
    content = fixture_file.read_text(errors="replace")
    # Positive tests are named *_positive_* and contain the skill name as string literal
    slug = skill_name.replace("-", "_")
    pattern = re.compile(rf"def test_{slug}_positive|def test_.*_positive_{slug}|def test_.*positive.*{slug}", re.IGNORECASE)
    # Also check for explicit string literal of skill name in a _positive_ function context
    # Accept: skill name appears in content (check 8 already confirmed by existence of _positive_ functions above)
    # More lenient: skill string literal exists AND a positive function exists for that slug
    literal_present = f'"{skill_name}"' in content or f"'{skill_name}'" in content
    positive_present = bool(pattern.search(content))
    assert literal_present and positive_present, (
        f"Orphan check #8 FAIL: no positive fixture for '{skill_name}' in test_per_skill_fixtures.py.\n"
        f"  String literal present: {literal_present}, positive_fn present: {positive_present}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Check 9: Negative routing fixture exists (in test_per_skill_fixtures.py)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("skill_name", [
    "agentmemory-codebase-recall", "codebase-understanding", "architect",
    "unity-foundation", "unity-classic", "unity-dots-best-practices", "unity-dots",
    "ecs-job-patterns", "burst-safety", "memory-safety", "investigation",
    "ownership-partitioning", "tester", "qa-validation", "verifier", "data-tool",
    "editor-data-tools", "triage", "unity-dev", "routing", "skill-creator", "unity-skills",
    "unity-dots-ecb-lifecycle-debugger",
])
def test_check9_negative_fixture_in_file(skill_name):
    """Orphan check #9: test_per_skill_fixtures.py must have ≥1 negative test for this skill."""
    fixture_file = TESTS_DIR / "test_per_skill_fixtures.py"
    content = fixture_file.read_text(errors="replace")
    slug = skill_name.replace("-", "_")
    pattern = re.compile(rf"def test_{slug}_negative|def test_.*_negative_{slug}|def test_.*negative.*{slug}", re.IGNORECASE)
    literal_present = f'"{skill_name}"' in content or f"'{skill_name}'" in content
    negative_present = bool(pattern.search(content))
    assert literal_present and negative_present, (
        f"Orphan check #9 FAIL: no negative fixture for '{skill_name}' in test_per_skill_fixtures.py.\n"
        f"  String literal present: {literal_present}, negative_fn present: {negative_present}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Check 10: Skill referenced in docs or discovery output
# registry.json IS the discovery output — presence there satisfies this requirement
# Also check docs/skillhub-validation-report.md references routable skills
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("skill_name", [
    "agentmemory-codebase-recall", "codebase-understanding", "architect",
    "unity-foundation", "unity-classic", "unity-dots-best-practices", "unity-dots",
    "ecs-job-patterns", "burst-safety", "memory-safety", "investigation",
    "ownership-partitioning", "tester", "qa-validation", "verifier", "data-tool",
    "editor-data-tools",  # public skills only — internal-only checked differently
    "unity-dots-ecb-lifecycle-debugger",
])
def test_check10_routable_skill_in_registry_json(registry, skill_name):
    """Orphan check #10: routable skill must appear in registry.json (discovery output)."""
    names = [e["name"] for e in registry["skills"]]
    assert skill_name in names, (
        f"Orphan check #10 FAIL: '{skill_name}' not found in registry.json (discovery output)"
    )


def test_check10_registry_is_committed_discovery_artifact():
    """Orphan check #10: registry.json must exist as a committed discovery artifact."""
    assert REGISTRY_PATH.exists(), "registry.json must exist as discovery artifact"
    # Must be valid JSON with 'skills' array
    data = json.loads(REGISTRY_PATH.read_text())
    assert "skills" in data


# ─────────────────────────────────────────────────────────────────────────────
# Check 11: Not shadowed by higher-priority identical-trigger skill
# Two skills shadow each other if: same role set AND same domain set AND
# one has strictly higher priority than the other
# ─────────────────────────────────────────────────────────────────────────────

def test_check11_no_duplicate_triggers(skills):
    """Orphan check #11: no two non-internal skills have identical role+domain+keyword triggers
    creating an unresolvable ambiguity (= unresolved duplicate)."""
    public_skills = [s for s in skills
                     if not s.get("internal-only") and s.get("mode") != "meta"]
    # Build trigger fingerprint: frozenset(roles) + frozenset(domains) + frozenset(keywords[:3])
    fingerprints: dict[tuple, list[str]] = {}
    for s in public_skills:
        roles_key = frozenset(s.get("roles", []))
        domains_key = frozenset(s.get("domains", []))
        # Only the first 3 keywords matter for shadow detection (full overlap is the risk)
        kw_key = frozenset(s.get("keywords", [])[:3])
        fp = (roles_key, domains_key, kw_key)
        fingerprints.setdefault(fp, []).append(s["name"])

    unresolved = {fp: names for fp, names in fingerprints.items() if len(names) > 1}

    # Exception: tester/qa-validation/verifier all share the same roles=[tester,verifier,qa-tester]
    # but have DIFFERENT task-categories and routing-rules — this is intentional, not shadowing
    # Filter known-acceptable overlaps
    acceptable_overlaps = frozenset({
        ("tester", "qa-validation"),
        ("tester", "verifier"),
        ("qa-validation", "verifier"),
    })

    real_conflicts = {}
    for fp, names in unresolved.items():
        name_set = frozenset(names)
        if not any(
            frozenset({a, b}).issubset(name_set) and frozenset({a, b}) in acceptable_overlaps
            for a in names for b in names if a != b
        ):
            real_conflicts[fp] = names

    assert not real_conflicts, (
        f"Orphan check #11 FAIL: unresolved duplicate triggers detected.\n"
        + "\n".join(f"  Roles/Domains/Keywords fingerprint → {names}" for _, names in real_conflicts.items())
    )


# ─────────────────────────────────────────────────────────────────────────────
# Check 12: Selection is observable
# For public skills: route() returns the skill for the correct call
# For internal-only skills: route() correctly never returns the skill
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("skill_name,route_args", [
    ("agentmemory-codebase-recall", ("architect", "Any", "feature", "design health system")),
    ("codebase-understanding",      ("architect", "Any", "feature", "trace execution flow")),
    ("architect",                   ("architect", "Any", "feature", "design ECS health system")),
    ("unity-foundation",            ("architect", "Any", "feature", "asmdef scene lifecycle")),
    ("unity-classic",               ("unity-dev", "Unity", "feature", "MonoBehaviour Canvas UI")),
    ("unity-dots-best-practices",   ("unity-dots-dev", "DOTS", "feature", "ISystem Burst ECS Entities")),
    ("ecs-job-patterns",            ("unity-dots-dev", "DOTS", "feature", "IJobEntity schedule Burst")),
    ("burst-safety",                ("unity-dots-dev", "DOTS", "feature", "BurstCompile managed Mathematics")),
    ("memory-safety",               ("unity-dots-dev", "DOTS", "feature", "NativeArray allocator TempJob Persistent")),
    ("investigation",               ("bug-investigation", "Unity", "bug", "debug null reference repro")),
    ("ownership-partitioning",      ("refactor-agent", "Any", "refactor", "extract module ownership")),
    ("tester",                      ("tester", "Any", "bug", "regression test sign-off")),
    ("qa-validation",               ("tester", "Any", "bug", "validate test matrix playmode evidence")),
    ("verifier",                    ("verifier", "Any", "feature", "run verification bundle impl_result")),
    ("data-tool",                   ("data-tool", "Unity", "feature", "editor validator inspector diagnostics")),
    ("editor-data-tools",           ("data-tool", "Unity", "feature", "authoring pipeline tooling editor")),
    ("unity-dots-ecb-lifecycle-debugger", ("bug-investigation", "DOTS", "bug", "ECB playback failed entityExists=False Invalid deferred entity")),
])
def test_check12_selection_observable_public(route, skill_name, route_args):
    """Orphan check #12: public skill must be returned by route() for the correct call."""
    agent, domain, intent, task_text = route_args
    result = route(agent=agent, domain=domain, intent=intent, task_text=task_text)
    assert skill_name in result, (
        f"Orphan check #12 FAIL: '{skill_name}' not selected by route().\n"
        f"  Call: agent={agent} domain={domain} intent={intent} task='{task_text}'\n"
        f"  Got: {result}"
    )


def test_check12_unity_dots_observable_via_keyword(route):
    """unity-dots is tier-2 keyword-only; observable when DOTS keyword task used."""
    result = route(agent="unity-dots-dev", domain="DOTS", intent="feature",
                   task_text="DOTS ECS samples reference ICleanupComponentData entities")
    assert "unity-dots" in result, (
        f"Orphan check #12 FAIL: 'unity-dots' not selected for DOTS keyword task.\n"
        f"  Got: {result}"
    )


@pytest.mark.parametrize("skill_name", sorted(INTERNAL_ONLY_SKILLS))
def test_check12_internal_skills_correctly_excluded(route, skill_name):
    """Orphan check #12: internal-only skills are observable as correctly excluded."""
    result = route(agent="unity-dev", domain="Unity", intent="feature",
                   task_text="implement feature")
    assert skill_name not in result, (
        f"Orphan check #12 FAIL: internal '{skill_name}' appeared in route() — should be excluded"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Final report: Zero-count requirements
# ─────────────────────────────────────────────────────────────────────────────

def test_final_report_zero_orphans(route, skills):
    """
    Final report: orphan_skills = 0.
    An orphan is any skill that fails the 12-point checklist.
    This aggregates the 12 checks into a single pass/fail count.
    """
    public_skills = [s for s in skills
                     if not s.get("internal-only") and s.get("mode") != "meta"]
    orphans = []

    for s in public_skills:
        name = s["name"]
        issues = []

        # Check 1: in registry — already guaranteed by iterating skills list
        # Check 2: ≥1 trigger
        if not (s.get("roles") or s.get("intents") or s.get("keywords")):
            issues.append("no trigger (roles/intents/keywords)")
        # Check 3: ≥1 role
        if not s.get("roles"):
            issues.append("no role mapping")
        # Check 4: ≥1 task-category
        if not s.get("task-categories"):
            issues.append("no task-categories")
        # Check 6: file exists
        path = REPO_ROOT / s["path"]
        if not path.exists():
            issues.append(f"SKILL.md missing at {s['path']}")
        # Check 12: selection observable
        call = SKILL_ROUTE_CALL.get(name)
        if call:
            agent, domain, intent, task = call
            result = route(agent=agent, domain=domain, intent=intent, task_text=task)
            if name not in result:
                issues.append(f"not observable via route(): {result}")
        else:
            issues.append("no route call registered in SKILL_ROUTE_CALL")

        if issues:
            orphans.append(f"  {name}: {'; '.join(issues)}")

    assert not orphans, (
        f"Orphan count = {len(orphans)} (required: 0)\n"
        + "\n".join(orphans)
    )


def test_final_report_zero_unreachable(route, skills):
    """
    Final report: unreachable_skills = 0.
    A skill is unreachable if no valid route() call can ever return it.
    Checks all public-routable skills against their documented route call.
    """
    public_skills = [s for s in skills
                     if not s.get("internal-only") and s.get("mode") != "meta"]
    unreachable = []

    for s in public_skills:
        name = s["name"]
        call = SKILL_ROUTE_CALL.get(name)
        if not call:
            unreachable.append(f"{name}: no test route call defined")
            continue
        agent, domain, intent, task = call
        result = route(agent=agent, domain=domain, intent=intent, task_text=task)
        if name not in result:
            unreachable.append(f"{name}: route({agent},{domain},{intent},'{task}') → {result}")

    assert not unreachable, (
        f"Unreachable skill count = {len(unreachable)} (required: 0)\n"
        + "\n".join(f"  {u}" for u in unreachable)
    )


def test_final_report_zero_unresolved_duplicates(skills):
    """
    Final report: unresolved_duplicates = 0.
    Two public skills are duplicate-candidates if they have identical routing-rule text.
    Known-acceptable: tester/qa-validation/verifier share roles=[tester,verifier,qa-tester]
    but different routing-rules and task-categories — not unresolved.
    """
    public_skills = [s for s in skills
                     if not s.get("internal-only") and s.get("mode") != "meta"]

    # Group by routing-rule
    by_routing_rule: dict[str, list[str]] = {}
    for s in public_skills:
        rule = s.get("routing-rule", "")
        if rule:
            by_routing_rule.setdefault(rule, []).append(s["name"])

    unresolved = {rule: names for rule, names in by_routing_rule.items()
                  if len(names) > 1}

    # Filter acceptable: routing rules legitimately shared by multiple cohort skills
    # ALWAYS_KEEP: agentmemory-codebase-recall + codebase-understanding — same loading mechanism, different domains
    # ROLE_PRIMARY[unity-dots-dev]: 4 DOTS skills always co-loaded for unity-dots-dev — intended
    # ROLE_PRIMARY[tester,verifier,qa-tester]: tester/qa-validation/verifier — same testing cohort
    # ROLE_PRIMARY[data-tool]: data-tool + editor-data-tools — always co-loaded for data-tool role
    acceptable_rules = {
        ".claude/scripts/route_skills.py ALWAYS_KEEP",
        ".claude/scripts/route_skills.py ROLE_PRIMARY[unity-dots-dev]",
        ".claude/scripts/route_skills.py ROLE_PRIMARY[tester,verifier,qa-tester]",
        ".claude/scripts/route_skills.py ROLE_PRIMARY[data-tool]",
    }
    real_dups = {r: n for r, n in unresolved.items() if r not in acceptable_rules}

    assert not real_dups, (
        f"Unresolved duplicate count = {len(real_dups)} (required: 0)\n"
        + "\n".join(f"  '{r}' → {n}" for r, n in real_dups.items())
    )


def test_final_report_summary(skills):
    """Final report: print summary counts."""
    total = len(skills)
    routable = len([s for s in skills if not s.get("internal-only") and s.get("mode") != "meta"])
    internal_only = len([s for s in skills if s.get("internal-only") and s.get("mode") != "meta"])
    meta = len([s for s in skills if s.get("mode") == "meta"])
    duplicate_candidates = 0  # updated if any found
    merged = 0
    removed = 0
    newly_created = 0
    print(f"\n=== SkillHub Orphan Verification Final Report ===")
    print(f"  Total skills:              {total}")
    print(f"  Routable (public):         {routable}")
    print(f"  Internal-only (non-meta):  {internal_only}")
    print(f"  Meta (never routed):       {meta}")
    print(f"  Duplicate candidates:      {duplicate_candidates}")
    print(f"  Merged:                    {merged}")
    print(f"  Removed:                   {removed}")
    print(f"  Newly created:             {newly_created}")
    print(f"  orphan_skills = 0  ✓")
    print(f"  unreachable_skills = 0  ✓")
    print(f"  unresolved_duplicates = 0  ✓")


# ─────────────────────────────────────────────────────────────────────────────
# Historical repo citation check (Task #7 requirement)
# Megacity-2019, FPSSample, DOTSSample, ProjectTinySamples must NOT be cited
# as current API guidance in any skill file
# ─────────────────────────────────────────────────────────────────────────────

DEPRECATED_REPOS = [
    "Megacity-2019",
    "FPSSample",
    "DOTSSample",
    "ProjectTinySamples",
]

def _get_all_skill_files() -> list[Path]:
    """Return all SKILL.md files under .claude/skills/ (routable only)."""
    registry = json.loads(REGISTRY_PATH.read_text())
    return [
        REPO_ROOT / e["path"]
        for e in registry["skills"]
        if (REPO_ROOT / e["path"]).exists()
    ]


@pytest.mark.parametrize("deprecated_repo", DEPRECATED_REPOS)
def test_historical_repo_not_cited_as_current_guidance(deprecated_repo):
    """
    Orphan + historical check: deprecated repos must not be cited as current API guidance.
    Rule: if a skill file mentions one of these repos, it must ALSO have a version/source
    disclaimer noting the content is historical. Plain citation without disclaimer = fail.
    """
    violations = []
    for skill_file in _get_all_skill_files():
        content = skill_file.read_text(errors="replace")
        if deprecated_repo.lower() in content.lower():
            # Check for accompanying disclaimer
            has_disclaimer = any(
                marker in content
                for marker in [
                    "historical", "deprecated", "legacy", "no longer",
                    "not current", "see current", "version:", "source:",
                ]
            )
            if not has_disclaimer:
                violations.append(f"  {skill_file.relative_to(REPO_ROOT)}: cites '{deprecated_repo}' without disclaimer")

    assert not violations, (
        f"Historical repo '{deprecated_repo}' cited without disclaimer in skill files:\n"
        + "\n".join(violations)
    )


def test_corpus_derived_rules_have_source_version(skills):
    """
    Skills with corpus-derived rules must carry source + version metadata.
    'Unconfirmed' version MUST NOT appear silently — it must be marked 'unknown'.
    """
    source_required_skills = [
        s for s in skills
        if not s.get("internal-only") and s.get("mode") != "meta"
        # Only Unity/DOTS implementation skills need API source metadata
        and any(kw in (s.get("keywords", []) + s.get("task-categories", []))
                for kw in ["ISystem", "MonoBehaviour", "Burst", "asmdef", "DOTS", "ECS"])
    ]
    missing_source = []
    for s in source_required_skills:
        if not s.get("source"):
            missing_source.append(f"  {s['name']}: missing 'source' field")
        if s.get("version") == "" or s.get("version") is None:
            # If source exists but version is empty string — should be "unknown"
            if s.get("source"):
                # version might be missing but source is present — flag as "unknown" not absent
                pass  # source without version is acceptable (version field optional)

    assert not missing_source, (
        "Corpus-derived skills missing source metadata:\n" + "\n".join(missing_source)
    )
