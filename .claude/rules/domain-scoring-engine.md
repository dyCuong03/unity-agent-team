# Domain Scoring Engine
<!-- Calculates DOTS_score, Unity_score, Hybrid_score from API fingerprints. -->

## Input

From api-fingerprinting-system.md scan:
- `dots_raw` = sum of all DOTS API weights found
- `unity_raw` = sum of all Unity API weights found
- `hybrid_raw` = sum of all Hybrid API weights found

## Normalization

```python
# Normalization constants (calibrated for a typical 1-5 file scan)
DOTS_MAX  = 2.0   # a pure DOTS file set typically scores up to 2.0 raw
UNITY_MAX = 2.0   # a pure Unity file set typically scores up to 2.0 raw
HYBRID_MAX = 1.0  # hybrid APIs are fewer but significant

DOTS_score  = min(1.0, dots_raw / DOTS_MAX)
Unity_score = min(1.0, unity_raw / UNITY_MAX)

# Hybrid score: elevated when BOTH DOTS and Unity are significantly present
Hybrid_score = min(1.0, (hybrid_raw / HYBRID_MAX) + (0.4 * min(DOTS_score, Unity_score)))
```

## Domain Classification

```python
def classify_domain(DOTS_score, Unity_score, Hybrid_score):
    dots_dominant  = DOTS_score >= 0.70 and (DOTS_score - Unity_score) >= 0.20
    unity_dominant = Unity_score >= 0.70 and (Unity_score - DOTS_score) >= 0.20
    hybrid         = Hybrid_score >= 0.60 and abs(DOTS_score - Unity_score) < 0.30

    if dots_dominant:   return "DOTS"
    if unity_dominant:  return "Unity"
    if hybrid:          return "Hybrid"
    return "Ambiguous"  # → escalate
```

## Worked Examples

### Example 1: EnemyAISystem.cs

APIs found:
- `ISystem` (0.20) + `[BurstCompile]` (0.20) + `NativeArray<T>` (0.20) +
  `SystemAPI` (0.20) + `ComponentLookup<T>` (0.12) + `[UpdateInGroup]` (0.06) +
  `Unity.Entities` namespace (0.06)

```
dots_raw  = 1.04   → DOTS_score  = min(1.0, 1.04/2.0) = 0.52... wait → 0.52
unity_raw = 0.00   → Unity_score = 0.00
hybrid_raw = 0.00  → Hybrid_score = 0 + 0.4 × min(0.52, 0) = 0.00
```

Hmm, 0.52 doesn't reach 0.70. Let me recalibrate. A typical DOTS system file
that hits 5+ DOTS APIs should score ≥ 0.70. With these weights:
ISystem(0.20) + BurstCompile(0.20) + NativeArray(0.20) + SystemAPI(0.20) = 0.80

```
dots_raw  = 0.80+   → DOTS_score  = min(1.0, 0.80/1.20) = 0.67 → close
```

With DOTS_MAX = 1.20 (recalibrated):
```
DOTS_score  = min(1.0, 1.04/1.20) = 0.87   ✓
Unity_score = 0.00
Hybrid_score = 0.00
```

**Domain: DOTS** (0.87 ≥ 0.70, gap 0.87 > 0.20)

Calibrated DOTS_MAX = 1.20, UNITY_MAX = 1.20 (4 medium-confidence APIs = saturation)

---

### Example 2: PopupPresenter.cs

APIs found:
- `MonoBehaviour` (0.20) + `Canvas` (0.20) + `CanvasGroup` (0.12) +
  `Button` (0.12) + `Image` (0.12) + `DOTween` (0.20) +
  `AsyncOperationHandle<T>` (0.20) + `[SerializeField]` (0.06) + `UnityEngine.UI` (0.06)

```
unity_raw  = 1.28   → Unity_score = min(1.0, 1.28/1.20) = 1.00
dots_raw   = 0.00   → DOTS_score  = 0.00
hybrid_raw = 0.00   → Hybrid_score = 0.00
```

