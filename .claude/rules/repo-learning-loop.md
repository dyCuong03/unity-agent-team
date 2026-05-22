# Repository Learning Loop
<!-- Defines when, what, and how agents save engineering knowledge to workspace/repo-knowledge.md and agentmemory. -->

## Purpose

Agents accumulate actionable engineering knowledge over time.
Knowledge must be non-obvious, specific, and high-signal.
Knowledge must NOT accumulate noise.

## Two Persistence Layers

| Layer | Location | Lifetime | Owner |
|-------|----------|---------|-------|
| Session knowledge | `workspace/repo-knowledge.md` | Persistent (commit to repo) | Defined per section |
| Cross-project memory | `agentmemory` via `memory_lesson_save` | Persistent cross-session | Defined per trigger |

## Learning Triggers

### Trigger 1: Successful Bug Fix

**When:** tester writes STATUS: PASSED to `workspace/test-plan.md`

**Who writes:** `bug-investigation` agent

**What to save to repo-knowledge.md:**

```markdown
## Failure Pattern: <short title>
Date: <YYYY-MM-DD>
Symptom: <exact error or behavior>
Root cause: <one sentence — specific system and component>
Affected systems: <list>
Detection signals: <what to look for — log pattern, profiler spike, etc.>
Fix applied: <what changed — file:line level>
Regression test: <test name that now pins this>
Skill modules used: <modules that were relevant to investigation>
```

**Quality gate:** Do NOT save if:
- Root cause was "null reference" with no specific ECS system implicated
- Fix was <3 lines and obviously self-explanatory from the code
- Pattern already exists in repo-knowledge.md (dedupe by symptom + affected system)

**What to save to agentmemory:**

```
mcp__agentmemory__memory_lesson_save({
  "lesson": "In <project>: <symptom> → root cause: <system>.<component>. Fix: <what>. Detection: <signal>.",
  "tags": ["bug", "<system_name>", "<module_name>"]
})
```

---

### Trigger 2: Approved Architecture Decision

**When:** architect sets STATUS: APPROVED in `workspace/design.md`

**Who writes:** `architect` agent

**What to save to repo-knowledge.md:**

```markdown
## Architecture Decision: <title>
Date: <YYYY-MM-DD>
Feature: <feature description>
Decision: <what was decided>
Reason: <why — constraint, performance, ECS policy>
Alternatives considered: <what was rejected and why>
Components added to registry: <list — should match ecs-registry.md>
Risk if violated: <what breaks if future code ignores this>
```

**Quality gate:** Do NOT save if:
- Decision is derivable from DOTS documentation alone
- Decision is "use IComponentData" without project-specific context
- A similar decision for the same system already exists

---

### Trigger 3: Tester Sign-Off with Regression Evidence

**When:** tester writes STATUS: PASSED + adjacent regression check CLEAR

**Who writes:** `tester` agent

**What to save to repo-knowledge.md:**

```markdown
## Regression Anchor: <test name>
Date: <YYYY-MM-DD>
Covers: <what system/behavior this test protects>
Trigger condition: <what must be true for this test to be relevant>
Critical assertion: <the one assertion that matters>
Adjacent systems to check: <systems that must still pass when this area changes>
```

**Quality gate:** Do NOT save if:
- Test is a trivial null check
- Test covers a system that is not part of the hot path or frequently changed

---

### Trigger 4: Performance Regression Found

**When:** `profiler_get_stats` or `performance/SKILL.md` advisory reveals a regression during investigation

**Who writes:** `data-tool` or `tester`

**What to save to repo-knowledge.md:**

```markdown
## Performance Finding: <system name>
Date: <YYYY-MM-DD>
System: <ISystem or MonoBehaviour>
Hotspot: <what was slow — specific method, job, or query>
Baseline: <frame time or memory before>
Regressed to: <frame time or memory after>
Root cause: <managed allocation / sync point / query breadth>
Fix applied: <what resolved it>
Detection: <profiler metric to watch — draw calls, GC alloc, job ms>
```

