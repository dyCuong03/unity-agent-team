# Knowledge Decay System
<!-- Prevents stale facts in repo-knowledge.md from misleading agents. -->

## Core Problem

repo-knowledge.md facts are written once but the codebase changes.
A fact written 6 months ago may be wrong today.
Agents reading it may make decisions based on outdated architecture.

## Fact Format

Every fact entry in repo-knowledge.md must include a confidence footer:

```markdown
## [tag:<tag>] <Title>
<fact content>

<!-- confidence:0.91 verified:2026-05-22 source:architect-run -->
```

Fields:
- `confidence`: 0.00–1.00 (starts at 1.00 for fresh facts)
- `verified`: last date this fact was confirmed still accurate
- `source`: which agent or trigger confirmed it (architect-run, tester-run, manual, migration)

## Decay Schedule

Confidence decreases automatically based on days since `verified`:

```python
def current_confidence(base_confidence, days_since_verified, fact_type):
    decay_rate = {
        "architecture_decision": 0.02,   # -2% per 7 days (slow decay)
        "failure_pattern":       0.04,   # -4% per 7 days
        "performance_finding":   0.05,   # -5% per 7 days (fast decay — Unity version changes)
        "regression_anchor":     0.01,   # -1% per 7 days (very stable)
        "refactor_risk":         0.03,   # -3% per 7 days
        "ownership_boundary":    0.02,   # -2% per 7 days
    }
    weekly_decay = decay_rate.get(fact_type, 0.03)
    weeks = days_since_verified / 7
    return max(0.10, base_confidence - (weekly_decay * weeks))
```

## Confidence Thresholds

| Confidence | Status | Agent behavior |
|-----------|--------|----------------|
| 0.80–1.00 | CURRENT — use as-is | Read and apply |
| 0.60–0.79 | AGING — use with caution | Read, note caveat, prefer MCP verification |
| 0.40–0.59 | NEEDS_REVALIDATION | Include in prompt but flag for recheck |
| < 0.40 | STALE | Mark [STALE] — do not apply, trigger revalidation |

## Stale Marker

When confidence falls below 0.40, the fact is marked:

```markdown
## [STALE: confidence<0.40 as of 2026-08-01] [tag:popup] Popup System Architecture
...
<!-- confidence:0.38 verified:2026-05-22 source:architect-run -->
```

Agents skip STALE facts. Architect reviews and either revalidates or removes.

## Revalidation Triggers

A fact is revalidated (confidence reset to 1.00) when:
- system-mapper runs and confirms the fact via CRG evidence
- architect approves a design that touches the fact's system
- tester sign-off covers the fact's affected system
- MCP evidence confirms the fact during investigation

On revalidation: update `verified` date and `source`. Do not reset `confidence` from decay if
the fact content was not confirmed — only update if the fact is explicitly checked.

## Who Manages Decay

- `architect` checks for STALE entries when `workspace/ecs-registry.md` has system removals
- `system-mapper` updates `verified` dates when it touches the relevant system in CRG
- Orchestrator appends a decay check result to `recent-changes.md` if a STALE fact is found:

```
[DATE] domain:general impact:medium affects:architect
change: <fact title> confidence below 0.40 — stale
risk: agents may apply outdated architectural facts
```

## Freshness on Read

Before applying a fact, agents check:
```python
if fact.confidence < 0.40:
    skip(fact)  # STALE — do not use
elif fact.confidence < 0.60:
    note("Aging fact — verify with MCP if decision depends on it")
else:
    apply(fact)
```
