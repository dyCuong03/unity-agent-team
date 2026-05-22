# Bug Investigation Output
<!-- SESSION-SCOPED — cleared at start of each /team --bug run -->
<!-- Owner: bug-investigation | Readers: unity-dev, tester -->

## Status
<!-- bug-investigation sets one of: IN_PROGRESS | COMPLETE | INCONCLUSIVE -->
STATUS: IN_PROGRESS

---

## Bug Description
<!-- Paste the /team --bug task description here -->

---

## Memory Recall
<!-- Result of agentmemory search before CRG investigation -->
<!-- Format: FOUND: <prior investigation summary> | NOT_FOUND -->
Prior investigation:

---

## Symptom Definition
<!-- Precise: what state is wrong, when, under what condition -->

**Wrong state:**

**Condition:**

**Reproducible steps:**

---

## CRG Trace

### Execution Flow
<!-- trace_execution_flow result — numbered steps from symptom to entry point -->

1.
2.
3.

### Component Writers
<!-- Who writes the mutated state -->

| Component | Writer system | Write condition |
|-----------|--------------|-----------------|

### Impact Radius
<!-- get_impact_radius result — what else changes if we fix this -->

---

## Root Cause
<!-- Precise statement — must be supported by evidence above -->

**Root cause:**

**Evidence chain:**
1.
2.
3.

---

## Safe Fix Strategy
<!-- Minimal change, preserves behavior, no refactor -->

**Change required:**

**Files to touch:**

**Must NOT touch:**

**ECS safety notes:**
- [ ] No structural changes in scheduled jobs
- [ ] System update order preserved
- [ ] [BurstCompile] preserved on hot paths
- [ ] No managed allocations added

---

## Regression Test Guidance
<!-- What tester must assert, under what condition, expected baseline: FAIL -->

**Test assertion:**

**Setup condition:**

**Expected pre-fix result:** FAIL

---

## Memory Save
<!-- bug-investigation saves this after delivering output -->
<!-- mcp__agentmemory__memory_lesson_save with: symptom + root cause + fix strategy -->
Saved: [ ]
