# Change Impact System
<!-- Metadata on recent-changes.md entries to drive targeted agent notification. -->

## Purpose

Not every agent needs to read every recent change.
Impact metadata routes each change only to the agents that need to know.

## Full Entry Format (extended)

```
[DATE] domain:<d> impact:<high|medium|low> affects:<agents> risk-category:<category>
change: <one line>
risk: <one line>
```

Field: `risk-category`

| Category | Meaning |
|----------|---------|
| `routing` | Changes how tasks are classified or skills are loaded |
| `ownership` | Changes which stack or agent owns a piece of state |
| `performance` | Changes ECS frame budget or Unity rendering cost |
| `safety` | Changes MCP phase gates or escalation thresholds |
| `investigation` | Changes how bugs are traced or root causes found |
| `tooling` | Changes editor tools, validators, or data-tool behavior |
| `convention` | New pattern discovered or naming convention changed |

## Impact Classification Rules

```
impact:high if:
  - breaks existing behavior (agents following old rules will produce wrong output)
  - changes ownership of runtime state
  - changes a safety/escalation threshold
  - adds or removes a mandatory step in any flow

impact:medium if:
  - changes routing or skill loading (different skills loaded, same behavior)
  - changes a fact in repo-knowledge.md that agents apply in decisions
  - changes workspace file schema

impact:low if:
  - additive only (new entry, new option, new advisory module)
  - documentation clarification
  - threshold loosened (more permissive, not breaking)
```

## Agent Notification Rules

When an agent reads recent-changes.md (via relevance-filtering.md), the filtering
also checks `affects` to determine if the entry applies to that agent specifically.

**Any entry tagged `affects:all`:** every agent reads it if relevance score ≥ 0.50.

**Entries tagged with specific agents:**
Only those agents read it (and their pipeline dependencies).

```python
AGENT_DEPENDENCIES = {
    "unity-dev":       ["architect"],    # unity-dev reads architect-relevant changes
    "tester":          ["unity-dev"],    # tester reads unity-dev-relevant changes
    "data-tool":       ["unity-dev"],    # data-tool reads unity-dev-relevant changes
    "architect":       [],               # architect has no upstream
    "bug-investigation": ["architect"],  # bug-investigation reads architecture changes
}
```

## Impact Propagation Example

Entry:
```
[2026-05-22] domain:routing impact:high affects:all risk-category:routing
change: domain scoring DOTS_MAX recalibrated 2.0 → 1.20
risk: DOTS domain classified for fewer APIs — more Ambiguous escalations
```

This entry affects ALL agents because:
- routing change = every agent's domain classification is affected
- impact:high = cannot be skipped

Entry:
```
[2026-05-21] domain:unity impact:medium affects:unity-dev,tester risk-category:convention
change: PopupPresenter now uses async Show/Hide lifecycle
risk: tests checking synchronous popup state will fail
```

This entry affects only unity-dev and tester — architect and investigation agents skip it.

## Writing Impact Metadata

When writing a recent-changes.md entry, the author must set:
1. `impact`: based on impact classification rules above
2. `affects`: the minimum set of agents that must know this change
3. `risk-category`: from the table above

If unsure about `affects`: use `all` (conservative, never wrong).
If unsure about `impact`: use `medium` (default).
