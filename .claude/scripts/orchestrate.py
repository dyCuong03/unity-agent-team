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
  commit [task] [--no-push]    — post-finalize gate: stage changed files, commit, push

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
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Root resolution is owned by roots.py — the single allowed mechanism.
_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import roots  # noqa: E402


def _resolve_project_root() -> Path:
    try:
        return roots.project_root()
    except roots.RootResolutionError:
        # Legacy behavior: fall back to the framework repo itself.
        return roots.framework_root()


REPO_ROOT = _resolve_project_root()
try:
    _CONFIG: dict[str, Any] = roots.load_config(REPO_ROOT)
except roots.RootResolutionError:
    _CONFIG = {}

# PROJECT-scoped paths come from roots helpers; FRAMEWORK-scoped paths
# (schemas, workspace templates) live under the framework's .claude/.
WORKSPACE = roots.workspace_dir(REPO_ROOT, _CONFIG or {})
TEMPLATES = roots.claude_root() / "workspace-templates"
SCHEMAS = roots.claude_root() / "schemas"

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

# Minimum root-cause confidence required to unblock implementation.
# Below this, the investigation is not certain enough — deepen it or escalate.
# A COMPLETE root_cause with confidence < this value MUST NOT open the impl phase.
ROOT_CAUSE_MIN_CONFIDENCE = 0.6

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


# Domain → implementation lane. `unity-dev` is the non-DOTS Unity-classic lane;
# `unity-dots-dev` is the DOTS/ECS lane. COMPLEXITY_PIPELINES use the placeholder
# `unity-dev`; this remaps it to the correct lane from triage.domain so DOTS/ECS
# tasks never land on the non-DOTS lane.
DOMAIN_IMPL_AGENT = {
    "DOTS": "unity-dots-dev",     # ISystem/Jobs/Burst/Entities/ECB/SystemAPI/Physics
    "Unity": "unity-dev",         # MonoBehaviour/UI/View/VContainer/DOTween/Addressables/pooling
    "Hybrid": "unity-dots-dev",   # DOTS owns runtime truth; architect coordinates the UI bridge
    "Ambiguous": "unity-dev",     # default; architect should confirm the lane
}

# Skill selection is delegated to the registry-backed router (scripts/route_skills.py),
# the single source of truth for "which skills does this agent load". The fallback map
# below is used ONLY if the router/registry cannot be imported (degraded mode). The
# router enforces: DOTS extras to DOTS lanes only; tester/verifier/data-tool/unity-dev
# never get DOTS skills; agentmemory-codebase-recall + codebase-understanding are
# must-keep for code-reading roles; total capped at registry.max_total_skills.
try:  # pragma: no cover - exercised at runtime
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import route_skills as _route_skills  # type: ignore
except Exception:  # registry/router unavailable — degrade gracefully
    _route_skills = None

# Fallback-only primary map (degraded mode when route_skills cannot load).
AGENT_PRIMARY_SKILLS: dict[str, list[str]] = {
    "architect":         ["architect", "unity-foundation", "codebase-understanding", "agentmemory-codebase-recall"],
    "unity-dots-dev":    ["unity-dots-best-practices", "ecs-job-patterns", "burst-safety", "memory-safety", "codebase-understanding", "agentmemory-codebase-recall"],
    "unity-dev":         ["unity-classic", "unity-foundation", "codebase-understanding", "agentmemory-codebase-recall"],
    "tester":            ["tester", "qa-validation", "verifier", "codebase-understanding", "agentmemory-codebase-recall"],
    "verifier":          ["tester", "qa-validation", "verifier", "codebase-understanding", "agentmemory-codebase-recall"],
    "qa-tester":         ["tester", "qa-validation", "verifier", "codebase-understanding", "agentmemory-codebase-recall"],
    "bug-investigation": ["investigation", "codebase-understanding", "agentmemory-codebase-recall"],
    "data-tool":         ["data-tool", "editor-data-tools", "codebase-understanding", "agentmemory-codebase-recall"],
    "refactor-agent":    ["codebase-understanding", "ownership-partitioning", "agentmemory-codebase-recall"],
    "system-mapper":     ["codebase-understanding", "agentmemory-codebase-recall"],
}


def _compute_skills_by_agent(
    pipeline: list[str],
    domain: str = "Ambiguous",
    intent: str = "feature",
    task_text: str = "",
    parallel_allowed: bool = False,
) -> dict[str, list[str]]:
    """Map every agent in the pipeline to its router-selected skill set.

    Uses the registry-backed router when available; otherwise the fallback primary
    map (degraded mode). DOTS extras never reach unity-dev/tester/verifier/data-tool.
    """
    out: dict[str, list[str]] = {}
    for agent in pipeline:
        if _route_skills is not None:
            out[agent] = _route_skills.route(
                agent, domain=domain, intent=intent,
                task_text=task_text, parallel_allowed=parallel_allowed,
            )
        else:
            out[agent] = list(AGENT_PRIMARY_SKILLS.get(agent, []))
    return out


