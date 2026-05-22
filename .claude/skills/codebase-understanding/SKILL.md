---
name: codebase-understanding
description: CRG-first codebase navigation skill. Load this when you need to understand architecture, trace execution flow, investigate bugs, plan refactors, or implement new features. Always query code-review-graph before opening files.
---

# Codebase Understanding — CRG-First

## Core Rule

Query `code-review-graph` before reading any file. Never guess from filenames. Never grep blindly.

## When to Use Each Agent

| Task | Agent | First CRG Call |
|------|-------|----------------|
| Understand system architecture | `architecture-agent` | `get_architecture_overview` |
| Read an unfamiliar feature | `codebase-reader` | `get_minimal_context` |
| Investigate a bug | `bug-investigation` | `trace_execution_flow` |
| Plan a refactor | `refactor-agent` | `get_impact_radius` |
| Implement a new feature | `feature-dev-agent` | find similar feature |

## CRG Tool Reference

| Tool | Use Case |
|------|----------|
| `get_architecture_overview` | Full system map before any analysis |
| `trace_execution_flow` | Follow what runs in what order |
| `get_minimal_context` | Orient around an unfamiliar symbol |
| `find_entry_points` | Where does this feature start? |
| `list_related_symbols` | What symbols participate in this feature? |
| `trace_callers_callees` | Who calls this? What does it call? |
| `get_impact_radius` | What breaks if I change this? |
| `trace_dependencies` | What does this depend on? |
| `identify_shared_symbols` | What is used by many callers? |
| `identify_extension_points` | Where does new code attach? |

## File Read Limit

Maximum 8 files per investigation, each justified by graph evidence.

## Fallback (no CRG)

State "Running without CRG evidence" once. Use targeted Grep on known symbols. Read only files directly implicated. State your reasoning for each file opened.

## Output Template

```
## Summary
<one paragraph>

## Execution Flow
<numbered steps>

## Relevant Systems
<list with ownership>

## Root Cause / Behavior
<precise statement>

## Impact Radius
<what would change if this is modified>

## Recommended Next Step
<single concrete action>
```
