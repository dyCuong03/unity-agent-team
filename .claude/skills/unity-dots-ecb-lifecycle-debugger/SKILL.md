---
name: unity-dots-ecb-lifecycle-debugger
description: >-
  ECB playback failure debugger for Unity DOTS/ECS. Load when you see: "EntityCommandBuffer playback
  failed", "entityExists=False", "Buffer does not exist on entity", "Component does not exist on
  entity", "AppendDestroyedEntityRecordError", "Invalid deferred entity", "Duplicate AddComponent
  during playback", "SetComponent on missing component", or "DestroyEntity executed before another
  ECB command". Do NOT load for: MonoBehaviour optimization, ECS architecture design, NavMesh,
  Addressables, UI event listeners, or generic DOTS implementation.
metadata:
  user-invocable: false
  platform-compat:
    - "Unity Entities 1.0+"
    - "Entities 1.3.x (tested)"
    - "Entities 1.4.x (tested)"
  security: >-
    All helper scripts in scripts/ are static syntax-pattern scanners only. They read .cs files
    via regex — no code execution, no writes, no network calls. Safe to run on any DOTS codebase.
use-when: |
  Load for unity-dots-dev and bug-investigation when a Unity console log contains:
  "EntityCommandBuffer playback failed", "entityExists=False", "AppendDestroyedEntityRecordError",
  "Buffer does not exist on entity", "Component does not exist on entity",
  "Invalid deferred entity", "Duplicate AddComponent during playback",
  "SetComponent on missing component", or "DestroyEntity executed before another ECB command".
  Load when debugging ECB command ordering across multiple systems sharing a playback phase.
do-not-use-when: |
  Do not load for MonoBehaviour optimization, ECS architecture design, NavMesh, Addressables,
  UI event listeners, timeline, or generic DOTS implementation. Do not load for tester, verifier,
  qa-tester, or architect roles. Not needed for Burst compilation errors (use burst-safety).
  Not needed for NativeContainer leaks (use memory-safety). Not needed for general ECB usage
  without playback failures (use ecs-job-patterns).
platforms: [claude-code, codex, copilot, cursor, windsurf]
---

# Unity DOTS ECB Lifecycle Debugger

**When to load this skill:**
- Runtime exception contains: `EntityCommandBuffer playback failed`, `entityExists=False`,
  `AppendDestroyedEntityRecordError`, `Buffer does not exist on entity`,
  `Component does not exist on entity`, `Invalid deferred entity`,
  `Duplicate AddComponent during playback`, `SetComponent on missing component`,
  `DestroyEntity executed before another ECB command`
- Question is about ordering of ECB commands across multiple systems targeting the same playback phase
- Entity is valid at record time but invalid at playback time

**When NOT to load this skill:**
- MonoBehaviour performance optimization
- ECS architecture design / component layout planning
- NavMesh, Addressables, UI events, Timeline, Animator
- Generic NullReferenceException without ECB stack trace
- Burst compilation errors (use `burst-safety`)
- NativeContainer leaks (use `memory-safety`)
- General ECS job implementation (use `ecs-job-patterns`)

> **NOT THIS SKILL** — If ECB is being used correctly and you want guidance on patterns
> (when to use which singleton, how to schedule jobs with ECB, ParallelWriter usage),
> load `ecs-job-patterns` instead. This skill starts where `ecs-job-patterns` ends:
> at playback failure. It does not teach correct ECB usage — it diagnoses why playback
> threw an exception.

---

## Core Mental Model

The fundamental ECB trap: **an entity is valid at record time but invalid at playback time.**

```
Frame N:
  ProducerSystem.OnUpdate():
    ecb.AppendToBuffer(TargetEntity, new TargetBufferElement{...})  // entity valid here ✓

  CleanupSystem.OnUpdate():
    ecb.DestroyEntity(TargetEntity)                                  // also valid here ✓

  // Both write to the SAME ECB singleton (same playback point)

Playback at BeginSimulationECBSystem:
  [1] ecb command from CleanupSystem executes first  → TargetEntity destroyed
  [2] ecb command from ProducerSystem executes next  → entityExists=False ✗
```

