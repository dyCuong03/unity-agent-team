---
description: Bug-fix workflow — CRG-first root cause investigation, targeted fix, regression test, sign-off.
argument-hint: "<bug description>"
---

# `/bugfix` — Bug-Fix Workflow

**Philosophy:** Prove root cause before writing a single line of fix code. Fix only what is broken. Pin the fix with a regression test.

**Flow:** Sequential investigation → parallel fix + test-prep → verification sign-off.

---

## STEP 1 — Investigate (sequential, wait for result)

Spawn `bug-investigation` and **wait for it to complete** before proceeding. Do not spawn unity-dev until root cause is confirmed.

```
Agent({
  subagent_type: "bug-investigation",
  description: "Root cause investigation",
  prompt: "@.claude/skills/codebase-understanding/SKILL.md @.claude/rules/GRAPH_FIRST.md\n\nBug: $ARGUMENTS\n\nTrace root cause using code-review-graph first:\n1. Define the symptom precisely — what state is wrong, when, under what condition.\n2. trace_execution_flow from symptom to entry point.\n3. Identify writers and readers of the mutated state.\n4. get_impact_radius — what else could be affected by a fix?\n5. Inspect only systems identified by graph evidence.\n\nDeliver:\n- Root cause (with evidence chain)\n- Impacted systems\n- Safe fix strategy (minimal blast radius, preserves behavior)\n- Regression test guidance (what to assert, under what condition)"
})
```

**Stop here.** Read the investigation output fully before moving to Step 2.

---

## STEP 2 — Fix + Test prep (parallel)

Spawn both agents in a **single message** with the investigation findings embedded in each prompt. Replace `<INVESTIGATION_OUTPUT>` with the full output from Step 1.

**Unity Dev — implement the fix**

```
Agent({
  subagent_type: "unity-dev",
  description: "Implement bug fix",
  prompt: "@.claude/skills/unity-dev/SKILL.md @.claude/skills/unity-dots-best-practices/SKILL.md\n\nBug: $ARGUMENTS\n\nInvestigation findings:\n<INVESTIGATION_OUTPUT>\n\nFix rules:\n- Implement the safe fix strategy exactly as described above.\n- Fix only the identified root cause — do not refactor surrounding code.\n- Minimal change, maximum precision.\n- All C# edits via mcp__ai-game-developer__script-update-or-create.\n- After fixing, SendMessage to tester: 'Fix applied. Systems changed: <list>. Ready for verification.'"
})
```

**Tester — prepare regression test**

```
Agent({
  subagent_type: "tester",
  description: "Regression test for bug fix",
  prompt: "@.claude/skills/tester/SKILL.md @.claude/skills/qa-validation/SKILL.md\n\nBug: $ARGUMENTS\n\nInvestigation findings:\n<INVESTIGATION_OUTPUT>\n\nTest prep rules:\n- Design a regression test that pins this exact root cause.\n- The test must fail before the fix and pass after it.\n- Assert the specific state that was wrong (from the evidence chain above).\n- Do not write the test yet — outline the assertion and setup. Wait for unity-dev's 'Fix applied' message before executing.\n- On receipt of that message: implement and run the regression test. Report: pass/fail + evidence."
})
```

---

## STEP 3 — Verification sign-off (sequential)

Wait for tester to report test results.

**Pass**: tester reports regression test passes + no adjacent regressions. Task complete.

**Fail**: return the failure report to unity-dev with the test evidence. Loop back to Step 2 until tester signs off.

---

## Quality Gates

| Gate | Rule | Enforcer |
|------|------|----------|
| G1 | Root cause proven by graph evidence before fix starts | bug-investigation |
| G2 | Fix is minimal — only the identified root cause, no refactor | unity-dev |
| G3 | Regression test must fail before fix, pass after | tester |
| G4 | No sign-off without test evidence | tester |
| G5 | Adjacent regressions block sign-off | tester |

---

## Completion Output

```
[Bugfix] Done

Bug: <description>

[Investigation]
  Root cause: <precise statement>
  Evidence chain: <numbered steps>
  Impacted systems: <list>

[Fix]
  Changed: <files / systems>
  Strategy applied: <what was done>

[Regression Test]
  Test: <name / assertion>
  Result: PASS
  Adjacent regressions: none / <list if any>

Sign-off: <tester verdict>
Open risks: <list>
```

---

## Usage

```sh
# Describe the symptom as precisely as possible
/bugfix Enemies stop chasing player after teleporting to a new zone

/bugfix Health bar shows wrong value when two damage sources apply in the same frame

/bugfix Zone_10 spawner points disappear after rapid teleport — Region_1
```