**Domain: Unity** (1.00 ≥ 0.70, gap 1.00 - 0.00 = 1.00 > 0.20)

---

### Example 3: HealthBarBinding.cs

APIs found:
DOTS: `ComponentLookup<HealthComponent>` (0.12) + `SystemAPI` (0.20) + `Unity.Entities` (0.06)
Unity: `RectTransform` (0.20) + `Image` (0.12) + `MonoBehaviour` (0.20) + `[SerializeField]` (0.06)
Hybrid: `Baker<T>` (0.25) + `GetEntity()` (... actually Baker not present in this file)

Let me reconsider — HealthBarBinding reads entity state in MonoBehaviour:
DOTS: `EntityManager` (0.12) + `ComponentLookup<T>` (0.12)
Unity: `MonoBehaviour` (0.20) + `Image` (0.12) + `RectTransform` (0.20)
Hybrid: `EntityCommandBuffer` in MonoBehaviour (0.15)

```
dots_raw   = 0.24  → DOTS_score  = min(1.0, 0.24/1.20) = 0.20
unity_raw  = 0.52  → Unity_score = min(1.0, 0.52/1.20) = 0.43
hybrid_raw = 0.15  → Hybrid_score = min(1.0, 0.15/1.0 + 0.4 × min(0.20, 0.43)) = 0.23
```

Hmm — no dominant domain. Ambiguous?

Actually HealthBarBinding is intrinsically hybrid. Let me recalibrate Hybrid_score:
The file uses both DOTS APIs and Unity APIs — that co-occurrence is the hybrid signal.

```
Hybrid_score = min(1.0, hybrid_raw/HYBRID_MAX + 0.5 × min(DOTS_score, Unity_score))
             = min(1.0, 0.15 + 0.5 × 0.20) = 0.25
```

Still low. The issue: HealthBarBinding doesn't use many APIs of either type.
In this case → Ambiguous → escalate to architect for domain classification.

This is correct behavior. HealthBarBinding IS ambiguous without more context.
Architect classifies it as Hybrid and defines the contract.

---

### Example 4: Enemy stuck after teleport — Multi-file

Files: EnemyMovementSystem.cs + NavMeshAgentBridge.cs

From EnemyMovementSystem.cs:
DOTS: `ISystem`(0.20) + `PhysicsVelocity`(0.20) + `LocalTransform`(0.20) + `IJobEntity`(0.20)

From NavMeshAgentBridge.cs:
Unity: `MonoBehaviour`(0.20) + `NavMeshAgent`(0.12) + `[SerializeField]`(0.06)
Hybrid: `GetComponent<T>() in Baker context`(0.08)

```
dots_raw   = 0.80  → DOTS_score  = 0.67
unity_raw  = 0.38  → Unity_score = 0.32
hybrid_raw = 0.08  → Hybrid_score = 0.08 + 0.4 × 0.32 = 0.21
```

DOTS_score 0.67 < 0.70 threshold — borderline.
Gap: 0.67 - 0.32 = 0.35 > 0.20 — sufficient gap.

Apply leniency rule: if gap ≥ 0.30 and highest score ≥ 0.60 → classify as that domain.

**Domain: DOTS** (0.67 with gap 0.35 → leniency applied)

Skills loaded: physics + movement (no navmesh-design — navmesh is secondary in DOTS domain).

---

## Calibration Constants

```
DOTS_MAX  = 1.20  # 4 high-confidence DOTS APIs = saturation
UNITY_MAX = 1.20  # 4 high-confidence Unity APIs = saturation
HYBRID_MAX = 1.00 # hybrid APIs are fewer but significant
LENIENCY_GAP = 0.30  # if gap ≥ 0.30, apply leniency
LENIENCY_MIN = 0.60  # leniency requires score ≥ 0.60
```

## Output

Write to workspace/domain-analysis.md:
```
DOTS_score: 0.87
Unity_score: 0.00
Hybrid_score: 0.00
Dominant domain: DOTS
Classification method: threshold (0.87 ≥ 0.70, gap 0.87)
```