def _route_impl_by_domain(
    pipeline: list[str], artifacts: dict[str, str], domain: str
) -> tuple[list[str], dict[str, str], str | None]:
    """Remap the placeholder `unity-dev` impl agent to the domain-correct lane.

    Returns (pipeline, artifacts, note). DOTS/Hybrid tasks must NOT land on the
    non-DOTS `unity-dev` lane.
    """
    impl = DOMAIN_IMPL_AGENT.get(domain, "unity-dev")
    note = None
    if impl != "unity-dev":
        pipeline = [impl if a == "unity-dev" else a for a in pipeline]
        if "unity-dev" in artifacts:
            artifacts[impl] = artifacts.pop("unity-dev")
        note = f"domain={domain}: implementation routed to {impl}"
    elif domain == "Ambiguous":
        note = "domain=Ambiguous: impl lane defaulted to unity-dev — architect should confirm"
    return pipeline, artifacts, note


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
            "skills_by_agent": {},
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

        # Domain routing: send the impl phase to the correct lane (DOTS → unity-dots-dev).
        pipeline, artifacts, route_note = _route_impl_by_domain(
            pipeline, artifacts, triage["domain"]
        )

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
            "skills_by_agent": _compute_skills_by_agent(
                pipeline,
                domain=triage["domain"],
                intent=intent,
                task_text=triage.get("task", ""),
                parallel_allowed=parallel_allowed,
            ),
            "ownership_partition": partition,
            "confidence_score": triage["confidence_score"],
            "domain": triage["domain"],
            "notes": "; ".join(filter(None, [triage.get("rationale", ""), route_note])),
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
    impl_agents = [a for a in rest if a in ("unity-dev", "unity-dots-dev", "data-tool")]
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
    # Drift gate only applies when an architect-approved plan is part of this
    # pipeline. tiny/small tasks have no approved_plan, so deviations are moot.
    approved_plan_required = "approved_plan.json" in artifacts_required.values()
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
            if art == "root_cause.json":
                if data.get("status") not in ("COMPLETE",):
                    failed.append(f"{agent} → {art}: status={data.get('status')!r} (must be COMPLETE)")
                else:
                    # Root-cause confidence gate — a COMPLETE-but-uncertain
                    # investigation must NOT unblock the fix. This enforces
                    # "find the real root cause, not a guess".
                    conf = data.get("confidence")
                    if not isinstance(conf, (int, float)) or isinstance(conf, bool):
                        failed.append(f"{agent} → {art}: confidence missing/invalid ({conf!r})")
                    elif conf < ROOT_CAUSE_MIN_CONFIDENCE:
                        failed.append(
                            f"{agent} → {art}: confidence={conf} < {ROOT_CAUSE_MIN_CONFIDENCE} "
                            "— root cause not certain enough to start implementation; "
                            "deepen the investigation or set status=ESCALATE"
                        )
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
                # Plan-adherence (anti-drift) gate — unreconciled deviations from
                # the approved plan block the phase. The architect must fold the
                # change into approved_plan.json (then this list is cleared) or
                # unity-dev reverts the drift. Silent drift is not allowed.
                deviations = data.get("deviations_from_plan") or []
                if deviations and approved_plan_required:
                    preview = "; ".join(str(d) for d in deviations[:5])
                    failed.append(
                        f"{agent} → {art}: {len(deviations)} unreconciled deviation(s) from approved_plan "
                        "— implementation drifted from the design. Architect must approve & fold them "
                        "into approved_plan.json (then clear deviations_from_plan), or revert. "
                        f"Deviations: {preview}"
                    )
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
# Commit + push gate
# ---------------------------------------------------------------------------

# Footer added to every /team auto-commit. Keep in sync with project policy.
COMMIT_COAUTHOR = "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"


def _project_root() -> Path:
    """Repo that holds the code /team edited. Env overrides
    (roots.ENV_PROJECT_ROOT and its legacy alias) and project-config.json
    are all honoured inside roots.py."""
    return REPO_ROOT


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True
    )