The guard `if (entityManager.Exists(entity))` before recording is **always wrong** — the entity
exists at record time. The problem is what happens *between record and playback*.

---

## Investigation Flow

Follow these steps in order. Do not skip to a fix before completing Step 5 (root-cause proof).

### Step 1 — Failure Classification

Extract from the exception / console log:

| Field | How to extract |
|-------|----------------|
| Exception type | First line of stack trace |
| Failing ECB operation | The command that threw (AppendToBuffer, SetComponent, AddComponent, DestroyEntity…) |
| Target entity index+version | Shown as `Entity(X:Y)` in error text |
| `entityExists` state | Stated in error: `entityExists=False` means destroyed; `True` = wrong component/buffer |
| Recording system | System name in the stack trace **above** the playback point — NOT the playback ECB system |
| Playback ECB system | The `XxxEntityCommandBufferSystem` shown at the top of the stack |
| ECB phase | Derived from playback system name (Begin/End + group) |
| Job / Burst context | Look for `BurstCompile` attribute or `IJobEntity` in recording system |
| Primary error vs secondary | Primary = first exception; secondary = cascade from destroyed components |

**Do not assume the system named in the stack trace IS the destructive producer.** The playback
system executes commands from *all* producers that wrote to that ECB. The stack trace identifies
the failing command's *recording* origin, not the destroyer.

---

### Step 2 — ECB Producer Inventory

Run the helper script from this skill directory:
```sh
python3 .claude/skills/unity-dots-ecb-lifecycle-debugger/scripts/find_ecb_producers.py <repo-root>
```

Manually verify output. Build a table — use DISCOVERED names from the repo:

| System | File | Update Group | Ordering Attrs | ECB Phase | Operation | Target Expression | Risk |
|--------|------|-------------|---------------|-----------|-----------|------------------|------|
| (discovered) | (file:line) | (group) | ([UpdateAfter...]) | (Begin/End+Group) | AppendToBuffer/Destroy/… | (entity field/var) | high/med/low |

Fill every cell from actual code evidence. A cell cannot be "unknown" — if you cannot determine
it, note "undetermined — read <file>:<line>".

Key patterns to locate (see `find_ecb_producers.py` for full list):
- `BeginSimulationEntityCommandBufferSystem.Singleton`
- `EndSimulationEntityCommandBufferSystem.Singleton`
- `BeginInitializationEntityCommandBufferSystem.Singleton`
- `EndInitializationEntityCommandBufferSystem.Singleton`
- `BeginPresentationEntityCommandBufferSystem.Singleton`
- `.CreateCommandBuffer(state.WorldUnmanaged)`
- `.AsParallelWriter()`
- `ecb.DestroyEntity`, `ecb.AppendToBuffer`, `ecb.AddBuffer`, `ecb.SetBuffer`
- `ecb.AddComponent`, `ecb.SetComponent`, `ecb.RemoveComponent`

**Focus on producers that target the same ECB phase as the failing command's playback system.**

---

### Step 3 — Entity Lifetime Tracing

For the target entity identified in Step 1, trace:

1. **Creation site** — which system/baker creates this entity? (`EntityManager.CreateEntity`,
   `ecb.CreateEntity`, baker `GetEntity()`, prefab instantiation via `ecb.Instantiate`)
2. **Owner** — which system or component "owns" this entity? (stores the entity ref in a component
   or buffer on another entity)
3. **Reference storage** — where is the `Entity` value stored? (field on IComponentData, DynamicBuffer,
   NativeArray, singleton component)
4. **LinkedEntityGroup membership** — is the entity part of a linked group? If so, destroying the
   root also destroys it.
5. **Lifetime states** — does the entity have lifecycle marker components?
   Generic lifecycle: `Created → Initialized → Referenced → Activated → Consumed → MarkedForCleanup → Destroyed`
