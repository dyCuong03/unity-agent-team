---
name: wave5-parent-child-hierarchy-dynamic
description: Attach and detach entities from a parent/child transform hierarchy at runtime using ECB, with correct handling of DynamicBuffer<Child> iteration.
---

# Parent-Child Hierarchy Dynamic

## Intent
Attach and detach entities from a parent/child transform hierarchy at runtime using ECB, with correct handling of DynamicBuffer<Child> iteration.

## Use When
- Entities must be attached/detached dynamically at runtime (weapon pickup, vehicle mounting, character part assembly)
- Batch reparenting of multiple children is required

## Avoid When
- Hierarchy is static and set at bake time — no runtime change needed
- Teleporting to a new position without hierarchy — write LocalTransform.Position directly

## Senior Pattern
```csharp
// Detach all children via ECB (safe during iteration):
DynamicBuffer<Child> children = SystemAPI.GetBuffer<Child>(parentEntity);
var ecb = ecbSystem.CreateCommandBuffer();
for (int i = 0; i < children.Length; i++)
    ecb.RemoveComponent<Parent>(children[i].Value);

// Batch detach (more efficient for large child counts):
ecb.RemoveComponent<Parent>(
    children.AsNativeArray().Reinterpret<Entity>(),
    ComponentType.ReadWrite<Parent>());

// Attach:
ecb.AddComponent(childEntity, new Parent { Value = parentEntity });
ecb.AddComponent(childEntity, LocalTransform.Identity);  // ensure LocalTransform present

// Verify hierarchy in OnCreate:
state.RequireForUpdate(SystemAPI.QueryBuilder().WithAll<Parent>().Build());
```

## Anti-Patterns
- Calling EntityManager.RemoveComponent<Parent>() inside DynamicBuffer<Child> loop — invalidates buffer reference mid-iteration; always use ECB.
- Adding Parent without ensuring child has LocalTransform — hierarchy propagation requires LocalTransform on the child.
- Reading child's LocalToWorld the same frame as reparent — one frame stale until ParentSystem + TransformSystemGroup runs.
- Manually adding or removing elements from DynamicBuffer<Child> — only modify Parent component on the child; ParentSystem exclusively owns Child buffers.

## Runtime Risks
- DynamicBuffer<Child> iteration while structural change pending on same entity — safe with ECB (deferred), unsafe with direct EntityManager calls.
- Children without LocalTransform after attachment are silently skipped by the transform system — no error, just missing world-space position.

## Performance Notes
- Reparenting is a structural change — batch all reparents in one ECB playback to minimize archetype churn.
- For > 100 children, use RemoveComponent<Parent>(query) or batch array overload rather than per-entity ECB commands.

## Architecture Guidance
- Rule: modify Parent on the child, never modify Child buffer on the parent.
- ParentSystem runs early in TransformSystemGroup and rebuilds Child buffers from Parent components each frame.
- Local-space child position after attach: write LocalTransform to desired local offset immediately after ECB adds Parent.

## Related Skills
[[local-transform-write-pattern]], [[local-to-world-read-only-contract]], [[entity-command-buffer]], [[ecb-parallel-writer]]
