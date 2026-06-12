# Recent Changes System
<!-- Defines workspace/recent-changes.md — the agent-facing architectural awareness layer. -->

## Purpose

A rolling, compressed, agent-readable record of architectural changes made in the last 14 days.
Sits between CHANGELOG.md (human, unbounded) and repo-knowledge.md (agent, stable facts).

Agents read this instead of the full CHANGELOG.md.
Maximum 300 tokens. Never grows beyond that.

## File Location

`workspace/recent-changes.md` — persistent (commit to repo alongside repo-knowledge.md).

## Entry Format

```
[DATE] domain:<domain> impact:<high|medium|low> affects:<agent1,agent2,...>
change: <one line — exactly what changed, specific>
risk: <one line — what breaks or behaves differently>
```

- DATE: YYYY-MM-DD
- domain: routing | ecs | unity | hybrid | mcp | workspace | investigation | skills | escalation | general
- impact: high (breaks existing behavior) | medium (changes routing or ownership) | low (additive only)
- affects: comma-separated agent names, or `all`
- change: ≤ 12 words
- risk: ≤ 12 words

## Example Entries

Example (illustrative class names):

```
[2026-05-22] domain:routing impact:medium affects:all
change: hybrid domain threshold changed 0.65 → 0.50
risk: more tasks classified Hybrid — extra skill slots used

[2026-05-22] domain:ecs impact:high affects:unity-dev,tester
change: HealthSystem added sync point before WeaponSystem
risk: frame budget increased ~0.8ms at 10k entities

[2026-05-21] domain:workspace impact:low affects:all
change: domain-analysis.md added to session workspace reset
risk: none — additive change

[2026-05-20] domain:skills impact:medium affects:unity-dev
change: ui/SKILL.md updated — ui_create_label removed
risk: any cached ui.cache.md is stale — invalidate
```

## Pruning Rule

At the start of each write operation:
1. Remove all entries with DATE older than 14 days from today
2. If total token count after pruning > 300: remove oldest entries first until ≤ 300
3. Never remove entries tagged impact:high until they are > 14 days old

## Who Writes

Any agent that triggers a qualifying change (see change-trigger-policy.md).
The orchestrator writes on behalf of agents during session completion.
Format must be exact — no prose, no explanation, only structured entries.

## Who Reads

All agents read this file as part of STEP 1.5 (after workspace reset, before spawning).
Agents filter entries by domain and affects using relevance-filtering.md.
They do NOT read all entries — they filter first.

## Freshness Contract

- An entry is CURRENT if its DATE is within 14 days.
- An entry is EXPIRED if older than 14 days — pruned on next write.
- An entry with impact:high is retained for 21 days before pruning.

## What This File Is NOT

- Not a full architectural log (that is CHANGELOG.md)
- Not a permanent fact store (that is repo-knowledge.md)
- Not session-scoped (it persists across sessions, committed to git)
- Not a debug log (that is workspace/investigation.md)
