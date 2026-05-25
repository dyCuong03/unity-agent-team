#!/usr/bin/env python3
"""
orchestrate.py — runtime enforcer for the Unity DOTS adaptive agent pipeline.

Every gate in /team calls this script. Non-zero exit blocks the next phase.
Markdown promises are not enforcement; this script is.

Subcommands:
  preflight                    — environment + MCP readiness (informational)
  reset                        — reset session-scoped workspace artifacts
  validate <artifact> <schema> — JSON-schema validate an artifact (strict)
  plan <triage.json>           — derive workspace/pipeline.json from triage
  gate <phase>                 — pre-phase check: all required artifacts present + valid
  ownership-check <agent> <files...>  — verify edits respect ownership.lock.json
  finalize                     — post-run completion gate; reads verification_result.json

Exit codes:
  0   ok
  1   internal error
  2   gate failed — phase must not proceed
  3   ownership violation
  4   verification FAIL
  10  retry limit hit (3 failed implementation cycles)

Stdlib only. Works on Windows + POSIX.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = REPO_ROOT / "workspace"
TEMPLATES = REPO_ROOT / ".claude" / "workspace-templates"
SCHEMAS = REPO_ROOT / ".claude" / "schemas"

SESSION_ARTIFACTS = [
    "triage.json",
    "pipeline.json",
    "root_cause.json",
    "approved_plan.json",
    "impl_result.json",
    "verification_result.json",
    "ownership.lock.json",
    "escalation-log.md",
]

# ---------------------------------------------------------------------------
# Tiny JSON-schema validator. Stdlib-only — no jsonschema dependency.
# Supports: type, required, enum, minimum/maximum, minLength, minItems,
#           minProperties, items, properties, additionalProperties.
# ---------------------------------------------------------------------------


class ValidationError(Exception):
    pass


def _type_check(value: Any, expected: str, path: str) -> None:
    py_types = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "null": type(None),
    }
    expected_py = py_types.get(expected)
    if expected_py is None:
        raise ValidationError(f"{path}: unknown schema type {expected!r}")
    if expected == "integer" and isinstance(value, bool):
        raise ValidationError(f"{path}: expected integer, got bool")
    if not isinstance(value, expected_py):
        raise ValidationError(
            f"{path}: expected {expected}, got {type(value).__name__}"
        )


def _validate(value: Any, schema: dict, path: str = "$") -> None:
    if "type" in schema:
        _type_check(value, schema["type"], path)

    if "enum" in schema and value not in schema["enum"]:
        raise ValidationError(f"{path}: {value!r} not in enum {schema['enum']}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ValidationError(
                f"{path}: string length {len(value)} < minLength {schema['minLength']}"
            )

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValidationError(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ValidationError(f"{path}: {value} > maximum {schema['maximum']}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise ValidationError(
                f"{path}: array length {len(value)} < minItems {schema['minItems']}"
            )
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(value):
                _validate(item, item_schema, f"{path}[{i}]")

    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                raise ValidationError(f"{path}: missing required property {req!r}")
        if "minProperties" in schema and len(value) < schema["minProperties"]:
            raise ValidationError(
                f"{path}: object has {len(value)} props < minProperties {schema['minProperties']}"
            )
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                _validate(v, props[k], f"{path}.{k}")
            else:
                add = schema.get("additionalProperties")
                if isinstance(add, dict):
                    _validate(v, add, f"{path}.{k}")
                elif add is False:
                    raise ValidationError(f"{path}: additional property {k!r} not allowed")


def load_schema(name: str) -> dict:
    path = SCHEMAS / (name if name.endswith(".json") else f"{name}.schema.json")
    if not path.exists():
        raise FileNotFoundError(f"schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_artifact(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"artifact missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValidationError(f"{path}: invalid JSON — {e}")


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_preflight(_args: argparse.Namespace) -> int:
    print("[preflight]")
    print(f"  repo_root        : {REPO_ROOT}")
    print(f"  workspace        : {WORKSPACE}")
    print(f"  schemas          : {'present' if SCHEMAS.exists() else 'MISSING'}")
    print(f"  templates        : {'present' if TEMPLATES.exists() else 'MISSING'}")
    print(f"  agent-team-mode  : {'on' if os.environ.get('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS') == '1' else 'off (default)'}")
    print(f"  tmux             : {'available' if shutil.which('tmux') else 'unavailable'}")
    print("  result           : informational — never blocks")
    return 0


def cmd_reset(_args: argparse.Namespace) -> int:
    WORKSPACE.mkdir(exist_ok=True)
    (WORKSPACE / "skill-cache").mkdir(exist_ok=True)
    cleared = []
    for name in SESSION_ARTIFACTS:
        path = WORKSPACE / name
        if path.exists():
            path.unlink()
            cleared.append(name)
    print(f"[reset] cleared {len(cleared)} session artifact(s): {', '.join(cleared) or 'none'}")
    print("[reset] persistent files preserved: repo-knowledge.md, ecs-registry.md, recent-changes.md")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    artifact_path = Path(args.artifact)
    if not artifact_path.is_absolute():
        artifact_path = REPO_ROOT / artifact_path
    try:
        data = load_artifact(artifact_path)
        schema = load_schema(args.schema)
        _validate(data, schema)
    except (FileNotFoundError, ValidationError) as e:
        print(f"[validate] FAIL — {e}", file=sys.stderr)
        return 2
    print(f"[validate] OK — {artifact_path.name} matches {args.schema}")
    return 0


# Complexity → minimum viable pipeline.
# This is the *adaptive* part: triage classifies; this maps to agents.
COMPLEXITY_PIPELINES: dict[str, dict[str, Any]] = {
    "tiny": {
        "pipeline": ["unity-dev"],
        "verification": "bundle",
        "parallel_allowed": False,
        "artifacts_required": {"unity-dev": "impl_result.json"},
    },
    "small": {
        "pipeline": ["unity-dev", "verifier"],
        "verification": "verifier",
        "parallel_allowed": False,
        "artifacts_required": {
            "unity-dev": "impl_result.json",
            "verifier": "verification_result.json",
        },
    },
    "medium": {
        "pipeline": ["architect", "unity-dev", "verifier"],
        "verification": "verifier",
        "parallel_allowed": False,
        "artifacts_required": {
            "architect": "approved_plan.json",
            "unity-dev": "impl_result.json",
            "verifier": "verification_result.json",
        },
    },
    "large": {
        "pipeline": ["architect", "unity-dev", "tester"],
        "verification": "tester",
        "parallel_allowed": False,
        "artifacts_required": {
            "architect": "approved_plan.json",
            "unity-dev": "impl_result.json",
            "tester": "verification_result.json",
        },
    },
    "critical": {
        "pipeline": ["architect", "unity-dev", "data-tool", "tester"],
        "verification": "tester",
        "parallel_allowed": False,
        "artifacts_required": {
            "architect": "approved_plan.json",
            "unity-dev": "impl_result.json",
            "tester": "verification_result.json",
        },
    },
}


def _apply_intent_overrides(pipeline: list[str], intent: str) -> list[str]:
    """Intent prepends a mandatory investigator."""
    if intent == "bug" and "bug-investigation" not in pipeline:
        return ["bug-investigation", *[a for a in pipeline if a != "architect" or pipeline.count(a) > 0]]
    if intent == "refactor" and "refactor-agent" not in pipeline:
        # refactor always needs blast-radius then architect approval then stepgated impl
        return ["refactor-agent", "architect", *[a for a in pipeline if a not in ("architect",)]]
    if intent == "explore":
        return []  # triage-only
    return pipeline


def _apply_depth(complexity: str, depth: str) -> str:
    order = ["tiny", "small", "medium", "large", "critical"]
    i = order.index(complexity)
    if depth == "quick" and i > 0:
        return order[i - 1]
    if depth == "deep" and i < len(order) - 1:
        return order[i + 1]
    return complexity


def cmd_plan(args: argparse.Namespace) -> int:
    triage_path = Path(args.triage)
    if not triage_path.is_absolute():
        triage_path = REPO_ROOT / triage_path
    try:
        triage = load_artifact(triage_path)
        _validate(triage, load_schema("triage"))
    except (FileNotFoundError, ValidationError) as e:
        print(f"[plan] FAIL — invalid triage: {e}", file=sys.stderr)
        return 2

    intent = triage["intent"]
    depth = triage.get("depth", "normal")
    complexity = _apply_depth(triage["complexity"], depth)

    if intent == "explore":
        pipeline_spec = {
            "intent": intent,
            "depth": depth,
            "effective_complexity": complexity,
            "phases": [],
            "verification_strategy": "none",
            "parallel_allowed": False,
            "artifacts_required": {},
            "skill_packs": triage.get("skill_packs", []),
            "ownership_partition": triage.get("ownership_partition", {}),
            "notes": "explore intent — triage-only, no implementation phase",
        }
    else:
        base = COMPLEXITY_PIPELINES[complexity]
        pipeline = list(base["pipeline"])
        pipeline = _apply_intent_overrides(pipeline, intent)
        artifacts = dict(base["artifacts_required"])
        if intent == "bug":
            artifacts["bug-investigation"] = "root_cause.json"
        if intent == "refactor":
            artifacts["refactor-agent"] = "root_cause.json"  # reuses schema (status + evidence)
            artifacts["architect"] = "approved_plan.json"

        # Parallelism rule: certainty-first. Only allow when confidence ≥ 0.8 AND
        # complexity ≥ medium AND ownership partition has ≥ 2 disjoint agents.
        partition = triage.get("ownership_partition") or {}
        parallel_allowed = (
            base["parallel_allowed"]
            or (
                triage["confidence_score"] >= 0.8
                and complexity in ("medium", "large", "critical")
                and len(partition) >= 2
            )
        )

        pipeline_spec = {
            "intent": intent,
            "depth": depth,
            "effective_complexity": complexity,
            "phases": _phaseize(pipeline, parallel_allowed),
            "verification_strategy": base["verification"],
            "parallel_allowed": parallel_allowed,
            "artifacts_required": artifacts,
            "skill_packs": triage.get("skill_packs", []),
            "ownership_partition": partition,
            "confidence_score": triage["confidence_score"],
            "domain": triage["domain"],
            "notes": triage.get("rationale", ""),
        }

    WORKSPACE.mkdir(exist_ok=True)
    out = WORKSPACE / "pipeline.json"
    out.write_text(json.dumps(pipeline_spec, indent=2), encoding="utf-8")
    print(f"[plan] wrote {out} — complexity={complexity} phases={len(pipeline_spec['phases'])} parallel={pipeline_spec['parallel_allowed']}")
    return 0


def _phaseize(pipeline: list[str], parallel_allowed: bool) -> list[dict]:
    """Convert a flat ordered list of agents into phases.

    Investigators (bug-investigation, refactor-agent, system-mapper) always run first
    sequentially. Architect always runs sequentially. Implementation + verifier can
    parallelise only if parallel_allowed.
    """
    if not pipeline:
        return []
    phases: list[dict] = []
    investigators = {"bug-investigation", "refactor-agent", "system-mapper"}
    pre = [a for a in pipeline if a in investigators]
    rest = [a for a in pipeline if a not in investigators]
    for a in pre:
        phases.append({"id": f"phase-{len(phases) + 1}", "agents": [a], "mode": "sequential"})
    if "architect" in rest:
        phases.append({"id": f"phase-{len(phases) + 1}", "agents": ["architect"], "mode": "sequential"})
        rest = [a for a in rest if a != "architect"]
    # Implementation
    impl_agents = [a for a in rest if a in ("unity-dev", "data-tool")]
    if impl_agents:
        mode = "parallel" if parallel_allowed and len(impl_agents) > 1 else "sequential"
        phases.append({"id": f"phase-{len(phases) + 1}", "agents": impl_agents, "mode": mode})
    # Verification
    verify_agents = [a for a in rest if a in ("verifier", "tester")]
    if verify_agents:
        phases.append({"id": f"phase-{len(phases) + 1}", "agents": verify_agents, "mode": "sequential"})
    return phases


def cmd_gate(args: argparse.Namespace) -> int:
    """Check that the artifacts for completed phases are present + valid before
    proceeding to <phase>. The user calls this BEFORE spawning the next phase.

    Usage: orchestrate.py gate <phase-id-about-to-start>
    Pass --completed to check the artifacts of agents that have finished.
    """
    pipeline_path = WORKSPACE / "pipeline.json"
    if not pipeline_path.exists():
        print("[gate] FAIL — workspace/pipeline.json missing. Run plan first.", file=sys.stderr)
        return 2
    spec = json.loads(pipeline_path.read_text(encoding="utf-8"))
    phases = spec["phases"]
    artifacts_required: dict[str, str] = spec.get("artifacts_required", {})

    # Determine which phases are "before" the target.
    target_id = args.phase
    target_idx = next((i for i, p in enumerate(phases) if p["id"] == target_id), None)
    if target_idx is None:
        print(f"[gate] FAIL — phase {target_id} not in pipeline", file=sys.stderr)
        return 2

    failed = []
    schema_map = {
        "root_cause.json": "root_cause",
        "approved_plan.json": "approved_plan",
        "impl_result.json": "impl_result",
        "verification_result.json": "verification_result",
        "ownership.lock.json": "ownership",
    }
    for prior in phases[:target_idx]:
        for agent in prior["agents"]:
            art = artifacts_required.get(agent)
            if not art:
                continue
            path = WORKSPACE / art
            schema = schema_map.get(art)
            try:
                data = load_artifact(path)
                if schema:
                    _validate(data, load_schema(schema))
            except (FileNotFoundError, ValidationError) as e:
                failed.append(f"{agent} → {art}: {e}")
                continue
            # Status checks
            if art == "approved_plan.json" and data.get("status") != "APPROVED":
                failed.append(f"{agent} → {art}: status={data.get('status')!r} (must be APPROVED)")
            if art == "root_cause.json" and data.get("status") not in ("COMPLETE",):
                failed.append(f"{agent} → {art}: status={data.get('status')!r} (must be COMPLETE)")
            if art == "impl_result.json":
                if data.get("compilation") != "CLEAN":
                    failed.append(f"{agent} → {art}: compilation={data.get('compilation')!r} (must be CLEAN)")
                if data.get("status") != "COMPLETE":
                    failed.append(f"{agent} → {art}: status={data.get('status')!r} (must be COMPLETE)")
                bundle = data.get("verification_bundle") or {}
                if not bundle.get("invariants"):
                    failed.append(f"{agent} → {art}: verification_bundle.invariants is empty")
                if not bundle.get("repro_steps"):
                    failed.append(f"{agent} → {art}: verification_bundle.repro_steps is empty")
            if art == "approved_plan.json":
                if not data.get("acceptance_criteria"):
                    failed.append(f"{agent} → {art}: acceptance_criteria is empty (must list ≥1)")
                if not data.get("ownership"):
                    failed.append(f"{agent} → {art}: ownership is empty")

    if failed:
        print(f"[gate] BLOCK — cannot enter {target_id}:", file=sys.stderr)
        for f in failed:
            print(f"  • {f}", file=sys.stderr)
        return 2
    print(f"[gate] OK — clear to enter {target_id}")
    return 0


def cmd_ownership_check(args: argparse.Namespace) -> int:
    lock_path = WORKSPACE / "ownership.lock.json"
    if not lock_path.exists():
        # No partition → unrestricted (tiny tasks).
        print("[ownership-check] no ownership.lock.json — unrestricted")
        return 0
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    try:
        _validate(lock, load_schema("ownership"))
    except ValidationError as e:
        print(f"[ownership-check] FAIL — malformed lock: {e}", file=sys.stderr)
        return 3
    partitions: dict[str, list[str]] = lock["partitions"]
    agent_globs = partitions.get(args.agent)
    if not agent_globs:
        print(
            f"[ownership-check] FAIL — agent {args.agent!r} has no partition; not allowed to edit any file",
            file=sys.stderr,
        )
        return 3
    forbidden = lock.get("forbidden") or []
    shared_ro = lock.get("shared_read_only") or []

    violations: list[str] = []
    for f in args.files:
        normalized = f.replace("\\", "/")
        if any(fnmatch.fnmatch(normalized, g) for g in forbidden):
            violations.append(f"{f}: matches forbidden glob")
            continue
        if any(fnmatch.fnmatch(normalized, g) for g in shared_ro):
            violations.append(f"{f}: shared_read_only — writes not allowed for any agent")
            continue
        if not any(fnmatch.fnmatch(normalized, g) for g in agent_globs):
            violations.append(f"{f}: outside {args.agent} partition {agent_globs}")

    if violations:
        print(f"[ownership-check] BLOCK — {len(violations)} violation(s):", file=sys.stderr)
        for v in violations:
            print(f"  • {v}", file=sys.stderr)
        return 3
    print(f"[ownership-check] OK — {len(args.files)} file(s) within {args.agent} partition")
    return 0


def cmd_finalize(args: argparse.Namespace) -> int:
    """Final completion gate. Reads verification_result.json (or, for explore intent,
    just succeeds with the triage report). Returns the completion report on stdout
    and exits with code reflecting verification status.
    """
    pipeline_path = WORKSPACE / "pipeline.json"
    if not pipeline_path.exists():
        print("[finalize] FAIL — no pipeline.json (run plan first)", file=sys.stderr)
        return 2
    spec = json.loads(pipeline_path.read_text(encoding="utf-8"))

    if spec.get("intent") == "explore":
        print("=== Adaptive Pipeline — Completion ===")
        print("Intent: explore (triage-only)")
        print(f"Risk level: LOW")
        print("Verification: not applicable")
        return 0

    vr_path = WORKSPACE / "verification_result.json"
    if not vr_path.exists():
        print("[finalize] FAIL — verification_result.json missing", file=sys.stderr)
        return 4
    try:
        vr = load_artifact(vr_path)
        _validate(vr, load_schema("verification_result"))
    except (FileNotFoundError, ValidationError) as e:
        print(f"[finalize] FAIL — invalid verification result: {e}", file=sys.stderr)
        return 4
    if vr["status"] != "PASS":
        print(f"[finalize] BLOCK — verification status={vr['status']}", file=sys.stderr)
        if vr.get("fail_reason"):
            print(f"  fail_reason: {vr['fail_reason']}", file=sys.stderr)
        return 4

    impl_path = WORKSPACE / "impl_result.json"
    impl = load_artifact(impl_path) if impl_path.exists() else {}
    changed = impl.get("changed_files") or []

    print("=== Adaptive Pipeline — Completion ===")
    print(f"Intent          : {spec.get('intent')}")
    print(f"Complexity      : {spec.get('effective_complexity')}")
    print(f"Risk level      : {vr.get('risk_level')}")
    print(f"Changed files   : {len(changed)}")
    for f in changed[:20]:
        print(f"  - {f}")
    if len(changed) > 20:
        print(f"  … and {len(changed) - 20} more")
    print(f"Verification    : {vr['status']} ({vr['method']})")
    if vr.get("regressions"):
        print(f"Open regressions: {len(vr['regressions'])}")
        for r in vr["regressions"]:
            print(f"  - {r}")
    print(f"Notes           : {vr.get('notes') or '—'}")
    return 0


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="orchestrate.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("preflight").set_defaults(func=cmd_preflight)
    sub.add_parser("reset").set_defaults(func=cmd_reset)

    p_validate = sub.add_parser("validate")
    p_validate.add_argument("artifact")
    p_validate.add_argument("schema")
    p_validate.set_defaults(func=cmd_validate)

    p_plan = sub.add_parser("plan")
    p_plan.add_argument("triage", help="path to triage.json")
    p_plan.set_defaults(func=cmd_plan)

    p_gate = sub.add_parser("gate")
    p_gate.add_argument("phase", help="phase id about to start (e.g. phase-2)")
    p_gate.set_defaults(func=cmd_gate)

    p_own = sub.add_parser("ownership-check")
    p_own.add_argument("agent")
    p_own.add_argument("files", nargs="+")
    p_own.set_defaults(func=cmd_ownership_check)

    sub.add_parser("finalize").set_defaults(func=cmd_finalize)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:  # noqa: BLE001
        print(f"[orchestrate] internal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
