---
name: require-for-update-gate
description: Declare a precondition that prevents a system from running when its required singleton or component type is absent, eliminating boilerplate null-checks and reducing unnecessary scheduling cost.
---

# RequireForUpdate Gate

## Intent
Declare a precondition that prevents a system from running when its required singleton or component type is absent, eliminating boilerplate null-checks and reducing unnecessary scheduling cost.

## Use When
A system only makes sense when a config entity, feature-flag singleton, or scene-scoped marker exists. Multiple requirements can be ANDed.

## Avoid When
The condition changes every frame — RequireForUpdate disables the entire system, including any OnUpdate side effects. If you need conditional logic inside an otherwise-always-running system, use a query filter instead.

## Senior Pattern
- Call state.RequireForUpdate<T>() in OnCreate, once per required type.
- Pair with GetSingleton<T>() inside OnUpdate — the gate guarantees the singleton exists when OnUpdate runs.
- Multiple RequireForUpdate calls are ANDed.

## Code Template
```csharp
[BurstCompile]
public partial struct SpawnSystem : ISystem
{
    [BurstCompile]
    public void OnCreate(ref SystemState state)
    {
        state.RequireForUpdate<SpawnerConfig>();
        state.RequireForUpdate<ExecuteSpawn>();  // scene-activation tag
    }

    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        var config = SystemAPI.GetSingleton<SpawnerConfig>();
        // config is guaranteed to exist here
    }
}
```

## Anti-Patterns
- Calling RequireForUpdate in OnUpdate (valid but wasteful — it rebuilds the query each call).
- Using RequireForUpdate as the only gate and then calling GetSingleton without it — NullReferenceException if entity not yet created.
- Relying on RequireForUpdate to enforce singleton uniqueness — it only checks existence, not count.

## Runtime Risks
- System silently never runs if the required entity is never created — can be hard to debug. Add a log in OnCreate to announce the gate.
- RequireForUpdate with a non-singleton type that has many entities is valid but semantically misleading — prefer WithAll query filter for multi-entity filtering.

## Performance Notes
Zero cost when condition is false — OnUpdate is never entered, no job scheduling overhead.

## Architecture Guidance
Declare all system preconditions in OnCreate. A system that has no entities to act on should cost nothing.
