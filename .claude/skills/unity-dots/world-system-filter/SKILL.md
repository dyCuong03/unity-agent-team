---
name: world-system-filter
description: Scope a system to specific world types (game world, editor world, thin client, server) so it runs exactly where needed and is excluded from worlds where it would be incorrect or harmful.
---

# WorldSystemFilter

## Intent
Scope a system to specific world types (game world, editor world, thin client, server) so it runs exactly where needed and is excluded from worlds where it would be incorrect or harmful.

## Use When
Custom transform systems that must preview correctly in the subscene editor. Systems that are editor-only (tooling, diagnostics). Multi-world architectures (client/server, editor/runtime).

## Avoid When
Single-world games with no editor-preview requirements and no multi-world architecture — the default behavior (Default world only) is correct.

## Senior Pattern
- `[WorldSystemFilter(WorldSystemFilterFlags.Default)]` — default world only (implicit, same as omitting the attribute).
- `[WorldSystemFilter(WorldSystemFilterFlags.Default | WorldSystemFilterFlags.Editor)]` — game world and editor live-baking world.
- `[WorldSystemFilter(WorldSystemFilterFlags.ServerSimulation)]` — server world only (Netcode for Entities).
- Flags are OR-combined for multi-world membership.

## Code Template
```csharp
// Custom 2D transform — must work in editor subscene preview:
[BurstCompile]
[WorldSystemFilter(WorldSystemFilterFlags.Default | WorldSystemFilterFlags.Editor)]
[UpdateInGroup(typeof(TransformSystemGroup))]
[UpdateAfter(typeof(ParentSystem))]
public partial struct Transform2DSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state) { }
}

// Server-only simulation system:
[BurstCompile]
[WorldSystemFilter(WorldSystemFilterFlags.ServerSimulation)]
[UpdateInGroup(typeof(SimulationSystemGroup))]
public partial struct AuthoritativeMovementSystem : ISystem { }
```

## Anti-Patterns
- Implementing a custom transform or rendering system without the Editor flag — system works in PlayMode but subscene editing preview is broken (entities appear in wrong position/orientation).
- Adding WorldSystemFilter.Editor to a system that reads from external/network state — editor world has no network connection.
- Omitting the attribute entirely when building a server-only system — system runs in the client world too, causing unintended computation.

## Runtime Risks
- Missing Editor flag on custom transform: visual artifacts in subscene editing, authoring workflow broken for designers.
- Wrong world membership in multi-world setup: system runs in a world where its required singletons or entities don't exist — NullReference or RequireForUpdate deadlock.

## Performance Notes
World filter resolution is at world initialization only. No per-frame cost. Systems excluded from a world have zero runtime footprint in that world.

## Architecture Guidance
For any system that extends or overrides a Unity built-in system (transform, rendering), always include WorldSystemFilter.Editor. For multi-world architectures, define world membership at the system level, not via runtime conditionals.
