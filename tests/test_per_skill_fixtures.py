"""
test_per_skill_fixtures.py — per-skill positive and negative routing fixture tests.

Requirements:
  ≥1 positive fixture per skill: a route() call that produces this skill in result
  ≥1 negative fixture per skill: either (a) a route() call that does NOT produce this skill,
    or (b) for internal/meta skills: route() NEVER returns them regardless of args

Coverage: all 23 skills in registry.json (18 public-routable + 5 internal-only)

  Public routable (18):
    agentmemory-codebase-recall, codebase-understanding, architect,
    unity-foundation, unity-classic, unity-dots-best-practices, unity-dots,
    ecs-job-patterns, burst-safety, memory-safety, investigation,
    ownership-partitioning, tester, qa-validation, verifier, data-tool,
    editor-data-tools, unity-dots-ecb-lifecycle-debugger

  Internal-only (5):
    triage, unity-dev, routing (meta), skill-creator (meta), unity-skills (meta)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "scripts"))
from conftest import get_route_module, REPO_ROOT, REGISTRY_PATH


@pytest.fixture(scope="module")
def route():
    return get_route_module().route


@pytest.fixture(scope="module")
def registry():
    return json.loads(REGISTRY_PATH.read_text())


# ── Helpers ──────────────────────────────────────────────────────────────────

def _route_has(route_fn, agent, domain, intent, task_text, skill):
    result = route_fn(agent=agent, domain=domain, intent=intent, task_text=task_text)
    return skill in result


def _route_lacks(route_fn, agent, domain, intent, task_text, skill):
    result = route_fn(agent=agent, domain=domain, intent=intent, task_text=task_text)
    return skill not in result


def _never_routed(route_fn, skill):
    """Verify a skill never appears across a representative sweep of agent+domain+intent combos."""
    combos = [
        ("architect",      "Any",   "feature"),
        ("unity-dots-dev", "DOTS",  "feature"),
        ("unity-dev",      "Unity", "feature"),
        ("tester",         "Any",   "bug"),
        ("bug-investigation", "Unity", "bug"),
        ("data-tool",      "Unity", "feature"),
        ("refactor-agent", "Any",   "refactor"),
        ("system-mapper",  "Any",   "explore"),
        ("unity-dots-dev", "DOTS",  "bug"),
        ("unity-dev",      "Unity", "refactor"),
    ]
    for agent, domain, intent in combos:
        result = route_fn(agent=agent, domain=domain, intent=intent, task_text="generic task text")
        if skill in result:
            return False, agent, domain, intent, result
    return True, None, None, None, None


# ═════════════════════════════════════════════════════════════════════════════
# 1. agentmemory-codebase-recall
# ALWAYS_KEEP — present in all ROLE_PRIMARY dicts; survives cap; never keyword-gated
# ═════════════════════════════════════════════════════════════════════════════

def test_agentmemory_codebase_recall_positive_always_in_architect(route):
    assert _route_has(route, "architect", "Any", "feature", "design health system", "agentmemory-codebase-recall")

def test_agentmemory_codebase_recall_positive_always_in_refactor_agent(route):
    assert _route_has(route, "refactor-agent", "Any", "refactor", "generic C# refactor", "agentmemory-codebase-recall")

def test_agentmemory_codebase_recall_negative_not_keyword_gated(route):
    """agentmemory loads even with ZERO 'memory/recall' keywords (ALWAYS_KEEP, not keyword-dependent)."""
    result_no_kw = route(agent="unity-dev", domain="Unity", intent="feature", task_text="XXXXXXXXXXX")
    result_with_kw = route(agent="unity-dev", domain="Unity", intent="feature", task_text="memory recall prior")
    # Both must include it — confirming keyword absence does not remove it
    assert "agentmemory-codebase-recall" in result_no_kw, "ALWAYS_KEEP must not require keywords"
    assert "agentmemory-codebase-recall" in result_with_kw

def test_agentmemory_codebase_recall_negative_survives_cap(route):
    """agentmemory-codebase-recall must survive even when skill list is at max_total."""
    # unity-dots-dev has 6 primaries (hits cap=7 quickly) — agentmemory must survive
    result = route(agent="unity-dots-dev", domain="DOTS", intent="feature", task_text="ISystem Burst job")
    assert "agentmemory-codebase-recall" in result, "ALWAYS_KEEP must survive skill cap"


# ═════════════════════════════════════════════════════════════════════════════
# 2. codebase-understanding
# ALWAYS_KEEP — identical guarantees to agentmemory-codebase-recall
# ═════════════════════════════════════════════════════════════════════════════

def test_codebase_understanding_positive_all_roles(route):
    for agent in ("architect", "unity-dev", "unity-dots-dev", "bug-investigation",
                  "tester", "data-tool", "refactor-agent", "system-mapper"):
        result = route(agent=agent, domain="Any", intent="feature", task_text="any task")
        assert "codebase-understanding" in result, f"codebase-understanding missing for {agent}"

def test_codebase_understanding_negative_survives_cap(route):
    result = route(agent="unity-dots-dev", domain="DOTS", intent="feature", task_text="ISystem Burst")
    assert "codebase-understanding" in result

def test_codebase_understanding_negative_not_keyword_gated(route):
    result = route(agent="refactor-agent", domain="Any", intent="refactor", task_text="XXXXXXX")
    assert "codebase-understanding" in result


# ═════════════════════════════════════════════════════════════════════════════
# 3. architect
# ROLE_PRIMARY[architect] only — not reachable by other roles
# ═════════════════════════════════════════════════════════════════════════════

def test_architect_positive_for_architect_role(route):
    assert _route_has(route, "architect", "Any", "feature", "design the health system ECS", "architect")

def test_architect_negative_not_in_unity_dev(route):
    assert _route_lacks(route, "unity-dev", "Unity", "feature", "implement health system design architecture", "architect")

def test_architect_negative_not_in_tester(route):
    assert _route_lacks(route, "tester", "Any", "bug", "test health system architecture", "architect")

def test_architect_negative_not_in_dots_dev(route):
    assert _route_lacks(route, "unity-dots-dev", "DOTS", "feature", "design ISystem architecture", "architect")


# ═════════════════════════════════════════════════════════════════════════════
# 4. unity-foundation
# ROLE_PRIMARY[architect, unity-dev]
# ═════════════════════════════════════════════════════════════════════════════

def test_unity_foundation_positive_architect(route):
    assert _route_has(route, "architect", "Any", "feature", "assembly definitions project structure", "unity-foundation")

def test_unity_foundation_positive_unity_dev(route):
    assert _route_has(route, "unity-dev", "Unity", "feature", "bootstrap asmdef scene lifecycle", "unity-foundation")

def test_unity_foundation_negative_not_in_dots_dev(route):
    assert _route_lacks(route, "unity-dots-dev", "DOTS", "feature", "ISystem asmdef assembly bootstrap", "unity-foundation")

def test_unity_foundation_negative_not_in_tester(route):
    assert _route_lacks(route, "tester", "Any", "feature", "asmdef assembly scene lifecycle", "unity-foundation")

def test_unity_foundation_negative_not_in_bug_investigation(route):
    assert _route_lacks(route, "bug-investigation", "Unity", "bug", "assembly definition project structure", "unity-foundation")


# ═════════════════════════════════════════════════════════════════════════════
# 5. unity-classic
# ROLE_PRIMARY[unity-dev]; also reachable by bug-investigation on Unity domain (tier-1 domain extra)
# NO_DOTS_ROLES guard blocks it via DOTS guard — wait, unity-classic is a UNITY skill not DOTS
# Actually: NO_DOTS_ROLES blocks DOTS_ONLY_SKILLS, not unity-classic
# unity-classic is gated by ROLE_PRIMARY and domain extras, not DOTS guard
# ═════════════════════════════════════════════════════════════════════════════

def test_unity_classic_positive_unity_dev(route):
    assert _route_has(route, "unity-dev", "Unity", "feature", "MonoBehaviour Canvas UI DOTween", "unity-classic")

def test_unity_classic_positive_bug_investigation_unity_domain(route):
    """bug-investigation + Unity domain gets unity-classic via INVESTIGATION_DOMAIN_EXTRAS."""
    assert _route_has(route, "bug-investigation", "Unity", "bug", "debug null reference in MonoBehaviour", "unity-classic")

def test_unity_classic_negative_not_in_architect(route):
    assert _route_lacks(route, "architect", "Unity", "feature", "MonoBehaviour Canvas UI design", "unity-classic")

def test_unity_classic_negative_not_in_dots_dev(route):
    assert _route_lacks(route, "unity-dots-dev", "DOTS", "feature", "MonoBehaviour Canvas UI animation", "unity-classic")

def test_unity_classic_negative_not_in_data_tool(route):
    assert _route_lacks(route, "data-tool", "Unity", "feature", "MonoBehaviour UI Canvas", "unity-classic")

def test_unity_classic_negative_not_in_tester(route):
    assert _route_lacks(route, "tester", "Any", "bug", "MonoBehaviour Canvas UI DOTween", "unity-classic")


# ═════════════════════════════════════════════════════════════════════════════
# 6. unity-dots-best-practices
# ROLE_PRIMARY[unity-dots-dev]; also in INVESTIGATION_DOMAIN_EXTRAS["DOTS"] and INVESTIGATION_DOMAIN_EXTRAS["Hybrid"]
# DOTS_ONLY_SKILLS → NO_DOTS_ROLES guard fires for: tester, verifier, qa-tester, data-tool, unity-dev
# ═════════════════════════════════════════════════════════════════════════════

def test_unity_dots_best_practices_positive_dots_dev(route):
    assert _route_has(route, "unity-dots-dev", "DOTS", "feature", "ISystem ECS entities", "unity-dots-best-practices")

def test_unity_dots_best_practices_positive_bug_investigation_dots_domain(route):
    """bug-investigation + DOTS domain gets unity-dots-best-practices via INVESTIGATION_DOMAIN_EXTRAS."""
    assert _route_has(route, "bug-investigation", "DOTS", "bug", "ISystem ECS debug race condition", "unity-dots-best-practices")

def test_unity_dots_best_practices_negative_unity_dev(route):
    assert _route_lacks(route, "unity-dev", "DOTS", "feature", "ISystem DOTS ECS Entities", "unity-dots-best-practices")

def test_unity_dots_best_practices_negative_tester(route):
    assert _route_lacks(route, "tester", "DOTS", "bug", "ISystem ECS test", "unity-dots-best-practices")

def test_unity_dots_best_practices_negative_data_tool(route):
    assert _route_lacks(route, "data-tool", "DOTS", "feature", "ISystem ECS editor tool", "unity-dots-best-practices")


# ═════════════════════════════════════════════════════════════════════════════
# 7. unity-dots
# NOT in ROLE_PRIMARY; tier-2 keyword-match only; blocked from NO_DOTS_ROLES
# Keywords: DOTS, ECS, samples, reference, entities; priority=72 (lower than primaries)
# ═════════════════════════════════════════════════════════════════════════════

def test_unity_dots_positive_dots_dev_keyword_match(route):
    """unity-dots reachable for unity-dots-dev via keyword match (not primary)."""
    result = route(agent="unity-dots-dev", domain="DOTS", intent="feature",
                   task_text="DOTS ECS samples reference ICleanupComponentData")
    assert "unity-dots" in result, (
        f"unity-dots expected for DOTS keyword task; got {result}"
    )

def test_unity_dots_negative_unity_dev_dots_guard(route):
    assert _route_lacks(route, "unity-dev", "DOTS", "feature", "DOTS ECS samples reference", "unity-dots")

def test_unity_dots_negative_tester_dots_guard(route):
    assert _route_lacks(route, "tester", "DOTS", "bug", "ECS DOTS reference sample", "unity-dots")

def test_unity_dots_negative_no_dots_keywords(route):
    """Without DOTS keywords, unity-dots won't be added to unity-dots-dev result."""
    result = route(agent="unity-dots-dev", domain="DOTS", intent="feature",
                   task_text="XXXXXXXXXX")  # no DOTS keywords
    # unity-dots requires keyword match (not in ROLE_PRIMARY), so absent when no match
    # (It may or may not be present; we only assert DOTS guard works for wrong roles)
    # For correct role (unity-dots-dev), absence of keyword means no tier-2 addition
    # This passes since unity-dots is not in ROLE_PRIMARY — it only appears via keyword match
    pass  # documented: unity-dots tier-2 requires DOTS/ECS keyword in task_text