6. **All destruction paths** — collect EVERY code path that could destroy or remove key components:
   - Direct `ecb.DestroyEntity` / `EntityManager.DestroyEntity`
   - `ecb.RemoveComponent<T>` / `EntityManager.RemoveComponent<T>` (if T is needed by failing op)
   - Cascaded destruction (LinkedEntityGroup, child entities)
   - Pooled return disguised as cleanup
   - State-driven cleanup (tag added → system destroys)
   - Scene-driven cleanup (unload triggers destruction)
7. **Stale reference check** — any system that caches the entity ref in a field and doesn't clear
   it after destruction is a stale-reference source.

---

### Step 4 — Ordering Reconstruction

Run the helper script:
```sh
python3 .claude/skills/unity-dots-ecb-lifecycle-debugger/scripts/find_system_ordering.py <repo-root>
```

Then manually reconstruct the actual execution order for the relevant frame.

**Frame timeline template (10-step minimum):**

```
Frame N execution timeline
──────────────────────────────────────────────────────────────────────────────
Step  | World time | System               | Entity state | Recorded op  | ECB phase
──────┼────────────┼──────────────────────┼──────────────┼──────────────┼──────────
  1   | t=0.000    | [group start]        | alive v=3    | —            | —
  2   | t=0.001    | ProducerSystem       | alive v=3    | AppendToBuffer(E:3) | BeginSim
  3   | t=0.002    | CleanupSystem        | alive v=3    | DestroyEntity(E:3) | BeginSim
  4   | t=0.003    | [group end]          | alive v=3    | —            | —
  5   | t=0.004    | BeginSimECBSystem    | alive v=3    | [playback begins] | —
  6   | t=0.004    | BeginSimECBSystem    | alive→dead   | DestroyEntity executes | —
  7   | t=0.004    | BeginSimECBSystem    | dead         | AppendToBuffer executes → FAIL | —
──────────────────────────────────────────────────────────────────────────────
ROOT CAUSE: CleanupSystem recorded DestroyEntity(E:3) to BeginSimECBSystem; 
ProducerSystem recorded AppendToBuffer(E:3) to same ECB; cleanup command executed 
first; entity version incremented; subsequent AppendToBuffer fails (entityExists=False).
```

Fill with DISCOVERED system names. Use placeholders only when actual system names are not yet known.

**Ordering factors to evaluate:**

1. `[UpdateInGroup]`, `[UpdateBefore]`, `[UpdateAfter]`, `[CreateBefore]`, `[CreateAfter]` on all
   relevant systems
2. Nested group execution order (outer group → inner groups → systems within inner)
3. Systems without explicit ordering attributes: they execute in creation/registration order
   (non-deterministic relative to each other — flag this as a risk)
4. When two separate ECBs both target `BeginSimulationEntityCommandBufferSystem`:
   - Commands from different `CreateCommandBuffer()` calls within the same phase
   - Order is registration order of the ECB singleton, NOT system execution order
5. `AsParallelWriter` sort keys: they control order *within one CB* only, not across CBs
6. Main-thread vs job-recorded commands: both land in same ECB; job commands arrive at
   `AddJobHandleForProducer` time
7. Frame of origin: a command recorded in frame N-1 via a persistent ECB plays in frame N

---

### Step 5 — Root-Cause Proof

Before proposing any fix, prove all of the following:

- [ ] **Exact failing op identified** — `ecb.<op>(Entity(X:Y), ...)` with recording system
- [ ] **Target entity source traced** — where it was created, who owns the ref
- [ ] **All candidate destructive producers listed** — every system that calls DestroyEntity or
      removes a component required by the failing op
- [ ] **Actual producer proven** — not just "probably CleanupSystem" — show the execution order
      evidence that puts its destroy command *before* the failing command in playback
- [ ] **Playback phase confirmed** — both recording and playback ECB singleton match
- [ ] **Record-time guard is insufficient** — document why `if (ecb.Exists(entity))` fails
- [ ] **Ordering is the root cause** — not a race condition, not a missing dependency, not a
      ref-counting error

