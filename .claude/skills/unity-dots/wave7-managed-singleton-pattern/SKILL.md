---
name: wave7-managed-singleton-pattern
description: Store a single managed object (shared service, UnityEngine asset, or configuration class) as an ECS singleton accessible from systems without dependency injection.
tags: [hybrid, managed, singleton]
---

# Managed Singleton Pattern

## Intent
Store a single managed object (shared service, UnityEngine asset, or configuration class) as an ECS singleton accessible from systems without dependency injection.

## Use When
- A globally accessible managed object is needed that systems can read without passing references through constructors
- A ScriptableObject, shared service class, or configuration asset must be accessible across multiple ECS systems

## Avoid When
- The singleton data is blittable — use a struct IComponentData singleton with SystemAPI.GetSingleton instead
- The singleton changes per-entity — use class IComponentData per entity, not singleton

## Senior Pattern
```csharp
public class GameConfigManaged : IComponentData
{
    public GameConfigAsset Asset;  // ScriptableObject
}

// Bootstrap system — creates singleton once in OnCreate:
[UpdateInGroup(typeof(InitializationSystemGroup))]
public partial class GameConfigBootstrapSystem : SystemBase
{
    public GameConfigAsset Config;  // assigned before world creation

    protected override void OnCreate()
    {
        var entity = EntityManager.CreateEntity();
        EntityManager.AddComponentObject(entity, new GameConfigManaged { Asset = Config });
        Enabled = false;  // run once
    }

    protected override void OnUpdate() { }
}

// Read from any non-Burst system:
var config = SystemAPI.ManagedAPI.GetSingleton<GameConfigManaged>();
int maxEnemies = config.Asset.MaxEnemies;

// Blittable singleton (for comparison — preferred when data is blittable):
var blittableConfig = SystemAPI.GetSingleton<GameConfigBlittable>();
```

## Anti-Patterns
- Using a static field as a substitute — bypasses ECS world lifecycle and teardown; static persists across domain reloads in Editor.
- Creating multiple entities with the same managed singleton component — GetSingleton throws; use HasSingleton guard on bootstrap.
- Accessing managed singleton inside Burst — compile error.
- Storing singleton in a managed field on the system class itself — couples data to system lifetime; not accessible from other systems.

## Runtime Risks
- If the singleton entity is destroyed without cleanup, subsequent GetSingleton calls throw — guard with HasSingleton check.
- Managed singleton holds GC roots; if the managed object implements IDisposable, ensure Dispose is called on world teardown via OnDestroy.
- Static fields as fallbacks persist across Play mode sessions in Editor — always prefer ECS singleton over static.

## Performance Notes
- GetSingleton / ManagedAPI.GetSingleton is O(1) archetype lookup.
- Managed singleton access is main-thread only with no Burst benefit.
- Bootstrap system disables itself after OnCreate — zero per-frame cost.

## Architecture Guidance
- Create managed singletons in a bootstrap system that runs once (Enabled = false after OnCreate).
- Pair with IDisposable and explicit Dispose in OnDestroy if the managed object holds unmanaged resources.
- Use blittable struct singleton (SystemAPI.GetSingleton) as primary pattern; managed singleton only when the data cannot be blittable.

## Related Skills
[[singleton-access]], [[wave7-system-api-managed-api-query]], [[managed-component-bridge]], [[wave7-idisposable-managed-component]]