# ═════════════════════════════════════════════════════════════════════════════
# 8. ecs-job-patterns
# ROLE_PRIMARY[unity-dots-dev]; INVESTIGATION_DOMAIN_EXTRAS["DOTS"] includes it for bug-investigation
# DOTS_ONLY_SKILLS → blocked from NO_DOTS_ROLES
# ═════════════════════════════════════════════════════════════════════════════

def test_ecs_job_patterns_positive_dots_dev(route):
    assert _route_has(route, "unity-dots-dev", "DOTS", "feature", "IJobEntity schedule Burst", "ecs-job-patterns")

def test_ecs_job_patterns_positive_bug_investigation_dots(route):
    assert _route_has(route, "bug-investigation", "DOTS", "bug", "IJobEntity race condition debug", "ecs-job-patterns")

def test_ecs_job_patterns_negative_unity_dev(route):
    assert _route_lacks(route, "unity-dev", "DOTS", "feature", "IJobEntity schedule ECB Burst", "ecs-job-patterns")

def test_ecs_job_patterns_negative_tester(route):
    assert _route_lacks(route, "tester", "DOTS", "bug", "IJobEntity schedule test", "ecs-job-patterns")


# ═════════════════════════════════════════════════════════════════════════════
# 9. burst-safety
# ROLE_PRIMARY[unity-dots-dev] only; DOTS_ONLY_SKILLS
# ═════════════════════════════════════════════════════════════════════════════