**Template — Root-Cause Proof Statement:**
```
PROVEN ROOT CAUSE:
  Failing op:         ecb.<op>(Entity(X:Y), <args>)
  Recording system:   <SystemName> at <File>:<Line>
  ECB phase:          <BeginXxx / EndXxx>EntityCommandBufferSystem
  Destructive producer: <SystemName> — ecb.DestroyEntity(Entity(X:Y)) at <File>:<Line>
  Ordering evidence:  <SystemName>[UpdateAfter(X)] executes before recording system [UpdateBefore(Y)]
                      OR: both write to same ECB singleton; cleanup CB registered first
  Why guard fails:    Entity exists at record time (frame N step A); destroyed at playback
                      (frame N step B, B > A); guard at record time cannot see playback-time state
  Rejected causes:    [list any hypotheses considered and ruled out with evidence]
```

---

### Step 6 — Fix Decision Tree

Apply the FIRST applicable fix. Do not apply multiple fixes simultaneously.

```
Is the entity destroyed by a system that MUST run in the same frame as dependents?
  YES →
    Can cleanup be split into two phases?
      YES → Preferred Lifecycle Fix (see below)
      NO  → Can cleanup be delayed one frame via a pending-cleanup tag?
              YES → Pending-Cleanup Tag Fix
              NO  → Consolidate Ownership Fix

Does the failing system record to a DIFFERENT ECB than the destroyer?
  YES →
    Are both ECBs targeting the same playback point?
      YES → Same-ECB Fix (merge to one ECB if local determinism is sufficient)
      NO  → ECB Phase Fix (change one system's ECB to a later playback point)

Is the problem a stale entity reference (entity destroyed but ref not cleared)?
  YES → Stale Reference Fix

Is the problem a deferred entity used across two separate ECBs?
  YES → Deferred Entity Fix (deferred entities are only valid within their origin ECB)

Is the problem ParallelWriter sort keys assumed to order across separate CBs?
  YES → Sort Key Scope Fix (educate: sort keys scope to one CB only)
```

---

#### Preferred Lifecycle Fix — Pending-Cleanup Pattern

Use whatever naming convention the target repo already uses (e.g., the existing marker component
name for "entity is being torn down"). If none exists, introduce a generic marker. The concept:

```
Phase 1 — Request cleanup:
  ProducerSystem detects entity should be cleaned up → adds a PendingCleanup marker component
  (structural change via ECB to an early playback point)

Phase 2 — Dependents finish:
  All systems that reference this entity check for the PendingCleanup marker
  → they complete their last writes (buffers, components) via ECB
  → playback of dependent commands happens BEFORE final destruction

Phase 3 — Final destruction:
  CleanupSystem runs AFTER dependents (explicit [UpdateAfter] or separate ECB phase)
  → reads PendingCleanup entities
  → ecb.DestroyEntity (later playback point than Phase 2)
```

**Implementation constraints:**
- Do NOT introduce a project-specific component name here — use target repo's existing convention
  or propose it in workspace/design.md for architect approval
- Do NOT change `[UpdateBefore/After]` attributes without architect approval
  ([BLOCK: architecture risk] per escalation-policy.md)
- If a new ECB phase is needed, route through architect — changing ECB singletons changes
  system execution contracts

---

#### Pending-Cleanup Tag Fix

When full 3-phase lifecycle is too heavy:
1. Recording system checks: `if (SystemAPI.HasComponent<PendingCleanupTag>(entity)) return;`
2. CleanupSystem adds `PendingCleanupTag` via ECB to an EARLY phase
3. Final DestroyEntity uses a LATER phase ECB
4. Dependents run between early and late phases

---

#### Same-ECB Fix

When destructive producer and dependent producer can deterministically share one ECB:
1. Consolidate to one `CreateCommandBuffer` call → one `ecb` instance
2. Record dependent commands first (lower in OnUpdate), destroy command last
3. Valid ONLY when ordering is local and explicit — not when scheduling is parallel

---

#### ECB Phase Fix

Change the failing system's ECB singleton to a later playback point:
- From `BeginSimulationEntityCommandBufferSystem` → `EndSimulationEntityCommandBufferSystem`
- Verify this does not break OTHER dependencies of the failing system
- Document the new semantic in workspace/design.md (what "end of simulation" means for this system)
- Route through architect if the change affects system group contracts

