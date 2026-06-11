---
name: wave5-write-group-custom-transform
description: Bypass the standard Unity transform system for specific entities by registering a custom component in the LocalToWorld write group, allowing a developer-owned system to compute LocalToWorld for tho...
tags: [transforms]
metadata:
  internal-only: true
  tier: 3
---

# WriteGroup Custom Transform

## Intent
Bypass the standard Unity transform system for specific entities by registering a custom component in the LocalToWorld write group, allowing a developer-owned system to compute LocalToWorld for those entities.

## Use When
- Non-standard transform type needed: 2D, billboard, procedural, skeletal
- Standard transform pipeline must be completely replaced for a subset of entities

## Avoid When
- Only post-processing after the standard transform is needed — use a system [UpdateAfter(TransformSystemGroup)] instead
- The entity has a parent — custom system must handle parent hierarchy propagation manually

## Senior Pattern
```csharp
// 1. Custom component registers in the write group:
[WriteGroup(typeof(LocalToWorld))]
public struct LocalTransform2D : IComponentData
{
    public float2 Position;
    public float Rotation;
}

// 2. Baker uses ManualOverride:
public class LocalTransform2DAuthoring : MonoBehaviour { }
public class LocalTransform2DBaker : Baker<LocalTransform2DAuthoring>
{
    public override void Bake(LocalTransform2DAuthoring authoring)
    {
        var entity = GetEntity(TransformUsageFlags.ManualOverride);
        AddComponent(entity, new LocalTransform2D { });
        AddComponent(entity, new LocalToWorld());
    }
}

// 3. Custom system in TransformSystemGroup after ParentSystem:
[UpdateInGroup(typeof(TransformSystemGroup))]
[UpdateAfter(typeof(ParentSystem))]
[BurstCompile]
public partial struct LocalToWorld2DSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        state.Dependency = new Compute2DJob().ScheduleParallel(state.Dependency);
    }
}

[BurstCompile]
public partial struct Compute2DJob : IJobEntity
{
    [BurstCompile]
    public void Execute(in LocalTransform2D t2d, ref LocalToWorld ltw)
    {
        float cos = math.cos(t2d.Rotation);
        float sin = math.sin(t2d.Rotation);
        ltw.Value = new float4x4(
            new float4(cos, sin, 0, 0),
            new float4(-sin, cos, 0, 0),
            new float4(0, 0, 1, 0),
            new float4(t2d.Position.x, t2d.Position.y, 0, 1)
        );
    }
}
```

## Anti-Patterns
- Forgetting [WriteGroup(typeof(LocalToWorld))] on the custom component — standard transform system overwrites custom LocalToWorld every frame.
- Forgetting TransformUsageFlags.ManualOverride in Baker — standard LocalTransform gets added; standard system processes entity.
- Running custom system before ParentSystem — children of custom-transform entities get stale parent data.
- Not handling PostTransformMatrix in the custom system — non-uniform scale silently discarded.
- Query too broad (includes entities without the custom component) or too narrow (misses some) — LocalToWorld computed by both or neither system.

## Runtime Risks
- If custom system query is too broad or narrow, some entities have LocalToWorld computed by both or neither system — silent transform corruption.
- Entities with custom transform cannot use standard Child hierarchy propagation without explicit implementation in the custom system.

## Performance Notes
- Zero overhead for excluded entities in standard transform system — WriteGroup filtering is archetype-level.
- Implement chunk.DidChange() in the custom system to match the standard incremental update behavior.

## Architecture Guidance
- Always apply the three-part contract: [WriteGroup] on component + TransformUsageFlags.ManualOverride in baker + custom system [UpdateAfter(ParentSystem)] inside TransformSystemGroup.
- Custom system must handle PostTransformMatrix if any affected entity uses non-uniform scale.

## Related Skills
[[local-transform-write-pattern]], [[local-to-world-read-only-contract]], [[post-transform-matrix-non-uniform-scale]], [[chunk-did-change-incremental-update]]
