---
name: dots-transform-patterns
description: The Entities 1.x transform model — LocalTransform (writable input) vs LocalToWorld (system-owned matrix), Parent/Child hierarchy, reparenting cost, uniform vs non-uniform scale (PostTransformMatrix), and when to opt out with custom transform systems. Use when designing parent/child hierarchies, runtime reparenting (mount/dismount/socket), or choosing transform components at the Baker boundary.
---

# Transform Patterns — Senior Patterns

Entities 1.x transforms are a tiny set of components with a strict contract: you write `LocalTransform`, the transform system writes `LocalToWorld`. Mix them up — write `LocalToWorld` directly, store world position in a custom field, or thrash `Parent` add/remove — and you get silent stale data, lagging children, or sky-high frame cost.

## Intent

Use the right components at the right times. Respect the writable-input / derived-output split. Treat hierarchy structural changes as expensive.

## The component model

| Component | Role | Writable by user code? |
|---|---|---|
| `LocalTransform` | Position + Rotation + uniform Scale, parent-relative if `Parent` present | **Yes** — this is the truth |
| `LocalToWorld` | World-space 4×4 matrix | **No** — written by `TransformSystemGroup` |
| `Parent` | Reference to the parent entity | Yes (structural change) |
| `Child` | `DynamicBuffer<Child>` auto-maintained on parents | **No** — maintained by `ParentSystem` |
| `PreviousParent` | Previous frame's parent (system bookkeeping) | No |
| `PostTransformMatrix` | Extra local matrix appended after LocalTransform | Yes — required for non-uniform scale, shear |

**Key rule**: `LocalTransform.Scale` is a `float` (uniform). For non-uniform scale or shear, add `PostTransformMatrix` and bake the float3 scale into its `Value`.

## Senior pattern

```csharp
// Root entity (no Parent): LocalTransform is world-space.
state.EntityManager.AddComponentData(rootEntity, LocalTransform.FromPositionRotationScale(
    new float3(0, 5, 0), quaternion.identity, 1f));

// Child entity: LocalTransform is PARENT-RELATIVE.
state.EntityManager.AddComponentData(childEntity, LocalTransform.FromPosition(new float3(0, 1, 0)));
state.EntityManager.AddComponentData(childEntity, new Parent { Value = rootEntity });

// Reading position correctly:
//   For gameplay: read LocalTransform (local-space) and apply yourself
//   For rendering / world queries: read LocalToWorld (RO output) — never write it
foreach (var l2w in SystemAPI.Query<RefRO<LocalToWorld>>().WithAll<EnemyTag>())
{
    var worldPos = l2w.ValueRO.Position;
    // ...
}
```

## Reparenting (the expensive part)

```csharp
// Adding/removing Parent is a STRUCTURAL CHANGE.
// Must go through ECB; cannot mutate inside a query iteration.
ecb.AddComponent(child, new Parent { Value = newParent });
ecb.SetComponent(child, LocalTransform.FromPosition(localOffset)); // re-set local-space pos

// Detaching: remove the Parent component. Child's LocalTransform becomes its world-space
// transform (which was, until now, the local-space relative to the old parent).
// Senior code SETS the LocalTransform to the desired world-space pose BEFORE removing Parent,
// otherwise the child snaps to its old local offset interpreted as world.
ecb.SetComponent(child, currentWorldTransform);  // freeze world pose
ecb.RemoveComponent<Parent>(child);
```

The transform system updates `Child` and `LocalToWorld` **next frame** after the structural change plays back. Readers in the same frame see stale matrices.

## Custom transforms (advanced opt-out)

You can replace `LocalTransform` with a smaller custom component (e.g. `LocalTransform2D` with only `position2 + rotZ`) and write your own system in `TransformSystemGroup` that produces `LocalToWorld`. Use cases:
- 2D games where rotation around X/Y is impossible by design
- Massive entity counts where the LocalTransform size matters (96 bytes vs 16)
- Billboards, decals, projected geometry

Tradeoff: you give up all Entities Graphics transform integration. Worth it only at >50k of these entities, or when the constraint is structural (truly 2D).