---

#### Stale Reference Fix

1. Identify the field/buffer that stores the stale entity ref
2. On the cleanup path, add `ecb.SetComponent(ownerEntity, new ComponentWithEntityRef { ref = Entity.Null })`
3. Consumers guard: `if (ref == Entity.Null || !SystemAPI.Exists(ref)) continue;`
4. This is a SECONDARY protection — fix the lifecycle first, then add the guard

---

#### Deferred Entity Fix

Deferred entities (created via `ecb.CreateEntity()` returning a temporary negative index) are
only valid within the ECB that created them. They cannot be stored and reused in a different ECB.

Fix: ensure the entity ref used in all commands originates from the same `ecb.CreateEntity()` call
within the same `CreateCommandBuffer()` scope. If the entity needs to outlive the ECB, bake it
or use a two-step pattern (create + set singleton → other system reads singleton next frame).

---

## Anti-Patterns — Reject These Fixes

| Anti-pattern | Why it fails |
|---|---|
| `if (entityManager.Exists(entity))` guard before recording | Entity exists at record time; guard passes; destroyed before playback |
| `if (!ecb.HasBuffer(entity))` early return | Same timing issue — HasBuffer is main-thread, recorded state is deferred |
| `try { ecb.AppendToBuffer(...) } catch { }` | Swallows the exception; underlying lifecycle bug remains; entity version incremented silently |
| Add `yield return null` or one-frame delay | Arbitrary delay; breaks when frame rate drops; creates new ordering ambiguity |
| Move ALL systems to `EndSimulationEntityCommandBufferSystem` | Shifts the problem; may create new ordering conflicts; breaks systems that need early playback |
| Add `state.Dependency.Complete()` before ECB recording | Sync point that blocks all jobs; expensive; does not fix the recording/playback ordering |
| Disable `[BurstCompile]` on the recording system | Does not affect ECB playback ordering; `[BLOCK: performance]` — never remove Burst from hot-path ISystem |
| Remove the CleanupSystem to "fix" the crash | Hides the symptom; entity memory leaks; cleanup requirements remain |
| Hardcode `[UpdateAfter(CleanupSystem)]` on every dependent | Brittle; creates circular dependency risk; couples unrelated systems; architecture risk |
| Treat `ParallelWriter` sort keys as ordering between separate CBs | Sort keys scope to one CB only; two different CBs registered to the same playback system have their own independent ordering |
| Assume the stack-trace system IS the destructive producer | Stack trace shows the recording origin of the *failing command*, not who destroyed the entity |

---

## Templates

### Template A — Investigation Report

```markdown
## ECB Playback Failure Investigation

### Failure Classification
- Exception type:          [e.g. InvalidOperationException]
- Failing ECB operation:   ecb.<op>(Entity(X:Y), <type>)
- Target entity:           Entity(X:Y)
- entityExists:            [False = destroyed | True = wrong component/buffer]
- Recording system:        <SystemName> at <File>:<Line>
- Playback ECB system:     <XxxEntityCommandBufferSystem>
- ECB phase:               <Begin/End><Group>EntityCommandBufferSystem
- Job/Burst context:       [IJobEntity | main-thread | IJobChunk]
- Primary error:           [exception message]
- Secondary errors:        [cascade exceptions from missing component/buffer]

### ECB Producer Inventory
[Paste table from Step 2]

### Entity Lifetime Trace
- Creation site:           <System> at <File>:<Line>
- Owner:                   <component field on OwnerEntity>
- Reference storage:       <IComponentData field | DynamicBuffer entry | NativeArray>
- LinkedEntityGroup:       [yes/no — root entity]
- Lifecycle states:        Created → … → MarkedForCleanup → Destroyed
- All destruction paths:   [list with file:line]
- Stale refs after cleanup: [list]

### Ordering Reconstruction
[Paste frame timeline from Step 4]

### Root-Cause Proof
[Paste proof statement from Step 5]

### Rejected Fix Candidates
- Guard-only (`Exists` check): [reason it fails in this case]
- [other rejected candidates]

### Selected Fix
- Fix type: [Preferred Lifecycle | Pending-Cleanup Tag | Same-ECB | ECB Phase | Stale Ref | Deferred Entity]
- Change: [what changes, file:line]
- New lifecycle contract: [describe the phases]

### Validation Results
- [ ] Compilation clean
- [ ] Exception no longer thrown
- [ ] Dependent behavior preserved (describe)
- [ ] Final cleanup still executes (describe)
- [ ] No new ECB ordering warnings in console
- [ ] Remaining uncertainty: [any unresolved questions]
```

