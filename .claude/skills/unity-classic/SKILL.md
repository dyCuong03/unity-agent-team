---
name: unity-classic
description: Non-DOTS "Unity classic" skill covering MonoBehaviour, UI Toolkit, UGUI, VContainer, Addressables, pooling, DOTween, async/UniTask, and per-frame performance. Loaded exclusively by the unity-dev (non-DOTS) lane. Does NOT cover ECS/DOTS — use unity-dots-best-practices for entities and systems.
use-when: |
  Load for unity-dev lane when triage classifies domain as Unity (not DOTS or Hybrid).
  Load for MonoBehaviour lifecycle, UI system, Addressables, pooling, or DOTween tasks.
do-not-use-when: |
  Do not load for unity-dots-dev lane. Do not load when task involves ISystem, IJobEntity,
  ECB, NativeContainers, or any ECS API. Do not load for tester, verifier, or architect roles.
platforms: [claude-code, codex, copilot, cursor, windsurf]
task-categories: [gameplay, ui, animation, audio, implementation, classic-unity]
metadata:
  source: https://docs.unity3d.com/Manual/
  version: Unity 6 (6000.0)
  tier: 1

---

# Unity Classic (Non-DOTS) Skill

The non-DOTS lane: `GameObject` + `MonoBehaviour` runtime, UI, gameplay glue,
DI, asset loading, tweening, pooling, async. If the task is `ISystem`/Jobs/Burst/
Entities, it belongs to `unity-dots-dev`, not here.

Root-cause first: for a bug, trace the lifecycle / data flow / event wiring and fix
the real cause. No null-guard or timer band-aid without proving the cause. Match
existing project patterns; do not add a parallel service/controller/model.

## MonoBehaviour lifecycle (the #1 bug source)

- `Awake` → references/self-init only. `OnEnable` → subscribe events / register.
  `Start` → cross-object init (others' Awake done). `OnDisable` → **unsubscribe
  everything subscribed in OnEnable**. `OnDestroy` → final teardown.
- **Every `+=` needs a matching `-=`.** Static / long-lived publisher + instance
  subscriber that never unsubscribes = leak + ghost callbacks after destroy.
- Pooled objects fire `OnEnable`/`OnDisable` per reuse, NOT `Awake`/`Start`.
  Put re-init in `OnEnable`, cleanup in `OnDisable` — not Start/OnDestroy.
- Coroutines stop when the MB disables; restart in `OnEnable` if needed.
  Never `StartCoroutine` on a disabled/inactive object.

## Pooling

- Reset full state on `Get`/spawn (transform, callbacks, tween handles, timers).
- On `Return`/despawn: kill tweens, cancel async, unsubscribe, stop coroutines.
- A pooled object's `OnDisable` runs on return — do destroy-like cleanup there,
  not in `OnDestroy` (which may never run for pooled objects).

## DOTween

- Cache the `Tween`/`Sequence`; `tween.Kill()` on disable/return/destroy before
  starting a new one — orphan tweens mutate recycled objects.
- `SetLink(gameObject)` or `SetAutoKill(true)` to bind lifetime; do not leak
  infinite-loop tweens on pooled UI.
- `DOTween.Kill(target)` in `OnDisable` for pooled views.

## VContainer / DI

- Inject via constructor or `[Inject]` method; injection completes **after**
  `Awake`, around `Start`/entry-point. Do not use injected refs in `Awake`.
- `IStartable`/`ITickable`/`IAsyncStartable` via `RegisterEntryPoint`; register
  in the right `LifetimeScope`. Mismatched scope = null inject or duplicate.
- Do not `new` a service that the container owns — resolve it.

## Addressables

- `Addressables.LoadAssetAsync` ↔ `Release(handle)`. `InstantiateAsync` ↔
  `ReleaseInstance(go)`. Mixing them leaks. Release exactly once per load.
- Hold the `AsyncOperationHandle` to release later; releasing the asset while an
  instance is live can break it. Check `.Status` before using `.Result`.

## Async / UniTask

- Pass a `CancellationToken`; use `this.destroyCancellationToken` (or a
  `CancellationTokenSource` tied to OnDisable/OnDestroy) so awaits stop on teardown.
- Never `async void` except top-level event handlers; catch there.
- Cancel in-flight loads/animations on disable to avoid acting on a dead object.

## UI

- Bind once; guard against double-subscribe on re-show. Unbind on hide.
- No `GetComponent`/`Find`/LINQ/`string.Format`/allocations in `Update` or
  per-item layout loops. Cache references. Batch canvas updates.

## Performance (per-frame)

- Hot path: no allocations, no `GetComponent` per frame, no `Camera.main` per
  frame, no boxing. Pool transient objects. Profile before/after non-trivial work.

## Output (handoff)

1. Unity classic analysis (lifecycle/data-flow/root cause)
2. Implementation plan (existing patterns reused — no duplication)
3. Changed files + one-line purpose
4. Validation steps (lifecycle, leak, alloc, release/kill checks)