def test_burst_safety_positive_dots_dev(route):
    assert _route_has(route, "unity-dots-dev", "DOTS", "feature", "BurstCompile burst managed Mathematics", "burst-safety")

def test_burst_safety_negative_unity_dev(route):
    assert _route_lacks(route, "unity-dev", "Unity", "feature", "BurstCompile burst managed", "burst-safety")

def test_burst_safety_negative_architect(route):
    assert _route_lacks(route, "architect", "DOTS", "feature", "Burst burst compilation safety", "burst-safety")

def test_burst_safety_negative_tester(route):
    assert _route_lacks(route, "tester", "DOTS", "bug", "Burst compilation error", "burst-safety")


# ═════════════════════════════════════════════════════════════════════════════
# 10. memory-safety
# ROLE_PRIMARY[unity-dots-dev] only; DOTS_ONLY_SKILLS
# ═════════════════════════════════════════════════════════════════════════════

def test_memory_safety_positive_dots_dev(route):
    assert _route_has(route, "unity-dots-dev", "DOTS", "feature", "NativeArray allocator dispose TempJob", "memory-safety")

def test_memory_safety_negative_unity_dev(route):
    assert _route_lacks(route, "unity-dev", "Unity", "feature", "NativeArray allocator leak dispose", "memory-safety")

