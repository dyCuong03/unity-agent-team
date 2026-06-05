#!/usr/bin/env python3
"""
Validate adaptive (Path A) per-agent skill routing.

Proves the lane-correctness guarantees of orchestrate.py `skills_by_agent` and that
the --team (Path B) Read-first per-role skill block in team.md is intact:

  1. An adaptive Unity task routed to `unity-dev` loads `unity-classic` and NOT
     `unity-dots-best-practices` by default.
  2. An adaptive DOTS task routed to `unity-dots-dev` loads `unity-dots-best-practices`
     plus the DOTS extras (ecs-job-patterns, burst-safety, memory-safety).
  3. `tester` / `verifier` / `data-tool` never receive DOTS skills by default.
  4. `/team --team` still pins Read-first per-role skills (block unchanged).

Exercises the SAME building blocks orchestrate.py `cmd_plan` uses to derive the
final pipeline, so the assertions track real behavior. No workspace side effects.

Usage:
    python .claude/scripts/validate_skill_routing.py
    python .claude/scripts/validate_skill_routing.py --json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORCH_PATH = Path(__file__).resolve().parent / "orchestrate.py"
TEAM_MD = ROOT / ".claude" / "commands" / "team.md"

DOTS_SKILLS = {"unity-dots-best-practices", "ecs-job-patterns", "burst-safety", "memory-safety"}
DOTS_EXTRAS = ["ecs-job-patterns", "burst-safety", "memory-safety"]


def _load_orchestrate():
    spec = importlib.util.spec_from_file_location("orchestrate", ORCH_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _final_pipeline(orch, complexity: str, intent: str, domain: str):
    """Reproduce cmd_plan's pipeline derivation (without file I/O)."""
    base = orch.COMPLEXITY_PIPELINES[complexity]
    pipeline = list(base["pipeline"])
    pipeline = orch._apply_intent_overrides(pipeline, intent)
    artifacts: dict[str, str] = dict(base["artifacts_required"])
    pipeline, _artifacts, _note = orch._route_impl_by_domain(pipeline, artifacts, domain)
    return pipeline


def run_checks() -> list[dict]:
    orch = _load_orchestrate()
    results: list[dict] = []

    def record(name: str, ok: bool, detail: str):
        results.append({"check": name, "pass": ok, "detail": detail})

    # --- Check 1: adaptive Unity task → unity-dev gets unity-classic, not DOTS ---
    pipe = _final_pipeline(orch, "medium", "feature", "Unity")
    sba = orch._compute_skills_by_agent(pipe, domain="Unity", intent="feature", task_text="add inventory UI")
    udev = sba.get("unity-dev", [])
    ok1 = (
        "unity-dev" in pipe
        and "unity-classic" in udev
        and "unity-dots-best-practices" not in udev
    )
    record(
        "unity task -> unity-dev has unity-classic, not unity-dots-best-practices",
        ok1,
        f"pipeline={pipe} unity-dev_skills={udev}",
    )

    # --- Check 2: adaptive DOTS task → unity-dots-dev gets DOTS stack + extras ---
    pipe = _final_pipeline(orch, "medium", "feature", "DOTS")
    sba = orch._compute_skills_by_agent(pipe, domain="DOTS", intent="feature", task_text="add enemy AI system")
    ddev = sba.get("unity-dots-dev", [])
    ok2 = (
        "unity-dots-dev" in pipe
        and "unity-dots-best-practices" in ddev
        and all(p in ddev for p in DOTS_EXTRAS)
    )
    record(
        "dots task -> unity-dots-dev has unity-dots-best-practices + DOTS extras",
        ok2,
        f"pipeline={pipe} unity-dots-dev_skills={ddev}",
    )

    # --- Check 3: tester/verifier/data-tool never get DOTS skills by default ---
    # Use a DOTS critical pipeline (has data-tool + tester) on a DOTS-keyword task.
    pipe = _final_pipeline(orch, "critical", "feature", "DOTS")
    sba = orch._compute_skills_by_agent(pipe, domain="DOTS", intent="feature", task_text="ISystem job burst entities")
    leaks: dict[str, list[str]] = {}
    for agent in ("tester", "verifier", "data-tool"):
        skills = sba.get(agent, [])
        bad = sorted(DOTS_SKILLS & set(skills))
        if bad:
            leaks[agent] = bad
    # also check verifier via a 'small' DOTS pipeline (tester absent there)
    pipe_s = _final_pipeline(orch, "small", "feature", "DOTS")
    sba_s = orch._compute_skills_by_agent(pipe_s, domain="DOTS", intent="feature", task_text="ISystem job burst entities")
    vbad = sorted(DOTS_SKILLS & set(sba_s.get("verifier", [])))
    if vbad:
        leaks["verifier"] = vbad
    ok3 = not leaks
    record(
        "tester/verifier/data-tool receive no DOTS skills by default",
        ok3,
        f"leaks={leaks or 'none'}",
    )

    # --- Check 4: --team Read-first per-role skills present in team.md ---
    text = TEAM_MD.read_text(encoding="utf-8", errors="replace") if TEAM_MD.exists() else ""
    needles = [
        "STEP 0",
        "unity-classic/SKILL.md",
        "unity-dots-best-practices/SKILL.md",
    ]
    missing = [n for n in needles if n not in text]
    ok4 = TEAM_MD.exists() and not missing
    record(
        "/team --team Read-first per-role skill block unchanged",
        ok4,
        f"missing={missing or 'none'}",
    )

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate adaptive per-agent skill routing")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = run_checks()
    failed = [r for r in results if not r["pass"]]

    if args.json:
        print(json.dumps({"results": results, "failed": len(failed)}, indent=2))
        return 1 if failed else 0

    for r in results:
        mark = "PASS" if r["pass"] else "FAIL"
        print(f"[{mark}] {r['check']}")
        print(f"       {r['detail']}")
    if failed:
        print(f"\n{len(failed)} check(s) FAILED")
        return 1
    print("\nAll 4 checks PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
