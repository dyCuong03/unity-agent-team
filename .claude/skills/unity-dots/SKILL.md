---
name: unity-dots
description: Index of 96 senior-level Unity DOTS/ECS skills mined from EntityComponentSystemSamples. Read ROUTING.md first to find the right skill fast — do NOT load this index as a skill on its own.
---

# Unity DOTS Skill Pack — Index

96 senior-level skills. Entities 1.4.x. Source: `Unity-Technologies/EntityComponentSystemSamples`.

**Fast path:** Read [`ROUTING.md`](ROUTING.md) first — match task keywords to a scenario, load 2–3 skills directly.
**Slow path:** Use the keyword column below to find relevant skills, then load by name.

---

## ECS Fundamentals

| Skill | Keywords |
|---|---|
| [`icomponentdata-value-component`](icomponentdata-value-component/SKILL.md) | IComponentData, blittable struct, chunk layout, RefRO, RefRW |
| [`tag-component`](tag-component/SKILL.md) | tag component, zero-size, feature flag, marker component |
| [`isystem-burst-compile`](isystem-burst-compile/SKILL.md) | ISystem, SystemBase, [BurstCompile], BurstDiscard, unmanaged system, bridge system |
| [`systemapi-query-main-thread`](systemapi-query-main-thread/SKILL.md) | SystemAPI.Query, foreach, RefRW, RefRO, WithAll, WithNone, WithEntityAccess |
| [`require-for-update-gate`](require-for-update-gate/SKILL.md) | RequireForUpdate, prerequisite gate, feature flag, ExecuteXxx |
| [`singleton-access`](singleton-access/SKILL.md) | GetSingleton, GetSingletonRW, config, registry, input state |
| [`system-update-order`](system-update-order/SKILL.md) | UpdateInGroup, UpdateBefore, UpdateAfter, execution order |
| [`world-system-filter`](world-system-filter/SKILL.md) | World filter, WorldFlags, disable system, world-specific |
| [`cross-entity-lookup`](cross-entity-lookup/SKILL.md) | ComponentLookup, BufferLookup, GetComponent, HasComponent |
| [`fixed-step-simulation`](fixed-step-simulation/SKILL.md) | FixedStepSimulationSystemGroup, fixed timestep, deterministic |
| [`managed-component-bridge`](managed-component-bridge/SKILL.md) | managed IComponentData, UnityEngine.Object, bridge, MonoBehaviour ref |

---

## Baking & Authoring (Wave 2)

| Skill | Keywords |
|---|---|
| [`baker-authoring-conversion`](baker-authoring-conversion/SKILL.md) | Baker<T>, GetEntity, AddComponent, IBaker, authoring MonoBehaviour |
| [`baker-depends-on`](baker-depends-on/SKILL.md) | DependsOn, baker dependency, incremental bake trigger |
| [`baking-system`](baking-system/SKILL.md) | BakingSystem, post-baking pass, baking world |
| [`baking-type-component`](baking-type-component/SKILL.md) | BakingType, bake-only component, editor-only data |
| [`baking-type-cleanup-component`](baking-type-cleanup-component/SKILL.md) | BakingType + cleanup, bake-and-remove pattern |
| [`baking-world-query-options`](baking-world-query-options/SKILL.md) | EntityQueryOptions.IncludePrefab, IncludeDisabledEntities, baking query |
| [`blob-asset-in-baker`](blob-asset-in-baker/SKILL.md) | BlobAssetReference, blob builder, immutable baked data |
| [`blob-asset-deduplication`](blob-asset-deduplication/SKILL.md) | blob dedup, BlobAssetStore, identical blob sharing |
| [`entity-prefab-reference`](entity-prefab-reference/SKILL.md) | prefab entity, baker prefab, Entity reference, instantiate |
| [`multi-entity-baker`](multi-entity-baker/SKILL.md) | CreateAdditionalEntity, multi-entity, baker child entities |
| [`temporary-baking-type`](temporary-baking-type/SKILL.md) | temporary baking component, bake-only lifetime |
| [`transform-usage-flags`](transform-usage-flags/SKILL.md) | TransformUsageFlags, Dynamic, Renderable, ManualOverride, None, archetype bloat |
| [`auto-authoring`](auto-authoring/SKILL.md) | auto-authoring, simplified baker, zero-config conversion |

---

## Entity Command Buffer (Wave 3)