**Quality gate:** Do NOT save if:
- Performance issue was <1ms impact at target entity count
- Finding duplicates an existing entry

---

### Trigger 5: Refactor Incident (Step Failed During Migration)

**When:** tester writes "Step N FAIL" to `workspace/migration-plan.md`

**Who writes:** `refactor-agent`

**What to save to repo-knowledge.md:**

```markdown
## Refactor Risk: <system or symbol name>
Date: <YYYY-MM-DD>
Target: <what was being refactored>
Step that failed: <step N description>
Root cause of failure: <why the step broke behavior>
Blast radius underestimated: <what was missed in the initial impact analysis>
Detection: <how to detect this risk in future CRG analysis>
Corrected rollback: <what the actual safe rollback was>
```

**Quality gate:** Do NOT save if:
- Failure was a trivial compile error (missing using directive)
- Failure was already covered by an existing blast radius entry

---

## Knowledge Format Rules

Each entry MUST:
- Be ≤ 200 tokens (enforced by format above)
- Name specific systems, components, or files
- Include a detection signal (what to look for)
- Include a date

Each entry MUST NOT:
- Be vague ("this was tricky")
- Repeat general DOTS documentation
- Reference temporary file paths or session-specific state
- Contradict the DOTS Conflict Resolution Policy in CLAUDE.md

## Retention Policy

### Persistent Entries (never delete automatically)
- Architecture decisions with `Risk if violated` filled
- Regression anchors (test names)
- Refactor risks with blast radius details

### Stale Entries (mark for review)

An entry becomes stale when:
- The affected system has been renamed or removed (detectable via CRG)
- The detection signal no longer applies (test deleted, system refactored)
- The entry is >180 days old and the system has had major changes

Stale entries are marked:
```
## [STALE: <reason>] Failure Pattern: <title>
```
They are NOT deleted automatically — architect reviews and removes on next session in that area.

### Cleanup Strategy

The `architect` agent checks for stale entries when:
- system-mapper updates `repo-knowledge.md` with a new system map
- `workspace/ecs-registry.md` has entries removed (system deleted)

Cleanup rule: if an entry references a system that no longer exists in `ecs-registry.md`:
1. Mark entry [STALE: system removed]
2. Write [ESCALATE: stale learning entry — review needed] to workspace

Do NOT auto-delete. Human review required before removal.

## Knowledge Bloat Prevention

### Deduplication

Before writing any new entry:
1. Search `repo-knowledge.md` for the same symptom + system combination
2. If found: UPDATE the existing entry with the new date and findings
3. If not found: append new entry

Maximum entries per section:
- Failure Patterns: 20 (remove oldest when exceeded, keep [STALE] ones for 30 days)
- Architecture Decisions: unlimited (these are permanent unless system is removed)
- Regression Anchors: 1 per test name
- Performance Findings: 10 per system
- Refactor Risks: 10 per target symbol

### Noise Gate

The orchestrator applies a noise gate before writing:

```python
def should_save(entry):
    if len(entry.affected_systems) == 0:
        return False  # too vague
    if entry.detection_signal is None:
        return False  # not actionable
    if entry.is_duplicate_of_existing():
        return False  # dedupe
    if entry.fix_lines_changed < 3 and entry.root_cause.is_obvious():
        return False  # too trivial
    return True
```

## agentmemory Cross-Project Lessons

In addition to repo-knowledge.md (project-local), agents save cross-project lessons to agentmemory for patterns that appear across Unity projects:

Save to agentmemory when:
- Bug pattern is common across Unity versions (e.g., Addressables handle leak)
- Performance pattern applies to any DOTS project (e.g., archetype churn in hot loop)
- Architecture decision is a reusable DOTS principle

Do NOT save to agentmemory:
- Project-specific component names
- Session-specific paths
- Anything that requires the project context to make sense
