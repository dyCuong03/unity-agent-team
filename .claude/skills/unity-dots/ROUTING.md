---
name: unity-dots-routing
description: Fast skill router for Unity DOTS tasks. Read this first — match keywords to a scenario, then load only the listed skills. Do NOT load this file as a skill.
---

# Unity DOTS Skill Router

**How to use:** Match your task description keywords to a scenario below. Load only the listed skills — 2–3 max. If no scenario matches, fall back to the `SKILL.md` index.

---

## Task Scenarios

### systems
**Keywords:** ISystem, SystemBase, new system, Burst, unmanaged, [BurstCompile], partial struct
**Load:** `isystem-burst-compile`, `require-for-update-gate`, `system-update-order`

### query
**Keywords:** SystemAPI.Query, foreach entity, RefRW, RefRO, WithAll, WithNone, filter entities
**Load:** `systemapi-query-main-thread`, `cross-entity-lookup`, `batch-structural-change-on-query`

### singleton
**Keywords:** singleton, GetSingleton, GetSingletonRW, config component, registry, SystemAPI.GetSingleton
**Load:** `singleton-access`, `require-for-update-gate`

### spawn / instantiate
**Keywords:** spawn, Instantiate, ECB.Instantiate, prefab entity, batched spawn, pool entities
**Load:** `entity-prefab-reference`, `ecb-parallel-writer`, `wave4-unity-mathematics-random-per-entity`

### baking / authoring
**Keywords:** baker, IBaker, Baker<T>, DependsOn, baking, authoring, MonoBehaviour→entity, TransformUsageFlags
**Load:** `baker-authoring-conversion`, `baker-depends-on`, `baking-type-component`
**Also consider:** `baking-system`, `blob-asset-in-baker`, `transform-usage-flags`, `multi-entity-baker`

### blob assets
**Keywords:** BlobAsset, BlobAssetReference, immutable data, blob, baked asset table
**Load:** `blob-asset-in-baker`, `blob-asset-deduplication`

### ECB / structural changes
**Keywords:** ECB, EntityCommandBuffer, AddComponent, RemoveComponent, DestroyEntity, structural change, playback
**Load:** `entity-command-buffer`, `ecb-system-timing`, `structural-change-cost-model`
**Also consider:** `ecb-parallel-writer`, `ecb-manual-immediate`, `ecb-multiplayback`, `batch-structural-change-on-query`

### enableable components / state toggle
**Keywords:** IEnableableComponent, SetComponentEnabled, EnabledRefRW, WithDisabled, state flip, hot toggle
**Load:** `enableable-component`, `wave6-enabled-ref-rw-in-job`, `wave6-with-disabled-query-filter`
**Also consider:** `wave6-zero-data-enableable-signal`, `wave6-ecb-set-component-enabled`

### state machine (ECS)
**Keywords:** state machine, states, transitions, ECS state, AI state, phase component
**Load:** `wave6-ecs-state-machine-design`, `enableable-component`, `wave6-zero-data-enableable-signal`

### jobs
**Keywords:** IJobEntity, IJobChunk, IJob, Schedule, ScheduleParallel, Burst, parallel job
**Load:** `ijobentity-parallel-job`, `wave4-ijobentity-advanced-patterns`, `wave4-burst-compilation-contract`
**Also consider:** `ijobchunk-chunk-job`, `wave4-ijobchunk-full-anatomy`, `wave4-ijob-single-thread-offload`, `job-dependency-chain`

### job dependencies / native containers
**Keywords:** NativeArray, NativeList, NativeHashMap, WorldUpdateAllocator, Allocator, JobHandle, dependency chain
**Load:** `job-dependency-chain`, `wave4-world-update-allocator-per-frame-native`, `wave4-jobhandle-combine-dependencies`
**Also consider:** `wave4-native-parallel-multihashmap-parallel-writer`, `wave4-native-disable-container-safety-restriction`

### transforms / hierarchy
**Keywords:** LocalTransform, LocalToWorld, parent, child, hierarchy, scale, WriteGroup, non-uniform scale
**Load:** `wave5-local-transform-write-pattern`, `wave5-parent-child-hierarchy-dynamic`, `wave5-local-to-world-read-only-contract`
**Also consider:** `wave5-post-transform-matrix-non-uniform-scale`, `wave5-write-group-custom-transform`