| Skill | Keywords |
|---|---|
| [`entity-command-buffer`](entity-command-buffer/SKILL.md) | ECB, EntityCommandBuffer, deferred, Playback, BeginSimulation |
| [`ecb-system-timing`](ecb-system-timing/SKILL.md) | ECB playback timing, BeginSimulationECB, EndSimulationECB, when playback fires |
| [`ecb-parallel-writer`](ecb-parallel-writer/SKILL.md) | ECB.ParallelWriter, parallel structural change, ChunkIndexInQuery sort key |
| [`ecb-manual-immediate`](ecb-manual-immediate/SKILL.md) | manual ECB, immediate playback, ECB.Dispose, owned ECB |
| [`ecb-multiplayback`](ecb-multiplayback/SKILL.md) | multi-playback ECB, reuse ECB, PlaybackPolicy.MultiPlayback |
| [`direct-entity-manager-structural-changes`](direct-entity-manager-structural-changes/SKILL.md) | EntityManager, sync point, main thread structural change |
| [`structural-change-cost-model`](structural-change-cost-model/SKILL.md) | archetype churn, structural change cost, batch vs deferred |
| [`batch-structural-change-on-query`](batch-structural-change-on-query/SKILL.md) | batch structural, AddComponentMatchingEntities, query-batch |
| [`toentityarray-snapshot-pattern`](toentityarray-snapshot-pattern/SKILL.md) | ToEntityArray, snapshot, structural change during iteration |
| [`icleanupcomponentdata-runtime`](icleanupcomponentdata-runtime/SKILL.md) | ICleanupComponentData, two-phase teardown, orphan entity, DestroyEntity |

---

## Jobs & Native Containers (Wave 4)

| Skill | Keywords |
|---|---|
| [`ijobentity-parallel-job`](ijobentity-parallel-job/SKILL.md) | IJobEntity, Schedule, ScheduleParallel, job query |
| [`ijobchunk-chunk-job`](ijobchunk-chunk-job/SKILL.md) | IJobChunk, Execute chunk, ArchetypeChunk, chunk iteration |
| [`job-dependency-chain`](job-dependency-chain/SKILL.md) | state.Dependency, JobHandle, chain, dependency propagation |
| [`wave4-ijobentity-advanced-patterns`](wave4-ijobentity-advanced-patterns/SKILL.md) | IJobEntity WithAll WithNone, ChunkIndexInQuery, EntityIndexInQuery |
| [`wave4-ijobchunk-full-anatomy`](wave4-ijobchunk-full-anatomy/SKILL.md) | IJobChunk full, GetNativeArray, chunk components, useEnabledMask |
| [`wave4-ijob-single-thread-offload`](wave4-ijob-single-thread-offload/SKILL.md) | IJob, single-threaded job, off main thread, background work |
| [`wave4-ijobparallelfor-array-transform`](wave4-ijobparallelfor-array-transform/SKILL.md) | IJobParallelFor, array transform, per-index parallel |
| [`wave4-burst-compilation-contract`](wave4-burst-compilation-contract/SKILL.md) | Burst contract, Burst-safe, no managed in Burst, BurstCompile rules |
| [`wave4-jobhandle-combine-dependencies`](wave4-jobhandle-combine-dependencies/SKILL.md) | JobHandle.CombineDependencies, fan-in, multiple dependencies |
| [`wave4-world-update-allocator-per-frame-native`](wave4-world-update-allocator-per-frame-native/SKILL.md) | WorldUpdateAllocator, per-frame NativeArray, auto-free allocator |
| [`wave4-native-parallel-multihashmap-parallel-writer`](wave4-native-parallel-multihashmap-parallel-writer/SKILL.md) | NativeParallelMultiHashMap, parallel writer, concurrent writes |
| [`wave4-native-disable-container-safety-restriction`](wave4-native-disable-container-safety-restriction/SKILL.md) | [NativeDisableContainerSafetyRestriction], alias containers, safety override |
| [`wave4-entity-index-in-query-scatter-pattern`](wave4-entity-index-in-query-scatter-pattern/SKILL.md) | EntityIndexInQuery, scatter write, per-entity index, NativeArray scatter |
| [`wave4-systembase-with-inner-ijobentity`](wave4-systembase-with-inner-ijobentity/SKILL.md) | SystemBase + IJobEntity, managed outer + Burst inner job |
| [`wave4-unity-mathematics-random-per-entity`](wave4-unity-mathematics-random-per-entity/SKILL.md) | Unity.Mathematics.Random, per-entity random, CreateFromIndex, deterministic RNG |

---

## Transforms & Hierarchy (Wave 5)

