# API Fingerprinting System
<!-- Detect domain from actual APIs in touched code — not from task keywords. -->

## How to Use

code-tracer scans each touched file (max 8) for these APIs.
Each hit adds a confidence weight to DOTS_raw, Unity_raw, or Hybrid_raw.
See domain-scoring-engine.md for how raw totals become normalized scores.

## DOTS API Fingerprints

### High Confidence (weight: 0.20 each)

| API | Context | DOTS Signal |
|-----|---------|-------------|
| `ISystem` | class declaration | Core DOTS system |
| `IJobEntity` | struct declaration | DOTS job processing |
| `EntityCommandBuffer` | field or local var | DOTS structural change |
| `NativeArray<T>` | field, parameter, or local | DOTS native memory |
| `SystemAPI` | method calls | DOTS system API |
| `[BurstCompile]` | attribute on struct/method | DOTS Burst compilation |
| `EntityQuery` | field declaration | DOTS query system |
| `PhysicsVelocity` | field or component access | DOTS Physics |
| `LocalTransform` | component access | DOTS transform |

### Medium Confidence (weight: 0.12 each)

| API | Context |
|-----|---------|
| `SystemBase` | class base | Legacy DOTS system |
| `IJobChunk` | struct declaration | DOTS chunk processing |
| `IAspect` | struct declaration | DOTS aspect |
| `ComponentLookup<T>` | field | DOTS lookup |
| `BufferLookup<T>` | field | DOTS buffer access |
| `DynamicBuffer<T>` | field or return type | DOTS buffer |
| `BlobAssetReference<T>` | field | DOTS immutable data |
| `NativeList<T>` | field or local | DOTS native list |
| `NativeHashMap<K,V>` | field | DOTS native map |
| `EntityManager` | field or method | DOTS entity manager |
| `IComponentData` | interface on struct | DOTS component |
| `IBufferElementData` | interface on struct | DOTS buffer element |
| `IBaker` | interface | DOTS baking |

### Low Confidence (weight: 0.06 each)

| API | Context |
|-----|---------|
| `[UpdateInGroup]` | attribute | DOTS system group |
| `[UpdateBefore]` | attribute | DOTS ordering |
| `[UpdateAfter]` | attribute | DOTS ordering |
| `[WithAll]` | attribute | DOTS query filter |
| `[WithNone]` | attribute | DOTS query filter |
| `Unity.Entities` | namespace import | DOTS assembly |
| `Unity.Physics` | namespace import | DOTS Physics |
| `Unity.Mathematics` | namespace import | DOTS math |
| `Unity.Collections` | namespace import | DOTS collections |
| `Unity.Transforms` | namespace import | DOTS transforms |
| `EntityArchetype` | type usage | DOTS archetype |
| `World` (Unity.Entities) | field or method | DOTS world |

---

## Unity API Fingerprints

### High Confidence (weight: 0.20 each)

| API | Context | Unity Signal |
|-----|---------|-------------|
| `MonoBehaviour` | class base | Unity lifecycle object |
| `Canvas` | component reference | UGUI canvas |
| `RectTransform` | field or GetComponent | UI element |
| `Animator` | field or GetComponent | Unity animation |
| `PlayableDirector` | field or GetComponent | Timeline |
| `AsyncOperationHandle<T>` | field or return | Addressables |
| `DOTween` | static call | DOTween tweening |
| `EditorWindow` | class base | Editor tooling |
| `ScriptableObject` | class base | Data asset |

### Medium Confidence (weight: 0.12 each)

| API | Context |
|-----|---------|
| `Image` | field or GetComponent | UGUI image |
| `Text` | field or GetComponent | UGUI text (legacy) |
| `TextMeshProUGUI` | field or GetComponent | TMP text |
| `Button` | field or GetComponent | UGUI button |
| `CanvasGroup` | field or GetComponent | UGUI group |
| `AudioSource` | field or GetComponent | Unity audio |
| `NavMeshAgent` | field or GetComponent | Unity NavMesh |
| `VisualEffect` | field or GetComponent | VFX Graph |
| `SerializedObject` | field | Editor serialization |
| `AssetReference` | field | Addressables reference |
| `UIDocument` | field | UI Toolkit |
| `VisualElement` | field or return | UI Toolkit element |
| `DOVirtual` | method call | DOTween virtual |
| `TweenCallback` | type | DOTween callback |