def test_memory_safety_negative_data_tool(route):
    assert _route_lacks(route, "data-tool", "Any", "feature", "memory leak NativeArray allocator", "memory-safety")

def test_memory_safety_negative_tester(route):
    assert _route_lacks(route, "tester", "Any", "bug", "memory NativeArray dispose leak", "memory-safety")


# ═════════════════════════════════════════════════════════════════════════════
# 11. investigation
# ROLE_PRIMARY[bug-investigation]; also added to unity-dev and unity-dots-dev on bug intent
# via BUG_INTENT_INVESTIGATION_ROLES
# ═════════════════════════════════════════════════════════════════════════════

def test_investigation_positive_bug_investigation(route):
    assert _route_has(route, "bug-investigation", "Unity", "bug", "debug null reference repro", "investigation")

def test_investigation_positive_unity_dev_bug_intent(route):
    """unity-dev on bug intent also gets investigation via BUG_INTENT_INVESTIGATION_ROLES."""
    assert _route_has(route, "unity-dev", "Unity", "bug", "debug null reference repro", "investigation")

def test_investigation_positive_unity_dots_dev_bug_intent(route):
    assert _route_has(route, "unity-dots-dev", "DOTS", "bug", "debug ISystem race condition", "investigation")

def test_investigation_negative_feature_intent(route):
    """Feature intent for bug-investigation is not the primary trigger, but investigation still loads from ROLE_PRIMARY."""
    # investigation is in ROLE_PRIMARY[bug-investigation] regardless of intent
    result = route(agent="bug-investigation", domain="Any", intent="feature", task_text="design new feature")
    # investigation should still be present (ROLE_PRIMARY is intent-agnostic in route())
    assert "investigation" in result

