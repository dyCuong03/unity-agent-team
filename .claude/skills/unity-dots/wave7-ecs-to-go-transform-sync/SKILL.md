---
name: wave7-ecs-to-go-transform-sync
description: Synchronize ECS entity world-space position/rotation to a companion GameObject''s Transform each frame for hybrid rendering or audio.
---

# ECS-to-GO Transform Sync

## Intent
Synchronize ECS entity world-space position/rotation to a companion GameObject's Transform each frame for hybrid rendering or audio.

## Use When
- A companion GO (VFX particle system, audio source, UI widget) must track an ECS entity's world-space position without full ECS rendering
- Hybrid mode where some entities use GO rendering alongside ECS simulation

## Avoid When
- The entity is rendered via Entities Graphics — LocalToWorld is consumed directly; no GO sync needed
- Entity count exceeds ~500 synced GOs — main-thread bottleneck; consider instanced rendering instead

## Senior Pattern
```csharp
[UpdateInGroup(typeof(PresentationSystemGroup))]
public partial class CompanionTransformSyncSystem : SystemBase
{
    protected override void OnUpdate()
    {
        foreach (var (l2w, go) in
            SystemAPI.Query<RefRO<LocalToWorld>, UnityEngine.GameObject>())
        {
            if (go == null) continue;  // guard against externally destroyed GOs

            // SetPositionAndRotation is one native call — faster than separate .position/.rotation:
            go.transform.SetPositionAndRotation(
                l2w.ValueRO.Position,
                l2w.ValueRO.Rotation);
        }
    }
}
```

## Anti-Patterns
- Syncing Transform.position inside a job — Transform is a managed type; jobs cannot access it.
- Reading LocalTransform instead of LocalToWorld for world-space sync — LocalTransform is local-space; wrong for child entities in a hierarchy.
- Syncing in SimulationSystemGroup — GO Transform state is not simulation input; sync must run after simulation completes in PresentationSystemGroup.
- Syncing every frame at high entity counts (>500) without LOD or distance culling — main-thread bottleneck; profile explicitly.
- Omitting null guard — GO destroyed externally produces MissingReferenceException every frame.

## Runtime Risks
- If the GO is destroyed externally (scene unload, Object.Destroy), the managed reference becomes null — null guard required.
- Transform sync reads LocalToWorld which is written by TransformSystemGroup — PresentationSystemGroup runs after TransformSystemGroup, so values are current-frame.

## Performance Notes
- Transform.SetPositionAndRotation is faster than separate .position + .rotation assignments — one native P/Invoke call.
- Still main-thread only. Profile at >200 synced entities. At >500, consider:
  - Distance-based culling (only sync entities within camera range)
  - Replacing companion GOs with GPU instancing

## Architecture Guidance
- Run exclusively in PresentationSystemGroup (after simulation and TransformSystemGroup).
- Never sync in SimulationSystemGroup or FixedStepSimulationSystemGroup — GO Transform state is not simulation input.
- Companion GO Transform is write-only from ECS perspective — never read GO Transform.position back into ECS.

## Related Skills
[[wave7-companion-go-lifecycle]], [[wave7-add-component-object-hybrid-attach]], [[local-to-world-read-only-contract]], [[wave7-system-api-managed-api-query]]
