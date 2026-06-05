---
name: agentmemory-codebase-recall
description: >
  Structured protocol for using agentmemory as a recall layer during codebase investigation.
  Load when any agent would otherwise start with broad Read/Grep/Glob exploration.
  agentmemory accelerates orientation — it is NOT a substitute for reading current source files.
user-invocable: false
---

# agentmemory Codebase Recall

This is a skill pack, not an agent. Load it when triage indicates prior sessions exist
for the touched system, or when an investigation, bug-fix, or feature task would benefit
from prior architectural knowledge.

## Core Contract

**agentmemory is a recall layer. It is NOT the source of truth.**

Current repo files always win. Memory surfaces candidate files, known pitfalls, and
architectural decisions from prior sessions. Every memory hit must be verified against
the actual file before being acted on.

| Principle | Meaning |
|-----------|---------|
| Recall before exploration | Query memory before opening files or running Grep |
| Verify before using | Read the current file; memory may be stale |
| Files win on conflict | If memory contradicts current source → trust the file |
| Never edit from memory alone | A memory fact is a hypothesis; code read confirms it |
| Never claim from memory alone | Do not assert architecture facts without file evidence |

---

## Mandatory Flow

```
agentmemory query
       │
       ▼ candidate files / symbols / known pitfalls
targeted file discovery (Read, Grep on known paths only)
       │
       ▼ current source text
verify memory against files
       │
       ▼ confirmed facts only
analyze / edit / implement
       │
       ▼ after task completes
save findings (mcp__agentmemory__memory_lesson_save or memory_save)
```

Do NOT skip to "targeted file discovery" without first running the memory query.
Do NOT skip the "verify against files" step even if memory looks confident.

---

## Tool Reference

The following tools are confirmed present in this project's MCP configuration.
Do NOT invent tool names — use only these.

> **Note:** The canonical source for the agentmemory MCP server capabilities is
> https://github.com/rohitg00/agentmemory — verify tool names against current docs
> if the list below ever diverges from actual MCP responses.

### Query tools (use BEFORE opening files)

| Tool | When to use |
|------|-------------|
| `mcp__agentmemory__memory_smart_search` | First call — natural-language search across all sessions. Pass the symptom, system name, or component name. |
| `mcp__agentmemory__memory_recall` | Direct recall by tag or session ID when you know the exact context. |
| `mcp__agentmemory__memory_sessions` | List prior sessions to find relevant context when smart_search returns nothing useful. |

### Save tools (use AFTER task completes)

| Tool | When to use |
|------|-------------|
| `mcp__agentmemory__memory_lesson_save` | Save a structured lesson: root cause, fix, detection signal, affected systems. Preferred for bug fixes and architecture decisions. |
| `mcp__agentmemory__memory_save` | Save raw notes, scratch, or partial findings when a full lesson isn't appropriate. |

### Maintenance tools (use only when directed)

| Tool | When to use |
|------|-------------|
| `mcp__agentmemory__memory_reflect` | Summarise or re-index a session's memories. Run when a session accumulated many unstructured saves. |
| `mcp__agentmemory__memory_consolidate` | Merge duplicate or redundant memories. Run when prior sessions produced overlapping lessons. |
| `mcp__agentmemory__memory_diagnose` | Check agentmemory health, index integrity, or connection issues. |

---

## Query Discipline

### Step 1 — Smart search first

```
mcp__agentmemory__memory_smart_search(
  query: "<symptom or system name>",
  tags:  ["<domain>", "<component>"]   // optional — improves recall precision
)
```

Good queries: component names (`HealthComponent`), system names (`DamageSystem`),
symptoms (`"ECB dropped dependency"`), patterns (`"structural change in job"`).

Bad queries: generic terms (`"bug"`, `"Unity"`, `"system"`).

### Step 2 — Interpret results

Each memory hit has a confidence score. Apply this policy:

| Confidence | Treatment |
|------------|-----------|
| High (≥ 0.80) | Use as strong candidate — still verify in file |
| Medium (0.50–0.79) | Use as weak hint — read file before trusting |
| Low (< 0.50) | Note but do not prioritise — likely stale or out-of-context |