### Low Confidence (weight: 0.06 each)

| API | Context |
|-----|---------|
| `[SerializeField]` | attribute | Unity serialization |
| `[MenuItem]` | attribute | Editor menu |
| `[CreateAssetMenu]` | attribute | SO asset menu |
| `Start()` / `Awake()` / `Update()` | method name | MonoBehaviour lifecycle |
| `OnEnable()` / `OnDisable()` | method name | MonoBehaviour events |
| `UnityEngine` | namespace | Core Unity |
| `UnityEngine.UI` | namespace | UGUI |
| `UnityEngine.UIElements` | namespace | UI Toolkit |
| `UnityEditor` | namespace | Editor code |
| `Cinemachine` | namespace | Cinemachine |
| `DG.Tweening` | namespace | DOTween |
| `Coroutine` | return type | Unity coroutine |
| `IEnumerator` | return type with yield | Unity coroutine body |

---

## Hybrid API Fingerprints

### High Confidence (weight: 0.25 each)

| API | Context | Hybrid Signal |
|-----|---------|---------------|
| `Baker<T>` | class base | ECS baking from authoring |
| `GetEntity()` | call in Baker | Baker creating entity |
| `AddComponent()` | call in Baker context | Baker writing component |
| `IBaker` | interface | Baking system |

### Medium Confidence (weight: 0.15 each)

| API | Context |
|-----|---------|
| `CompanionComponent` | class reference | ECS companion object |
| `IConvertGameObjectToEntity` | interface (legacy) | GameObject → Entity |
| `EntityView` | class reference | Entity visual representation |
| `AuthoringComponent` | naming pattern | Authoring MonoBehaviour |
| `GetComponentInParent<Baker>` | method in Baker | Baker dependency |

### Low Confidence (weight: 0.08 each)

| API | Context |
|-----|---------|
| `GetComponent<T>()` in Baker | Baker read | Baker input reading |
| `DependsOn()` | Baker method | Baker dependency chain |
| Prefab field in authoring MonoBehaviour | field type | Authoring input |
| `EntityCommandBuffer` in MonoBehaviour | field | Hybrid bridge |

---

## API Scan Rules

1. Scan only files in the CRG execution path (max 8)
2. Count unique APIs — do not double-count the same API appearing multiple times in one file
3. Cross-file deduplication: if same API appears in 3 files, count it once with weight × 1.5 (indicates broader usage)
4. Namespace imports count at 50% of their weight if the namespace is imported but no APIs from it are explicitly called
5. If a file contains BOTH ISystem (DOTS) AND MonoBehaviour (Unity) → strong Hybrid signal (add hybrid weight for both)

---

## Quick Classification Table

| File name pattern | Strong initial signal | Verify with |
|------------------|-----------------------|-------------|
| `*System.cs` | DOTS (verify ISystem or SystemBase) | namespace Unity.Entities |
| `*Presenter.cs` | Unity (verify Canvas/MonoBehaviour) | Presenter pattern |
| `*View.cs` | Unity or Hybrid | check for Entity refs |
| `*Baker.cs` | Hybrid (verify Baker<T>) | GetEntity() call |
| `*Binding.cs` | Hybrid | both DOTS and Unity APIs |
| `*Manager.cs` | Ambiguous | scan all APIs |
| `*Editor.cs` | Unity (editor) | UnityEditor namespace |
| `*SO.cs` / `*Config.cs` | Unity | ScriptableObject base |
| `*Job.cs` | DOTS | IJobEntity or IJob |
| `*Authoring.cs` | Hybrid | MonoBehaviour + Baker |