---

### Template B — ECB Producer Inventory

```markdown
## ECB Producer Inventory

Repo root: <path>
Scan date: <date>
Scanned with: scripts/find_ecb_producers.py + manual verification

| System | File | Update Group | Ordering Attrs | ECB Phase | CB Creation Site | Operation | Target Expression | Component/Buffer Type | Job Type | Parallel Writer | Sort Key | Dep Registration | Risk |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <name> | <file:line> | <group> | [UpdateAfter(...)] | BeginSim | <line> | AppendToBuffer | <var>/<field> | <BufferType> | IJobEntity | yes/no | <expr> | AddJobHandleForProducer | high |
```

---

### Template C — Lifecycle Timeline

```markdown
## ECB Lifecycle Timeline — Frame N

| Step | World time | System | Entity(X:Y) state | Recorded operation | ECB phase | CB identity | Expected | Observed |
|---|---|---|---|---|---|---|---|---|
| 1 | t=N.000 | [SimGroup start] | alive v=Y | — | — | — | alive | alive |
| 2 | t=N.001 | <ProducerSystem> | alive v=Y | AppendToBuffer(E:X:Y, elem) | BeginSim | CB#1 | queued | queued |
| 3 | t=N.002 | <CleanupSystem> | alive v=Y | DestroyEntity(E:X:Y) | BeginSim | CB#2 | queued | queued |
| 4 | t=N.003 | [SimGroup end] | alive v=Y | — | — | — | — | — |
| 5 | t=N.004 | BeginSimECBSystem | alive v=Y | [CB#2 plays] DestroyEntity | — | CB#2 | after CB#1 | BEFORE CB#1 |
| 6 | t=N.004 | BeginSimECBSystem | dead v=Y+1 | [CB#1 plays] AppendToBuffer → FAIL | — | CB#1 | entity alive | entityExists=False |
```

---

## Helper Scripts

Three read-only Python 3 scripts in `scripts/`. Each outputs `file:line` evidence.

Run from repo root:
```sh
python3 .claude/skills/unity-dots-ecb-lifecycle-debugger/scripts/find_ecb_producers.py <repo-root>
python3 .claude/skills/unity-dots-ecb-lifecycle-debugger/scripts/find_destroy_paths.py <repo-root>
python3 .claude/skills/unity-dots-ecb-lifecycle-debugger/scripts/find_system_ordering.py <repo-root>
```

All scripts:
- Read `.cs` files recursively from `<repo-root>`
- Use regex pattern matching only (no compilation, no execution)
- Are read-only — no writes to the target repo
- Have no network calls
- Output structured tables to stdout

---

## Self-Check Before Proposing a Fix

- [ ] Root-cause proof complete (all 7 checkboxes in Step 5 checked)
- [ ] Frame timeline shows the actual ordering with discovered system names
- [ ] Destructive producer identified with file:line evidence (not just "probably")
- [ ] Guard-only fix explicitly considered and rejected with explanation
- [ ] Fix type selected from decision tree
- [ ] Fix does not require changing `[UpdateBefore/After]` without architect approval
- [ ] Fix does not add `state.Dependency.Complete()` without performance review
- [ ] Fix does not remove `[BurstCompile]` (automatic [BLOCK: performance])
- [ ] Validation plan covers: compilation + exception gone + dependent behavior preserved + cleanup still works
