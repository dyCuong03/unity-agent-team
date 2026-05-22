# Workspace File Ownership

This workspace is shared across all agents in a session.
Each file has exactly one writer and defined readers.
No agent writes to a file it does not own.

---

## File Registry

| File | Owner (writes) | Readers | Persistence |
|------|---------------|---------|-------------|
| `repo-knowledge.md` | `system-mapper` | all agents | **persistent** — commit to repo |
| `ecs-registry.md` | `architect` | all agents | **persistent** — commit to repo |
| `design.md` | `architect` | unity-dev, data-tool, tester | session-scoped — cleared per run |
| `investigation.md` | `bug-investigation` | unity-dev, tester | session-scoped — cleared per run |
| `test-plan.md` | `tester` | unity-dev, architect | session-scoped — cleared per run |
| `migration-plan.md` | `refactor-agent` + `architect` | unity-dev, tester | session-scoped — cleared per run |
| `escalation-log.md` | orchestrator | all | session-scoped — retain if unresolved BLOCK |

---

## Rules

- An agent that does not own a file must NOT write to it.
- An agent should READ its input files before starting work.
- Session-scoped files are overwritten at the start of each new `/team` run.
- Persistent files (`repo-knowledge.md`, `ecs-registry.md`) are never overwritten — only appended or updated in place with a datestamp.
- If a persistent file does not exist, create it. If it exists, read it first before updating.

---

## Authority Signals

Any agent may write one of these signals as the first line of its output file to communicate phase status to the orchestrator:

| Signal | Meaning | Orchestrator action |
|--------|---------|---------------------|
| `[BLOCKED: <reason>]` | Agent cannot proceed — hard stop | Halt phase, route to responsible upstream agent |
| `[REJECTED: <reason>]` | Architect rejects design or plan | Halt phase, return to previous phase owner |
| `[ESCALATE: <reason>]` | Non-blocking — flag for human review | Continue but append to open risks |
| `[SCOPE_EXCEEDED]` | unity-dev in --fast-fix exceeded 20 lines | Halt, re-run as --bug |

The orchestrator MUST check for these signals before spawning the next phase.
