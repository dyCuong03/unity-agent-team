---
name: unity-postprocess
description: "Modern SRP post-processing effects on URP / HDRP VolumeProfiles (built on top of the Volume framework). Use when users want to add / remove / inspect or tune Bloom, Depth Of Field, Tonemapping, Vignette, Color Adjustments, or any modern PP effect override on a VolumeProfile. Do NOT use for the legacy PPv2 stack (`com.unity.postprocessing`). Triggers (EN): post-processing, modern post-processing, Bloom, Depth Of Field, DOF, Tonemapping, Vignette, Color Adjustments, color grading, post effect, VolumeProfile effect. Triggers (ZH): 后处理, 现代后处理, 泛光, Bloom, 景深, 色调映射, 暗角, 颜色调整, 调色, Volume 后处理."
platforms: [unity-editor, claude-code]
task-categories: [post-processing, rendering, editor-automation]
use-when: |-
  Load when the task requires: Modern SRP post-processing effects on URP / HDRP VolumeProfiles (built on top of the Volume framework). Use when users want to add / remove / inspect or tune Bloom, Depth Of Field, Tonemapping, Vignette, Color Adjustments, or any modern PP effect override on a VolumeProfile. Do NOT use for the legacy PPv2 stack (`com.unity.postprocessing`). Triggers (EN): post-processing, modern post-processing, Bloom, Depth Of Field, DOF, Tonemapping, Vignette, Color Adjustments, color grading, post effect, VolumeProfile effect. Triggers (ZH): 后处理, 现代后处理, 泛光, Bloom, 景深, 色调映射, 暗角, 颜色调整, 调色, Volume 后处理. Unity Editor must be running with the unity-skills REST server reachable at http://localhost:8090.
do-not-use-when: |-
  Do not load when Unity Editor is not running locally. Do not load when unity-skills REST server is unreachable at http://localhost:8090.
metadata:
  source: https://github.com/Besty0728/Unity-Skills
  version: 1.9.2
  tier: 2

---

# PostProcess Skills

Modern URP / HDRP post-processing skills built on top of the SRP Volume framework. For Volume container / profile CRUD (`volume_profile_create`, `volume_create`, etc.), use the `volume` module.

## Operating Mode

- Query skills (`postprocess_list_effects`, `postprocess_get_effect`) are `SkillMode.SemiAuto` — they run in all three modes without grant.
- Mutating skills (`postprocess_add_effect`, `postprocess_set_parameter`, `postprocess_set_bloom`, `postprocess_set_depth_of_field`, `postprocess_set_tonemapping`, `postprocess_set_vignette`, `postprocess_set_color_adjustments`) are `SkillMode.FullAuto` — under **Approval** they need user grant (grant triggers one server-side execute returning the result); under **Auto** / **Bypass** they execute directly.
- `postprocess_remove_effect` carries `SkillOperation.Delete` and is **auto-forbidden** in Approval / Auto modes (NeverInSemi). Only **Bypass** or the user-managed **Allowlist** can run it.

## SRP Package Stub

This module is compiled against `com.unity.render-pipelines.core` (`SRP_CORE`). When neither URP nor HDRP is installed (no SRP Core), **every** skill returns a stub `{ error: "Scriptable Render Pipeline Core package … is not installed." }` (`RenderPipelineSkillsCommon.NoSRP()`). The stub is a diagnostic payload, not a permission denial — it does **not** require grant and is **not** treated as NeverInSemi.

## Guardrails

**DO NOT**:
- Use this module for PPv2 / `com.unity.postprocessing`
- Use this module for general Volume container/profile management; use `volume`

**Runtime-first rules**:
- Always call `postprocess_list_effects` before assuming an effect exists on the active pipeline
- Use `postprocess_get_effect` or `volume_get_component` to inspect real parameter names before setting generic parameters
- Prefer the dedicated high-frequency skills (`postprocess_set_bloom`, `postprocess_set_depth_of_field`, etc.) over guessing generic parameter names
- Treat URP and HDRP parameter surfaces as similar-but-not-identical; do not reuse names blindly across pipelines

## Skills

### `postprocess_list_effects`
List modern SRP post-processing effects supported by the active pipeline.

### `postprocess_add_effect`
Add a post-processing effect override to a VolumeProfile.

### `postprocess_remove_effect`
Remove a post-processing effect override from a VolumeProfile.

### `postprocess_get_effect`
Inspect a post-processing effect override.

### `postprocess_set_parameter`
Set one parameter on a post-processing effect override.

### `postprocess_set_bloom`
Configure Bloom.

### `postprocess_set_depth_of_field`
Configure Depth Of Field.

### `postprocess_set_tonemapping`
Configure Tonemapping.

### `postprocess_set_vignette`
Configure Vignette.

### `postprocess_set_color_adjustments`
Configure Color Adjustments.

---
## Exact Signatures

Exact names, parameters, defaults, and returns are defined by `GET /skills/schema` or `unity_skills.get_skill_schema()`, not by this file.
