---
name: wave8-baker-dependency-registration
description: Register all external asset and component dependencies in a Baker so that incremental baking re-triggers correctly when referenced objects change.
---

# Baker Dependency Registration — DependsOn

## Intent
Register all external asset and component dependencies in a Baker so that incremental baking re-triggers correctly when referenced objects change.

## Use When
- A Baker reads data from child GameObjects, referenced assets (ScriptableObjects, Textures, etc.), or other components not on the primary authoring GameObject
- Any data source that is not a direct serialized field on the primary authoring MonoBehaviour

## Avoid When
- The Baker only reads from the primary authoring MonoBehaviour's own serialized fields — Unity registers those automatically
- The dependency is read via Baker API methods (GetComponent, GetComponentInChildren) which have their own automatic tracking

## Senior Pattern
```csharp
public class EnemyConfigBaker : Baker<EnemyConfigAuthoring>
{
    public override void Bake(EnemyConfigAuthoring authoring)
    {
        // Reading a referenced asset — MUST call DependsOn:
        DependsOn(authoring.ConfigAsset);  // re-bake if ScriptableObject changes

        // Reading child component via raw Unity API — MUST call DependsOn:
        var childRenderer = authoring.GetComponentInChildren<MeshRenderer>();
        DependsOn(childRenderer);          // re-bake if childRenderer changes

        // Reading via Baker API — automatically tracked, DependsOn not needed:
        var rb = GetComponent<Rigidbody>();     // auto-tracked
        var children = GetChildren();           // auto-tracked

        var entity = GetEntity(TransformUsageFlags.Dynamic);
        AddComponent(entity, new EnemyConfig
        {
            Speed        = authoring.ConfigAsset != null ? authoring.ConfigAsset.Speed : 0f,
            HasRenderer  = childRenderer != null
        });
    }
}
```

## Auto-Tracked vs Manual DependsOn

| Access method | Auto-tracked? | DependsOn needed? |
|---|---|---|
| Direct serialized field on authoring | Yes | No |
| `GetComponent<T>()` (Baker API) | Yes | No |
| `authoring.someField.GetComponent<T>()` (raw Unity API) | No | Yes |
| Referenced ScriptableObject / asset | No | Yes |
| `authoring.transform.GetChild(0).GetComponent<T>()` | No | Yes |
| Static fields / singletons | Never | Cannot register |

## Anti-Patterns
- Accessing `authoring.transform.GetChild(0).GetComponent<T>()` without DependsOn — child change not detected; stale bake with no error.
- Reading a ScriptableObject field without DependsOn — asset change does not trigger re-bake.
- Using static fields or singletons inside Baker.Bake — untracked dependencies; non-deterministic baking results.
- Over-registering DependsOn for fields that are already auto-tracked — causes unnecessary bake invalidation on every change.

## Runtime Risks
- Missing DependsOn causes stale baked data in SubScenes — entity has wrong data until manual re-import.
- This is a silent correctness bug with no runtime error — only manifests as wrong game behavior after source asset changes.
- In Editor Play mode, stale bakes are invisible until SubScene reimport; can cause intermittent test failures.

## Performance Notes
- DependsOn adds incremental bake tracking overhead proportional to the number of registered dependencies.
- Only register dependencies that actually vary between bakes.
- Unnecessary DependsOn calls cause cascading bake invalidations across the SubScene.

## Architecture Guidance
- Rule: if Baker.Bake reads it via raw Unity API and it is not a direct serialized field on the authoring component, call DependsOn.
- Baker-registered dependencies are the baking system's incremental cache invalidation mechanism — correctness of baked data depends on complete dependency registration.

## Related Skills
[[baker-authoring-conversion]], [[baker-depends-on]], [[baking-system]], [[baking-type-component]]
