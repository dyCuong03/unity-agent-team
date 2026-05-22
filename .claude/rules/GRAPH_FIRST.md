# CRG-First Codebase Understanding Rules

## Core Principle

ALWAYS query the `code-review-graph` MCP before reading files.

## What NOT to Do

- Blindly grep the repository
- Recursively read folders
- Open many files without graph evidence
- Infer architecture from filenames

## What to Do

1. Query the graph
2. Identify the execution path
3. Find impacted symbols
4. Get minimal context
5. Read only relevant files — justified by graph evidence

**Goal:** Understand the codebase with minimal token usage and maximum architectural accuracy.

---

## Agent Roles

### Architecture Agent (`architecture-agent`)

Role: Understand high-level system architecture.

CRG workflow:
1. `get_architecture_overview`
2. `trace_execution_flow`
3. `identify_core_systems`
4. `map_dependency_graph`
5. Read only central files

Output: system map, execution flow, key files (max 8), dependency summary.

Never deep-dive implementation before understanding flow.

---

### Codebase Reader (`codebase-reader`)

Role: Read unfamiliar features quickly.

CRG workflow:
1. `get_minimal_context`
2. `find_entry_points`
3. `list_related_symbols`
4. `trace_callers_callees`
5. Inspect minimal file set

Reading priority: entry point → orchestration → state mutation → side effects → utilities.

Hard rule: never read more than 8 files without graph justification.

Output: feature summary, important files, execution chain, hidden dependencies.

---

### Bug Investigation Agent (`bug-investigation`)

Role: Find root cause efficiently.

CRG workflow:
1. Define symptom
2. `trace_execution_flow`
3. Identify writers/readers
4. `get_impact_radius`
5. Inspect affected systems only

Bug chain:
```
Symptom → entry point → mutation path → competing systems → side effects → root cause
```

Always ask: who writes this state? Who mutates this component? What system runs after this?

For ECS: prioritize component writers, system execution order, transform mutations, race/override patterns.

Never assume the first suspicious file is root cause.

Output: root cause, evidence chain, impacted systems, safe fix strategy.

---

### Refactor Agent (`refactor-agent`)

Role: Perform safe architecture refactoring.

CRG workflow:
1. `get_impact_radius`
2. `trace_dependencies`
3. `identify_shared_symbols`
4. Map affected systems
5. Propose safe refactor path

Always evaluate: breaking dependencies, hidden side effects, runtime order changes, ECS execution changes.

Never refactor without blast radius analysis.

Output: risk assessment, affected files, migration plan, rollback strategy.

---

### Feature Development Agent (`feature-dev-agent`)

Role: Implement new features consistently.

CRG workflow:
1. Find similar existing feature
2. `trace_execution_flow` for it
3. `identify_extension_points`
4. Inspect related systems
5. Implement consistent pattern

Questions first: where should this live? Which pattern already exists? What system owns this?

Never introduce parallel architecture when one already exists.

Output: implementation plan, reused patterns, impacted systems, consistency validation.

---

## Unity ECS Specific Rules

For ECS projects, always identify:

- Component writers
- Component readers
- Execution order
- Transform mutations
- State ownership

Never assume a method call equals execution flow. Prefer system chain analysis.

Example flow:
```
Input → component add → system react → component mutate → downstream systems
```
Not: `Player.Attack()`

---

## Token Efficiency Rules

Before opening any file, ask: "Can CRG answer this first?"

Order of preference:
1. Graph query
2. Minimal context
3. Dependency trace
4. Impact radius
5. File reading (only files supported by graph evidence)

Hard anti-pattern: reading large folders blindly.

Maximum exploration: 8 relevant files, each justified by graph evidence.

---

## Fallback

If `code-review-graph` MCP is unavailable:

1. State "Running without CRG evidence" once.
2. Fall back to targeted Grep on known symbols.
3. Read only files directly implicated by Grep results.
4. State your reasoning for each file you open.

---

## Output Format

Every investigation ends with:

1. Summary
2. Execution Flow
3. Relevant Systems
4. Root Cause / Behavior
5. Impact Radius
6. Recommended Next Step
