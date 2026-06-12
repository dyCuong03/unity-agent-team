# Skill Confidence Routing
<!-- Replaces keyword-only routing. Load routing/SKILL.md for examples. -->

## Purpose

Score every candidate skill module (0.0–1.0) before loading it.
Load only the top-scoring modules within budget.
Never load a module below threshold 0.70.

## Budget (hard limits)

- Domain modules: max 2 per agent per task
- Advisory modules: max 2 per agent per task
- Load threshold: score ≥ 0.70 (below this: skip, load nothing for that slot)
- If no module scores ≥ 0.70: load Layer 1 + Layer 2 only — do not force a load

## Scoring Algorithm

```
score(module, task) =
  (0.35 × keyword_score)
+ (0.30 × symptom_score)
+ (0.20 × history_score)
+ (0.10 × ecs_penalty_modifier)
+ (0.05 × issue_type_modifier)
```

All sub-scores are 0.0–1.0. Final score is 0.0–1.0.

### 1. keyword_score (weight 0.35)

Direct string match between task text and module's known trigger keywords.

```
keyword_score = matches / max(total_trigger_keywords_for_module, 5)
capped at 1.0
```

Scoring bands:
- 3+ keyword matches in task text → 1.00
- 2 matches → 0.75
- 1 match → 0.50
- 0 matches → 0.00

### 2. symptom_score (weight 0.30)

Match the task description against known symptom patterns.
Use the Symptom Pattern Library below.

```
symptom_score = best_matching_pattern_score for this module
```

If no pattern matches: 0.00.

### 3. history_score (weight 0.20)

Check workspace/repo-knowledge.md for prior sessions that involved this module.

```
history_score =
  1.0 if this module appeared in a prior fix/feature in the same system area
  0.5 if this module appeared in any prior fix/feature in the repo
  0.0 if no history found
```

Read the "Session History" section of workspace/repo-knowledge.md.
If repo-knowledge.md is empty or missing: history_score = 0.0 for all modules.

### 4. ecs_penalty_modifier (weight 0.10)

Penalize MonoBehaviour-first modules when the task is ECS-bound.

```
ecs_penalty_modifier =
  -1.0  if module is MonoBehaviour-first AND task mentions ECS/ISystem/entity/DOTS
  -0.5  if module is MonoBehaviour-first AND task is --feature or --refactor in ECS area
   0.0  if module is ECS-safe or ECS-compatible
  +0.3  if module is ECS-safe AND task explicitly mentions DOTS/Entities/ISystem
```

Modifier is added to the raw score total. Score is then clamped to [0.0, 1.0].

MonoBehaviour-first modules (apply penalty when ECS context detected):
ui, animator, navmesh, dotween, event, gameobject, component

### 5. issue_type_modifier (weight 0.05)

```
--bug flag:
  debug, console → +0.20
  profiler        → +0.10
  domain modules  → no bonus

--feature flag:
  advisory modules → +0.15
  domain modules   → +0.05

--refactor flag:
  performance, profiler → +0.10
  optimization          → +0.10
  domain modules        → no bonus

--fast-fix flag:
  all modules → -0.20 (discourage loading; fast-fix should need nothing)

no flag (general):
  no bonus or penalty
```

## Symptom Pattern Library

Maintained by bug-investigation. Updated after each successful root-cause resolution.
Entries are scored 0.0–1.0 for each module they implicate.

### Pattern: entity_stuck_after_teleport
Triggers: "stuck", "teleport", "position reset", "entity not moving", "transform sync"

| Module | Score | Reason |
|--------|-------|--------|
| debug | 0.92 | always check compile/runtime errors first |
| console | 0.88 | runtime exceptions often logged |
| physics | 0.74 | physics state may not reset on teleport |
| navmesh | 0.83 | NavMeshAgent loses path on position jump |
| cinemachine | 0.41 | camera follow can mask position issues |
| profiler | 0.45 | unlikely cause but worth ruling out at scale |

ECS note: if task mentions ISystem or entity — navmesh gets -0.5 penalty (no DOTS navmesh).

### Pattern: memory_leak
Triggers: "memory leak", "memory grows", "out of memory", "GC pressure", "allocation"

| Module | Score | Reason |
|--------|-------|--------|
| profiler | 0.93 | primary diagnostic tool |
| debug | 0.88 | check for allocation errors |
| optimization | 0.81 | asset loading issues |
| addressables-design | 0.77 | handle not released = most common leak |
| yooasset-design | 0.71 | similar to Addressables |
| console | 0.65 | warnings about leaked objects |

### Pattern: ui_not_updating
Triggers: "UI", "text not updating", "button not responding", "HUD", "canvas"

| Module | Score | Reason |
|--------|-------|--------|
| ui | 0.90 | direct match |
| uitoolkit | 0.72 | if project uses UI Toolkit |
| debug | 0.80 | check for null refs in UI scripts |
| console | 0.75 | UI errors usually logged |

ECS note: if task mentions ECS → ui score gets ecs_penalty_modifier. Hybrid boundary likely.

### Pattern: animation_glitch
Triggers: "animation", "animator", "blend", "state machine", "jitter", "T-pose"

| Module | Score | Reason |
|--------|-------|--------|
| animator | 0.91 | direct match |
| debug | 0.82 | Animator can throw runtime errors |
| console | 0.75 | parameter errors logged |
| physics | 0.45 | ragdoll/cloth edge case |

ECS note: if task mentions ECS entities → animator gets -0.50 (DOTS Animation is separate).

### Pattern: performance_drop
Triggers: "slow", "frame drop", "lag", "FPS", "performance", "jank"

