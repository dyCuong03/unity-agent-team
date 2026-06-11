"""
test_routing.py — per-role routing correctness tests.

Verifies that:
  - architect gets architecture/codebase skills but NOT Unity implementation skills
  - tester/verifier/qa-tester get testing + security skills
  - DOTS skills (unity-dots-best-practices, ecs-job-patterns, burst-safety,
    memory-safety, unity-dots) ONLY reach DOTS roles
  - Unity Classic skills ONLY reach classic Unity roles (not unity-dots-dev)
  - agentmemory-codebase-recall is always present for code-reading roles
  - The skill cap (max_total_skills = 7) is respected for all roles
  - Bug intent adds `investigation` skill for relevant roles
  - Refactor/parallel intent adds `ownership-partitioning` for relevant roles
  - No role receives more skills than the cap
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "scripts"))

from conftest import get_route_module, REPO_ROOT
import json

REGISTRY_PATH = REPO_ROOT / ".claude" / "skills" / "registry.json"

# Role categories (mirrors route_skills.py constants)
DOTS_ONLY_SKILLS = frozenset({
    "unity-dots-best-practices",
    "unity-dots",
    "ecs-job-patterns",
    "burst-safety",
    "memory-safety",
})
NO_DOTS_ROLES = frozenset({"tester", "verifier", "qa-tester", "data-tool", "unity-dev"})
UNITY_IMPL_SKILLS = frozenset({"unity-classic", "unity-foundation"})
CODE_READING_ROLES = frozenset({
    "architect", "unity-dots-dev", "unity-dev", "bug-investigation",
    "data-tool", "tester", "verifier", "qa-tester", "refactor-agent", "system-mapper",
})

MAX_CAP = json.loads(REGISTRY_PATH.read_text()).get("max_total_skills", 7)


@pytest.fixture(scope="module")
def route():
    return get_route_module().route


# ── Architect role ───────────────────────────────────────────────────────────

def test_architect_gets_no_unity_implementation_skills(route):
    """Architect designs; it must not load unity-classic (that is unity-dev's tool)."""
    for domain in ("Unity", "DOTS", "Hybrid", "Ambiguous"):
        result = route(agent="architect", domain=domain, intent="feature",
                       task_text="design popup inventory system")
        assert "unity-classic" not in result, (
            f"architect/{domain}: unity-classic (impl skill) must not be loaded; got {result}"
        )


def test_architect_gets_architect_skill(route):
    result = route(agent="architect", domain="Any", intent="feature", task_text="design system")
    assert "architect" in result, f"architect must receive 'architect' skill; got {result}"


def test_architect_gets_codebase_understanding(route):
    result = route(agent="architect", domain="Any", intent="feature", task_text="design system")
    assert "codebase-understanding" in result, (
        f"architect must receive 'codebase-understanding'; got {result}"
    )


# ── Tester / Verifier / QA-Tester roles ─────────────────────────────────────

@pytest.mark.parametrize("role", ["tester", "verifier", "qa-tester"])
def test_testing_roles_get_tester_skill(route, role):
    result = route(agent=role, domain="Any", intent="feature", task_text="validate feature")
    assert "tester" in result or "qa-validation" in result, (
        f"{role}: must receive tester or qa-validation skill; got {result}"
    )


@pytest.mark.parametrize("role", ["tester", "verifier", "qa-tester"])
def test_testing_roles_never_get_dots_skills(route, role):
    """Testing roles must never receive DOTS-specific skills."""
    for domain in ("DOTS", "Any", "Unity"):
        result = route(agent=role, domain=domain, intent="feature",
                       task_text="ISystem entity ECS burst job")
        leaked = DOTS_ONLY_SKILLS & set(result)
        assert not leaked, (
            f"{role}/{domain}: DOTS skills leaked to test role: {sorted(leaked)}"
        )


# ── Unity Dev role ───────────────────────────────────────────────────────────

def test_unity_dev_gets_unity_classic_on_unity_domain(route):
    result = route(agent="unity-dev", domain="Unity", intent="feature",
                   task_text="build popup UI canvas")
    assert "unity-classic" in result, (
        f"unity-dev/Unity: must get unity-classic; got {result}"
    )


def test_unity_dev_never_gets_dots_skills_any_domain(route):
    """unity-dev must never receive DOTS skills even when task mentions DOTS."""
    for domain in ("DOTS", "Unity", "Hybrid", "Ambiguous"):
        result = route(agent="unity-dev", domain=domain, intent="feature",
                       task_text="ISystem entity ECS burst job NativeArray")
        leaked = DOTS_ONLY_SKILLS & set(result)
        assert not leaked, (
            f"unity-dev/{domain}: DOTS skills leaked: {sorted(leaked)}; got {result}"
        )


# ── Unity DOTS Dev role ──────────────────────────────────────────────────────

def test_unity_dots_dev_gets_dots_best_practices(route):
    result = route(agent="unity-dots-dev", domain="DOTS", intent="feature",
                   task_text="implement enemy AI system with ISystem burst")
    assert "unity-dots-best-practices" in result, (
        f"unity-dots-dev/DOTS: must get unity-dots-best-practices; got {result}"
    )


def test_unity_dots_dev_gets_at_least_one_dots_extra(route):
    result = route(agent="unity-dots-dev", domain="DOTS", intent="feature",
                   task_text="implement movement system IJobEntity")
    dots_present = DOTS_ONLY_SKILLS & set(result)
    assert len(dots_present) >= 1, (
        f"unity-dots-dev/DOTS: must have at least one DOTS extra skill; got {result}"
    )


def test_unity_dots_dev_never_gets_unity_classic(route):
    """DOTS dev lane must not receive unity-classic — that belongs to the Unity lane."""
    for domain in ("DOTS", "Unity", "Hybrid"):
        result = route(agent="unity-dots-dev", domain=domain, intent="feature",
                       task_text="implement feature")
        assert "unity-classic" not in result, (
            f"unity-dots-dev/{domain}: unity-classic must not appear; got {result}"
        )


# ── agentmemory-codebase-recall guard ────────────────────────────────────────

@pytest.mark.parametrize("role", sorted(CODE_READING_ROLES))
def test_code_reading_roles_always_get_agentmemory_recall(route, role):
    result = route(agent=role, domain="Any", intent="feature", task_text="investigate code")
    assert "agentmemory-codebase-recall" in result, (
        f"{role}: agentmemory-codebase-recall must always be present; got {result}"
    )


# ── DOTS skills don't leak to any no-DOTS role ───────────────────────────────

@pytest.mark.parametrize("role", sorted(NO_DOTS_ROLES))
def test_no_dots_roles_never_get_dots_skills(route, role):
    """DOTS skills must never reach these roles regardless of domain or task keywords."""
    for domain in ("DOTS", "Unity", "Any", "Hybrid"):
        result = route(agent=role, domain=domain, intent="feature",
                       task_text="ISystem ECS entity burst NativeArray job")
        leaked = DOTS_ONLY_SKILLS & set(result)
        assert not leaked, (
            f"{role}/{domain}: DOTS skills leaked: {sorted(leaked)}; result={result}"
        )


# ── Skill cap respected ───────────────────────────────────────────────────────

all_roles = [
    "architect", "unity-dots-dev", "unity-dev", "tester", "verifier",
    "qa-tester", "bug-investigation", "data-tool", "refactor-agent", "system-mapper",
]

@pytest.mark.parametrize("role", all_roles)
def test_skill_cap_respected_for_all_roles(route, role):
    result = route(agent=role, domain="DOTS", intent="feature",
                   task_text="ISystem entity ECS burst job memory")
    assert len(result) <= MAX_CAP, (
        f"{role}: skill count {len(result)} exceeds cap {MAX_CAP}; got {result}"
    )


# ── Bug intent must-keep skills ───────────────────────────────────────────────

@pytest.mark.parametrize("role", ["unity-dev", "unity-dots-dev"])
def test_bug_intent_adds_investigation_skill(route, role):
    result = route(agent=role, domain="DOTS", intent="bug",
                   task_text="animation not playing ISystem")
    assert "investigation" in result, (
        f"{role}/bug: 'investigation' must be present on bug intent; got {result}"
    )


# ── Refactor/parallel intent must-keep skills ────────────────────────────────

@pytest.mark.parametrize("role", ["architect", "unity-dev", "unity-dots-dev", "refactor-agent"])
def test_refactor_intent_adds_ownership_partitioning(route, role):
    result = route(agent=role, domain="Any", intent="refactor",
                   task_text="extract zone spawner into shared system",
                   parallel_allowed=False)
    assert "ownership-partitioning" in result, (
        f"{role}/refactor: 'ownership-partitioning' must be present; got {result}"
    )


# ── Hybrid domain routing ─────────────────────────────────────────────────────

def test_bug_investigation_hybrid_domain_loads_both_stacks(route):
    """bug-investigation on Hybrid domain should get both Unity Classic and DOTS skills."""
    result = route(agent="bug-investigation", domain="Hybrid", intent="bug",
                   task_text="health bar binding not updating MonoBehaviour ECS")
    has_unity = "unity-classic" in result
    has_dots = "unity-dots-best-practices" in result or "ecs-job-patterns" in result
    assert has_unity, f"Hybrid bug-investigation: should include unity-classic; got {result}"
    assert has_dots, f"Hybrid bug-investigation: should include a DOTS skill; got {result}"


# ── data-tool role ────────────────────────────────────────────────────────────

def test_data_tool_never_gets_dots_skills_even_on_dots_domain(route):
    result = route(agent="data-tool", domain="DOTS", intent="feature",
                   task_text="build inspector for ISystem entities ECS burst")
    leaked = DOTS_ONLY_SKILLS & set(result)
    assert not leaked, (
        f"data-tool/DOTS: DOTS skills must not reach data-tool; leaked={sorted(leaked)}"
    )


def test_data_tool_gets_own_skills(route):
    result = route(agent="data-tool", domain="Any", intent="feature",
                   task_text="build editor validator tool")
    assert "data-tool" in result or "editor-data-tools" in result, (
        f"data-tool must receive data-tool or editor-data-tools skill; got {result}"
    )
