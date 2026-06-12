# Knowledge Token Budget
<!-- Hard token governance for all knowledge loaded per agent per task. -->

## Total Knowledge Budget

Maximum **800 tokens** of knowledge context per agent per task spawn.
This budget covers everything that is "knowledge" — not the task description,
not the agent skill definitions, just the contextual knowledge loaded from workspace files.

## Priority Allocation

Load in priority order. Drop from lowest priority first when budget is tight.

| Priority | Source | Budget | Drop? |
|---------|--------|--------|-------|
| P1 — ECS Core | `unity-dots-best-practices/SKILL.md` | 200 tokens | Never |
| P2 — Foundation | `unity-foundation/SKILL.md` | 100 tokens | Never |
| P3 — Touched-code facts | repo-knowledge.md sections (relevant tags) | 150 tokens | Never |
| P4 — Recent changes | recent-changes.md (filtered entries, max 5) | 75 tokens | When over budget |
| P5 — Domain skills | 2 domain modules (cache hits: 150t; misses: 400t) | 150–400 tokens | Drop 1 if needed |
| P6 — Investigation | investigation/SKILL.md | 100 tokens | Drop if DOTS/Unity domain only |
| Total (cache hits) | | ~775 tokens | — |
| Total (cache miss ×2) | | ~1025 tokens | Drop P6 + 1 domain |

## Drop Order

When total exceeds 800 tokens:

```
Step 1: Drop P6 (investigation layer) if not an investigation agent — saves 100 tokens
Step 2: Drop lower-scoring domain module — saves 150-400 tokens
Step 3: Drop P4 (recent-changes) entries below score 0.60 — saves ~15-30 tokens each
Step 4: Truncate P3 repo-knowledge sections to 100 tokens (drop lower-scoring sections)
Step 5: Never drop P1 or P2
```

## Per-Agent Budget Profiles

| Agent | P1 | P2 | P3 | P4 | P5 | P6 | Total |
|-------|----|----|----|----|----|----|-------|
| `architect` | 200 | 100 | 150 | 75 | 150 | — | 675 |
| `unity-dev` | 200 | 100 | 150 | 75 | 300 | — | 825 → drop 1 domain if cache miss |
| `data-tool` | 200 | 100 | 100 | 75 | 150 | — | 625 |
| `tester` | 200 | 100 | 100 | 75 | 150 | — | 625 |
| `system-mapper` | 200 | 100 | 150 | 75 | — | 100 | 625 |
| `code-tracer` | 200 | 100 | 100 | 75 | — | 100 | 575 |
| `bug-investigation` | 200 | 100 | 150 | 75 | — | 100 | 625 |
| `refactor-agent` | 200 | 100 | 150 | 75 | — | 100 | 625 |

## Budget Enforcement

At STEP 1.5, before spawning each agent:

```python
def compute_knowledge_budget(agent_type, domain_modules, cache_hits):
    budget = {
        "p1": 200, "p2": 100, "p3": 150, "p4": 75,
        "p5": sum(150 if m in cache_hits else 400 for m in domain_modules[:2]),
        "p6": 100 if agent_type in INVESTIGATION_AGENTS else 0
    }
    total = sum(budget.values())

    if total > 800:
        if budget["p6"] > 0 and agent_type not in INVESTIGATION_AGENTS:
            total -= budget.pop("p6")
        while total > 800 and len(domain_modules) > 1:
            domain_modules.pop()  # remove lowest-scoring domain module
            total -= 150  # approximate
        if total > 800:
            budget["p3"] = 100  # truncate repo-knowledge sections

    return budget
```

## Cache Hit Importance

Cache hits save 250 tokens per domain module (400 → 150).
A session with 2 agents sharing 1 module saves 250 tokens minimum.
Maintaining fresh caches is the single highest-ROI token optimization.

## What Is NOT in the Budget

- Task description and arguments: not knowledge, not counted
- Agent role SKILL.md (architect/SKILL.md, unity-dev/SKILL.md): role definition, not knowledge
- Workspace output files (investigation.md, design.md): agents write these, not read as knowledge input
