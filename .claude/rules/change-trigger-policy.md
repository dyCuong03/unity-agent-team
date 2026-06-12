# Change Trigger Policy
<!-- Defines WHEN to write to workspace/recent-changes.md and CHANGELOG.md. -->

## Core Rule

Write only when a meaningful architectural mutation occurs.
Do NOT write for trivial changes, formatting, or non-architectural edits.

## Triggers — ALWAYS write recent-changes.md entry

The Example column uses illustrative class names — not tied to any specific project.

| Trigger | Domain tag | Example |
|---------|-----------|---------|
| New agent added or removed | `general` | code-tracer added; codebase-reader removed |
| Domain routing threshold changed | `routing` | hybrid threshold 0.65 → 0.50 |
| Ownership boundary changed | `hybrid` or `ecs` | PopupPresenter moved to ScreenService |
| MCP phase gate changed | `mcp` | Phase 2 now allows prefab_apply |
| Workspace schema changed | `workspace` | domain-analysis.md added to session files |
| ECS architecture changed | `ecs` | System execution order changed |
| Skill module loading rule changed | `skills` | ui/SKILL.md excluded from DOTS domain |
| Investigation strategy changed | `investigation` | CRG fallback threshold updated |
| Escalation trigger rule changed | `escalation` | BLOCK threshold >3 systems → >2 systems |
| New architectural convention discovered | `general` | Presenter pattern mapped to ui skill |
| API fingerprint weight changed | `routing` | ISystem weight 0.20 → 0.25 |
| Domain scoring threshold changed | `routing` | DOTS_MAX recalibrated to 1.20 |

## Triggers — write CHANGELOG.md entry (and recent-changes.md if above applies)

- Any of the above triggers
- New feature or workflow added to the agent system
- Significant bug fixed in orchestration logic
- New rule file added
- New workspace file type added

## DO NOT write any entry for:

- Formatting fixes in markdown files
- Typo corrections
- Comment clarifications
- README prose updates
- Version bump without behavior change
- Adding examples without changing rules
- Workspace session files cleared/reset (this is expected behavior)

## Who Writes What

| Agent | Writes to |
|-------|-----------|
| `architect` | recent-changes.md + repo-knowledge.md (architecture decisions) |
| `unity-dev` | recent-changes.md (if implementation changes a convention) |
| `refactor-agent` | recent-changes.md (blast radius findings) |
| `bug-investigation` | recent-changes.md (if root cause reveals architectural drift) |
| orchestrator | recent-changes.md (post-session summary) + CHANGELOG.md |
| human engineer | CHANGELOG.md (always), recent-changes.md (optional) |

## Entry Quality Gate

Before writing any entry:
1. Is this change architectural? (affects routing, ownership, scheduling, conventions)
2. Will a future agent make wrong decisions without knowing this?
3. Is this information not already in repo-knowledge.md as a stable fact?

If all three: YES → write entry.
If any: NO → skip.

## Deduplication

Before writing, scan recent-changes.md for an existing entry with the same `domain` tag
and `change` description. If found: update the DATE and risk field; do not add a duplicate.
