# Relevance Filtering
<!-- How agents select which recent-changes.md entries apply to the current task. -->

## Purpose

Prevent agents from reading all recent-changes entries.
Select only the entries that affect the current task's domain and touched code.

## Input

- Task description (text)
- Current domain classification (from domain-analysis.md after investigation)
- Affected agents (from phase assignment)

## Filter Algorithm

```python
def filter_recent_changes(entries, task_text, domain, affected_agents):
    scored = []
    for entry in entries:
        score = 0.0

        # Rule 1: domain match
        if entry.domain == domain or entry.domain == "general":
            score += 0.50
        elif entry.domain in related_domains(domain):
            score += 0.25

        # Rule 2: affects match
        if "all" in entry.affects or current_agent in entry.affects:
            score += 0.30

        # Rule 3: keyword match in task text
        keywords = extract_keywords(task_text)
        entry_text = entry.change + " " + entry.risk
        matches = sum(1 for kw in keywords if kw.lower() in entry_text.lower())
        score += min(0.20, matches * 0.07)

        # Rule 4: impact multiplier
        if entry.impact == "high":   score *= 1.30
        if entry.impact == "medium": score *= 1.00
        if entry.impact == "low":    score *= 0.70

        if score >= 0.50:
            scored.append((score, entry))

    # Sort by score descending, return top N within token budget
    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:MAX_ENTRIES]]  # MAX_ENTRIES = 5

MAX_ENTRIES = 5  # max 5 entries per agent = ~75 tokens
```

## Domain Relationship Map

```python
def related_domains(domain):
    relationships = {
        "ecs":         ["hybrid", "routing", "investigation"],
        "unity":       ["hybrid", "skills", "routing"],
        "hybrid":      ["ecs", "unity", "routing"],
        "routing":     ["ecs", "unity", "hybrid", "skills"],
        "mcp":         ["investigation", "escalation"],
        "workspace":   ["investigation", "general"],
        "skills":      ["routing", "ecs", "unity"],
        "escalation":  ["investigation", "general"],
        "investigation": ["ecs", "unity", "hybrid"],
        "general":     []  # matches everything via Rule 1
    }
    return relationships.get(domain, [])
```

## Priority Rules

When two entries have the same score, sort by:
1. impact:high before impact:medium before impact:low
2. More recent DATE first
3. Domain exact match before related domain match

## Fallback Rules

If no entries score ≥ 0.50:
- Include any entry tagged impact:high (regardless of score)
- If still none: return empty list (no recent-changes context loaded)
- Do NOT force-load entries just to fill the slot

If domain is "Ambiguous" (not yet classified):
- Include entries for all domains with score ≥ 0.30
- Cap at 3 entries

## Output Format

Filtered entries are included in the agent prompt as (example — illustrative class names):

```
## Relevant Recent Changes (filtered from recent-changes.md)
[2026-05-22] domain:routing impact:medium
change: hybrid threshold changed 0.65 → 0.50
risk: more tasks classified Hybrid

[2026-05-21] domain:hybrid impact:high
change: HealthBarBinding ownership moved to ECS
risk: check existing binding code before implementing
```

If no relevant entries: omit section entirely — do not print empty header.

## Token Budget for Filtered Changes

Maximum 5 entries × 15 tokens each = ~75 tokens per agent.
This replaces reading any portion of CHANGELOG.md (~200–500 tokens for tail).