| Skill | Keywords |
|---|---|
| [`wave5-local-transform-write-pattern`](wave5-local-transform-write-pattern/SKILL.md) | LocalTransform, write position rotation scale, transform mutation |
| [`wave5-local-to-world-read-only-contract`](wave5-local-to-world-read-only-contract/SKILL.md) | LocalToWorld, read-only, computed transform, do not write |
| [`wave5-parent-child-hierarchy-dynamic`](wave5-parent-child-hierarchy-dynamic/SKILL.md) | Parent, Child, dynamic hierarchy, reparent, transform propagation |
| [`wave5-post-transform-matrix-non-uniform-scale`](wave5-post-transform-matrix-non-uniform-scale/SKILL.md) | PostTransformMatrix, non-uniform scale, stretch, TRS matrix |
| [`wave5-write-group-custom-transform`](wave5-write-group-custom-transform/SKILL.md) | WriteGroup, custom transform system, override TransformSystem |
| [`wave5-chunk-did-change-incremental-update`](wave5-chunk-did-change-incremental-update/SKILL.md) | DidChange, chunk version, incremental update, change filter |
| [`wave5-isystem-start-stop`](wave5-isystem-start-stop/SKILL.md) | ISystem OnStartRunning, OnStopRunning, enabled system lifecycle |

---

## Physics (Wave 5)

| Skill | Keywords |
|---|---|
| [`wave5-physics-velocity-force-application`](wave5-physics-velocity-force-application/SKILL.md) | PhysicsVelocity, force, impulse, dynamic body, linear angular |
| [`wave5-physics-world-singleton-queries`](wave5-physics-world-singleton-queries/SKILL.md) | PhysicsWorld, singleton, raycast, overlap, CollisionWorld queries |
| [`wave5-collision-filter-layer-masking`](wave5-collision-filter-layer-masking/SKILL.md) | CollisionFilter, layer mask, BelongsTo, CollidesWith |
| [`wave5-stateful-physics-event-buffers`](wave5-stateful-physics-event-buffers/SKILL.md) | StatefulTriggerEvent, StatefulCollisionEvent, persistent physics events |
| [`wave5-fixed-step-simulation-system-group`](wave5-fixed-step-simulation-system-group/SKILL.md) | FixedStepSimulationSystemGroup, fixed step scheduling, physics update group |

---

## Enableable Components (Wave 6)

| Skill | Keywords |
|---|---|
| [`enableable-component`](enableable-component/SKILL.md) | IEnableableComponent, enableable, zero-size, hot toggle, no archetype churn |
| [`wave6-enabled-ref-rw-in-job`](wave6-enabled-ref-rw-in-job/SKILL.md) | EnabledRefRW, EnabledRefRO, enable/disable in IJobEntity |
| [`wave6-with-disabled-query-filter`](wave6-with-disabled-query-filter/SKILL.md) | WithDisabled, query disabled entities, include disabled in query |
| [`wave6-is-component-enabled-check`](wave6-is-component-enabled-check/SKILL.md) | IsComponentEnabled, HasComponent enabled check, SystemAPI enabled |
| [`wave6-baker-set-component-enabled`](wave6-baker-set-component-enabled/SKILL.md) | baker SetComponentEnabled, bake initially disabled |
| [`wave6-ecb-set-component-enabled`](wave6-ecb-set-component-enabled/SKILL.md) | ECB SetComponentEnabled, deferred enable/disable |
| [`wave6-entity-manager-set-component-enabled`](wave6-entity-manager-set-component-enabled/SKILL.md) | EntityManager SetComponentEnabled, immediate enable/disable |
| [`wave6-zero-data-enableable-signal`](wave6-zero-data-enableable-signal/SKILL.md) | zero-data enableable, signal component, boolean state, pure flag |
| [`wave6-ecs-state-machine-design`](wave6-ecs-state-machine-design/SKILL.md) | ECS state machine, enum vs enableable vs structural, state decision model |

---

## Managed Components & Hybrid (Wave 7)

