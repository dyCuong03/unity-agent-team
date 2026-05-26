---
name: dots-hybrid-bridge
description: The one-way bridge between DOTS-owned runtime state and Unity-owned presentation. Covers UnityObjectRef for managed asset refs in components, the DOTS-writes / Unity-reads ownership rule, when to use managed IComponentData vs UnityObjectRef vs CompanionComponent, baker-bridge vs runtime-bridge, and SubScene boundary rules. Use when an entity must reference Unity assets (Mesh, Material, AudioClip, ScriptableObject), a MonoBehaviour view must read entity state, or input/UI must trigger ECS work.
---

# Hybrid Bridge — Senior Patterns

The bridge between Unity's GameObject world and DOTS' entity world is the highest-bug-density area in any production project. The rule is brutally simple: **DOTS owns the runtime truth; Unity reads it. Never the reverse for gameplay state.** Everything else is a footnote on how to honor that rule efficiently.

## Intent

Cross the GO↔Entity boundary deliberately, one-way, with explicit ownership of which side writes and which side reads.

## Three bridge pathways

| Pathway | What it carries | When |
|---|---|---|
| **`UnityObjectRef<T>`** in `IComponentData` | Reference to a Unity asset (Mesh, Material, AudioClip, Prefab, ScriptableObject) | Default for asset refs. Burst-friendly to **hold**; deref needs main thread. |
| **Managed `class : IComponentData`** | Holds a GameObject / MonoBehaviour reference for a hybrid entity | Last resort. Forces non-Burst. Costs GC. Use only when CompanionComponent isn't enough. |
| **Companion GameObject** (Entities Graphics) | A real GameObject parented to an entity transform for editor visualization | Almost always a debugging/visualization crutch, not architecture. |

For Unity→DOTS communication (input, UI button → game state), use the **event-driven** pathway from `dots-event-driven-ecs`, not direct entity component writes.

## Senior pattern — `UnityObjectRef<T>` (the default)

```csharp
public struct WeaponVisual : IComponentData
{
    public UnityObjectRef<Mesh>     Mesh;
    public UnityObjectRef<Material> Material;
    public UnityObjectRef<AudioClip> FireSound;
}

public class WeaponAuthoring : MonoBehaviour
{
    public Mesh     Mesh;
    public Material Material;
    public AudioClip FireSound;

    class Baker : Baker<WeaponAuthoring>
    {
        public override void Bake(WeaponAuthoring authoring)
        {
            // DependsOn so the baker re-runs if the asset changes (see dots-baking-patterns).
            DependsOn(authoring.Mesh);
            DependsOn(authoring.Material);

            var e = GetEntity(TransformUsageFlags.Dynamic);
            AddComponent(e, new WeaponVisual {
                Mesh      = new UnityObjectRef<Mesh>     { Value = authoring.Mesh },
                Material  = new UnityObjectRef<Material> { Value = authoring.Material },
                FireSound = new UnityObjectRef<AudioClip>{ Value = authoring.FireSound },
            });
        }
    }
}

// Read on main thread (deref forces main thread).
public partial struct WeaponFireSystem : ISystem
{
    public void OnUpdate(ref SystemState state)
    {
        foreach (var (visual, _) in SystemAPI.Query<RefRO<WeaponVisual>, RefRO<FireRequest>>())
        {
            // .Value performs main-thread deref. Inside a job, you must pass the
            // UnityObjectRef value AND deref on main thread before the job runs.
            AudioSource.PlayClipAtPoint(visual.ValueRO.FireSound.Value, Vector3.zero);
        }
    }
}
```

## Senior pattern — Unity reads entity state (HUD, minimap)

```csharp
// MonoBehaviour-side. Cache the entity manager once; query main-thread.
public class HealthBarBinding : MonoBehaviour
{
    public Image Fill;
    Entity _entity;
    EntityManager _em;

    void Start() {
        _em = World.DefaultGameObjectInjectionWorld.EntityManager;
        // Acquire _entity via baking lookup or registration system.
    }

    void LateUpdate()  // AFTER PresentationSystemGroup
    {
        if (!_em.Exists(_entity)) return;
        if (!_em.HasComponent<HealthComponent>(_entity)) return;
        var hp = _em.GetComponentData<HealthComponent>(_entity);
        Fill.fillAmount = hp.Current / (float)hp.Max;
    }

    // DO NOT call _em.SetComponentData<HealthComponent>(...) from here.
    // That would be Unity writing gameplay state — a dual-ownership defect.
}
```

## Senior pattern — Unity triggers ECS work (input)

Don't write into gameplay components from MonoBehaviours. Append a **request**:

```csharp
// MonoBehaviour input system reads the keyboard, creates a request entity.
void Update()
{
    if (Input.GetKeyDown(KeyCode.Space))
    {
        var em = World.DefaultGameObjectInjectionWorld.EntityManager;
        var req = em.CreateEntity();
        em.AddComponentData(req, new JumpRequest { Player = _localPlayerEntity });
    }
}

// ECS-side consumer (see dots-event-driven-ecs for the full pattern).
```

## Anti-patterns

- ❌ Caching a raw `Mesh` / `Material` reference in a `class : IComponentData`. Breaks Burst on the component, breaks domain reload, breaks serialization. Use `UnityObjectRef<T>`.
- ❌ `MonoBehaviour` calling `EntityManager.SetComponentData<HP>(...)` for gameplay state. **Dual ownership.** Escalate in review.
- ❌ Per-frame `World.DefaultGameObjectInjectionWorld.EntityManager` lookup from `Update()` on dozens of MonoBehaviours. Each is a main-thread sync point. Cache `EntityManager` once.
- ❌ Bidirectional binding: UI writes to ECS, ECS writes back to UI, both inside the same frame. Race; values diverge. The bridge is **one-way**.
- ❌ `IConvertGameObjectToEntity` / `ConvertToEntity` MonoBehaviours. **Removed in 1.x.** Bakers only.
- ❌ Adding entity components outside the Baker for entities that live in a baked subscene. They get **wiped on subscene rebake**.

## Failure modes

| Symptom | Cause |
|---|---|
| Material/mesh ref null after domain reload | Stored as raw managed ref instead of `UnityObjectRef<T>` |
| UI bar lags one frame behind state | MonoBehaviour reads in `Update()` before DOTS writer in `PresentationSystemGroup` finishes — move to `LateUpdate` or read `LocalToWorld`-equivalent late-frame output |
| HP value sometimes resets to spawn value | A MonoBehaviour also writes HP; two writers; the order resolved at runtime "wins" |
| `InvalidOperationException: Entity does not exist` in `LateUpdate` | MonoBehaviour holds an entity ref across destruction; missing `EntityManager.Exists` check |
| Editor "subscene out of date" warning, then your custom components disappear | Components added outside the Baker — rebake wipes them |
| Burst-time crash inside a job using `UnityObjectRef.Value` | `.Value` deref isn't job-safe; capture the ref value into the job, deref on main thread |

## Runtime verification (Tester Verification Contract)

- **Static:** grep for `class : IComponentData` — every match needs review; preferred replacement is `UnityObjectRef<T>` for asset refs. Grep for `IConvertGameObjectToEntity` / `ConvertToEntity` — refuse.
- **Runtime:** for each hybrid-bridge feature, identify the writer side and reader side. Assert the reader never writes by inspecting the diff of one full frame — writer-side fields must only change in the writer's frame phase.

## Performance notes

- `UnityObjectRef<T>` is a value type wrapping an instance ID. Holding it is free. Deref is a managed-side lookup — main thread only.
- Per-frame `EntityManager.GetComponentData` from a MonoBehaviour is a sync point. For >10 MonoBehaviours doing this, batch via a dedicated bridge system that writes a `NativeArray` MonoBehaviours can read.
- Companion GameObjects double the cost (entity transform + GO transform). Acceptable in editor visualization, banned in shipping hot paths.

## Compile / editor safety

- `UnityObjectRef<T>` requires `T : Object` (UnityEngine.Object) — won't compile for pure C# types.
- Managed `class : IComponentData` requires `using Unity.Entities;` and you must guard `#if !UNITY_DISABLE_MANAGED_COMPONENTS` for projects that disable managed components.
- `SubScene` baking is destructive — agents must NOT instruct users to "just AddComponent after baking" inside a subscene boundary.

## Entities version notes (1.4.x)

- `UnityObjectRef<T>` — current. Replaces 0.x raw managed asset refs.
- `IConvertGameObjectToEntity` / `ConvertToEntity` — **gone**. Bakers (`Baker<TAuthoring>`) only.
- `class : IComponentData` (managed components) — still supported; gate with `UNITY_DISABLE_MANAGED_COMPONENTS` for builds that disable them.
- `EntityManager.AddComponentObject(entity, monoBehaviour)` — still the way to attach a MonoBehaviour to an entity for editor companion display.

## See also
- `dots-baking-patterns` — `TransformUsageFlags`, `DependsOn`, the baker-side of the bridge
- `dots-event-driven-ecs` — Unity→DOTS via request entities, not direct writes
- `dots-singleton-patterns` — a "global ScriptableObject config" becomes a baked singleton with `UnityObjectRef`-typed fields
