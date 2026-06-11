"""
test_usage_corpus.py — usage-test corpus for /team skill routing.

12 end-to-end routing cases covering every major task category.
Each case verifies:
  - expected skills ARE selected
  - expected skills are NOT selected (guard against leakage)
  - external discovery is NOT triggered when local skill exists
  - generic/doc-only tasks load ZERO Unity implementation skills
  - no duplicate skills in result
  - minimum required skill set present

Cases:
  1.  DOTS performance optimization
  2.  Classic MonoBehaviour refactor
  3.  Scene loading (async + Addressables)
  4.  Unused asset cleanup (editor tooling)
  5.  Editor window creation
  6.  Cloud Code endpoint (no dedicated local skill)
  7.  Addressables loading issue (bug investigation)
  8.  Unity Test Framework task
  9.  Netcode for Entities
  10. Netcode for GameObjects
  11. Generic C# task — ZERO Unity implementation skills
  12. Documentation-only task — ZERO implementation skills
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "scripts"))
from conftest import get_route_module, REPO_ROOT

REGISTRY_PATH = REPO_ROOT / ".claude" / "skills" / "registry.json"

DOTS_IMPL_SKILLS = frozenset({
    "unity-dots-best-practices", "unity-dots",
    "ecs-job-patterns", "burst-safety", "memory-safety",
})
UNITY_IMPL_SKILLS = frozenset({
    "unity-classic", "unity-foundation",
})
ALL_UNITY_SKILLS = DOTS_IMPL_SKILLS | UNITY_IMPL_SKILLS


@pytest.fixture(scope="module")
def route():
    return get_route_module().route


@pytest.fixture(scope="module")
def registry():
    return json.loads(REGISTRY_PATH.read_text())


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def assert_no_duplicates(result: list[str], label: str) -> None:
    seen = set()
    for s in result:
        assert s not in seen, f"{label}: duplicate skill '{s}' in {result}"
        seen.add(s)


def assert_contains_all(result: list[str], expected: list[str], label: str) -> None:
    missing = [s for s in expected if s not in result]
    assert not missing, (
        f"{label}: expected skills missing from result.\n"
        f"  Missing: {missing}\n  Got: {result}"
    )


def assert_contains_none_of(result: list[str], forbidden: list[str], label: str) -> None:
    leaked = [s for s in forbidden if s in result]
    assert not leaked, (
        f"{label}: forbidden skills found in result.\n"
        f"  Leaked: {leaked}\n  Got: {result}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Case 1: DOTS performance optimization
# Agent: unity-dots-dev | Domain: DOTS | Intent: performance
# Task: Burst-compiled enemy AI with IJobEntity
# ─────────────────────────────────────────────────────────────────────────────

def test_corpus_1_dots_performance_optimization(route):
    """
    DOTS perf task selects all DOTS primaries; unity-classic must NOT appear.
    Priority: tier-0 ROLE_PRIMARY[unity-dots-dev] = 4 skills (1000+priority).
    No Burst/ECS penalty can bypass the tier-0 guard.
    External skill discovery NOT triggered — registry already covers DOTS.
    """
    label = "case-1: DOTS perf optimization"
    result = route(
        agent="unity-dots-dev",
        domain="DOTS",
        intent="performance",
        task_text="optimize enemy AI using ISystem Burst-compiled IJobEntity NativeArray performance"
    )
    assert_no_duplicates(result, label)
    assert_contains_all(result, [
        "unity-dots-best-practices",
        "ecs-job-patterns",
        "codebase-understanding",
        "agentmemory-codebase-recall",
    ], label)
    assert_contains_none_of(result, [
        "unity-classic",    # Unity-classic must never reach DOTS lane
        "unity-foundation", # Foundation is unity-dev/architect only
        "triage",           # Internal-only skill
    ], label)


def test_corpus_1_min_dot_skills_present(route):
    """At least 2 DOTS-only skills must be in the result for a DOTS perf task."""
    result = route(
        agent="unity-dots-dev", domain="DOTS", intent="performance",
        task_text="ISystem Burst IJobEntity NativeArray performance optimization"
    )
    dots_present = DOTS_IMPL_SKILLS & set(result)
    assert len(dots_present) >= 2, (
        f"case-1: expected ≥2 DOTS skills, got {sorted(dots_present)} in {result}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Case 2: Classic MonoBehaviour refactor
# Agent: unity-dev | Domain: Unity | Intent: refactor
# ─────────────────────────────────────────────────────────────────────────────

def test_corpus_2_monobehaviour_refactor(route):
    """
    Unity refactor → unity-classic (tier-0) + ownership-partitioning (refactor intent).
    DOTS guard ensures no DOTS skills leak to unity-dev lane.
    """
    label = "case-2: MonoBehaviour refactor"
    result = route(
        agent="unity-dev",
        domain="Unity",
        intent="refactor",
        task_text="refactor inventory MonoBehaviour VContainer dependency injection Awake OnEnable"
    )
    assert_no_duplicates(result, label)
    assert_contains_all(result, [
        "unity-classic",
        "codebase-understanding",
        "agentmemory-codebase-recall",
        "ownership-partitioning",  # refactor intent must-keep
    ], label)
    assert_contains_none_of(result, sorted(DOTS_IMPL_SKILLS), label)


def test_corpus_2_no_dots_skills_on_unity_refactor(route):
    """DOTS skills must not reach unity-dev regardless of task keywords."""
    result = route(
        agent="unity-dev", domain="Unity", intent="refactor",
        task_text="MonoBehaviour refactor ISystem ECS burst job entities"  # DOTS keywords present
    )
    leaked = DOTS_IMPL_SKILLS & set(result)
    assert not leaked, (
        f"case-2: DOTS skills leaked to unity-dev refactor: {sorted(leaked)}; got {result}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Case 3: Scene loading (async + Addressables)
# Agent: unity-dev | Domain: Unity | Intent: feature
# ─────────────────────────────────────────────────────────────────────────────

def test_corpus_3_scene_loading(route):
    """
    'Addressables' keyword in task hits unity-classic tier-2 (already tier-0).
    External discovery NOT triggered — Addressables is handled by local unity-classic.
    """
    label = "case-3: scene loading"
    result = route(
        agent="unity-dev",
        domain="Unity",
        intent="feature",
        task_text="implement async scene loading with Addressables and loading screen MonoBehaviour"
    )
    assert_no_duplicates(result, label)
    assert_contains_all(result, ["unity-classic", "codebase-understanding", "agentmemory-codebase-recall"], label)
    assert_contains_none_of(result, sorted(DOTS_IMPL_SKILLS), label)


def test_corpus_3_local_skill_covers_addressables_no_external_discovery(route):
    """When local skill (unity-classic) covers Addressables, route must NOT go external."""
    result = route(
        agent="unity-dev", domain="Unity", intent="feature",
        task_text="Addressables handle scene load"
    )
    # External discovery would add skills not in the registry; check result is subset of registry
    registry = json.loads(REGISTRY_PATH.read_text())
    known_names = {e["name"] for e in registry["skills"]}
    unknown = [s for s in result if s not in known_names]
    assert not unknown, (
        f"case-3: route returned skills not in local registry (external discovery triggered?): {unknown}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Case 4: Unused asset cleanup (editor tooling)
# Agent: data-tool | Domain: Unity | Intent: feature
# ─────────────────────────────────────────────────────────────────────────────

def test_corpus_4_unused_asset_cleanup(route):
    """
    data-tool tier-0 = [data-tool, editor-data-tools, codebase-understanding, agentmemory-codebase-recall].
    data-tool is in NO_DOTS_ROLES — DOTS guard fires hard.
    unity-classic roles=[unity-dev, bug-investigation] — data-tool cannot receive it.
    """
    label = "case-4: unused asset cleanup"
    result = route(
        agent="data-tool",
        domain="Unity",
        intent="feature",
        task_text="build a validator tool to find and report unused assets in the project"
    )
    assert_no_duplicates(result, label)
    assert_contains_all(result, [
        "data-tool",
        "editor-data-tools",
        "codebase-understanding",
        "agentmemory-codebase-recall",
    ], label)
    assert_contains_none_of(result, sorted(DOTS_IMPL_SKILLS) + ["unity-classic"], label)


# ─────────────────────────────────────────────────────────────────────────────
# Case 5: Editor window creation
# Agent: data-tool | Domain: Unity | Intent: feature
# ─────────────────────────────────────────────────────────────────────────────

def test_corpus_5_editor_window_creation(route):
    """
    'editor' keyword in task hits editor-data-tools (already tier-0).
    Selection reason: data-tool tier-0 primaries + 'editor' keyword confirming tier-2 (redundant).
    Priority resolution: tier-0 (1000+85) beats tier-2 (0+85). Result same either way.
    """
    label = "case-5: editor window creation"
    result = route(
        agent="data-tool",
        domain="Unity",
        intent="feature",
        task_text="create a custom EditorWindow for authoring backpack item data editor tooling"
    )
    assert_no_duplicates(result, label)
    assert "editor-data-tools" in result, f"{label}: editor-data-tools must be selected; got {result}"
    assert "data-tool" in result, f"{label}: data-tool must be selected; got {result}"
    assert_contains_none_of(result, sorted(DOTS_IMPL_SKILLS), label)


# ─────────────────────────────────────────────────────────────────────────────
# Case 6: Cloud Code endpoint (no dedicated local skill)
# Agent: unity-dev | Domain: Unity | Intent: feature
# ─────────────────────────────────────────────────────────────────────────────

def test_corpus_6_cloud_code_endpoint(route):
    """
    'Cloud Code' has no keyword match in local registry.
    Routing falls back to tier-0 primaries only (unity-classic, unity-foundation).
    External skill discovery NOT triggered — registry is the sole routing source.
    Result: same primaries as any generic Unity feature task.
    """
    label = "case-6: Cloud Code endpoint"
    result = route(
        agent="unity-dev",
        domain="Unity",
        intent="feature",
        task_text="implement a Cloud Code endpoint for player progression sync"
    )
    assert_no_duplicates(result, label)
    # Should still get unity-classic (tier-0 primary) even without keyword match
    assert "unity-classic" in result, f"{label}: unity-classic must be in result; got {result}"
    assert_contains_none_of(result, sorted(DOTS_IMPL_SKILLS), label)

    # KEY assertion: no unknown skills (= no external discovery triggered)
    registry = json.loads(REGISTRY_PATH.read_text())
    known_names = {e["name"] for e in registry["skills"]}
    unknown = [s for s in result if s not in known_names]
    assert not unknown, (
        f"{label}: external discovery triggered for unrecognized Cloud Code task: {unknown}"
    )


def test_corpus_6_unmatched_task_keyword_returns_tier0_only(route):
    """Task with no keyword matches returns ONLY tier-0 primaries (no tier-2 additions)."""
    result_with_kw = route(
        agent="unity-dev", domain="Unity", intent="feature",
        task_text="implement a Cloud Code endpoint for player progression sync"
    )
    result_no_kw = route(
        agent="unity-dev", domain="Unity", intent="feature",
        task_text="XXXXXXXXXXXXXXX"  # guaranteed no keyword match
    )
    # Both should return the same tier-0 set (no keyword enrichment)
    assert set(result_with_kw) == set(result_no_kw), (
        f"case-6: Cloud Code task adds unexpected skills vs no-match task.\n"
        f"  Cloud Code result: {sorted(result_with_kw)}\n"
        f"  No-match result:   {sorted(result_no_kw)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Case 7: Addressables loading issue (bug investigation)
# Agent: bug-investigation | Domain: Unity | Intent: bug
# ─────────────────────────────────────────────────────────────────────────────

def test_corpus_7_addressables_loading_issue(route):
    """
    bug-investigation + Unity domain → INVESTIGATION_DOMAIN_EXTRAS["Unity"] = [unity-classic].
    'Addressables' keyword in unity-classic matches tier-2 (already present via tier-1).
    Selection: investigation (tier-0) + unity-classic (tier-1 domain extra) + navigation skills.
    Priority: tier-1 (500+100) beats tier-2 (0+100). Domain extras load correctly.
    """
    label = "case-7: Addressables loading issue"
    result = route(
        agent="bug-investigation",
        domain="Unity",
        intent="bug",
        task_text="debug Addressables load failure handle not released after scene unload"
    )
    assert_no_duplicates(result, label)
    assert_contains_all(result, [
        "investigation",
        "unity-classic",         # domain extra for Unity bug-investigation
        "codebase-understanding",
        "agentmemory-codebase-recall",
    ], label)
    assert_contains_none_of(result, sorted(DOTS_IMPL_SKILLS), label)


# ─────────────────────────────────────────────────────────────────────────────
# Case 8: Unity Test Framework task
# Agent: tester | Domain: Any | Intent: bug (regression)
# ─────────────────────────────────────────────────────────────────────────────

def test_corpus_8_unity_test_framework(route):
    """
    tester tier-0 = [tester, qa-validation, verifier, codebase-understanding, agentmemory-codebase-recall].
    tester is in NO_DOTS_ROLES — hard guard. Minimum skill set: tester + qa-validation.
    'test' keyword hits tester tier-2 (already tier-0; no double-add).
    """
    label = "case-8: Unity Test Framework"
    result = route(
        agent="tester",
        domain="Any",
        intent="bug",
        task_text="write regression tests using Unity Test Framework for the spawn system"
    )
    assert_no_duplicates(result, label)
    assert_contains_all(result, [
        "tester",
        "qa-validation",
        "codebase-understanding",
        "agentmemory-codebase-recall",
    ], label)
    assert_contains_none_of(result, sorted(DOTS_IMPL_SKILLS), label)


def test_corpus_8_minimum_test_skill_set(route):
    """Both tester AND qa-validation must always be present for tester role."""
    result = route(agent="tester", domain="Any", intent="feature", task_text="validate feature")
    assert "tester" in result, "tester skill must always be present for tester role"
    assert "qa-validation" in result, "qa-validation must always be present for tester role"


# ─────────────────────────────────────────────────────────────────────────────
# Case 9: Netcode for Entities (DOTS networking)
# Agent: unity-dots-dev | Domain: DOTS | Intent: feature
# ─────────────────────────────────────────────────────────────────────────────

def test_corpus_9_netcode_for_entities(route):
    """
    Netcode for Entities is ECS-native → unity-dots-dev is the correct agent.
    No dedicated 'netcode-dots' skill in registry → falls back to DOTS primaries.
    'Entities' keyword matches unity-dots-best-practices tier-2 (already tier-0).
    DOTS guard ensures unity-classic never appears.
    """
    label = "case-9: Netcode for Entities"
    result = route(
        agent="unity-dots-dev",
        domain="DOTS",
        intent="feature",
        task_text="implement Netcode for Entities ghost sync for player health ISystem Entities"
    )
    assert_no_duplicates(result, label)
    assert_contains_all(result, [
        "unity-dots-best-practices",
        "codebase-understanding",
        "agentmemory-codebase-recall",
    ], label)
    assert_contains_none_of(result, ["unity-classic", "unity-foundation"], label)


def test_corpus_9_dots_lane_selected_for_entities_netcode(route):
    """unity-dots-dev must receive ≥1 DOTS-only skill for Netcode for Entities task."""
    result = route(
        agent="unity-dots-dev", domain="DOTS", intent="feature",
        task_text="Netcode for Entities ghost synchronization ISystem"
    )
    dots_present = DOTS_IMPL_SKILLS & set(result)
    assert len(dots_present) >= 1, (
        f"case-9: expected ≥1 DOTS skill for Entities netcode task; got {sorted(dots_present)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Case 10: Netcode for GameObjects (Unity Classic networking)
# Agent: unity-dev | Domain: Unity | Intent: feature
# ─────────────────────────────────────────────────────────────────────────────

def test_corpus_10_netcode_for_gameobjects(route):
    """
    NGO is MonoBehaviour-based → unity-dev + Unity domain.
    'MonoBehaviour' keyword hits unity-classic (already tier-0). No DOTS skills.
    Key distinction from case 9: same task domain → different agent + different skills.
    """
    label = "case-10: Netcode for GameObjects"
    result = route(
        agent="unity-dev",
        domain="Unity",
        intent="feature",
        task_text="add multiplayer support using Netcode for GameObjects NetworkVariable MonoBehaviour"
    )
    assert_no_duplicates(result, label)
    assert "unity-classic" in result, f"{label}: unity-classic must be selected; got {result}"
    assert_contains_none_of(result, sorted(DOTS_IMPL_SKILLS), label)


def test_corpus_10_ngo_vs_nfe_different_skills(route):
    """Netcode for GameObjects (unity-dev) and Netcode for Entities (unity-dots-dev)
    must produce disjoint implementation skill sets."""
    ngo_skills = set(route(
        agent="unity-dev", domain="Unity", intent="feature",
        task_text="Netcode for GameObjects NetworkVariable MonoBehaviour multiplayer"
    ))
    nfe_skills = set(route(
        agent="unity-dots-dev", domain="DOTS", intent="feature",
        task_text="Netcode for Entities ghost sync ISystem Entities"
    ))
    # NGO must have unity-classic; NFE must not
    assert "unity-classic" in ngo_skills, "NGO routing must include unity-classic"
    assert "unity-classic" not in nfe_skills, "NFE routing must NOT include unity-classic"
    # NFE must have DOTS skills; NGO must not
    nfe_dots = DOTS_IMPL_SKILLS & nfe_skills
    ngo_dots = DOTS_IMPL_SKILLS & ngo_skills
    assert nfe_dots, f"NFE routing must include DOTS skills; got none in {sorted(nfe_skills)}"
    assert not ngo_dots, f"NGO routing must have zero DOTS skills; got {sorted(ngo_dots)}"


# ─────────────────────────────────────────────────────────────────────────────
# Case 11: Generic C# task — ZERO Unity implementation skills
# Agent: refactor-agent | Domain: Any | Intent: refactor
# ─────────────────────────────────────────────────────────────────────────────

def test_corpus_11_generic_csharp_zero_unity_skills(route):
    """
    refactor-agent tier-0: [codebase-understanding, ownership-partitioning, agentmemory-codebase-recall]
    unity-classic roles=[unity-dev, bug-investigation] → UNREACHABLE by refactor-agent.
    Task text has zero Unity keywords → no tier-2 additions.
    RESULT: ZERO Unity implementation skills (unity-classic, unity-foundation, all DOTS).
    This is the canonical 'generic task' test.
    """
    label = "case-11: generic C# task"
    result = route(
        agent="refactor-agent",
        domain="Any",
        intent="refactor",
        task_text="refactor a generic C# utility class to use interface segregation principle"
    )
    assert_no_duplicates(result, label)
    assert_contains_all(result, [
        "codebase-understanding",
        "agentmemory-codebase-recall",
        "ownership-partitioning",  # refactor intent + OWNERSHIP_ROLES includes refactor-agent
    ], label)
    assert_contains_none_of(result, sorted(ALL_UNITY_SKILLS), label)


def test_corpus_11_system_mapper_also_zero_unity_skills(route):
    """system-mapper role also returns ZERO Unity implementation skills."""
    result = route(
        agent="system-mapper",
        domain="Any",
        intent="explore",
        task_text="map all C# classes in the project for documentation"
    )
    unity_leaked = ALL_UNITY_SKILLS & set(result)
    assert not unity_leaked, (
        f"case-11 (system-mapper): Unity implementation skills leaked: {sorted(unity_leaked)}; "
        f"got {result}"
    )


def test_corpus_11_no_unity_skills_when_no_unity_keywords_in_task(route):
    """For any non-Unity role, zero Unity keywords → zero Unity implementation skills loaded."""
    for agent in ("refactor-agent", "system-mapper"):
        result = route(
            agent=agent, domain="Any", intent="feature",
            task_text="improve performance of generic data structure lookup algorithm"
        )
        unity_leaked = ALL_UNITY_SKILLS & set(result)
        assert not unity_leaked, (
            f"case-11 ({agent}): Unity skills loaded for generic task: {sorted(unity_leaked)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Case 12: Documentation-only task — ZERO implementation skills
# Agent: system-mapper | Domain: Any | Intent: explore
# ─────────────────────────────────────────────────────────────────────────────

def test_corpus_12_documentation_only_task(route):
    """
    system-mapper tier-0: [codebase-understanding, agentmemory-codebase-recall]
    explore intent adds no extras. No domain extras (only bug-investigation gets those).
    RESULT: navigation skills only. Zero implementation skills of any kind.
    """
    label = "case-12: documentation-only task"
    result = route(
        agent="system-mapper",
        domain="Any",
        intent="explore",
        task_text="map and document the existing ECS system architecture"
    )
    assert_no_duplicates(result, label)
    assert_contains_all(result, [
        "codebase-understanding",
        "agentmemory-codebase-recall",
    ], label)
    assert_contains_none_of(result, sorted(ALL_UNITY_SKILLS) + ["triage"], label)


def test_corpus_12_zero_implementation_skills_for_explore_intent(route):
    """explore intent must load navigation skills only — no implementation extras."""
    result = route(
        agent="system-mapper", domain="Any", intent="explore",
        task_text="document the scene management architecture"
    )
    impl_skills = (ALL_UNITY_SKILLS | {"investigation", "ownership-partitioning", "data-tool",
                                        "editor-data-tools"}) & set(result)
    assert not impl_skills, (
        f"case-12: implementation skills leaked for explore/doc task: {sorted(impl_skills)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cross-case invariants
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("agent,domain,intent,task_text", [
    ("unity-dots-dev", "DOTS",  "performance", "ISystem Burst NativeArray optimize"),
    ("unity-dev",      "Unity", "feature",     "MonoBehaviour UI Canvas"),
    ("data-tool",      "Unity", "feature",     "editor validator tool"),
    ("tester",         "Any",   "bug",         "regression test Unity"),
    ("refactor-agent", "Any",   "refactor",    "generic C# refactor"),
    ("system-mapper",  "Any",   "explore",     "map codebase architecture"),
    ("bug-investigation", "Unity", "bug",      "debug Addressables load"),
])
def test_corpus_no_duplicates_all_cases(route, agent, domain, intent, task_text):
    """No case must ever return duplicate skill names."""
    result = route(agent=agent, domain=domain, intent=intent, task_text=task_text)
    assert_no_duplicates(result, f"{agent}/{domain}/{intent}")


@pytest.mark.parametrize("agent,domain,intent,task_text", [
    ("unity-dots-dev", "DOTS",  "performance", "ISystem Burst NativeArray optimize"),
    ("unity-dev",      "Unity", "feature",     "MonoBehaviour UI Canvas"),
    ("data-tool",      "Unity", "feature",     "editor validator tool"),
    ("tester",         "Any",   "bug",         "regression test"),
    ("refactor-agent", "Any",   "refactor",    "generic C# refactor"),
    ("system-mapper",  "Any",   "explore",     "map codebase"),
])
def test_corpus_skill_cap_respected_all_cases(route, agent, domain, intent, task_text):
    """All cases must respect max_total_skills cap."""
    from conftest import REGISTRY_PATH as _rp
    cap = json.loads(_rp.read_text()).get("max_total_skills", 7)
    result = route(agent=agent, domain=domain, intent=intent, task_text=task_text)
    assert len(result) <= cap, (
        f"{agent}/{domain}/{intent}: {len(result)} skills exceeds cap {cap}; got {result}"
    )


@pytest.mark.parametrize("agent,domain,intent,task_text", [
    ("unity-dots-dev", "DOTS",  "feature", "ISystem ECS implement"),
    ("unity-dev",      "Unity", "feature", "MonoBehaviour implement"),
    ("architect",      "Any",   "feature", "design system"),
])
def test_corpus_always_keep_skills_present_all_cases(route, agent, domain, intent, task_text):
    """agentmemory-codebase-recall + codebase-understanding must always be present (code-reading roles)."""
    result = route(agent=agent, domain=domain, intent=intent, task_text=task_text)
    assert "agentmemory-codebase-recall" in result, (
        f"{agent}: agentmemory-codebase-recall missing; got {result}"
    )
    assert "codebase-understanding" in result, (
        f"{agent}: codebase-understanding missing; got {result}"
    )
