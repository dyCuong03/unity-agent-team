# Domain Escalation Rules
<!-- Extends escalation-policy.md with domain-specific triggers. -->
<!-- These triggers fire during domain classification, before implementation starts. -->

## Trigger 1: Domain Ambiguity

**Condition:** No domain scores above threshold after full API scan.

```
DOTS_score < 0.60 AND Unity_score < 0.60 AND Hybrid_score < 0.60
```

**Signal:** `[ESCALATE_ARCHITECT: domain ambiguous]`

**Written to:** workspace/domain-analysis.md Escalation Risk section

**Resolution required:** Architect reads domain-analysis.md evidence, classifies
domain manually, writes decision to workspace/design.md:
```
Domain classification: <DOTS | Unity | Hybrid>
Reason: <evidence-based reasoning>
```

**Blocking:** Yes — unity-dev must not start until domain is classified.

---

## Trigger 2: Domain Ambiguity > 0.40

**Condition:** All three scores are within 0.40 of each other AND all < 0.70.

```python
ambiguity = max(abs(DOTS - Unity), abs(DOTS - Hybrid), abs(Unity - Hybrid))
if ambiguity < 0.40 and max(DOTS, Unity, Hybrid) < 0.70:
    trigger = True
```

**Signal:** `[ESCALATE_ARCHITECT: domain scores too close to classify reliably]`

**Resolution:** Same as Trigger 1.

---

## Trigger 3: Ownership Conflict Detected

**Condition:** Both DOTS APIs AND Unity APIs write to logically the same state in touched code.

**Examples:**
- MonoBehaviour.Update() writes Transform.position AND ISystem writes LocalTransform
- AudioSource.Play() called from both MonoBehaviour AND ISystem in same file chain
- Health value stored in both a MonoBehaviour field AND HealthComponent

**Signal:** `[ESCALATE_ARCHITECT: ownership conflict detected — <description>]`

**Written to:** workspace/domain-analysis.md + workspace/design.md Open Risks

**Resolution required:** Architect defines source of truth and removes dual ownership.
Implementation cannot proceed until ownership contract is defined.

---

## Trigger 4: DOTS and Unity Guidance Conflict

**Condition:** The loaded skills from both stacks give contradictory advice for the same code location.

**Example:**
- Unity `async/SKILL.md` recommends coroutine for sequence
- DOTS best-practices recommends IJobEntity with dependency chain for same sequence
- Both apply to the same initialization code

**Signal:** `[ESCALATE_ARCHITECT: DOTS and Unity guidance conflict on <topic>]`

**Resolution:** Architect defines which stack leads for that specific code location.
This is a Hybrid boundary definition task.

---

## Trigger 5: Cross-Domain Complexity High

**Condition:** Task touches systems in 2+ domains AND each domain has DOTS_score or Unity_score > 0.60.

**Signal:** `[AUTO_ESCALATE: cross-domain complexity high — <domain1> score:<x>, <domain2> score:<y>]`

**Effect:** Non-blocking. Architect is notified. Unity-dev receives a complexity warning.
Tester adds cross-domain regression to test plan.

---

## Domain Escalation Decision Tree

```
Investigation complete — domain scores calculated
        │
        ▼
Domain classification clear? (one domain ≥ 0.70, gap ≥ 0.20)
        │
       YES → proceed to skill loading → spawn agents
        │
        NO
        │
        ▼
Hybrid condition met? (Hybrid ≥ 0.60, gap < 0.30)
        │
       YES → classify Hybrid → define contract → spawn agents
        │
        NO
        │
        ▼
[ESCALATE_ARCHITECT: domain ambiguous]
        │
        ▼
Architect classifies → writes to design.md
        │
        ▼
Orchestrator reads classification → continues
```

## Domain Escalation is NOT a Failure

Domain escalation means the codebase is genuinely complex.
A 30-second architect classification prevents 30 minutes of wrong-stack implementation.
Escalate early. Resolve fast. Proceed correctly.
