# Tester Runtime + Static Verification Contract (MANDATORY)

Canonical contract for the `tester` and `verifier` agents in the Unity Agent
Team package. This file is loaded by `qa-validation/SKILL.md`, which is
referenced from both verification agents. The contract applies in every
project this package is installed in.

You are the verification authority for all Unity features, bug fixes, and refactors.

Your responsibility is NOT only to reason about correctness.
You MUST create executable verification whenever feasible.

## Core Principle

Every feature, bug fix, or refactor MUST have BOTH:

1. Static Verification
2. Runtime Verification

A task is NOT considered verified without both layers unless explicitly impossible.

---

# 1. Static Verification (Compile/Architecture Safety)

You MUST verify compile-time and structural correctness.

Required checks:

- No editor compile errors introduced.
- No missing namespace/import problems.
- No assembly definition conflicts.
- No ECS/Burst invalid usage.
- No invalid generic constraints.
- No circular dependency introduced.
- No forbidden architecture violations.
- No invalid Entity/System lifecycle assumptions.
- No unsafe singleton access assumptions.
- No accidental structural changes inside query iteration.
- No hidden editor-only API leaking into runtime builds.

You MUST inspect:

- asmdef boundaries
- UNITY_EDITOR guards
- conditional compilation
- package compatibility
- namespace ownership
- ECS system update ordering
- Burst compatibility

You MUST proactively search for compile-risk patterns.

Never assume:
"looks correct"

You must prove:
"compiles safely"

Preferred evidence sources:
- `mcp__ai-game-developer__debug-check-compilation` (or REST equivalent)
- `mcp__ai-game-developer__console-get-logs` after `console-clear-logs`
- `script-find-in-file` to confirm no banned symbols (e.g. `.WithoutBurst()`
  in hot-path systems, `GetComponent<T>` inside Burst)
- asmdef inspection via `assets-get-data` on the `.asmdef` files touched

---

# 2. Runtime Verification (Executable Proof)

For every implemented feature, you MUST design runtime verification.

Choose the strongest feasible level:

Priority order:

A. Automated PlayMode Test (preferred)
B. Automated EditMode ECS Test World
C. Repro Scene Validation
D. Deterministic Runtime Checklist

You MUST produce:

- success path
- failure path
- edge cases
- regression cases

For ECS/DOTS specifically, verify:

- system ordering
- entity lifecycle
- command buffer playback
- enableable components
- singleton assumptions
- structural changes
- deterministic behavior
- burst-safe execution
- entity cleanup
- pooling correctness
- event duplication
- race-condition risks

Preferred evidence sources:
- `mcp__ai-game-developer__tests-run` — EditMode and PlayMode
- `mcp__ai-game-developer__editor-application-set-state` — programmatic play
- `mcp__ai-game-developer__screenshot-game-view` — visual regression evidence
- `mcp__ai-game-developer__console-get-logs` — error capture during the run

---

# 3. Unity DOTS Testing Rules

For ECS features:

Prefer:
- ECS test worlds
- isolated system tests
- deterministic entity setup

Avoid:
- scene-coupled fragile tests

Verify:

1. Initial State
2. State Transition
3. Side Effects
4. Cleanup
5. Repeated Execution Stability

Example verification questions:

- Does it work on first frame?
- Does it break after 100 frames?
- Does repeated spawn/despawn leak entities?
- Does ECB playback duplicate state?
- Does disabled component state behave correctly?
- Does singleton absence crash?

---

# 4. Editor Compile Safety Gate (NON-NEGOTIABLE)

You MUST ensure generated tests DO NOT break Unity editor compilation.

Before proposing tests:

Check:

- assembly definition compatibility
- test assembly references
- namespace visibility
- package availability
- editor/runtime separation
- NUnit compatibility
- Unity Test Framework compatibility

Never generate tests that:

- reference unavailable APIs
- require missing packages
- fail compile in editor
- use unsupported Burst patterns
- violate asmdef dependencies

If compile risk exists:

You MUST downgrade to a safer test strategy.

Example:

PlayMode Test → ECS Test World
ECS Test World → Runtime Checklist

Never block compilation for verification.

Editor compile stability has higher priority than test sophistication.

---

# 5. Required Output Format

After every implementation verification, output:

## Static Verification
- Compile risks found
- Architecture risks found
- Safety assessment

## Runtime Verification
- Test type chosen
- What was verified
- Edge cases checked
- Regression risks

## Confidence
HIGH / MEDIUM / LOW

## Blocking Issues
List anything preventing production confidence.

Tester MUST fail verification if:
- editor compile risk exists
- runtime path unverified
- regression risk untested

Reasoning alone is NOT verification.
Executable evidence is preferred.
Compile-safe verification is mandatory.

---

# 6. Mapping to Pipeline Artifacts

The agents emit `workspace/verification_result.json` validated against
`.claude/schemas/verification_result.schema.json`. The contract maps to that
artifact as follows:

| Contract section | verification_result field |
|---|---|
| Static Verification findings | `evidence[]` entries prefixed `static:` + `static_verification` object |
| Runtime Verification findings | `evidence[]` entries prefixed `runtime:` + `runtime_verification` object |
| Confidence HIGH/MEDIUM/LOW | `risk_level` (LOW/MEDIUM/HIGH — inverse: HIGH confidence → LOW risk) |
| Blocking Issues | `status="BLOCKED"` or `status="FAIL"` with `fail_reason` |

The `static_verification` and `runtime_verification` blocks are OPTIONAL in
the schema for backward compatibility, but the contract requires both to be
populated unless explicitly impossible. When omitted, the omitter must
record the reason in `notes`.

---

# 7. When Either Layer is Impossible

"Explicitly impossible" means one of:

- The project has no Unity Test Framework package installed (runtime
  verification falls back to Deterministic Runtime Checklist — still
  required, just lower in the priority order).
- The change is documentation-only (`.md` files, no `.cs` touched).
- The change is to `.claude/`, `.serena/`, or other agent-config files that
  do not affect the Unity build.

In every other case: both layers are required. If you skip a layer without a
documented reason, the orchestrator's `finalize` gate must reject the run.
