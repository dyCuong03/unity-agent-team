# Workspace Knowledge Layout
<!-- Complete definition of workspace/ — ownership, lifecycle, token cost, write triggers. -->

## Directory Structure

```
workspace/
├── repo-knowledge.md        ← PERSISTENT — commit to repo
├── ecs-registry.md          ← PERSISTENT — commit to repo
├── recent-changes.md        ← PERSISTENT — commit to repo (rolling 14 days)
├── domain-analysis.md       ← SESSION-SCOPED — reset at each run start
├── design.md                ← SESSION-SCOPED
├── investigation.md         ← SESSION-SCOPED
├── test-plan.md             ← SESSION-SCOPED
├── migration-plan.md        ← SESSION-SCOPED
├── escalation-log.md        ← SESSION-SCOPED (retained if BLOCK unresolved)
└── skill-cache/
    ├── ui.cache.md          ← SESSION-SCOPED (hash-invalidated)
    ├── netcode.cache.md
    └── ...
```

## File Registry

| File | Owner | Readers | Persist | Token cost | Write trigger |
|------|-------|---------|---------|-----------|---------------|
| `repo-knowledge.md` | `architect` (primary) | All (section retrieval) | Yes | ~150 (filtered) | Learning triggers (repo-learning-loop.md) |
| `ecs-registry.md` | `architect` | All | Yes | ~50 (on-demand) | New components/systems designed |
| `recent-changes.md` | Orchestrator | All (filtered) | Yes | ~75 (5 entries) | change-trigger-policy.md |
| `domain-analysis.md` | Investigation agents | All | No | ~100 | After CRG + fingerprinting |
| `design.md` | `architect` | unity-dev, data-tool, tester | No | ~200 | Feature design complete |
| `investigation.md` | `bug-investigation` | unity-dev, tester | No | ~150 | Root cause found |
| `test-plan.md` | `tester` | unity-dev, architect | No | ~100 | Test matrix written |
| `migration-plan.md` | `refactor-agent` → `architect` | unity-dev, tester | No | ~200 | Phase 1 complete |
| `escalation-log.md` | Orchestrator | All | Conditional | ~50 | Escalation triggered |
| `skill-cache/<m>.cache.md` | Orchestrator | All | No | 150 (hit) / 400 (miss) | First full load of module |

## Persistent File Lifecycle

**repo-knowledge.md:**
- New entries appended when learning triggers fire
- Confidence metadata updated on revalidation
- STALE entries marked (not deleted) when decay threshold reached
- Reviewed by architect on system-mapper runs touching the relevant system

**ecs-registry.md:**
- New entries added when architect designs new components/systems
- Existing entries updated when systems are refactored
- Entries removed only when system is confirmed deleted from codebase

**recent-changes.md:**
- New entries appended when change-trigger-policy.md conditions are met
- Entries older than 14 days pruned on each write
- impact:high entries retained for 21 days
- Total never exceeds 300 tokens

## Session Reset Protocol

At start of each `/team` run (STEP 1.5):

```sh
# Session-scoped files — always reset
cp .claude/workspace-templates/domain-analysis.md workspace/domain-analysis.md
cp .claude/workspace-templates/escalation-log.md workspace/escalation-log.md
# design.md, investigation.md, test-plan.md, migration-plan.md are created fresh per mode

# Skill cache — hash-invalidate stale entries (see skill-cache-freshness.md)
for cache_file in workspace/skill-cache/*.cache.md; do
    # compare hash, delete if stale
done

# recent-changes.md — DO NOT reset, it persists across sessions
# repo-knowledge.md — DO NOT reset, it persists across sessions
# ecs-registry.md — DO NOT reset, it persists across sessions
```

## .gitignore Guidance

```
# Session-scoped workspace files — do not commit
workspace/domain-analysis.md
workspace/design.md
workspace/investigation.md
workspace/test-plan.md
workspace/migration-plan.md
workspace/escalation-log.md
workspace/skill-cache/

# Persistent workspace files — commit these
# workspace/repo-knowledge.md
# workspace/ecs-registry.md
# workspace/recent-changes.md
```
