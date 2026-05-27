---
name: wave5-local-transform-write-pattern
description: Write entity movement, rotation, and uniform scale through LocalTransform — the single authoritative local-space transform component in Entities 1.x.
tags: [transforms]
---

# LocalTransform Write Pattern

## Intent
Write entity movement, rotation, and uniform scale through LocalTransform — the single authoritative local-space transform component in Entities 1.x.

## Use When
- Moving, rotating, or scaling an entity from gameplay logic
- Reading local-space position/rotation for physics force application on root entities

## Avoid When
- Reading world-space for rendering or spatial queries — read LocalToWorld instead
- Non-uniform scale is needed — use PostTransformMatrix

## Senior Pattern
```csharp
[BurstCompile]
public partial struct MoveJob : IJobEntity
{
    public float DeltaTime;

    [BurstCompile]
    public void Execute(ref LocalTransform transform, in Velocity velocity)
    {
        transform.Position += velocity.Value * DeltaTime;
    }
}

// Field access:
// transform.Position (float3), transform.Rotation (quaternion), transform.Scale (float)

// Construction:
// LocalTransform.FromPositionRotationScale(pos, rot, scale)
```

## Anti-Patterns
- Writing LocalTransform after TransformSystemGroup on a child entity — overwrite takes effect next frame.
- Reading LocalToWorld.Position instead of LocalTransform.Position for physics input on non-root entities — wrong space.
- Teleporting by writing LocalTransform and expecting physics to respond immediately — physics world not rebuilt until PhysicsWorldBuildSystem runs.
- Parallel jobs writing LocalTransform must not also write LocalToWorld in the same job.

## Runtime Risks
- Child entities: LocalTransform is local-space relative to parent; LocalToWorld is computed world-space — confusing them produces wrong physics force direction.
- Writing LocalTransform does not synchronously update LocalToWorld — reads of LocalToWorld are stale until TransformSystemGroup runs.

## Performance Notes
- Single flat component; cache-local access in chunk memory.
- `ref LocalTransform` in IJobEntity gives direct chunk-memory write, no indirection.

## Architecture Guidance
- Root entities: LocalTransform.Position == LocalToWorld.Position.
- Child entities: LocalTransform is local-space relative to parent; LocalToWorld is computed world-space.
- Write motion via LocalTransform; never write LocalToWorld from gameplay systems.
- Non-uniform scale: use PostTransformMatrix — LocalTransform.Scale is a single float.

## Related Skills
[[local-to-world-read-only-contract]], [[post-transform-matrix-non-uniform-scale]], [[parent-child-hierarchy-dynamic]], [[write-group-custom-transform]]
