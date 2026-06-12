# Domain-Aware MCP Strategy
<!-- Which Unity-MCP / unity-skills REST calls to make per domain. -->
<!-- Runtime truth overrides reasoning. Always. -->

## Core Rule

Call `unity_diagnose` first, always. Then domain-specific queries.
MCP evidence overrides domain reasoning. If MCP says X, X is true regardless of score.

## DOTS Domain MCP Strategy

**Goal:** Understand ECS system state, scheduling, and entity component data.

### Priority Call Sequence

```
1. unity_diagnose                     ← always first
2. debug_check_compilation            ← ensure compilation clean
3. mcp__ai-game-developer__console-get-logs  ← check for ECS runtime errors
4. profiler_get_stats                 ← frame time, job time
5. profiler_get_object_count          ← entity counts
6. profiler_get_runtime_memory        ← native allocations
7. script_dependency_graph            ← system dependencies
8. scene_analyze                      ← if scene-bound issue
```

### DOTS-Specific Evidence to Collect

- System execution order violations (from console errors or unexpected frame behavior)
- ECB playback errors (structural change in job without ECB)
- Burst compilation failures (from console — `[BurstCompile]` errors)
- NativeContainer aliasing (from safety system errors)
- Job dependency chain violations (from console — AccessViolation or AtomicSafetyHandle)

### What NOT to Query in DOTS Domain

- `ui_find_all`, `animator_get_info` — irrelevant unless hybrid evidence detected
- `prefab_find_instances` on runtime prefabs — entities don't use runtime prefabs
- `gameobject_*` skills — GameObjects are not the runtime data model

---

## Unity Domain MCP Strategy

**Goal:** Understand scene hierarchy, component state, UI state, animation state.

### Priority Call Sequence

```
1. unity_diagnose                     ← always first
2. debug_check_compilation            ← compilation clean
3. console_get_logs                   ← UI/animation errors
4. scene_analyze                      ← hierarchy and component state
5. scene_health_check                 ← broken references
6. validate_find_missing_scripts      ← null component refs
7. validate_missing_references        ← asset refs
8. prefab_find_instances              ← prefab relationship issues
```

### Domain-Specific Queries by Symptom

**UI issue:**
```
scene_analyze → find Canvas hierarchy
validate_find_missing_scripts → UI scripts may have broken refs
console_get_logs → NullReference in UI code
```

**Animation issue:**
```
animator_get_info (if animator-domain skill loaded) → state machine state
console_get_logs → Animator parameter errors
```

**Addressables issue:**
```
console_get_logs → AsyncOperation errors, handle release warnings
profiler_get_memory → memory after load
```

**Timeline issue:**
```
scene_analyze → PlayableDirector bindings
console_get_logs → binding errors
```

### What NOT to Query in Unity Domain

- `profiler_get_object_count` for entity counts — irrelevant
- `script_dependency_graph` for system scheduling — not the execution model
- `profiler_get_stats` for job time — not the performance model (use CPU time instead)

---

## Hybrid Domain MCP Strategy

**Goal:** Understand both ECS state and Unity presentation state. Trace the bridge.

### Priority Call Sequence

```
1. unity_diagnose                     ← always first
2. debug_check_compilation
3. console_get_logs                   ← errors from both stacks
4. scene_analyze                      ← Unity side of the bridge
5. profiler_get_stats                 ← frame time (ECS + Unity combined)
6. script_dependency_graph            ← how bridge code connects
7. validate_find_missing_scripts      ← Unity side refs
```

### Bridge-Specific Queries

Example (illustrative class names):

```
# Find the bridge component
script_find_in_file(file: "HealthBarBinding.cs", pattern: "ComponentLookup")

# Trace ECS state
mcp__ai-game-developer__script-read(path: "HealthComponent.cs")

# Trace Unity presentation
scene_analyze → find Canvas child of entity-linked GameObject
```

### Hybrid Investigation Pattern

```
1. Confirm DOTS side: does the component have the expected value?
   → script_find_in_file for component definition
   → profiler / entities profiler if available

2. Confirm Unity side: does the view have the expected state?
   → scene_analyze for hierarchy
   → console_get_logs for binding errors

3. Trace the bridge: where does data flow from DOTS to Unity?
   → script_dependency_graph for binding class
   → Find where ComponentLookup<T>.TryGetComponent is called
```

---

## MCP Evidence Override Examples

Examples below use illustrative class names:

**Evidence contradicts DOTS domain score:**
```
DOTS_score = 0.82 (predicted DOTS domain)
MCP: scene_analyze shows no Systems running, only MonoBehaviours
MCP evidence: Unity domain
Action: reclassify, reload Unity skills
```

**Evidence confirms Hybrid classification:**
```
Hybrid_score = 0.65
MCP: console_get_logs shows NullReferenceException in HealthBarBinding.Update()
Evidence: Unity side of bridge is broken (Unity domain symptoms with DOTS source)
Action: confirm Hybrid, load both ui + ECS data flow skills
```

---

## Degraded Mode (MCP Unreachable)

If unity-skills server or ai-game-developer MCP is unavailable:

1. State "Running without MCP evidence" once
2. Rely on CRG + API fingerprinting for domain classification
3. Increase domain ambiguity threshold by 0.10 (escalate more aggressively)
4. Note in workspace/domain-analysis.md: "MCP evidence unavailable — classification from code only"
