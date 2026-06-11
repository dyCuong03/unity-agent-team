---
name: wave5-collision-filter-layer-masking
description: Control which physics bodies interact with each other and with spatial queries using CollisionFilter bitmask layer assignment, reducing broadphase pairs and query false positives.
tags: [physics]
metadata:
  internal-only: true
  tier: 3
---

# Collision Filter Layer Masking

## Intent
Control which physics bodies interact with each other and with spatial queries using CollisionFilter bitmask layer assignment, reducing broadphase pairs and query false positives.

## Use When
- Physics simulation should exclude certain body pairs (enemies don't collide with each other, bullets pass through allies)
- Spatial queries should hit only specific layers
- Performance optimization in dense scenes by reducing broadphase pairs

## Avoid When
- Only 2-3 bodies need selective collision — trigger-only colliders or kinematic bodies may be simpler
- More than 32 distinct layer categories needed — CollisionFilter has exactly 32 bits

## Senior Pattern
```csharp
// Define layer constants in one shared location:
public static class PhysicsLayer
{
    public const uint Ground     = 1u << 0;
    public const uint Player     = 1u << 1;
    public const uint Enemy      = 1u << 2;
    public const uint Projectile = 1u << 3;
    public const uint Trigger    = 1u << 4;
}

// Interaction rule: A and B interact iff:
//   (A.BelongsTo & B.CollidesWith) != 0  AND  (B.BelongsTo & A.CollidesWith) != 0

// Query-time filter — projectile only hits ground and enemies:
var input = new RaycastInput
{
    Start = origin,
    End   = origin + direction * 100f,
    Filter = new CollisionFilter
    {
        BelongsTo    = PhysicsLayer.Projectile,
        CollidesWith = PhysicsLayer.Ground | PhysicsLayer.Enemy,
        GroupIndex   = 0
    }
};
physicsWorld.CollisionWorld.CastRay(input, out RaycastHit hit);

// Authoring-time — set on PhysicsCollider via Baker:
public override void Bake(ProjectileAuthoring authoring)
{
    var entity = GetEntity(TransformUsageFlags.Dynamic);
    AddComponent(entity, new PhysicsCollider
    {
        Value = Unity.Physics.BoxCollider.Create(
            geometry,
            new CollisionFilter
            {
                BelongsTo    = PhysicsLayer.Projectile,
                CollidesWith = PhysicsLayer.Ground | PhysicsLayer.Enemy,
                GroupIndex   = 0
            })
    });
}
```

## Anti-Patterns
- Using CollisionFilter.Default for all queries — hits every body; expensive in dense scenes.
- Defining filters as plain integers (0, 1, 2) instead of bitmasks (1u << 0, 1u << 1) — integer 1 means layer 0 not layer 1; integer 2 means layer 1 not layer 2.
- Asymmetric filters without intent: A collides with B but B doesn't collide with A — both sides of the AND must agree; asymmetric is valid but requires explicit design documentation.
- Using ~0u (all layers) on high-frequency query colliders — disables all filtering; worst-case broadphase cost.

## Runtime Risks
- Changing CollisionFilter on a PhysicsCollider at runtime requires replacing the BlobAsset reference — structural operation; cannot be done from a parallel job.
- GroupIndex != 0: positive GroupIndex forces collision even if bitmasks disagree; negative GroupIndex forces non-collision even if bitmasks agree — use only when symmetric override is intentional.

## Performance Notes
- Broadphase filter check: single 64-bit AND operation — essentially free per pair.
- Halving the number of candidates reduces narrowphase pair evaluations by ~75%.
- Review layer assignments during architecture design — retroactively adding layers requires auditing and updating all existing filters.

## Architecture Guidance
- Define all layer constants in one shared static class — single source of truth.
- Set BelongsTo on the body (who am I); set CollidesWith on the query or body (who can I hit).
- Review layer assignments during architecture design — retroactive layer additions require changing all existing filters.
- 32-bit limit: plan layer budget early; merge low-priority categories if approaching limit.

## Related Skills
[[wave5-physics-world-singleton-queries]], [[wave5-physics-velocity-force-application]], [[wave5-stateful-physics-event-buffers]], [[wave5-fixed-step-simulation-system-group]]
