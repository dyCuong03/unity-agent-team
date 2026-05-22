# Cross-Agent Skill Cache
<!-- Prevents redundant full SKILL.md loading across agents in the same session. -->

## Problem

Without a cache, 3 agents loading `ui/SKILL.md` (400 tokens each) = 1200 tokens.
With cache: first agent loads full (400), others load summary (150 each) = 700 tokens.
Saving: 42% per duplicated module.

## Mechanism

The cache lives in `workspace/skill-cache/` — session-scoped files written during the session.
Each entry is a 150-token summary of a full SKILL.md.

```
workspace/
└── skill-cache/
    ├── ui.cache.md           ← written after first load of ui/SKILL.md
    ├── netcode.cache.md
    └── performance.cache.md
```

Session-scoped: `workspace/skill-cache/` is cleared at the start of each `/team` run (like other session files).

## Ownership Rules

| Rule | Detail |
|------|--------|
| First loader is the writer | The first agent that loads a module's full SKILL.md writes its cache summary |
| Owner is not exclusive | Any agent can read the cache — ownership only controls who writes |
| Cache is write-once per session | Once written, the summary is not updated until next session |
| Only the routing layer writes | Agents do not write cache directly — the orchestrator writes after each Phase 1 load |

## Cache Entry Format (target: 150 tokens)

```markdown
# <module> SKILL Cache
<!-- Written by: <agent> at Phase <N> -->
<!-- Source: .claude/skills/unity-skills/skills/<module>/SKILL.md -->

## Callable Skills (top 5)
<skill_name_1>, <skill_name_2>, <skill_name_3>, <skill_name_4>, <skill_name_5>

## Mode
<FullAuto | SemiAuto | Mixed | Advisory-only>

## Key Rules (max 3)
- <most important rule>
- <most important DO NOT>
- <most important parameter note>

## DO NOT Hallucinate
<top 3 hallucinated skill names that do not exist>
```

## Example Cache Entry: ui.cache.md

```markdown
# ui SKILL Cache
<!-- Written by: unity-dev at Phase 3 (--feature run) -->

## Callable Skills (top 5)
ui_create_canvas, ui_create_button, ui_create_panel, ui_create_text, ui_layout_children

## Mode
FullAuto

## Key Rules
- Use ui_create_canvas before any other UI skill
- ui_create_label does not exist — use ui_create_text
- ui_create_checkbox does not exist — use ui_create_toggle

## DO NOT Hallucinate
ui_add_canvas, ui_create_label, ui_create_checkbox
```

## Orchestrator Write Protocol

After Phase 1 (investigation) and Phase 2 (architect) complete, before spawning Phase 3 agents:

```
For each domain module M selected by skill routing:
  If workspace/skill-cache/<M>.cache.md does not exist:
    First agent that uses M is designated WRITER
    After that agent completes: orchestrator extracts 150-token summary → writes to skill-cache/<M>.cache.md
  If workspace/skill-cache/<M>.cache.md already exists:
    All subsequent agents receive @workspace/skill-cache/<M>.cache.md (150 tokens)
    instead of @.claude/skills/unity-skills/skills/<M>/SKILL.md (400 tokens)
```

## Agent Prompt Integration

In agent prompts, the orchestrator substitutes based on cache state:

```
# Cache HIT (module already loaded this session):
"Read workspace/skill-cache/ui.cache.md for UI skill reference."

# Cache MISS (first load this session):
"@.claude/skills/unity-skills/skills/ui/SKILL.md"
[orchestrator writes cache after this agent completes]
```

## Cache Invalidation

Invalidate (delete) a cache entry when:
- Unity-Skills version changes (check package.json version)
- The source SKILL.md file has been modified since the session started
- Agent reports that a skill call returned "skill not found" (indicates stale cache)

The orchestrator checks cache validity at STEP 1.5 (preflight):
```sh
# Simple check: cache files older than 24 hours are stale
find workspace/skill-cache/ -name "*.cache.md" -mtime +1 -delete 2>/dev/null
```

## Token Savings Estimate

| Scenario | Without cache | With cache | Saving |
|----------|--------------|------------|--------|
| 1 agent, 1 module | 400 tokens | 400 tokens | 0% |
| 3 agents, 1 shared module | 1200 tokens | 700 tokens | 42% |
| 3 agents, 2 shared modules | 2400 tokens | 1400 tokens | 42% |
| 4 agents, 3 shared modules | 4800 tokens | 2050 tokens | 57% |
| --feature full run (typical) | ~3200 tokens | ~1600 tokens | ~50% |

## Independence Guarantee

Agents read the cache as read-only reference — they do NOT share execution state.
Each agent still operates independently with its own context window.
The cache only reduces redundant prompt tokens — it does not create hidden coupling.

## Stale State Prevention

- Cache is session-scoped (cleared at each run start)
- Cache entries are read-only after writing
- No agent can modify another agent's cache entry
- If an agent detects a discrepancy between cache and actual skill call behavior:
  → Write [ESCALATE: skill-cache stale for <module>] to workspace
  → Orchestrator reloads full SKILL.md for that module in next agent spawn
