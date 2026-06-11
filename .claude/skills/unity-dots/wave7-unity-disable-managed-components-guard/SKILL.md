---
name: wave7-unity-disable-managed-components-guard
description: Conditionally compile out all managed IComponentData usage when building for platforms or configurations that prohibit managed components (IL2CPP strict, DOTS Runtime, or custom stripped builds).
tags: [hybrid, managed]
metadata:
  internal-only: true
  tier: 3
---

# UNITY_DISABLE_MANAGED_COMPONENTS Guard

## Intent
Conditionally compile out all managed IComponentData usage when building for platforms or configurations that prohibit managed components (IL2CPP strict, DOTS Runtime, or custom stripped builds).

## Use When
- The project must support both managed-component and managed-component-free build targets
- A platform or build configuration defines UNITY_DISABLE_MANAGED_COMPONENTS

## Avoid When
- The project targets only the standard Unity player — the guard adds complexity without benefit
- All builds will always support managed components — unnecessary conditional complexity

## Senior Pattern
```csharp
// Managed component and its system — guarded:
#if !UNITY_DISABLE_MANAGED_COMPONENTS

public class RenderDataManaged : IComponentData
{
    public Material OverrideMaterial;
}

[UpdateInGroup(typeof(PresentationSystemGroup))]
public partial class ManagedRenderSystem : SystemBase
{
    protected override void OnUpdate()
    {
        foreach (var data in SystemAPI.Query<RenderDataManaged>())
        {
            // apply override material
        }
    }
}

#endif

// Blittable fallback — always present in ALL build configurations:
public struct RenderDataBlittable : IComponentData
{
    public int MaterialIndex;  // index into a shared material array
}

// Systems consuming blittable data — no guard needed:
[BurstCompile]
public partial struct RenderCategoryJob : IJobEntity
{
    [BurstCompile]
    public void Execute(in RenderDataBlittable data, ref RenderTag tag)
    {
        tag.MaterialIndex = data.MaterialIndex;
    }
}
```

## Anti-Patterns
- Leaving managed component code unguarded in a project that enables UNITY_DISABLE_MANAGED_COMPONENTS — compile error at build time, not runtime.
- Guarding only the component definition but not the systems that use it — partial compile failure; system references undefined type.
- Using the guard as an excuse to defer designing a blittable alternative — always provide a blittable fallback; the guard is an opt-in overlay, not a design deferral.
- Nesting guards inconsistently (#if in one file, #endif in another) — C# requires matched pairs per file.

## Runtime Risks
- If a preprocessor guard is missing on a newly added system that references the managed component, the build fails at compile time — not runtime. Risk is missed guards in new code.
- Guard absence is not detectable at runtime — enforce via build pipeline (CI build with UNITY_DISABLE_MANAGED_COMPONENTS defined).

## Performance Notes
- No runtime cost — compile-time only.
- The blittable fallback struct is the hot-path data model in all configurations.
- Managed overlay under the guard is the low-frequency presentation layer.

## Architecture Guidance
- Define blittable struct components as the primary data model — these are the performance-critical ECS data.
- Use managed components as an opt-in overlay under the guard — presentation/rendering quality features.
- Document which systems require the guard to be unset in a project-level comment or README.
- Add a CI build target with UNITY_DISABLE_MANAGED_COMPONENTS defined to catch missing guards early.

## Related Skills
[[managed-component-bridge]], [[wave7-system-api-managed-api-query]], [[icomponentdata-value-component]], [[world-system-filter]]
