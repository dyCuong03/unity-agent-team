# Agent Knowledge Policy
<!-- Per-agent rules for reading workspace knowledge files. -->

## Core Rule

Agents read the minimum knowledge needed to do their job correctly.
They do NOT read all workspace files. They do NOT read full files — only relevant sections.

## Reading Protocol (all agents)

Before starting work, every agent:
1. Reads `workspace/domain-analysis.md` (if session is in Phase 2+)
2. Reads relevant sections of `workspace/repo-knowledge.md` (by tag matching)
3. Reads filtered entries of `workspace/recent-changes.md` (via relevance-filtering.md)
4. Reads the specific session workspace file it needs (design.md, investigation.md, etc.)

Total reading budget: 800 tokens (knowledge-token-budget.md).

## Per-Agent Reading Policy

### `architect`

```
ALWAYS read:
  - workspace/ecs-registry.md (before designing — check existing components)
  - workspace/repo-knowledge.md sections tagged: routing, ownership, architecture_decision
  - workspace/recent-changes.md entries: domain:routing, domain:ecs, domain:hybrid, impact:high

READ IF FEATURE MODE:
  - workspace/domain-analysis.md (system map from system-mapper)
  - workspace/design.md (own output, to append to)

DO NOT read:
  - workspace/investigation.md (architect doesn't debug)
  - workspace/test-plan.md (not architect's concern)
  - workspace/skill-cache/ (architect doesn't call REST skills directly)

After completing work:
  - If architecture decision made: append to workspace/repo-knowledge.md
  - If ownership changed: update workspace/ecs-registry.md
  - If routing changed: append to workspace/recent-changes.md
```

### `unity-dev`

```
ALWAYS read:
  - workspace/design.md (feature mode) OR workspace/investigation.md (bug mode)
  - workspace/ecs-registry.md (before touching any component)
  - workspace/repo-knowledge.md sections tagged: the touched system areas
  - workspace/recent-changes.md entries filtered by: touched code domain + affects:unity-dev

DO NOT read:
  - workspace/migration-plan.md unless --refactor mode
  - workspace/test-plan.md (tester owns this)
  - Full workspace/repo-knowledge.md

After completing work:
  - If implementation reveals architectural drift: append to workspace/recent-changes.md
  - If new ECS component created: update workspace/ecs-registry.md
```

### `tester`

```
ALWAYS read:
  - workspace/test-plan.md (own file)
  - workspace/design.md Acceptance Criteria section (for test matrix)
  - workspace/recent-changes.md entries: risk-category:ownership, risk-category:convention, affects:tester

READ IF BUG MODE:
  - workspace/investigation.md (root cause and regression test guidance)

DO NOT read:
  - workspace/repo-knowledge.md sections unrelated to the tested system
  - workspace/domain-analysis.md (tester inherits domain from design.md)
  - workspace/ecs-registry.md (unless testing an ECS component)

After completing work:
  - If sign-off: save regression anchor to workspace/repo-knowledge.md (via learning-loop.md)
  - If performance regression found: append to workspace/recent-changes.md
```

### `data-tool`

```
ALWAYS read:
  - workspace/design.md (component and system shapes for tooling)
  - workspace/ecs-registry.md (real field names before building inspector)
  - workspace/recent-changes.md entries: domain:tooling, affects:data-tool

DO NOT read:
  - workspace/investigation.md
  - workspace/repo-knowledge.md unless building diagnostics for a specific system

After completing work:
  - If tooling reveals architectural gap: append to workspace/recent-changes.md
```

### `system-mapper`

```
ALWAYS read:
  - workspace/repo-knowledge.md (full relevant sections — system-mapper is the primary updater)
  - workspace/ecs-registry.md (existing system map)
  - workspace/recent-changes.md entries: domain:ecs, domain:routing, domain:hybrid

READ to detect freshness:
  - repo-knowledge.md section confidence scores — if any < 0.60, flag for revalidation

After completing work:
  - Write workspace/domain-analysis.md
  - Update workspace/repo-knowledge.md repo map sections with new session findings
  - Update `verified` dates on confirmed facts
```

### `code-tracer`

```
ALWAYS read:
  - workspace/repo-knowledge.md sections tagged for the feature area
  - workspace/domain-analysis.md (after system-mapper writes it)
  - workspace/recent-changes.md entries filtered by domain and touched files

DO NOT read:
  - workspace/design.md (code-tracer runs before design)
  - workspace/ecs-registry.md unless needed for ownership verification

After completing work:
  - Update workspace/domain-analysis.md with API fingerprinting results
  - If domain reload triggered: write ## Domain Reload section to domain-analysis.md
```

### `bug-investigation`

```
ALWAYS read:
  - workspace/repo-knowledge.md sections tagged: failure-pattern, regression, the affected system
  - workspace/recent-changes.md entries: risk-category:investigation, risk-category:ownership, impact:high
  - agentmemory: search for prior investigations of same symptom (via memory_smart_search)

READ to seed hypothesis:
  - workspace/ecs-registry.md (who owns the mutated component)

After completing work:
  - Write workspace/investigation.md (root cause + fix strategy)
  - Write workspace/domain-analysis.md (API fingerprinting results)
  - If root cause reveals architectural drift: append to workspace/recent-changes.md
  - If quality gate passes: append failure-pattern to workspace/repo-knowledge.md
```

### `refactor-agent`

```
ALWAYS read:
  - workspace/repo-knowledge.md sections tagged: refactor-risk, the target system
  - workspace/ecs-registry.md (blast radius from ownership map)
  - workspace/recent-changes.md entries: domain:ecs, risk-category:ownership, impact:high

After completing work:
  - Write workspace/migration-plan.md
  - If refactor incident: append to workspace/recent-changes.md + workspace/repo-knowledge.md
```

## Knowledge Reading is NOT Blocking

Agents do not wait for knowledge files to be "perfect".
If a file is missing or empty: state the gap and proceed.
If a fact is STALE: note it and prefer MCP evidence.
Knowledge context improves decision quality — it does not gatekeep execution.
