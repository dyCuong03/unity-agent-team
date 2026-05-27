---
name: auto-authoring
description: Eliminate Baker boilerplate for components with a direct field-for-field mapping between authoring Inspector and runtime IComponentData, using a generic base class that auto-generates the Baker via...
tags: [baking]
---

# AutoAuthoring — Zero-Boilerplate Baker

## Intent
Eliminate Baker boilerplate for components with a direct field-for-field mapping between authoring Inspector and runtime IComponentData, using a generic base class that auto-generates the Baker via reflection.

## Use When
Rapid prototyping. Components where every authoring field maps directly to a runtime field with no conversion logic. The component is [Serializable] and its Entity fields should resolve directly from GameObject references.

## Avoid When
The Baker needs custom logic (unit conversion, math operations, multi-entity spawning, DependsOn registration for nested assets, blob asset creation). When baking logic grows beyond "copy fields", write an explicit Baker<T>.

## Senior Pattern
- Define the runtime struct as `[Serializable] public struct MyComponent : IComponentData`.
- Declare the authoring class as `public class MyComponentAuthoring : AutoAuthoring<MyComponent>`.
- Add `void OnEnable() {}` to the authoring class to show the enabled checkbox in the Inspector.
- Entity fields in the struct are automatically resolved from Inspector GameObject references via PropertyContainer.
- For buffers: `AutoAuthoring<T>` → `BufferAutoAuthoring<T>`. For shared components: `SharedAutoAuthoring<T>`.

## Code Template
```csharp
// Runtime component — must be [Serializable]
[Serializable]
public struct SpawnConfig : IComponentData
{
    public Entity SpawnPointPrefab;
    public int MaxSpawnCount;
    public float SpawnInterval;
}

// Authoring — zero Baker boilerplate
public class SpawnConfigAuthoring : AutoAuthoring<SpawnConfig>
{
    void OnEnable() { }  // shows enabled checkbox in Inspector
}

// When custom logic is needed, graduate to explicit Baker:
public class SpawnConfigAuthoring : MonoBehaviour
{
    public GameObject SpawnPointPrefab;
    public int MaxSpawnCount = 10;
    public float SpawnIntervalSeconds = 2f;

    class Baker : Baker<SpawnConfigAuthoring>
    {
        public override void Bake(SpawnConfigAuthoring authoring)
        {
            var entity = GetEntity(TransformUsageFlags.None);  // config, not moving
            AddComponent(entity, new SpawnConfig
            {
                SpawnPointPrefab = GetEntity(authoring.SpawnPointPrefab,
                    TransformUsageFlags.Dynamic),
                MaxSpawnCount = authoring.MaxSpawnCount,
                SpawnInterval = authoring.SpawnIntervalSeconds
            });
        }
    }
}
```

## Anti-Patterns
- Using AutoAuthoring when the component needs degrees-to-radians conversion, nested asset loading, or BlobBuilder — base Baker won't do any of this.
- Not adding `[Serializable]` to the IComponentData struct — PropertyContainer cannot serialize it, Inspector shows no fields.
- Expecting AutoAuthoring to register DependsOn for nested assets — it won't, stale bakes possible.

## Runtime Risks
No runtime risks from AutoAuthoring itself. Risk is in misuse: AutoAuthoring always uses `TransformUsageFlags.Dynamic` — data-only entities get unnecessary LocalTransform.

## Performance Notes
AutoAuthoring uses PropertyContainer reflection at bake time — managed, not Burst. Zero runtime cost. Acceptable overhead for simple cases in the authoring workflow.

## Architecture Guidance
AutoAuthoring is a prototyping accelerator. Use it when designing data layouts before committing to a full Baker. Graduate to explicit Baker<T> as soon as baking logic becomes non-trivial.

## Related Skills
[[baker-authoring-conversion]]
