# Ownership Boundaries
<!-- Defines who owns what state. Prevents dual ownership. -->

## Core Rule

Every piece of state has exactly one owner.
Dual ownership is always a design defect. Escalate if found.

## Runtime Gameplay State — DOTS Owns

| State | Owner | Unity role |
|-------|-------|------------|
| Entity health value | DOTS (IComponentData) | May read for display |
| Movement position | DOTS (LocalTransform) | May read for camera |
| AI state | DOTS (IComponentData) | May read for animation trigger |
| Combat tags | DOTS (zero-size IComponentData) | May read for VFX trigger |
| Cooldown timers | DOTS (IComponentData) | May read for UI display |
| Inventory contents | DOTS (DynamicBuffer) | May read for UI population |
| Spawn state | DOTS (IComponentData) | May read for pooling |
| Simulation truth | DOTS | Never written by Unity |
| Runtime stats | DOTS | May read for display |
| Networking state | DOTS (if Netcode for Entities) | Bridge layer owns sync |

**Rule:** Unity reads entity state. Unity does NOT write entity state.
If Unity needs to mutate gameplay state → it sends an event or command that DOTS processes next frame.
Unity never calls EntityManager.SetComponentData() on runtime gameplay components.

---

## Presentation State — Unity Owns

| State | Owner | DOTS role |
|-------|-------|-----------|
| Animation state machine | Unity (Animator) | May signal via event |
| Timeline playback | Unity (PlayableDirector) | May trigger via signal |
| Audio playback | Unity (AudioSource) | May trigger via event |
| Popup visibility | Unity (Canvas/CanvasGroup) | May signal to show/hide |
| VFX playback | Unity (VisualEffect) | May trigger via event |
| Camera target | Unity (Cinemachine) | May provide position data |
| HUD element values | Unity (Text/Image) | Reads from DOTS |
| Menu state | Unity (UIDocument/Canvas) | Reads from game state |
| Tooltip visibility | Unity (CanvasGroup) | Reads from interaction state |

**Rule:** DOTS signals presentation state changes. DOTS does NOT own presentation.
If DOTS needs to trigger an animation → it sets a component flag or raises an event that Unity reads.
DOTS never calls GetComponent<Animator>() in a hot-path ISystem.

---

## Hybrid Bridge State — Explicit Contract Required

| State | Contract | Source of truth |
|-------|----------|-----------------|
| Health bar fill amount | Entity HealthComponent → HealthBarView reads | DOTS |
| Damage popup text | DamageEventBuffer → PopupSpawner reads | DOTS |
| Enemy name display | Entity NameComponent → EnemyNameplate reads | DOTS |
| Quest marker position | Entity QuestComponent → QuestMarker reads | DOTS |
| Minimap dot position | Entity LocalTransform → MinimapDot reads | DOTS |
| Loot drop presentation | Drop entity → LootView prefab | DOTS entity, Unity visual |
| Baker authoring data | MonoBehaviour → Baker → IComponentData | Baked (one-way) |

**Contract format** (required in workspace/design.md for hybrid features):

```
Hybrid Contract: <name>
Source of truth: DOTS — <component name>
Presentation owner: Unity — <class name>
Data flow: DOTS → read by Unity each frame via <SystemAPI.GetComponent / ComponentLookup>
Write path: Never — Unity reads only. Changes go through <system or ECB>
Update frequency: Every frame / On change / On event
```

---

## Conflict Detection

**Dual ownership signal:** Two agents write to the same logical state.

Examples:
- MonoBehaviour.Update() sets Transform.position AND LocalTransform is set in ISystem → conflict
- AudioSource.Play() called from MonoBehaviour AND from ISystem in same frame → conflict
- Canvas health bar reads from both a cached float AND EntityQuery → conflict

**Resolution:** Escalate to architect. Never silently resolve dual ownership.

---

## Authoring Layer (Special Case)

Baker inputs are the one place Unity writes data that becomes DOTS state.
This is intentional and NOT a conflict.

Rules for baker layer:
- Authoring MonoBehaviour: Unity owned, no runtime tick
- Baker<T>: writes IComponentData exactly once (at baking time)
- After baking: DOTS owns the component, the authoring MonoBehaviour is irrelevant at runtime
- Baker inputs are editor-time only: `#if UNITY_EDITOR` not required but authoring scene excluded from player build