### physics (DOTS)
**Keywords:** PhysicsVelocity, PhysicsWorld, RigidBody, collision, trigger, force, impulse, FixedStep, physics query
**Load:** `wave5-physics-velocity-force-application`, `wave5-physics-world-singleton-queries`, `wave5-fixed-step-simulation-system-group`
**Also consider:** `wave5-stateful-physics-event-buffers`, `wave5-collision-filter-layer-masking`, `fixed-step-simulation`

### hybrid ECS + GameObject
**Keywords:** CompanionComponent, MonoBehaviour, companion, GameObject sync, IConvertGameObjectToEntity, managed component
**Load:** `managed-component-bridge`, `wave7-companion-go-lifecycle`, `wave7-ecs-to-go-transform-sync`
**Also consider:** `wave7-add-component-object-hybrid-attach`, `wave7-idisposable-managed-component`

### managed singletons / assets
**Keywords:** ScriptableObject, managed singleton, UnityObjectRef, blittable asset reference, GameObject reference in ECS
**Load:** `wave7-managed-singleton-pattern`, `wave7-unity-object-ref-blittable-asset`

### entity lifecycle / cleanup
**Keywords:** DestroyEntity, ICleanupComponentData, cleanup component, orphan, subscene unload, two-phase teardown
**Load:** `icleanupcomponentdata-runtime`, `entity-command-buffer`

### change detection / incremental
**Keywords:** DidChange, chunk version, incremental update, only-if-changed, ChangeFilter
**Load:** `wave5-chunk-did-change-incremental-update`, `toentityarray-snapshot-pattern`

---

## Symptom Scenarios (Bug Investigation)

### symptom: main-thread stall
**Keywords:** WaitForJobGroupID, Complete(), stall, frame spike, profiler stall, sync point
**Load:** `wave8-handle-complete-sync-point-antipattern`, `wave4-jobhandle-combine-dependencies`, `wave4-world-update-allocator-per-frame-native`

### symptom: system runs at wrong time / frequency
**Keywords:** runs every frame when shouldn't, physics not updating, fixed step firing too much, wrong system group
**Load:** `wave8-wrong-system-group-fixed-timestep`, `wave5-fixed-step-simulation-system-group`, `system-update-order`

### symptom: ECB commands not applied
**Keywords:** ECB not played back, deferred command missing, entity not created, structural change not visible
**Load:** `wave8-ecb-system-group-mismatch`, `ecb-system-timing`, `ecb-manual-immediate`

### symptom: query returns wrong entities
**Keywords:** too many results, missing entities, disabled entity included, enabled entity excluded
**Load:** `wave8-enableable-component-query-mismatch`, `wave6-with-disabled-query-filter`, `wave6-is-component-enabled-check`

### symptom: DynamicBuffer stale / corrupted
**Keywords:** buffer data wrong, buffer reference invalid, DynamicBuffer after structural change
**Load:** `wave8-dynamic-buffer-invalidation`, `toentityarray-snapshot-pattern`

### symptom: baker not running / incremental bake broken
**Keywords:** baker skipped, dependency not tracked, bake not triggered, authoring change ignored
**Load:** `wave8-baker-dependency-registration`, `baker-depends-on`, `wave5-chunk-did-change-incremental-update`

### symptom: IJobChunk skipping entities
**Keywords:** entities skipped, chunk job partial, enabled mask ignored, wrong entity count in job
**Load:** `wave8-ijobchunk-use-enabled-mask-guard`, `wave4-ijobchunk-full-anatomy`, `enableable-component`

### symptom: Complete() in editor / tests acceptable
**Keywords:** editor-only, test mode, Dependency.Complete acceptable, one-shot operation
**Load:** `wave8-dependency-complete-editor-only-fence`, `wave8-handle-complete-sync-point-antipattern`

### symptom: managed system query API failing
**Keywords:** SystemBase managed query, GetComponentObject, managed API, SystemAPI in managed system
**Load:** `wave7-system-api-managed-api-query`, `wave7-unity-disable-managed-components-guard`
