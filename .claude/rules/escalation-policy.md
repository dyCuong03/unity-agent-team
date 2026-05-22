# Escalation Policy
<!-- Mandatory escalation triggers with routing rules. No discretion on AUTO_ESCALATE or BLOCK conditions. -->

## Signal Types

| Signal | Blocking? | Who handles | Orchestrator action |
|--------|-----------|-------------|---------------------|
| `[AUTO_ESCALATE]` | No — continues but flags | Responsible upstream agent | Appends to workspace open risks; continues |
| `[BLOCK]` | Yes — halts phase | Architect or orchestrator | Halts current phase; routes to handler |
| `[ESCALATE_ARCHITECT]` | Yes | Architect | Architect must respond before phase resumes |
| `[ESCALATE_TESTER]` | No | Tester | Tester adds to test matrix; continues |
| `[ESCALATE_HUMAN]` | Yes | Human engineer | Orchestrator pauses; awaits human input |

## Category 1: Architecture Risk

### AUTO_ESCALATE triggers (non-blocking)

```
[AUTO_ESCALATE: architecture]
Condition: bug fix touches exactly 2 systems (borderline scope)
Who fires: unity-dev
Routed to: architect (informational)
Action: architect reviews workspace/design.md and confirms boundary is respected
```

```
[AUTO_ESCALATE: architecture]
Condition: new ECS component added but NOT in workspace/ecs-registry.md
Who fires: unity-dev
Routed to: architect
Action: architect updates ecs-registry.md before tester runs
```

### BLOCK triggers (hard stop)

```
[BLOCK: architecture risk]
Condition: bug fix touches >3 systems (exceeds expected blast radius)
Who fires: unity-dev, bug-investigation
Routed to: ESCALATE_ARCHITECT
Action: halt Phase 2; architect must approve expanded scope before implementation continues
```

```
[BLOCK: architecture risk]
Condition: system execution order ([UpdateBefore/After]) changed without explicit architect design
Who fires: unity-dev
Routed to: ESCALATE_ARCHITECT
Action: halt; architect must verify scheduling safety before commit
```

```
[BLOCK: architecture risk]
Condition: singleton component (SystemAPI.GetSingleton<T>) ownership changed
Who fires: unity-dev
Routed to: ESCALATE_ARCHITECT
Action: halt; singleton ownership is an architecture decision
```

```
[BLOCK: architecture risk]
Condition: ECS structural change (AddComponent/RemoveComponent) in a system that was previously non-structural
Who fires: unity-dev
Routed to: ESCALATE_ARCHITECT
Action: halt; structural change cost must be explicitly approved
```

---

## Category 2: Performance Risk

### AUTO_ESCALATE triggers

```
[AUTO_ESCALATE: performance]
Condition: managed allocation introduced in OnUpdate (LINQ, new List<>, string format)
Who fires: unity-dev (ECS Safety Checklist)
Routed to: ESCALATE_TESTER (add to test matrix)
Action: tester adds GC alloc check to test plan
```

```
[AUTO_ESCALATE: performance]
Condition: profiler shows >10% frame time increase after implementation
Who fires: tester (Phase 3 profiler check)
Routed to: ESCALATE_ARCHITECT (for scope decision)
Action: architect decides if regression is acceptable or must be fixed before sign-off
```

### BLOCK triggers

```
[BLOCK: performance]
Condition: [BurstCompile] removed from any ISystem that had it before
Who fires: unity-dev (ECS Safety Checklist)
Routed to: ESCALATE_ARCHITECT
Action: halt; Burst removal on hot-path system requires explicit architect approval
```

```
[BLOCK: performance]
Condition: synchronization point (CompleteAll, Dependency.Complete()) added in a system that previously had none
Who fires: unity-dev (ECS Safety Checklist)
Routed to: ESCALATE_ARCHITECT
Action: halt; sync point cost must be explicitly designed — not accidentally introduced
```

```
[BLOCK: performance]
Condition: tester measures >50% frame time regression in Play Mode
Who fires: tester
Routed to: ESCALATE_HUMAN
Action: halt sign-off; human engineer decision required (performance regression too severe)
```

---

## Category 3: Runtime Risk

### AUTO_ESCALATE triggers

```
[AUTO_ESCALATE: runtime]
Condition: any prefab that is also a baker input prefab is modified
Who fires: unity-dev
Routed to: ESCALATE_TESTER
Action: tester adds baker output validation to test plan
```

```
[AUTO_ESCALATE: runtime]
Condition: save data serialization format touched (any serialized field renamed/removed)
Who fires: unity-dev
Routed to: ESCALATE_ARCHITECT + ESCALATE_HUMAN
Action: architect confirms backward compatibility; human approves save data migration risk
```

### BLOCK triggers

```
[BLOCK: runtime]
Condition: networking/Netcode components or systems modified (NetworkVariable, Spawn, RPC)
Who fires: unity-dev
Routed to: ESCALATE_ARCHITECT
Action: halt; networking changes require explicit architect design — multiplayer behavior is high blast-radius
```