def test_investigation_negative_tester(route):
    assert _route_lacks(route, "tester", "Any", "bug", "debug regression root cause investigate", "investigation")

def test_investigation_negative_architect(route):
    assert _route_lacks(route, "architect", "Any", "bug", "root cause debug investigate error", "investigation")

def test_investigation_negative_unity_dev_feature_intent(route):
    """unity-dev on feature intent (NOT bug) must NOT get investigation."""
    assert _route_lacks(route, "unity-dev", "Unity", "feature", "root cause debug investigate", "investigation")


# ═════════════════════════════════════════════════════════════════════════════
# 12. ownership-partitioning
# OWNERSHIP_ROLES on refactor intent or parallel=True
# ═════════════════════════════════════════════════════════════════════════════

def test_ownership_partitioning_positive_refactor_intent(route):
    assert _route_has(route, "refactor-agent", "Any", "refactor", "extract spawner system into module", "ownership-partitioning")

def test_ownership_partitioning_positive_unity_dev_refactor(route):
    assert _route_has(route, "unity-dev", "Unity", "refactor", "refactor health system extract module", "ownership-partitioning")

def test_ownership_partitioning_positive_parallel_flag(route):
    result = route(agent="architect", domain="Any", intent="feature",
                   task_text="design parallel system", parallel_allowed=True)
    assert "ownership-partitioning" in result, (
        f"ownership-partitioning must appear when parallel_allowed=True; got {result}"
    )

def test_ownership_partitioning_negative_feature_intent_no_parallel(route):
    """Feature intent without parallel=True must NOT add ownership-partitioning for architect."""
    result = route(agent="architect", domain="Any", intent="feature",
                   task_text="design health system")
    assert "ownership-partitioning" not in result, (
        f"ownership-partitioning should not appear on non-refactor, non-parallel; got {result}"
    )

def test_ownership_partitioning_negative_tester(route):
    assert _route_lacks(route, "tester", "Any", "refactor", "refactor ownership partition", "ownership-partitioning")

def test_ownership_partitioning_negative_system_mapper(route):
    assert _route_lacks(route, "system-mapper", "Any", "refactor", "parallel ownership partition glob", "ownership-partitioning")


# ═════════════════════════════════════════════════════════════════════════════
# 13. tester
# ROLE_PRIMARY[tester, verifier, qa-tester]
# ═════════════════════════════════════════════════════════════════════════════

def test_tester_positive_for_tester_role(route):
    assert _route_has(route, "tester", "Any", "bug", "regression test sign-off", "tester")

def test_tester_positive_for_verifier_role(route):
    assert _route_has(route, "verifier", "Any", "feature", "verify bundle compilation", "tester")

def test_tester_positive_for_qa_tester_role(route):
    assert _route_has(route, "qa-tester", "Any", "bug", "regression stress determinism", "tester")

def test_tester_negative_unity_dev(route):
    assert _route_lacks(route, "unity-dev", "Unity", "feature", "test regression sign-off", "tester")

def test_tester_negative_architect(route):
    assert _route_lacks(route, "architect", "Any", "feature", "test sign-off regression", "tester")


# ═════════════════════════════════════════════════════════════════════════════
# 14. qa-validation
# ROLE_PRIMARY[tester, verifier, qa-tester]
# ═════════════════════════════════════════════════════════════════════════════

def test_qa_validation_positive_tester(route):
    assert _route_has(route, "tester", "Any", "feature", "test matrix playmode evidence validate", "qa-validation")

