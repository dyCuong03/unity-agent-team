# Knowledge Ownership Model
<!-- Single source of truth for every fact type. No overlapping responsibility. -->

## Core Rule

Every architectural fact lives in exactly one file.
When the same fact appears in two files, one is the owner and the other is wrong.

## Ownership Table

| Fact type | Owner file | Access | TTL |
|-----------|-----------|--------|-----|
| Human-readable change history | `CHANGELOG.md` | Human only | Permanent |
| Recent architectural mutations | `workspace/recent-changes.md` | Agents (filtered) | Rolling 14 days |
| Stable architecture facts | `workspace/repo-knowledge.md` | All agents | Permanent (with decay) |
| ECS component/system ownership | `workspace/ecs-registry.md` | All agents | Permanent |
| Session domain classification | `workspace/domain-analysis.md` | All agents (session) | Session-scoped |
| Bug root cause + fix | `workspace/investigation.md` | unity-dev, tester | Session-scoped |
| Feature design | `workspace/design.md` | All agents (session) | Session-scoped |
| Refactor migration steps | `workspace/migration-plan.md` | unity-dev, tester | Session-scoped |
| Test plan and results | `workspace/test-plan.md` | unity-dev, architect | Session-scoped |
| Escalation history | `workspace/escalation-log.md` | All agents | Session (retain if BLOCK) |
| Skill summaries (cache) | `workspace/skill-cache/<m>.cache.md` | All agents | Session (hash-invalidated) |

## Strict Ownership Rules

### CHANGELOG.md — Human Historical Log

- Owner: human engineer
- Contains: every meaningful change, with context, readable prose
- Does NOT contain: agent routing facts, confidence scores, decay metadata
- Agents NEVER read this file in prompts
- Grows indefinitely — no pruning

### workspace/recent-changes.md — Recent Mutations (Agent-Facing)

- Owner: orchestrator (on behalf of triggering agent)
- Contains: compressed architectural mutations from last 14 days
- Does NOT contain: prose explanation, full context, stable facts
- Read by: agents via relevance-filtering.md
- Agents NEVER copy content from here to repo-knowledge.md

### workspace/repo-knowledge.md — Stable Architecture Facts

- Owner: architect (primary), other agents (append only with quality gate)
- Contains: stable ECS architecture, failure patterns, performance findings, regression anchors
- Does NOT contain: recent changes (those go in recent-changes.md), session state (domain-analysis)
- Read by: all agents, filtered by section tags
- Each entry must have confidence/verified/source footer

### workspace/ecs-registry.md — ECS Ownership Map

- Owner: architect
- Contains: component and system registry with ownership rules
- Does NOT contain: failure patterns, routing rules, skill decisions
- This is the single source of truth for "who owns HealthComponent"

### workspace/domain-analysis.md — Session Reasoning

- Owner: investigation agents (system-mapper, code-tracer, bug-investigation)
- Contains: domain scores, API evidence, touched files, routing decisions — for THIS session
- Does NOT contain: permanent facts (those go to repo-knowledge.md after session)
- Cleared at start of each new session

### workspace/investigation.md — Bug Investigation Output

- Owner: bug-investigation
- Contains: root cause, evidence chain, fix strategy — for THIS session only
- Does NOT contain: permanent patterns (those are extracted to repo-knowledge.md if they pass quality gate)

## Cross-Contamination Rules

1. Do NOT copy a domain-analysis.md fact to repo-knowledge.md without architect approval
2. Do NOT copy a recent-changes.md entry to repo-knowledge.md — they serve different purposes
3. Do NOT put architectural facts in investigation.md — that file is session-scoped
4. Do NOT read CHANGELOG.md in any agent prompt — use recent-changes.md instead
5. Do NOT duplicate ECS ownership between ecs-registry.md and repo-knowledge.md

## Resolution When Conflict Found

If the same fact appears in two owner files with different values:
- Owner file wins — the other is stale
- Write [ESCALATE: knowledge conflict — <fact> in <file1> contradicts <file2>] to escalation-log
- Architect resolves before session continues
