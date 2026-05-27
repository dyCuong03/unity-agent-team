---
name: blob-asset-deduplication
description: Avoid creating duplicate blob assets for identical source data by checking BlobAssetStore before building, using a stable hash as the deduplication key.
tags: [baking, performance]
---

# Blob Asset Deduplication

## Intent
Avoid creating duplicate blob assets for identical source data by checking BlobAssetStore before building, using a stable hash as the deduplication key.

## Use When
Multiple entities share the same source asset (same mesh, same config file, same ScriptableObject), and creating a separate blob per entity would waste memory. Also when incremental rebaking must avoid rebuilding blobs that haven't changed.

## Avoid When
Every entity has unique blob content — deduplication adds overhead with no benefit. Avoid using GetHashCode() for the stable hash — it is not deterministic across domain reloads.

## Senior Pattern
- Compute a stable hash from the source asset: `AssetDatabase.GetAssetDependencyHash(path)` for Unity assets; custom deterministic hash for procedural data.
- In Baker: `AddBlobAsset(ref blobRef, out _)` performs automatic per-Baker deduplication — identical blobs from the same Baker context are merged.
- For cross-Baker deduplication (baking system): access `BlobAssetStore` via `state.World.GetExistingSystemManaged<BakingSystem>().BlobAssetStore`.
- `blobAssetStore.TryGet<T>(hash, out var existing)` — returns true if an identical blob was already created this bake cycle.
- If TryGet returns false: create the blob, call `blobAssetStore.TryAdd(hash, ref blobRef)`.
- Track processed hashes locally (NativeParallelHashMap) to avoid redundant work within one baking system pass.

## Code Template
```csharp
[WorldSystemFilter(WorldSystemFilterFlags.BakingSystem)]
public partial struct MeshBlobBakingSystem : ISystem
{
    private NativeParallelHashMap<Hash128, BlobAssetReference<MeshBlobData>> m_Cache;

    public void OnCreate(ref SystemState state)
    {
        m_Cache = new NativeParallelHashMap<Hash128, BlobAssetReference<MeshBlobData>>(
            64, Allocator.Persistent);
    }

    public void OnDestroy(ref SystemState state) => m_Cache.Dispose();

    public void OnUpdate(ref SystemState state)
    {
        var blobStore = state.World
            .GetExistingSystemManaged<BakingSystem>().BlobAssetStore;

        foreach (var (rawMesh, entity) in
            SystemAPI.Query<RefRO<RawMeshData>>()
                .WithOptions(EntityQueryOptions.IncludePrefab |
                             EntityQueryOptions.IncludeDisabledEntities)
                .WithEntityAccess())
        {
            var hash = rawMesh.ValueRO.SourceHash;

            if (!m_Cache.TryGetValue(hash, out var blobRef))
            {
                if (!blobStore.TryGet(hash, out blobRef))
                {
                    blobRef = BuildMeshBlob(rawMesh.ValueRO);
                    blobStore.TryAdd(hash, ref blobRef);
                }
                m_Cache[hash] = blobRef;
            }

            state.EntityManager.AddComponentData(entity,
                new MeshBlobComponent { Blob = blobRef });
        }
    }
}
```

## Anti-Patterns
- Using `mesh.GetHashCode()` as the blob hash — not stable across domain reloads, causes false cache misses every reload.
- Not clearing the local hash tracking map between baking passes — stale references from previous pass are used instead of checking BlobAssetStore.
- Creating blobs in parallel jobs and trying to register them in BlobAssetStore from worker threads — BlobAssetStore is not thread-safe for registration; register on main thread only.

## Runtime Risks
Hash collisions (extremely rare with stable hashes) cause incorrect blob sharing — one entity gets another entity's data. Use high-quality hashes (MD5, SHA1, or AssetDatabase dependency hashes).

## Performance Notes
O(1) hash lookup per entity. Deduplication is most valuable when many entities share a small set of source assets (e.g., 100 enemies all using the same animation curve). Without deduplication, N identical blobs × blob_size bytes of wasted memory.

## Architecture Guidance
Deduplication belongs in a baking system, not individual Bakers. Baker.AddBlobAsset handles within-Baker deduplication automatically. Cross-Baker or cross-scene deduplication requires the BlobAssetStore pattern.

## Related Skills
[[blob-asset-in-baker]], [[baking-system]]