| Module | Score | Reason |
|--------|-------|--------|
| profiler | 0.94 | mandatory starting point |
| performance | 0.91 | advisory — red flags checklist |
| optimization | 0.83 | asset-level optimization |
| debug | 0.77 | check for per-frame allocations |

### Pattern: network_desync
Triggers: "desync", "network", "multiplayer", "client", "server", "lag", "rollback"

| Module | Score | Reason |
|--------|-------|--------|
| netcode | 0.90 | direct match |
| netcode-design | 0.88 | design rules — 10 critical rules |
| debug | 0.82 | network errors in console |
| console | 0.78 | packet errors logged |

### Pattern: asset_not_loading
Triggers: "asset", "load", "addressable", "bundle", "yooasset", "404", "null asset"

| Module | Score | Reason |
|--------|-------|--------|
| addressables-design | 0.89 | handle lifecycle rules |
| yooasset-design | 0.86 | init/update flow rules |
| debug | 0.82 | loading errors |
| console | 0.78 | asset errors logged |
| profiler | 0.65 | memory after load |

### Pattern: shader_artifact
Triggers: "shader", "rendering", "artifact", "pink", "transparent", "ShaderGraph"

| Module | Score | Reason |
|--------|-------|--------|
| shadergraph | 0.88 | direct REST skills for inspection |
| shadergraph-design | 0.84 | version-specific rules |
| urp | 0.75 | render pipeline compatibility |
| debug | 0.71 | shader compile errors |

## Fallback Behavior

If score calculation is impossible (no workspace files, no MCP evidence):
1. Fall back to keyword-only scoring (use keyword_score × 0.35 + 0.30 uniform symptom)
2. Apply 0.70 threshold still — if no module clears it, load nothing extra
3. Log: "Routing fallback: workspace/repo-knowledge.md missing or MCP unavailable"

If all scored modules are below 0.70:
- Load only Layer 1 (Core ECS) + Layer 2 (Foundation) + Layer 4 (Investigation if applicable)
- Do NOT force-load the highest-scoring module just to fill the slot
- State: "No domain module scored above threshold. Proceeding with core layers only."

## Pseudocode

```python
def route_skills(task_text, issue_type, workspace, mcp_evidence):
    candidates = get_all_candidate_modules()
    scores = {}

    for module in candidates:
        kw = keyword_score(task_text, module.trigger_keywords)
        sym = symptom_score(task_text, SYMPTOM_PATTERNS, module)
        hist = history_score(module, workspace.repo_knowledge)
        ecs = ecs_penalty(task_text, module.dots_safety)
        it = issue_type_modifier(issue_type, module)

        raw = (0.35 * kw) + (0.30 * sym) + (0.20 * hist) + (0.10 * ecs) + (0.05 * it)
        scores[module] = clamp(raw, 0.0, 1.0)

    domain_modules = [m for m in sort_by_score(scores) if m.type == "domain" and scores[m] >= 0.70][:2]
    advisory_modules = [m for m in sort_by_score(scores) if m.type == "advisory" and scores[m] >= 0.70][:2]

    return domain_modules, advisory_modules

def ecs_penalty(task_text, dots_safety):
    ecs_keywords = ["ISystem", "entity", "DOTS", "ECS", "IComponentData", "SystemAPI"]
    ecs_context = any(kw in task_text for kw in ecs_keywords)
    if dots_safety == "MonoBehaviour-first":
        return -1.0 if ecs_context else -0.5
    elif dots_safety in ["ECS-safe", "ECS-compatible"]:
        return 0.3 if ecs_context else 0.0
    return 0.0
```

## Routing Output Format

Orchestrator writes routing decision to a single line before spawning agents:

```
[SKILL_ROUTING] domain:[ui, physics] advisory:[performance] threshold:0.70 dropped:[navmesh(0.41)]
```

If no modules selected:
```
[SKILL_ROUTING] domain:[] advisory:[] threshold:0.70 reason:no_module_above_threshold
```

## Examples

### Example 1: `--bug` "enemy stuck after teleport"

```
Scores (ECS context: None detected):
  debug         0.92  → LOAD (advisory budget)
  navmesh       0.83  → LOAD (domain budget, slot 1)
  console       0.88  → LOAD (advisory budget, slot 2)
  physics       0.74  → WOULD LOAD but domain budget full (navmesh already loaded)
  cinemachine   0.41  → SKIP (below threshold)

Result: domain:[navmesh] advisory:[debug, console]
Note: debug and console both advisory — ok to load both
```

### Example 2: `--bug` "enemy stuck after teleport" with ECS context ("ISystem in task")

```
Scores (ECS context: DETECTED — "ISystem" in task):
  debug         0.92  → LOAD
  navmesh       0.83  → penalty -1.0 → final 0.09 → SKIP (MonoBehaviour-first + ECS context)
  console       0.88  → LOAD
  physics       0.74  → LOAD (domain)

Result: domain:[physics] advisory:[debug, console]
```

### Example 3: `--feature` "add inventory shop UI"

```
Scores (no ECS context):
  ui            0.90  → LOAD (domain slot 1)
  uitoolkit     0.72  → LOAD (domain slot 2)
  architecture  0.68  → SKIP (below 0.70)
  debug         0.55  → SKIP

Result: domain:[ui, uitoolkit] advisory:[]
```

### Example 4: `--refactor` "extract zone spawner into shared system"

```
Scores (ECS context: DETECTED):
  performance   0.91  → LOAD (advisory)
  profiler      0.83  → LOAD (advisory, +0.10 refactor bonus)
  ui            0.12  → SKIP (no keyword match)
  asmdef        0.68  → SKIP (below threshold)

Result: domain:[] advisory:[performance, profiler]
```
