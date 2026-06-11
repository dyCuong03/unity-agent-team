#!/usr/bin/env python3
"""
route_skills.py — the /team skill router (Skill Registry -> Skill Router).

Selects a curated, role-correct skill subset for one agent based on:
    role primary skills
  + domain extra skills
  + intent extra skills
  + keyword-matched skills (from registry)
  + agentmemory hint nudges

Hard rules:
  - Never load all skills. Capped at registry.max_total_skills (default 7).
  - Role / domain / intent priority is STRONGER than keyword matching.
  - DOTS extras attach to DOTS lanes only. tester/verifier/qa-tester/data-tool/
    unity-dev never receive DOTS skills.
  - agentmemory-codebase-recall + codebase-understanding are must-keep for
    code-reading roles (never trimmed by the cap).
  - External skill discovery runs ONLY when tier0+tier1+tier2 yield < 2 skills.
  - Agent MUST read each skill's SKILL.md before first use (enforced in prompt output).

Pure + importable (orchestrate.py uses it). Also runnable as a dry-run CLI:
    python .claude/scripts/route_skills.py --agent unity-dev --domain Unity --intent bug --task "popup not showing"
    python .claude/scripts/route_skills.py --agent triage --domain Ambiguous --json

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / ".claude" / "skills" / "registry.json"

# Role primary skills (ordered). Folder names = routing keys. From the /team spec.
ROLE_PRIMARY: dict[str, list[str]] = {
    "architect":         ["architect", "unity-foundation", "codebase-understanding", "agentmemory-codebase-recall"],
    # `unity-dots` (DOTS sample index) is intentionally NOT a forced primary: its own
    # SKILL.md says "do NOT load this index as a skill on its own". It stays
    # keyword-reachable (task text naming DOTS samples) instead of always-loaded.
    "unity-dots-dev":    ["unity-dots-best-practices", "ecs-job-patterns", "burst-safety", "memory-safety", "codebase-understanding", "agentmemory-codebase-recall"],
    "unity-dev":         ["unity-classic", "unity-foundation", "codebase-understanding", "agentmemory-codebase-recall"],
    "tester":            ["tester", "qa-validation", "verifier", "codebase-understanding", "agentmemory-codebase-recall"],
    "verifier":          ["tester", "qa-validation", "verifier", "codebase-understanding", "agentmemory-codebase-recall"],
    "qa-tester":         ["tester", "qa-validation", "verifier", "codebase-understanding", "agentmemory-codebase-recall"],
    "bug-investigation": ["investigation", "codebase-understanding", "agentmemory-codebase-recall"],
    "data-tool":         ["data-tool", "editor-data-tools", "codebase-understanding", "agentmemory-codebase-recall"],
    "refactor-agent":    ["codebase-understanding", "ownership-partitioning", "agentmemory-codebase-recall"],
    "system-mapper":     ["codebase-understanding", "agentmemory-codebase-recall"],
    "triage":            ["triage"],
}

# Minimum local skills below which we allow external discovery fallback.
EXTERNAL_DISCOVERY_MIN_LOCAL = 2

# bug-investigation domain extras.
INVESTIGATION_DOMAIN_EXTRAS: dict[str, list[str]] = {
    "Unity":  ["unity-classic"],
    "DOTS":   ["unity-dots-best-practices", "ecs-job-patterns"],
    "Hybrid": ["unity-classic", "unity-dots-best-practices", "ownership-partitioning"],
}

# Roles that must NEVER receive DOTS skills (hard guard, defence-in-depth).
NO_DOTS_ROLES = {"tester", "verifier", "qa-tester", "data-tool", "unity-dev"}
DOTS_ONLY_SKILLS = {"unity-dots-best-practices", "unity-dots", "ecs-job-patterns", "burst-safety", "memory-safety", "unity-dots-ecb-lifecycle-debugger"}

# Roles that get investigation added on a bug intent.
BUG_INTENT_INVESTIGATION_ROLES = {"unity-dev", "unity-dots-dev"}
# Roles that get ownership-partitioning when parallel/refactor.
OWNERSHIP_ROLES = {"architect", "unity-dev", "unity-dots-dev", "refactor-agent", "data-tool"}

# Must-keep for code-reading roles — never trimmed by the cap.
ALWAYS_KEEP = {"agentmemory-codebase-recall", "codebase-understanding"}

_REGISTRY_CACHE: dict | None = None


def load_registry() -> dict:
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is None:
        _REGISTRY_CACHE = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return _REGISTRY_CACHE


def _by_name(reg: dict) -> dict[str, dict]:
    return {e["name"]: e for e in reg.get("skills", [])}


def route(
    agent: str,
    domain: str = "Ambiguous",
    intent: str = "feature",
    task_text: str = "",
    parallel_allowed: bool = False,
    memory_hints: list[str] | None = None,
    max_total: int | None = None,
) -> list[str]:
    """Return the ordered, capped skill list for `agent`."""
    reg = load_registry()
    by_name = _by_name(reg)
    cap = max_total if max_total is not None else reg.get("max_total_skills", 7)
    memory_hints = memory_hints or []
    is_refactor = intent == "refactor"

    def prio(name: str) -> int:
        return by_name.get(name, {}).get("priority", 0)

    def routable(name: str) -> bool:
        e = by_name.get(name)
        return (
            bool(e)
            and e.get("mode") != "meta"
            and e.get("load_by_default", True) is not False
            and e.get("routing-eligible", True) is not False
        )

    # tier 0: role primaries
    tier0 = [s for s in ROLE_PRIMARY.get(agent, []) if routable(s)]

    # tier 1: domain + intent + conditional extras
    tier1: list[str] = []
    if agent == "bug-investigation":
        tier1 += INVESTIGATION_DOMAIN_EXTRAS.get(domain, [])
    if intent == "bug" and agent in BUG_INTENT_INVESTIGATION_ROLES:
        tier1.append("investigation")
    if (parallel_allowed or is_refactor) and agent in OWNERSHIP_ROLES:
        tier1.append("ownership-partitioning")
    tier1 = [s for s in tier1 if routable(s)]

    # tier 2: keyword matches (role-appropriate only)
    tl = task_text.lower()
    tier2: list[str] = []
    for e in reg.get("skills", []):
        if e.get("mode") == "meta" or e.get("load_by_default") is False:
            continue
        if not e.get("routing-eligible", True):
            continue
        if agent not in e.get("roles", []):
            continue
        # Honour intent restriction when the registry entry declares intents.
        skill_intents = e.get("intents")
        if skill_intents and intent not in skill_intents:
            continue
        # Match against both keywords and error-keywords (exact substring match).
        all_triggers = e.get("keywords", []) + e.get("error-keywords", [])
        if any(kw.lower() in tl for kw in all_triggers):
            tier2.append(e["name"])

    # tier 3: agentmemory hints (role-appropriate only)
    tier3 = [s for s in memory_hints if routable(s) and agent in by_name.get(s, {}).get("roles", [])]

    # Assemble with tier bonus; higher = kept first.
    TIER_BONUS = {0: 1000, 1: 500, 2: 0, 3: -200}
    TIER_LABELS = {0: "role-primary", 1: "domain/intent", 2: "keyword-match", 3: "memory-hint"}
    scored: dict[str, float] = {}
    reasons: dict[str, str] = {}  # skill_name -> human-readable selection reason
    for tier, names in ((0, tier0), (1, tier1), (2, tier2), (3, tier3)):
        for n in names:
            score = TIER_BONUS[tier] + prio(n)
            if n not in scored or score > scored[n]:
                scored[n] = score
                reasons[n] = TIER_LABELS[tier]

    # Hard DOTS guard for no-DOTS roles.
    if agent in NO_DOTS_ROLES:
        for d in DOTS_ONLY_SKILLS:
            scored.pop(d, None)
            reasons.pop(d, None)

    ordered = sorted(scored, key=lambda n: (-scored[n], n))

    # Apply cap, guaranteeing must-keep. Must-keep = ALWAYS_KEEP companions PLUS any
    # intent-triggered skill that the spec REQUIRES (investigation on bug,
    # ownership-partitioning on refactor/parallel). Without this, a 7-primary lane like
    # unity-dots-dev would let tier-0 primaries crowd out a required conditional skill.
    required_extra: set[str] = set()
    if intent == "bug" and agent in BUG_INTENT_INVESTIGATION_ROLES:
        required_extra.add("investigation")
    if (parallel_allowed or is_refactor) and agent in OWNERSHIP_ROLES:
        required_extra.add("ownership-partitioning")
    keep_set = set(ALWAYS_KEEP) | required_extra
    must_keep = [s for s in ordered if s in keep_set and s in (tier0 + tier1)]
    if len(ordered) <= cap:
        result = ordered
    else:
        kept = list(must_keep)
        for n in ordered:
            if len(kept) >= cap:
                break
            if n not in kept:
                kept.append(n)
        # Re-sort kept to preserve priority order.
        result = sorted(kept, key=lambda n: (-scored[n], n))

    # Attach ordered reasons (parallel list) to the returned list via a side-channel
    # dict stored on the list object so callers that just want names work unchanged.
    result_list = list(result)
    # Store reasons as module-level side-channel for route_with_reasons().
    # route() itself stays backward-compatible (returns plain list).
    _last_reasons[agent] = {n: reasons.get(n, "unknown") for n in result_list}
    _last_external_needed[agent] = len(result_list) < EXTERNAL_DISCOVERY_MIN_LOCAL
    return result_list


# Module-level side-channel for reason introspection without changing route() signature.
_last_reasons: dict[str, dict[str, str]] = {}
_last_external_needed: dict[str, bool] = {}


def route_with_reasons(
    agent: str,
    domain: str = "Ambiguous",
    intent: str = "feature",
    task_text: str = "",
    parallel_allowed: bool = False,
    memory_hints: list[str] | None = None,
    max_total: int | None = None,
) -> dict:
    """Like route() but returns a structured dict with skills, reasons, and read instructions.

    Return format:
    {
        "agent": str,
        "domain": str,
        "intent": str,
        "skills": [str, ...],
        "reasons": {skill_name: reason_str, ...},
        "read_skill_md": "Before using each skill, read its SKILL.md: ...",
        "external_discovery_allowed": bool,
        "external_discovery_note": str | None
    }
    """
    skills = route(agent, domain, intent, task_text, parallel_allowed, memory_hints, max_total)
    reg = load_registry()
    skills_root = Path(__file__).resolve().parents[2] / ".claude" / "skills"
    reasons = _last_reasons.get(agent, {})
    external_needed = _last_external_needed.get(agent, False)

    read_instructions = []
    for s in skills:
        skill_md = skills_root / s / "SKILL.md"
        read_instructions.append(f"  - {s}: {skill_md}")

    return {
        "agent": agent,
        "domain": domain,
        "intent": intent,
        "skills": skills,
        "reasons": reasons,
        "read_skill_md": (
            "BEFORE using any skill, read its SKILL.md:\n"
            + "\n".join(read_instructions)
        ),
        "external_discovery_allowed": external_needed,
        "external_discovery_note": (
            "No local skills matched beyond role-primaries. "
            "External discovery permitted per AGENTS.md workflow."
            if external_needed else None
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Dry-run the skill router for one agent")
    ap.add_argument("--agent", required=True)
    ap.add_argument("--domain", default="Ambiguous", choices=["DOTS", "Unity", "Hybrid", "Ambiguous"])
    ap.add_argument("--intent", default="feature", choices=["bug", "feature", "refactor", "implement", "performance", "explore"])
    ap.add_argument("--task", default="")
    ap.add_argument("--parallel", action="store_true")
    ap.add_argument("--memory-hints", nargs="*", default=[])
    ap.add_argument("--json", action="store_true", help="Output structured JSON including reasons and read instructions")
    args = ap.parse_args()
    if args.json:
        result = route_with_reasons(args.agent, args.domain, args.intent, args.task, args.parallel, args.memory_hints)
        print(json.dumps(result, indent=2))
    else:
        skills = route(args.agent, args.domain, args.intent, args.task, args.parallel, args.memory_hints)
        reasons = _last_reasons.get(args.agent, {})
        print(f"{args.agent} [{args.domain}/{args.intent}]")
        for s in skills:
            print(f"  {s}  ({reasons.get(s, '?')})")
        if _last_external_needed.get(args.agent):
            print("  [external discovery permitted — no local skill match]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