| Skill | Keywords |
|---|---|
| [`wave7-companion-go-lifecycle`](wave7-companion-go-lifecycle/SKILL.md) | CompanionComponent, companion GameObject, entity-linked GO |
| [`wave7-ecs-to-go-transform-sync`](wave7-ecs-to-go-transform-sync/SKILL.md) | ECS→GO transform sync, LocalToWorld→Transform, copy to GameObject |
| [`wave7-add-component-object-hybrid-attach`](wave7-add-component-object-hybrid-attach/SKILL.md) | AddComponentObject, hybrid attach, managed component on entity |
| [`wave7-idisposable-managed-component`](wave7-idisposable-managed-component/SKILL.md) | IDisposable managed component, cleanup, managed lifetime |
| [`wave7-managed-singleton-pattern`](wave7-managed-singleton-pattern/SKILL.md) | managed singleton, ScriptableObject ref in ECS, non-blittable singleton |
| [`wave7-system-api-managed-api-query`](wave7-system-api-managed-api-query/SKILL.md) | SystemAPI managed, GetComponentObject, managed query from ISystem |
| [`wave7-unity-object-ref-blittable-asset`](wave7-unity-object-ref-blittable-asset/SKILL.md) | UnityObjectRef, blittable Unity asset reference, Mesh Material reference |
| [`wave7-unity-disable-managed-components-guard`](wave7-unity-disable-managed-components-guard/SKILL.md) | UNITY_DISABLE_MANAGED_COMPONENTS, managed component guard, stripping |

---

## Anti-Patterns & Debug (Wave 8)

| Skill | Keywords |
|---|---|
| [`wave8-handle-complete-sync-point-antipattern`](wave8-handle-complete-sync-point-antipattern/SKILL.md) | handle.Complete(), sync point, WaitForJobGroupID, main thread stall |
| [`wave8-wrong-system-group-fixed-timestep`](wave8-wrong-system-group-fixed-timestep/SKILL.md) | wrong system group, fixed timestep, SimulationSystemGroup vs FixedStep |
| [`wave8-ecb-system-group-mismatch`](wave8-ecb-system-group-mismatch/SKILL.md) | ECB group mismatch, playback timing wrong, deferred commands missing |
| [`wave8-enableable-component-query-mismatch`](wave8-enableable-component-query-mismatch/SKILL.md) | query returns wrong entities, enabled/disabled mismatch, WithPresent |
| [`wave8-dynamic-buffer-invalidation`](wave8-dynamic-buffer-invalidation/SKILL.md) | DynamicBuffer stale, buffer reference invalid after structural change |
| [`wave8-ijobchunk-use-enabled-mask-guard`](wave8-ijobchunk-use-enabled-mask-guard/SKILL.md) | IJobChunk enabled mask, useEnabledMask, skip disabled entities in chunk |
| [`wave8-baker-dependency-registration`](wave8-baker-dependency-registration/SKILL.md) | baker dependency missing, incremental bake not triggered, DependsOn |
| [`wave8-dependency-complete-editor-only-fence`](wave8-dependency-complete-editor-only-fence/SKILL.md) | Dependency.Complete acceptable, editor-only fence, test sync |

---

## Pre-existing Skills (Wave 1 Originals)

| Skill | Keywords |
|---|---|
| [`dots-baking-patterns`](dots-baking-patterns/SKILL.md) | baking deep-dive, BakingDependencies, Baker multi-phase |
| [`dots-ecb-orchestration`](dots-ecb-orchestration/SKILL.md) | ECB orchestration, BeginSimulation, EndSimulation, parallel writer |
| [`dots-enableable-components`](dots-enableable-components/SKILL.md) | enableable deep-dive, IEnableableComponent full guide |
| [`dots-entity-lifecycle`](dots-entity-lifecycle/SKILL.md) | entity lifecycle, DestroyEntity, ICleanupComponentData, orphan |
| [`dots-spawning-patterns`](dots-spawning-patterns/SKILL.md) | spawning patterns, ECB.Instantiate, RequireForUpdate, Random spawn |
| [`ecs-fundamentals-isystem-default`](ecs-fundamentals-isystem-default/SKILL.md) | ISystem vs SystemBase deep-dive, BurstDiscard trap |
| [`ecs-fundamentals-transformusageflags`](ecs-fundamentals-transformusageflags/SKILL.md) | TransformUsageFlags full guide, archetype bloat |
| [`singleton-patterns-config-and-access`](singleton-patterns-config-and-access/SKILL.md) | singleton config deep-dive, prefab table, input state |
| [`entity-query-patterns-systemapi-query`](entity-query-patterns-systemapi-query/SKILL.md) | SystemAPI.Query deep-dive, IJobEntity promotion |
| [`entity-query-patterns-requireforupdate-gating`](entity-query-patterns-requireforupdate-gating/SKILL.md) | RequireForUpdate deep-dive, feature flag gate, first-frame race |

---

## Authoring Rules

- Senior-level only. No tutorial content.
- Entities 1.x APIs only. Deprecated 0.x APIs get a "DO NOT USE" callout.
- Each skill must answer: *what does a senior DOTS engineer know that a junior doesn't?*
