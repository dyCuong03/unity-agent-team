---
name: codebase-understanding
description: CRG-first codebase navigation skill for all agents. Load when architecture must be traced, execution flow understood, impact radius determined, or entry points located before any implementation. Always queries code-review-graph before opening files — prevents blind file reads.
use-when: |
  Load for any agent that needs to understand an unfamiliar system before working on it.
  Load at the start of bug investigation, feature design, or refactor planning.
  Load whenever an agent would otherwise start with broad Read/Grep/Glob.
do-not-use-when: |
  Do not load when the task is a trivial change to a well-known file that requires no
  architecture investigation. Not needed for a quick comment fix or rename.
platforms: [claude-code, codex, copilot, cursor, windsurf]
task-categories: [navigation, analysis, investigation, architecture]
metadata:
  source: internal
  version: 1.0.0
  tier: 1

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