## Anti-patterns

- ❌ Writing into `LocalToWorld` from gameplay code. The transform system overwrites it next frame — your write "disappears" and looks like a bug.
- ❌ Storing world position in a custom field on a gameplay component. Now `LocalTransform` and your field are dual-ownership — they will diverge. Read `LocalToWorld` for world position instead.
- ❌ `EntityManager.AddComponent<Parent>` per frame for a transient mount (e.g. "pickup attached for 5 frames"). Pure archetype churn. Use a follow-system that writes child position from parent's `LocalToWorld` without an actual `Parent` component.
- ❌ Using `LocalTransform.Scale` with `float3(1, 2, 1)` semantics — it's a single float. Non-uniform scale requires `PostTransformMatrix`.
- ❌ The 0.x components: `Translation`, `Rotation`, `NonUniformScale`, `Scale`, `CompositeRotation`, `CompositeScale`. **All gone.** Refuse code that uses them.

## Failure modes

| Symptom | Cause |
|---|---|
| Child entity at origin | Has `Parent` but no `LocalTransform`; or `LocalTransform` zeroed because the Baker chose `TransformUsageFlags.None` |
| Child position lags one frame | Reader runs before `TransformSystemGroup` resolved the new `LocalToWorld` — order the reader after the group, or read `LocalTransform` directly and recompute |
| Scale visible only on one axis | Used `LocalTransform.Scale` for non-uniform; need `PostTransformMatrix` |
| 5× frame cost on reparent-heavy scenes | `Parent` add/remove triggering archetype changes for thousands of entities per frame |
| Detached child snaps to wrong place | Removed `Parent` without first setting `LocalTransform` to the intended world pose |
| Hierarchy seems to work but `Child` buffer is empty | `ParentSystem` runs in `TransformSystemGroup` — read `Child` AFTER that group, not before |

## Runtime verification (Tester Verification Contract)

- **Static:** grep for `RefRW<LocalToWorld>` or `SetComponent<LocalToWorld>(...)` outside `TransformSystemGroup`-resident systems — every match is a bug. Grep for 0.x types (`Translation`, `Rotation`, `NonUniformScale`) — every match is a refactor target.
- **Runtime:** spawn N parented entities, move parents, snapshot child `LocalToWorld` positions, compare against `parent.LocalToWorld * child.LocalTransform`. Mismatch → reading before `TransformSystemGroup` ran.

## Performance notes

- `LocalTransform` size: 32 bytes (position 12 + rotation 16 + scale 4). `LocalToWorld`: 64 bytes. Both on every transform-relevant entity. For 100k entities this is meaningful.
- Reparenting cost = structural change cost = archetype move. Batched via ECB it's tolerable; per-frame it isn't.
- `PostTransformMatrix` adds 64 bytes per entity that needs it. Only attach where non-uniform scale or shear is actually required.

## Compile / editor safety

- `TransformUsageFlags` at the Baker boundary determines which transform components even exist on the runtime entity. Choosing `.None` and then expecting `LocalTransform` to be there is a silent bug. See `dots-baking-patterns`.
- `[WriteGroup(typeof(LocalToWorld))]` lets a custom transform system exclude default writers. Required when implementing a custom transform.

## Entities version notes (1.4.x)

- `LocalTransform` — current. Replaces 0.x `Translation` + `Rotation` + `NonUniformScale`.
- `LocalToWorld` — current, same name as 0.x but now an explicit RO output.
- `Parent` + `Child` (`DynamicBuffer<Child>`) — current. `PreviousParent` is system-internal.
- `PostTransformMatrix` — current, replaces 0.x `CompositeScale` for non-uniform / shear.
- `TransformSystemGroup` runs `ParentSystem` then `LocalToWorldSystem` — order matters for readers.

## See also
- `dots-baking-patterns` — `TransformUsageFlags` selects which transform components a baker emits
- `dots-ecb-orchestration` — reparenting from jobs must go through ECB
- `dots-update-groups` — readers of `LocalToWorld` must run after `TransformSystemGroup`
