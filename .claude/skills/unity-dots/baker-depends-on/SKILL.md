---
name: baker-depends-on
description: Register all data sources a Baker reads via Baker API methods so the baking system reruns the Baker when any of those sources change, enabling correct incremental live-baking.
---

# Baker DependsOn — Dependency Registration

## Intent
Register all data sources a Baker reads via Baker API methods so the baking system reruns the Baker when any of those sources change, enabling correct incremental live-baking.

## Use When
Any Baker that reads assets, sibling components, referenced GameObjects, ScriptableObjects, or nested asset data beyond the primary authoring MonoBehaviour.

## Avoid When
There is no "avoid when" — if you read it, register it. Unregistered reads produce stale baked data that is silent and hard to diagnose.

## Senior Pattern
- Use `GetComponent<T>(gameObject)` instead of `authoring.GetComponent<T>()` — Baker API method registers the dependency implicitly.
- Use `DependsOn(asset)` for any asset reference (Mesh, Texture, ScriptableObject, etc.) read in the Baker.
- Register DependsOn BEFORE the null check — a null asset may mean "deleted from disk"; the dependency must be registered so the Baker reruns when it is restored.
- Chain DependsOn for nested asset references: `DependsOn(authoring.Info); DependsOn(authoring.Info.Mesh);`
- Do NOT call `DependsOn` in a BakingSystem — not supported and silently ignored.

## Code Template
```csharp
public override void Bake(MeshConfigAuthoring authoring)
{
    // Register BEFORE null check
    DependsOn(authoring.SourceMesh);
    DependsOn(authoring.Config);
    if (authoring.Config != null)
        DependsOn(authoring.Config.Material);  // nested dependency

    if (authoring.SourceMesh == null || authoring.Config == null)
        return;

    // GetComponent registers transform dependency implicitly
    var parentTransform = GetComponent<Transform>(authoring.ReferenceGO);

    var entity = GetEntity(TransformUsageFlags.None);
    AddComponent(entity, new MeshConfig
    {
        Scale = authoring.Config.Scale,
        Offset = parentTransform.localPosition
    });
}
```

## Anti-Patterns
- Reading `authoring.transform` directly instead of `GetComponent<Transform>()` — dependency bypassed, Baker won't rerun on transform change.
- Calling `DependsOn` after a null-guard early return — if the asset is currently null, the dependency is never registered and won't trigger rebaking when the asset is restored.
- Accessing `authoring.someScriptableObject.Field` without `DependsOn(authoring.someScriptableObject)` — SO changes are invisible to the baking system.

## Runtime Risks
No runtime errors — baking dependency failures produce stale baked data. Effects are silent wrong values, missing components, or outdated blobs. Discovered during iteration, not at runtime.

## Performance Notes
Dependency tracking is bake-time only. The more precise the dependencies, the faster incremental rebaking (fewer Bakers triggered per asset change).

## Architecture Guidance
Think of Baker API methods as the "input declaration" of the Baker. Everything the Baker reads must be declared via the Baker API. Direct C# field access on authoring bypasses the declaration.

## Related Skills
[[baker-authoring-conversion]]