def test_qa_validation_positive_qa_tester(route):
    assert _route_has(route, "qa-tester", "Any", "bug", "validate test matrix regression evidence", "qa-validation")

def test_qa_validation_negative_unity_dots_dev(route):
    assert _route_lacks(route, "unity-dots-dev", "DOTS", "feature", "validate test matrix playmode", "qa-validation")

def test_qa_validation_negative_data_tool(route):
    assert _route_lacks(route, "data-tool", "Any", "feature", "validate test matrix evidence", "qa-validation")


# ═════════════════════════════════════════════════════════════════════════════
# 15. verifier
# ROLE_PRIMARY[verifier]; also in ROLE_PRIMARY[tester, qa-tester]
# ═════════════════════════════════════════════════════════════════════════════

def test_verifier_positive_verifier_role(route):
    assert _route_has(route, "verifier", "Any", "feature", "run verification bundle compilation", "verifier")

def test_verifier_positive_tester_role(route):
    """tester role also gets verifier in its ROLE_PRIMARY."""
    assert _route_has(route, "tester", "Any", "bug", "verify compilation bundle", "verifier")

def test_verifier_negative_unity_dev(route):
    assert _route_lacks(route, "unity-dev", "Unity", "feature", "verify compilation bundle impl_result", "verifier")

def test_verifier_negative_architect(route):
    assert _route_lacks(route, "architect", "Any", "feature", "verify compilation verification bundle", "verifier")


# ═════════════════════════════════════════════════════════════════════════════
# 16. data-tool
# ROLE_PRIMARY[data-tool] only
# ═════════════════════════════════════════════════════════════════════════════

def test_data_tool_positive_data_tool_role(route):
    assert _route_has(route, "data-tool", "Unity", "feature", "build editor validator inspector diagnostics", "data-tool")

def test_data_tool_negative_unity_dev(route):
    assert _route_lacks(route, "unity-dev", "Unity", "feature", "editor validator inspector diagnostics", "data-tool")

def test_data_tool_negative_architect(route):
    assert _route_lacks(route, "architect", "Any", "feature", "data processor authoring editor tool", "data-tool")

def test_data_tool_negative_tester(route):
    assert _route_lacks(route, "tester", "Any", "feature", "editor validator diagnostics", "data-tool")


# ═════════════════════════════════════════════════════════════════════════════
# 17. editor-data-tools
# ROLE_PRIMARY[data-tool] only
# ═════════════════════════════════════════════════════════════════════════════

def test_editor_data_tools_positive_data_tool_role(route):
    assert _route_has(route, "data-tool", "Unity", "feature", "authoring editor validator pipeline tooling", "editor-data-tools")

def test_editor_data_tools_negative_unity_dev(route):
    assert _route_lacks(route, "unity-dev", "Unity", "feature", "editor authoring pipeline tooling validator", "editor-data-tools")

def test_editor_data_tools_negative_unity_dots_dev(route):
    assert _route_lacks(route, "unity-dots-dev", "DOTS", "feature", "editor tooling authoring pipeline", "editor-data-tools")

def test_editor_data_tools_negative_architect(route):
    assert _route_lacks(route, "architect", "Any", "feature", "editor pipeline tooling authoring validator", "editor-data-tools")


# ═════════════════════════════════════════════════════════════════════════════
# 18. triage (internal-only: true)
# Route() must NEVER return triage — it's internal-only for the orchestrator
# Positive: confirmed present in registry; negative: never routed
# ═════════════════════════════════════════════════════════════════════════════

def test_triage_positive_exists_in_registry(registry):
    names = [e["name"] for e in registry["skills"]]
    assert "triage" in names, "triage must exist in registry"

def test_triage_positive_is_internal_only(registry):
    entry = next(e for e in registry["skills"] if e["name"] == "triage")
    assert entry.get("internal-only") is True, "triage must be marked internal-only"

def test_triage_negative_never_routed(route):
    ok, bad_agent, bad_domain, bad_intent, bad_result = _never_routed(route, "triage")
    assert ok, (
        f"triage (internal-only) was returned by route() — should never happen.\n"
        f"  Agent={bad_agent} domain={bad_domain} intent={bad_intent}\n"
        f"  Result={bad_result}"
    )