### Step 3 — Targeted file discovery

Use memory output to form **specific** Read/Grep targets:
- "memory says `DamageSystem.cs` owned `HealthComponent` writes" → `Read DamageSystem.cs`
- "memory warns about dropped Dependency in `WeaponSystem`" → grep for `state.Dependency` in `WeaponSystem.cs`

Do NOT issue broad `Glob("**/*.cs")` or `Read`-all-in-folder after memory returns results.

---

## Unavailability Fallback

If any `mcp__agentmemory__*` call fails with a connection error or the server is unreachable:

1. Report `[MEMORY UNAVAILABLE]` once in your output.
2. Do NOT retry in a loop.
3. Fall back to **targeted repo search** — Grep known symbol names, Read specific files
   from triage / approved_plan. No random exploration.
4. If this is a bug investigation: note the gap in `workspace/investigation.md`:
   `"Prior session recall unavailable — investigation proceeds from code evidence only."`

---

## Save Discipline

After completing a task, save one lesson per non-obvious finding. Quality gate:

**Save if:**
- Root cause was not obvious from a single file read
- A DOTS pitfall was discovered (Dependency drop, ECB singleton mismatch, Burst error)
- An architecture decision was made that future agents should know
- A component ownership boundary was clarified or changed

**Do NOT save if:**
- The fix was ≤ 3 lines and self-explanatory from the code
- The finding repeats something already in `workspace/repo-knowledge.md` verbatim
- The session produced only read-only investigation with no confirmed conclusions

### Lesson format for `memory_lesson_save`

```
lesson: "In <project>: <symptom> → root cause: <SystemName>.<field/component>. 
         Fix: <what changed>. Detection: <signal to look for>."
tags: ["<system-area>", "<domain>", "<component-name>"]
```

Example:
```
lesson: "In BackpackAdventures: enemies stop moving after area transition → root cause:
         MovementSystem drops state.Dependency when CombatSystem schedules first.
         Fix: combine handles with JobHandle.CombineDependencies. 
         Detection: profile job overlap in frame after transition."
tags: ["movement", "ecs", "dependency-chain", "combat"]
```

---

## DOTS-Specific Recall Hints

When querying memory for a DOTS bug or feature, always include these recall probes
if the standard smart_search returns low-confidence results:

| Probe | Why it matters |
|-------|---------------|
| `"update order <SystemName>"` | Prior ordering decisions are invisible in code; memory captures them |
| `"ECB playback <system group>"` | Wrong ECB singleton is a common silent bug |
| `"state.Dependency <SystemName>"` | Dropped dependency produces no error — only stale reads |
| `"component ownership <ComponentName>"` | Dual ownership surfaces here before it surfaces in tests |
| `"Burst error <job name>"` | Burst failures are often project-specific type mismatches |
| `"IEnableableComponent <ComponentName>"` | Toggles vs add/remove decisions are architectural |
| `"ComponentLookup update <SystemName>"` | Stale lookup is a common oversight after refactor |
| `"NativeContainer lifetime <SystemName>"` | Disposal gaps only appear under domain reload or scene change |
| `"Schedule ScheduleParallel <JobName>"` | Parallelism decisions carry hidden constraints |

---

## Self-Check Before Moving to Implementation

- [ ] `memory_smart_search` was called before any `Read`/`Grep`/`Glob`
- [ ] Each memory hit was verified against the current file (not assumed correct)
- [ ] No edit or claim was made based solely on memory output
- [ ] If memory was unavailable: `[MEMORY UNAVAILABLE]` was reported once
- [ ] At least one `memory_lesson_save` queued for end-of-task (if findings are non-trivial)

---

## Anti-Patterns

- Opening broad file lists before querying memory
- Trusting a 6-month-old memory fact without re-reading the file
- Skipping memory because "I already know this system"
- Saving every trivial read as a lesson (noise bloat)
- Using `memory_consolidate` or `memory_reflect` during an active investigation (maintenance ops, not investigation ops)
