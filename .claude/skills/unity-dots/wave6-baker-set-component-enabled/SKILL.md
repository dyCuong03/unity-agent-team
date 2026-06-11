---
name: wave6-baker-set-component-enabled
description: Set the initial enabled state of an IEnableableComponent at bake time using Baker.SetComponentEnabled<T>(), avoiding runtime first-frame conditionals.
tags: [enableable, baking]
metadata:
  internal-only: true
  tier: 3
---

# Baker.SetComponentEnabled — Bake-Time Initial State

## Intent
Set the initial enabled state of an IEnableableComponent at bake time using Baker.SetComponentEnabled<T>(), avoiding runtime first-frame conditionals.

## Use When
- Entity should start with a component present but inactive (e.g., Carry component exists but disabled until grabbed)
- Initial enabled state varies per authoring instance

## Avoid When
- All instances start enabled — AddComponent default is enabled; SetComponentEnabled unnecessary
- Initial state must be set at runtime based on dynamic data — use ISystemStartStop.OnStartRunning

## Senior Pattern
```csharp
public class BallAuthoring : MonoBehaviour
{
    public bool startCarried;
}

public class BallBaker : Baker<BallAuthoring>
{
    public override void Bake(BallAuthoring authoring)
    {
        var entity = GetEntity(TransformUsageFlags.Dynamic);

        // Component must be added before SetComponentEnabled:
        AddComponent<Carry>(entity);
        SetComponentEnabled<Carry>(entity, authoring.startCarried);  // false = present but inactive

        AddComponent<Ball>(entity);
    }
}
```

## Anti-Patterns
- Calling SetComponentEnabled<T> before AddComponent<T> — exception; component must exist first.
- Omitting SetComponentEnabled when default-disabled is required — AddComponent always starts enabled.
- Using a runtime system to set initial state when it could be baked — unnecessary first-frame overhead and potential one-frame visible error state.
- Calling SetComponentEnabled with a hard-coded `true` — this is the default; the call is redundant noise.

## Runtime Risks
- Baker-set enabled state is serialized with SubScene — changing authoring data requires SubScene reimport to take effect.
- If baking is incremental and only the enabled state changes (not component data), ensure DependsOn() captures the relevant authoring property.

## Performance Notes
Zero runtime cost — bake-time operation only. State is embedded in chunk bitmask at SubScene load.

## Architecture Guidance
- Standard baker pattern: `AddComponent<T>(entity)` then `SetComponentEnabled<T>(entity, initialState)`.
- For components that should always start disabled across all instances, document the intent with a comment — otherwise the pattern looks like a mistake.
- Pair with ISystemStartStop.OnStartRunning for runtime initial state that depends on world conditions not available at bake time.

## Related Skills
[[enableable-component]], [[wave6-entity-manager-set-component-enabled]], [[wave6-ecs-state-machine-design]], [[baker-authoring-conversion]]