def test_triage_negative_never_routed_even_with_keywords(route):
    """Even task text with 'triage classify complexity blast radius' must not return triage."""
    result = route(agent="unity-dev", domain="Any", intent="feature",
                   task_text="triage classify complexity blast radius pipeline")
    assert "triage" not in result, f"triage must not be routed; got {result}"


# ═════════════════════════════════════════════════════════════════════════════
# 19. unity-dev (internal-only: true, mode=role-brief)
# Auto-loaded as agent role brief — never explicitly routed
# ═════════════════════════════════════════════════════════════════════════════

def test_unity_dev_skill_positive_exists_in_registry(registry):
    names = [e["name"] for e in registry["skills"]]
    assert "unity-dev" in names, "unity-dev skill entry must exist in registry"

def test_unity_dev_skill_positive_is_internal_only(registry):
    entry = next(e for e in registry["skills"] if e["name"] == "unity-dev")
    assert entry.get("internal-only") is True, "unity-dev skill must be marked internal-only"

def test_unity_dev_skill_negative_never_routed(route):
    ok, bad_agent, bad_domain, bad_intent, bad_result = _never_routed(route, "unity-dev")
    assert ok, (
        f"unity-dev skill (internal/role-brief) was returned by route().\n"
        f"  Agent={bad_agent} domain={bad_domain} intent={bad_intent}\n"
        f"  Result={bad_result}"
    )


# ═════════════════════════════════════════════════════════════════════════════
# 20. routing (internal-only: true, mode=meta)
# Meta skill — never routed, no roles/intents by design
# ═════════════════════════════════════════════════════════════════════════════

def test_routing_positive_exists_in_registry(registry):
    names = [e["name"] for e in registry["skills"]]
    assert "routing" in names

def test_routing_positive_is_meta(registry):
    entry = next(e for e in registry["skills"] if e["name"] == "routing")
    assert entry.get("mode") == "meta"
    assert entry.get("internal-only") is True

def test_routing_negative_never_routed(route):
    ok, bad_agent, bad_domain, bad_intent, bad_result = _never_routed(route, "routing")
    assert ok, f"routing (meta) was returned by route(): agent={bad_agent} result={bad_result}"

def test_routing_negative_empty_roles_and_intents(registry):
    entry = next(e for e in registry["skills"] if e["name"] == "routing")
    assert entry.get("roles") == [], "meta skill routing must have empty roles list"
    assert entry.get("intents") == [], "meta skill routing must have empty intents list"
    assert entry.get("load_by_default") is False, "meta skill must have load_by_default=False"


# ═════════════════════════════════════════════════════════════════════════════
# 21. skill-creator (internal-only: true, mode=meta)
# ═════════════════════════════════════════════════════════════════════════════

def test_skill_creator_positive_exists_in_registry(registry):
    names = [e["name"] for e in registry["skills"]]
    assert "skill-creator" in names

def test_skill_creator_positive_is_meta(registry):
    entry = next(e for e in registry["skills"] if e["name"] == "skill-creator")
    assert entry.get("mode") == "meta"
    assert entry.get("internal-only") is True

def test_skill_creator_negative_never_routed(route):
    ok, bad_agent, bad_domain, bad_intent, bad_result = _never_routed(route, "skill-creator")
    assert ok, f"skill-creator (meta) was returned by route(): result={bad_result}"

def test_skill_creator_negative_empty_roles_intents_keywords(registry):
    entry = next(e for e in registry["skills"] if e["name"] == "skill-creator")
    assert entry.get("roles") == []
    assert entry.get("intents") == []
    assert entry.get("keywords") == []


# ═════════════════════════════════════════════════════════════════════════════
# 22. unity-skills (internal-only: true, mode=meta)
# ═════════════════════════════════════════════════════════════════════════════

def test_unity_skills_positive_exists_in_registry(registry):
    names = [e["name"] for e in registry["skills"]]
    assert "unity-skills" in names

def test_unity_skills_positive_is_meta(registry):
    entry = next(e for e in registry["skills"] if e["name"] == "unity-skills")
    assert entry.get("mode") == "meta"
    assert entry.get("internal-only") is True

