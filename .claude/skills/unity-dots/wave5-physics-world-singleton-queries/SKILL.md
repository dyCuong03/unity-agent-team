---
name: wave5-physics-world-singleton-queries
description: Perform runtime spatial queries (raycast, collider cast, distance, overlap) against the Unity Physics collision world using PhysicsWorldSingleton.
tags: [physics, query, singleton]
---

# PhysicsWorldSingleton Spatial Queries

## Intent
Perform runtime spatial queries (raycast, collider cast, distance, overlap) against the Unity Physics collision world using PhysicsWorldSingleton.

## Use When
- Line-of-sight checks, ground detection, projectile trajectory, AOE range detection
- Spatial queries against current physics world state (after world build)

## Avoid When
- Queries inside FixedStepSimulationSystemGroup before PhysicsBuildWorldGroup — world not yet built
- Per-entity collision response — use trigger/collision event buffers instead

## Senior Pattern
```csharp
[UpdateInGroup(typeof(SimulationSystemGroup))]
[BurstCompile]
public partial struct RaycastSystem : ISystem
{
    [BurstCompile]
    public void OnUpdate(ref SystemState state)
    {
        // Complete physics jobs before reading PhysicsWorldSingleton:
        state.EntityManager.CompleteDependencyBeforeRO<PhysicsWorldSingleton>();

        var physicsWorld = SystemAPI.GetSingleton<PhysicsWorldSingleton>().PhysicsWorld;

        state.Dependency = new RaycastJob
        {
            World = physicsWorld.CollisionWorld,
            Input = new RaycastInput
            {
                Start = float3.zero,       // replace with actual origin
                End = float3.zero + math.forward() * 100f,
                Filter = new CollisionFilter
                {
                    BelongsTo = ~0u,
                    CollidesWith = 1u << 0,  // target layer only
                    GroupIndex = 0
                }
            },
            Hits = new NativeList<RaycastHit>(Allocator.TempJob)
        }.Schedule(state.Dependency);
    }
}

[BurstCompile]
public struct RaycastJob : IJob
{
    [ReadOnly] public CollisionWorld World;
    public RaycastInput Input;
    public NativeList<RaycastHit> Hits;

    public void Execute() { World.CastRay(Input, ref Hits); }
}
```

Available query types:
```csharp
// Single closest hit:
world.CollisionWorld.CastRay(input, out RaycastHit hit)

// All hits:
world.CollisionWorld.CastRay(input, ref NativeList<RaycastHit> hits)

// Shape cast:
world.CollisionWorld.CastCollider(input, out ColliderCastHit hit)

// Nearest body to point:
world.CollisionWorld.CalculateDistance(input, out DistanceHit hit)

// Broad-phase AABB overlap:
world.CollisionWorld.OverlapAabb(input, ref NativeList<int> bodyIndices)
```

## Anti-Patterns
- Forgetting CompleteDependencyBeforeRO<PhysicsWorldSingleton>() — physics jobs may still be writing; safety error or silent corruption.
- Using CollisionFilter.Default for all queries — hits every body; expensive in dense scenes.
- Scheduling per-entity parallel raycasts via ScheduleParallel — CollisionWorld is shared read-only; batch into a single IJob.Schedule instead.
- Querying inside FixedStepSimulationSystemGroup [UpdateBefore(PhysicsSystemGroup)] — world not yet built for this tick.

## Runtime Risks
- PhysicsWorldSingleton is valid only after PhysicsBuildWorldGroup completes — in SimulationSystemGroup it is always valid (physics runs in fixed step before simulation group).
- ColliderCastInput contains an unsafe Collider pointer — requires [NativeDisableUnsafePtrRestriction] on the field in a job struct.
- NativeList<RaycastHit> allocated with Allocator.TempJob must be Disposed within 4 frames — or use WorldUpdateAllocator.

## Performance Notes
- Single raycast against well-built BVH: O(log N) — very fast.
- Always use CollisionFilter to reduce candidates; batch multiple raycasts into one IJob.
- For many queries per frame, pre-build a NativeArray<RaycastInput> and process all in one IJobParallelFor.

## Architecture Guidance
- Place query systems in SimulationSystemGroup [UpdateAfter(TransformSystemGroup)] for up-to-date positions.
- Always narrow CollisionFilter to minimum necessary layers — review with collision-filter-layer-masking skill.
- Do not store PhysicsWorld reference across frames — rebuild from PhysicsWorldSingleton each OnUpdate.

## Related Skills
[[wave5-fixed-step-simulation-system-group]], [[wave5-collision-filter-layer-masking]], [[wave5-physics-velocity-force-application]], [[wave4-world-update-allocator-per-frame-native]]
