---
name: unity-decal
description: "URP Decal Projector creation and configuration plus DecalRendererFeature setup. Use when users want to create, inspect, configure, batch-edit, delete or validate URP DecalProjectors in the scene, or ensure the active URP renderer has DecalRendererFeature attached. HDRP decal APIs are out of scope. Triggers (EN): decal, Decal Projector, DecalProjector, URP decal, DecalRendererFeature, decal renderer feature, decal material, projector. Triggers (ZH): 贴花, 贴花投射器, 投影贴花, URP 贴花, DecalProjector, 贴花渲染器特性."
platforms: [unity-editor, claude-code]
task-categories: [rendering, urp, editor-automation]
use-when: |-
  Load when the task requires: URP Decal Projector creation and configuration plus DecalRendererFeature setup. Use when users want to create, inspect, configure, batch-edit, delete or validate URP DecalProjectors in the scene, or ensure the active URP renderer has DecalRendererFeature attached. HDRP decal APIs are out of scope. Triggers (EN): decal, Decal Projector, DecalProjector, URP decal, DecalRendererFeature, decal renderer feature, decal material, projector. Triggers (ZH): 贴花, 贴花投射器, 投影贴花, URP 贴花, DecalProjector, 贴花渲染器特性. Unity Editor must be running with the unity-skills REST server reachable at http://localhost:8090.
do-not-use-when: |-
  Do not load when Unity Editor is not running locally. Do not load when unity-skills REST server is unreachable at http://localhost:8090.
metadata:
  source: https://github.com/Besty0728/Unity-Skills
  version: 1.9.2
  tier: 2

---

# Decal Skills

URP Decal Projector creation and configuration (URP only; HDRP decal APIs are not covered here).

## Operating Mode

- Query skills (`decal_get_info`, `decal_find_all`) are `SkillMode.SemiAuto` — they run in all three modes without grant.
- Mutating skills (`decal_create`, `decal_set_properties`, `decal_set_properties_batch`, `decal_ensure_renderer_feature`) are `SkillMode.FullAuto` — under **Approval** they need user grant (grant triggers one server-side execute returning the result); under **Auto** / **Bypass** they execute directly.
- `decal_delete` carries `SkillOperation.Delete` and is **auto-forbidden** in Approval / Auto modes (NeverInSemi). Only **Bypass** or the user-managed **Allowlist** can run it.

## URP Package Stub

This module is compiled against `com.unity.render-pipelines.universal` (`URP`). When URP is not installed, **every** skill returns a stub `{ error: "Universal Render Pipeline package … is not installed." }` (`RenderPipelineSkillsCommon.NoURP()`). The stub is a diagnostic payload, not a permission denial — it does **not** require grant and is **not** treated as NeverInSemi.

## Guardrails

**Routing**:
- For renderer feature management in general: `urp`
- For DecalProjector scene operations: this module

**Runtime-first rules**:
- Call `decal_ensure_renderer_feature` before assuming the current URP renderer is decal-ready
- Use `decal_get_info` / `decal_find_all` to discover real projector state before editing
- `decal_set_properties_batch` expects `items` to be a JSON array string
- This module targets the URP Decal workflow first; do not assume HDRP decal APIs are covered here

## Skills

### `decal_create`
Create a Decal Projector.

### `decal_get_info`
Inspect a Decal Projector.

### `decal_set_properties`
Modify Decal Projector properties.

### `decal_find_all`
List Decal Projectors in the scene.

### `decal_delete`
Delete a Decal Projector GameObject.

### `decal_set_properties_batch`
Batch-edit Decal Projectors.

### `decal_ensure_renderer_feature`
Ensure the target URP renderer has a DecalRendererFeature.

---
## Exact Signatures

Exact names, parameters, defaults, and returns are defined by `GET /skills/schema` or `unity_skills.get_skill_schema()`, not by this file.
