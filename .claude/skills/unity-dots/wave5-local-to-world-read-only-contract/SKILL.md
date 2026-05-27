---
name: wave5-local-to-world-read-only-contract
description: Read the computed world-space transform matrix from LocalToWorld for rendering, physics queries, and spatial calculations — never write it from gameplay systems.
tags: [transforms]
---

# LocalToWorld Read-Only Contract

## Intent
Read the computed world-space transform matrix from LocalToWorld for rendering, physics queries, and spatial calculations — never write it from gameplay systems.

## Use When
- World-space position/orientation of any entity (root or child) is needed
- Physics queries require world-space origin/direction
- Rendering or culling systems need the composed TRS matrix

## Avoid When
- Writing entity movement — write LocalTransform instead
- Reading before TransformSystemGroup has run — value is stale from last frame

## Senior Pattern
```csharp
[BurstCompile]
public partial struct SpatialQueryJob : IJobEntity
{
    [BurstCompile]
    public void Execute(in LocalToWorld ltw, ref TargetingData targeting)
    {
        targeting.WorldPosition = ltw.Position;
        targeting.Forward = ltw.Forward;
    }
}

// Accessors:
// ltw.Position (float3), ltw.Forward, ltw.Right, ltw.Up, ltw.Value (float4x4)
```

## Anti-Patterns
- Writing LocalToWorld from a gameplay system — overwritten by TransformSystemGroup next frame.
- Reading LocalToWorld the same frame as a parent reparent — one frame stale until TransformSystemGroup propagates.
- Using LocalToWorld.Position for physics velocity input on child entities without understanding it is world-space.
- Scheduling a system [UpdateBefore(TransformSystemGroup)] and reading LocalToWorld — value is last frame's.

## Runtime Risks
- Reading LocalToWorld before TransformSystemGroup runs returns last frame's value — schedule [UpdateAfter(typeof(TransformSystemGroup))] or accept last-frame latency explicitly.
- If a custom system must write LocalToWorld, it must use [WriteGroup(typeof(LocalToWorld))] to avoid conflict with the standard transform system.

## Performance Notes
- Mark as `in LocalToWorld` in IJobEntity to generate RO type handle — allows parallel reads alongside other RO systems.
- ltw.Value is float4x4 (64 bytes); fits in one or two cache lines.

## Architecture Guidance
- Rule: write motion via LocalTransform; read world-space via LocalToWorld.
- Root entities: LocalToWorld == LocalTransform as a 4x4 matrix (same position).
- Child entities: LocalToWorld is the fully composed parent chain — always correct world-space.
- Custom systems overriding LocalToWorld must use [WriteGroup(typeof(LocalToWorld))].

## Related Skills
[[local-transform-write-pattern]], [[write-group-custom-transform]], [[post-transform-matrix-non-uniform-scale]], [[chunk-did-change-incremental-update]]