```
[BLOCK: runtime]
Condition: scene boot/bootstrap sequence modified (DefaultExecutionOrder(-10000) class changed)
Who fires: unity-dev
Routed to: ESCALATE_ARCHITECT
Action: halt; bootstrap changes affect world initialization order — architect must verify
```

```
[BLOCK: runtime]
Condition: ECS World initialization code changed (World.Create, DefaultWorldInitialization)
Who fires: unity-dev
Routed to: ESCALATE_ARCHITECT + ESCALATE_HUMAN
Action: halt; world initialization change has total system blast radius
```

---

## Category 4: Complexity Risk

### AUTO_ESCALATE triggers

```
[AUTO_ESCALATE: complexity]
Condition: bug fix requires changes to files not in the initial blast radius
Who fires: unity-dev
Routed to: ESCALATE_ARCHITECT (informational)
Action: architect confirms the scope expansion is acceptable
```

```
[AUTO_ESCALATE: complexity]
Condition: bug fix has failed twice (tester reported FAIL twice on same fix)
Who fires: tester (second FAIL)
Routed to: ESCALATE_ARCHITECT
Action: architect reviews investigation findings — root cause may be wrong
```

### BLOCK triggers

```
[BLOCK: complexity]
Condition: change set exceeds 500 lines of code across any files
Who fires: unity-dev
Routed to: ESCALATE_HUMAN
Action: halt; 500 LOC is beyond single-session scope — requires human scope decision
```

```
[BLOCK: complexity]
Condition: bug fix has failed 3+ times (same symptom, different fixes tried)
Who fires: tester (third FAIL)
Routed to: ESCALATE_HUMAN
Action: halt; repeated failures suggest wrong root cause or unknown dependency — human review required
```

```
[BLOCK: complexity]
Condition: CRG impact radius is UNKNOWN (get_impact_radius fails or returns no data)
Who fires: refactor-agent, bug-investigation
Routed to: ESCALATE_HUMAN
Action: halt; proceeding without known impact radius is not safe in production
```

```
[BLOCK: complexity]
Condition: unity-dev signals [SCOPE_EXCEEDED] (--fast-fix exceeded 20 lines/2 files)
Who fires: unity-dev
Routed to: orchestrator (re-run as --bug)
Action: halt fast-fix; orchestrator re-routes as full --bug investigation
```

---

## Escalation Routing Decision Tree

```
Escalation triggered
        │
        ├─ Category = Architecture?
        │       └─ ESCALATE_ARCHITECT → architect reads workspace/design.md
        │                               architect responds with APPROVED or REJECTED
        │                               orchestrator resumes or halts based on response
        │
        ├─ Category = Performance?
        │       ├─ Regression < 50%? → ESCALATE_ARCHITECT (scope decision)
        │       └─ Regression ≥ 50%? → ESCALATE_HUMAN (too severe for agent decision)
        │
        ├─ Category = Runtime?
        │       ├─ Networking/World init? → ESCALATE_ARCHITECT + ESCALATE_HUMAN
        │       └─ Save data/Prefab?      → ESCALATE_ARCHITECT (confirm backward compat)
        │
        └─ Category = Complexity?
                ├─ >500 LOC? → ESCALATE_HUMAN
                ├─ 3+ failed fixes? → ESCALATE_HUMAN
                ├─ Unknown blast radius? → ESCALATE_HUMAN
                └─ Scope exceeded? → orchestrator re-routes
```

## Resolution Requirements

| Escalation type | Resolution required before continuing |
|----------------|--------------------------------------|
| ESCALATE_ARCHITECT | Architect writes APPROVED or REJECTED to workspace with reasoning |
| ESCALATE_TESTER | Tester acknowledges and updates test-plan.md |
| ESCALATE_HUMAN | Human engineer responds in conversation; orchestrator documents decision |
| AUTO_ESCALATE | No resolution required — append to open risks and continue |

## Writing Escalation Signals

Agents write escalation signals to the relevant workspace file:

```markdown
<!-- In workspace/design.md, investigation.md, or migration-plan.md: -->
[BLOCK: architecture risk] System execution order changed without architect approval.
Affected: RegionLoadSystem [UpdateAfter(ZoneInitSystem)] modified.
Resolution required: architect must verify scheduling safety.
```

```markdown
<!-- AUTO_ESCALATE — append to Open Risks section: -->
[AUTO_ESCALATE: performance] Managed allocation introduced in HealthSystem.OnUpdate.
Signal: New List<EntityHitResult>() allocated per frame.
Action needed: tester to add GC alloc assertion to test plan.
```

## Escalation Log

All escalations are appended to `workspace/escalation-log.md` (session-scoped):

```markdown
# Escalation Log

| Time | Type | Category | Signal | Agent | Status |
|------|------|----------|--------|-------|--------|
| Phase 2 | BLOCK | Architecture | system order changed | unity-dev | PENDING |
| Phase 3 | AUTO_ESCALATE | Performance | GC alloc detected | tester | LOGGED |
```

The escalation log is written to `workspace/` — session-scoped but retained if the session produced a BLOCK that was not resolved.