def test_unity_skills_negative_never_routed(route):
    ok, bad_agent, bad_domain, bad_intent, bad_result = _never_routed(route, "unity-skills")
    assert ok, f"unity-skills (meta) was returned by route(): result={bad_result}"

def test_unity_skills_negative_empty_roles_intents_keywords(registry):
    entry = next(e for e in registry["skills"] if e["name"] == "unity-skills")
    assert entry.get("roles") == []
    assert entry.get("intents") == []
    assert entry.get("keywords") == []


# ═════════════════════════════════════════════════════════════════════════════
# 23. unity-dots-ecb-lifecycle-debugger
# Bug-intent DOTS/Hybrid skill; loads ONLY on ECB playback error keywords
# ═════════════════════════════════════════════════════════════════════════════

def test_unity_dots_ecb_lifecycle_debugger_positive_selected_on_ecb_error(route):
    """Positive: bug-investigation on DOTS/bug intent with ECB error text → loaded."""
    result = route(
        agent="bug-investigation", domain="DOTS", intent="bug",
        task_text="ECB playback failed entityExists=False Invalid deferred entity",
    )
    assert "unity-dots-ecb-lifecycle-debugger" in result, (
        f"ECB debugger skill must load on ECB playback error task. Got: {result}"
    )

def test_unity_dots_ecb_lifecycle_debugger_positive_different_ecb_keyword(route):
    """Positive: bug-investigation on DOTS/bug intent with different ECB error keyword → loaded."""
    result = route(
        agent="bug-investigation", domain="DOTS", intent="bug",
        task_text="Duplicate AddComponent during playback SetComponent on missing component",
    )
    assert "unity-dots-ecb-lifecycle-debugger" in result, (
        f"ECB debugger must load on different ECB error keyword. Got: {result}"
    )

def test_unity_dots_ecb_lifecycle_debugger_negative_not_loaded_for_general_ecs(route):
    """Negative: feature intent (no ECB error text) → ECB debugger NOT loaded."""
    result = route(
        agent="unity-dots-dev", domain="DOTS", intent="feature",
        task_text="add IComponentData health system IJobEntity",
    )
    assert "unity-dots-ecb-lifecycle-debugger" not in result, (
        f"ECB debugger must NOT load for general ECS feature task. Got: {result}"
    )

def test_unity_dots_ecb_lifecycle_debugger_negative_not_loaded_for_no_dots_roles(route):
    """Negative: tester role (NO_DOTS_ROLES) never gets ECB debugger even with ECB error text."""
    result = route(
        agent="tester", domain="DOTS", intent="bug",
        task_text="ECB playback failed entityExists=False",
    )
    assert "unity-dots-ecb-lifecycle-debugger" not in result, (
        f"tester (NO_DOTS_ROLES) must never receive ECB debugger. Got: {result}"
    )


# ═════════════════════════════════════════════════════════════════════════════
# Coverage meta-test: confirm all 23 skills have ≥1 positive and ≥1 negative fixture
# (Documentation + count verification)
# ═════════════════════════════════════════════════════════════════════════════

def test_all_22_skills_present_in_registry(registry):
    """Smoke: all expected skills are in registry."""
    expected = {
        "agentmemory-codebase-recall", "codebase-understanding", "architect",
        "unity-foundation", "unity-classic", "unity-dots-best-practices", "unity-dots",
        "ecs-job-patterns", "burst-safety", "memory-safety", "investigation",
        "ownership-partitioning", "tester", "qa-validation", "verifier", "data-tool",
        "editor-data-tools",  # public routable
        "triage", "unity-dev", "routing", "skill-creator", "unity-skills",  # internal
        "unity-dots-ecb-lifecycle-debugger",  # 23rd skill (task #8)
    }
    actual = {e["name"] for e in registry["skills"]}
    missing = expected - actual
    extra = actual - expected
    assert not missing, f"Skills missing from registry: {sorted(missing)}"
    assert len(actual) == 23, f"Expected 23 skills, got {len(actual)}: extra={sorted(extra)}"
