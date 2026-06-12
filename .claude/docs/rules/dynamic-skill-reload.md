# Dynamic Skill Reload
<!-- When investigation contradicts initial domain classification, update and reload. -->

## Trigger Condition

Dynamic reload activates when:

```python
def should_reload(initial_domain, evidence_domain):
    return (
        evidence_domain != initial_domain
        and confidence_in_evidence > 0.70
    )
```

## When This Happens

### Scenario 1: Keyword suggested X, code says Y

Initial guess from task text: NavMesh bug (Unity domain, keyword "stuck on navmesh").
Investigation finds: PhysicsVelocity overwrite in EnemyMovementSystem.cs.
API scan: DOTS_score 0.82. Unity_score 0.31.

Action:
1. Update workspace/domain-analysis.md with revised scores and `## Reload Reason`
2. Drop navmesh from skill loading
3. Add physics + movement DOTS skills
4. Orchestrator reads updated domain-analysis.md before spawning unity-dev

---

### Scenario 2: Feature task expands scope

Initial guess: UI feature (Unity domain, "add inventory screen").
Investigation finds: Screen reads from DynamicBuffer<InventoryItem> on player entity.
API scan: Hybrid_score rises to 0.72 (both Canvas + DynamicBuffer<T> found).

Action:
1. Reclassify as Hybrid
2. Load both ui + ecs data flow skills
3. Require hybrid contract in workspace/design.md before architect approves

---

### Scenario 3: Bug reveals unexpected system interaction

Initial guess: Animation issue (Unity domain, "animation not playing").
Investigation finds: AnimationTriggerSystem.cs using ECB to enable a component that Animator reads.
API scan: DOTS_score 0.61. Unity_score 0.67. Hybrid_score 0.74.

Action:
1. Reclassify as Hybrid
2. Load animator (Unity) + ECS state management (DOTS) skills
3. Define contract: DOTS signals animation state, Unity Animator reads it

---

## Reload Protocol

```
1. code-tracer / bug-investigation detects domain contradiction
2. Writes to workspace/domain-analysis.md:
   ## Domain Reload
   Previous domain: <domain>
   Revised domain: <domain>
   Reason: <API evidence that contradicts initial classification>
   New scores: DOTS:<x> Unity:<y> Hybrid:<z>
   Skills added: <list>
   Skills removed: <list>

3. Orchestrator reads updated domain-analysis.md
4. Orchestrator adds new skill @-imports and removes obsolete ones
5. unity-dev receives updated prompt with new domain and skills
```

## What Does NOT Trigger Reload

- Keyword mismatch alone (without API evidence)
- Score change < 0.15 from initial
- Score change that does not cross a domain threshold boundary
- Ambiguous → Ambiguous (still escalate)

## Token Cost of Reload

Reload adds minimal tokens: only the changed skill entries, not a full re-investigation.
If a cache miss occurs for newly loaded skills, apply cache-miss protocol from cross-agent-skill-cache.md.