def cmd_commit(args: argparse.Namespace) -> int:
    """Post-finalize commit+push gate. Only a PASS run may commit. Stages the
    files unity-dev reported plus persistent knowledge, commits on the current
    branch, and pushes to origin. Never auto-creates branches; never force-pushes.
    """
    root = _project_root()

    # 0. must be a git work tree
    if _git(["rev-parse", "--is-inside-work-tree"], root).returncode != 0:
        print(f"[commit] SKIP — {root} is not a git repository", file=sys.stderr)
        return 0

    # 1. completion gate — mirror finalize. explore = nothing to commit.
    pipeline_path = WORKSPACE / "pipeline.json"
    intent = None
    if pipeline_path.exists():
        try:
            intent = json.loads(pipeline_path.read_text(encoding="utf-8")).get("intent")
        except json.JSONDecodeError:
            pass
    if intent == "explore":
        print("[commit] SKIP — explore intent produces no changes")
        return 0

    vr_path = WORKSPACE / "verification_result.json"
    if not vr_path.exists():
        print("[commit] BLOCK — verification_result.json missing (run finalize first)",
              file=sys.stderr)
        return 2
    try:
        vr = load_artifact(vr_path)
        _validate(vr, load_schema("verification_result"))
    except (FileNotFoundError, ValidationError) as e:
        print(f"[commit] BLOCK — invalid verification result: {e}", file=sys.stderr)
        return 4
    if vr.get("status") != "PASS":
        print(f"[commit] BLOCK — verification status={vr.get('status')}; only PASS may commit",
              file=sys.stderr)
        return 4

    # 2. branch safety — no detached HEAD, no force.
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], root).stdout.strip()
    if not branch or branch == "HEAD":
        print("[commit] BLOCK — detached HEAD; checkout a branch before /team commit",
              file=sys.stderr)
        return 2

    # 2b. branch policy — allowedBranches from project config. Empty list (the
    # default) means no restriction, which preserves the legacy behavior of
    # committing on whatever branch is currently checked out.
    allowed = (_CONFIG or {}).get("allowedBranches") or []
    if allowed and branch not in allowed:
        default = roots.default_branch(root, _CONFIG or {})
        print(
            f"[commit] BLOCK — branch {branch!r} not in allowedBranches {allowed} "
            f"(project default branch: {default}); checkout an allowed branch",
            file=sys.stderr,
        )
        return 2

    # 3. stage: files unity-dev changed + persistent knowledge files.
    impl_path = WORKSPACE / "impl_result.json"
    changed: list[str] = []
    if impl_path.exists():
        try:
            changed = load_artifact(impl_path).get("changed_files") or []
        except ValidationError:
            changed = []
    persistent = [
        "workspace/repo-knowledge.md",
        "workspace/ecs-registry.md",
        "workspace/recent-changes.md",
    ]
    for rel in changed + persistent:
        p = Path(rel) if os.path.isabs(rel) else (root / rel)
        if p.exists():
            _git(["add", "--", str(p)], root)

    staged = _git(["diff", "--cached", "--name-only"], root).stdout.strip()
    if not staged:
        print("[commit] nothing to commit — working tree clean for tracked changes")
        return 0
    n_files = len(staged.splitlines())

    # 4. commit message
    task = (args.task or vr.get("notes") or "automated change").strip().replace("\n", " ")
    complexity = ""
    if pipeline_path.exists():
        try:
            spec = json.loads(pipeline_path.read_text(encoding="utf-8"))
            intent = spec.get("intent") or intent or "team"
            complexity = spec.get("effective_complexity") or ""
        except json.JSONDecodeError:
            pass
    scope = f"{intent or 'team'}" + (f"/{complexity}" if complexity else "")
    subject = f"team({scope}): {task}"
    if len(subject) > 72:
        subject = subject[:69] + "..."
    body = (
        f"Auto-committed by /team after verification PASS "
        f"({vr.get('method', 'unknown')}, risk={vr.get('risk_level', 'n/a')}).\n"
        f"{n_files} file(s) changed.\n\n"
        f"{COMMIT_COAUTHOR}"
    )

    cr = _git(["commit", "-m", subject, "-m", body], root)
    if cr.returncode != 0:
        print(f"[commit] FAIL — git commit failed:\n{cr.stderr.strip()}", file=sys.stderr)
        return 1
    sha = _git(["rev-parse", "--short", "HEAD"], root).stdout.strip()
    print(f"[commit] committed {sha} on {branch} — {n_files} file(s)")

    # 5. push (non-fatal if no remote / rejected — commit stays local)
    if args.no_push:
        print("[commit] push skipped (--no-push); commit retained locally")
        return 0
    if _git(["remote"], root).stdout.strip() == "":
        print("[commit] no git remote configured — commit retained locally, not pushed")
        return 0
    pr = _git(["push", "origin", "HEAD"], root)
    if pr.returncode != 0:
        print(f"[commit] WARN — push failed (commit retained locally):\n{pr.stderr.strip()}",
              file=sys.stderr)
        return 0
    print(f"[commit] pushed {branch} → origin")
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

    p_commit = sub.add_parser("commit")
    p_commit.add_argument("task", nargs="?", default="", help="task summary for the commit subject")
    p_commit.add_argument("--no-push", action="store_true", help="commit locally, do not push")
    p_commit.set_defaults(func=cmd_commit)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:  # noqa: BLE001
        print(f"[orchestrate] internal error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
