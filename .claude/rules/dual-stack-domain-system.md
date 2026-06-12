# Dual-Stack Domain System
<!-- Replaces DOTS-always-wins with domain-aware precedence. -->
<!-- Agents use the right stack for the right code, not a framework bias. -->

## Core Principle

The right stack for the right code.

Not ECS everywhere. Not MonoBehaviour everywhere.
Code evidence determines which stack leads. Investigation runs before reasoning.

## Three Domains

### Domain 1 — Runtime ECS (DOTS leads)

DOTS reasoning weight: **dominant**.
Unity reasoning weight: secondary.

**Characteristics:** ISystem, IJobEntity, ECB, NativeArray, BlobAsset, EntityQuery,
Burst jobs, scheduling, memory-sensitive simulation, structural changes, entity
ownership, runtime gameplay (combat, movement, AI, cooldowns, spawning, networking).

**Decision rule:** If DOTS_score ≥ 0.70 and DOTS_score > Unity_score + 0.20.

**Skill loading:** Layer 1 ECS heavy. Domain skills from DOTS side only unless
hybrid APIs detected. Unity skills load as secondary, advisory only.

**Examples (illustrative class names):**
- EnemyAISystem.cs, MovementSystem.cs, CombatSystem.cs → DOTS domain
- "combat race condition" + IJobEntity fingerprint → DOTS domain
- "cooldown desync" + ComponentLookup → DOTS domain

**ECS reasoning bias in this domain:**
- ISystem wins over MonoBehaviour Update
- ECB wins over EntityManager in jobs
- Jobs + Dependency wins over async in hot paths
- Burst-safe code wins over managed allocation

---

### Domain 2 — Unity View / Authoring (Unity leads)

Unity reasoning weight: **dominant**.
DOTS reasoning weight: secondary.

**Characteristics:** MonoBehaviour, Canvas, Animator, DOTween, AudioSource,
PlayableDirector, AddressableAssets, EditorWindow, ScriptableObject authoring,
VFX, ShaderGraph, UIToolkit, prefab workflows, editor tooling, build pipeline,
inspector design, scene composition, timeline, localization.

**Decision rule:** If Unity_score ≥ 0.70 and Unity_score > DOTS_score + 0.20.

**Skill loading:** Layer 2 Unity Foundation heavy. Domain skills from Unity side
(ui, animator, timeline, shadergraph, addressables-design, etc.). ECS skills load
as secondary, advisory only.

**Examples (illustrative class names):**
- PopupPresenter.cs, UIManager.cs, AnimationController.cs → Unity domain
- "popup not appearing" + Canvas/CanvasGroup fingerprint → Unity domain
- "addressables build failure" → Unity domain
- "timeline sequence not playing" + PlayableDirector → Unity domain

**Unity reasoning bias in this domain:**
- MonoBehaviour lifecycle is the execution model
- Coroutines / async are valid (not inferior to Jobs)
- ScriptableObjects are valid config assets
- Prefab workflow is the authoring pattern

---

### Domain 3 — Hybrid Boundary (Both cooperate)

DOTS reasoning weight: **balanced with explicit contract**.
Unity reasoning weight: **balanced with explicit contract**.

**Characteristics:** ECS → UI binding, ECS health bar, ECS animation bridge, baker
inputs, ECS save/load, entity visual representation, prefab visual for ECS entity,
compound components (Baker + MonoBehaviour authoring), ECS + Addressables loading.

**Decision rule:** If Hybrid_score ≥ 0.60 AND abs(DOTS_score - Unity_score) < 0.30.

**Skill loading:** Both DOTS and Unity skills. Domain analysis must define the
explicit contract: who owns runtime truth, who owns presentation.

**Examples (illustrative class names):**
- HealthBarBinding.cs + HealthComponent + Canvas → Hybrid
- "HP bar not updating" with both EntityQuery and RectTransform → Hybrid
- "enemy presentation not syncing" → Hybrid
- Baker<EnemyAuthoring> + EnemyView → Hybrid

**Hybrid reasoning rules:**
- DOTS owns runtime truth (health value, damage state, position)
- Unity owns presentation (bar fill, popup, animation trigger)
- Bridge is explicit: one-way data flow, DOTS → Unity
- Dual ownership is always a bug — escalate if found

---

### Ambiguous (Escalate)

**Condition:** No domain scores above threshold or domain ambiguity > 0.40.

**Action:** Write [ESCALATE_ARCHITECT: domain ambiguous] to workspace/domain-analysis.md.
Architect classifies domain before implementation starts.

**Never:** Guess the domain and proceed. Ambiguity means investigation was insufficient.

---

## Precedence Summary

| Situation | DOTS | Unity | Hybrid |
|-----------|------|-------|--------|
| Runtime simulation system | Leads | Secondary | N/A |
| Presentation / view code | Secondary | Leads | N/A |
| Baker / authoring layer | N/A | Input provider | Leads |
| ECS → view binding | Secondary | Secondary | Leads |
| Editor tooling | Secondary | Leads | N/A |
| Build pipeline | Secondary | Leads | N/A |
| Performance analysis | Leads | Secondary | N/A |

---

## Migration from DOTS-first Bias

Old behavior: DOTS Conflict Resolution Policy made DOTS win in all ambiguous cases.

New behavior: Domain classification runs first. DOTS leads only in Domain 1.
Unity leads in Domain 2. Both cooperate in Domain 3.

The old DOTS Conflict Resolution Policy still applies — but only within Domain 1.
In Domain 2 and Domain 3, it is suspended in favor of domain-appropriate reasoning.
