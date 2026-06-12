#!/usr/bin/env python3
"""
triage.py — helper that the triage agent (or orchestrator) calls to assemble
a triage.json from inputs it has already gathered.

This is NOT a classifier on its own. The triage agent does the CRG +
fingerprinting work; this script just packages the decision into a valid
artifact and writes it to workspace/triage.json.

Usage (typically called by the triage agent):

  python .claude/scripts/triage.py \\
    --intent feature \\
    --task "Add stamina regen" \\
    --depth normal \\
    --complexity medium \\
    --blast-radius local \\
    --systems CombatSystem MovementSystem \\
    --files-est 4 \\
    --confidence 0.82 \\
    --domain DOTS \\
    --pipeline architect unity-dev verifier \\
    --strategy verifier \\
    --skill-packs ecs-job-patterns burst-safety \\
    --rationale "Single feature area; 4 files; clear ECS extension point"

Heuristics:
- parallel_allowed = (confidence >= 0.8) AND (complexity in medium/large/critical)
  AND (ownership partition has >= 2 entries). triage.py decides this; the
  partition itself is set by the architect for large/critical and by the
  triage agent for tiny/small/medium.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import roots  # noqa: E402

# PROJECT-scoped: workspace belongs to the project being worked on.
try:
    REPO_ROOT = roots.project_root()
except roots.RootResolutionError:
    REPO_ROOT = roots.framework_root()
try:
    WORKSPACE = roots.workspace_dir(REPO_ROOT, roots.load_config(REPO_ROOT))
except roots.RootResolutionError:
    WORKSPACE = REPO_ROOT / "workspace"


def parse_ownership(pairs: list[str]) -> dict[str, list[str]]:
    """--own unity-dev=Assets/Scripts/Combat/** --own data-tool=Assets/Editor/**"""
    out: dict[str, list[str]] = {}
    for p in pairs or []:
        if "=" not in p:
            raise SystemExit(f"--own expects agent=glob, got {p!r}")
        agent, glob = p.split("=", 1)
        out.setdefault(agent, []).append(glob)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(prog="triage.py")
    ap.add_argument("--intent", required=True, choices=["bug", "feature", "refactor", "explore"])
    ap.add_argument("--task", required=True)
    ap.add_argument("--depth", default="normal", choices=["quick", "normal", "deep"])
    ap.add_argument("--complexity", required=True, choices=["tiny", "small", "medium", "large", "critical"])
    ap.add_argument("--blast-radius", required=True, choices=["isolated", "local", "multi-system", "cross-cutting"])
    ap.add_argument("--systems", nargs="*", default=[])
    ap.add_argument("--files-est", type=int, default=0)
    ap.add_argument("--confidence", type=float, required=True)
    ap.add_argument("--domain", required=True, choices=["DOTS", "Unity", "Hybrid", "Ambiguous"])
    ap.add_argument("--pipeline", nargs="+", required=True)
    ap.add_argument("--strategy", default="bundle", choices=["bundle", "verifier", "tester", "stepgated"])
    ap.add_argument("--skill-packs", nargs="*", default=[])
    ap.add_argument("--own", action="append", default=[],
                    help="agent=glob, repeatable")
    ap.add_argument("--rationale", required=True)
    ap.add_argument("--escalate", nargs="*", default=[])
    args = ap.parse_args()

    ownership = parse_ownership(args.own)
    parallel_allowed = (
        args.confidence >= 0.8
        and args.complexity in ("medium", "large", "critical")
        and len(ownership) >= 2
    )

    out = {
        "intent": args.intent,
        "task": args.task,
        "depth": args.depth,
        "complexity": args.complexity,
        "blast_radius": args.blast_radius,
        "systems_affected": args.systems,
        "files_touched_estimate": args.files_est,
        "confidence_score": args.confidence,
        "domain": args.domain,
        "recommended_pipeline": args.pipeline,
        "parallel_allowed": parallel_allowed,
        "verification_strategy": args.strategy,
        "ownership_partition": ownership,
        "skill_packs": args.skill_packs,
        "rationale": args.rationale,
        "escalations": args.escalate,
    }

    WORKSPACE.mkdir(exist_ok=True)
    path = WORKSPACE / "triage.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[triage] wrote {path}")
    print(f"[triage] complexity={args.complexity} confidence={args.confidence} parallel={parallel_allowed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
