# SkillHub Discovery Audit
<!-- Architect output — Task #1. Branch: feature/improve-skillhub-discovery -->
<!-- Date: 2026-06-11 -->

## Executive Summary

SkillHub indexed this repo and discovered **2 skills** (`unity-scene`, `unity-cleaner`) out of **186 SKILL.md files** across 3 tiers. Root cause: `task-categories` field exists in `registry.json` but is absent from all SKILL.md frontmatter. SkillHub scans file frontmatter, not the internal routing registry. No skill exposes machine-readable category tags in the file SkillHub reads.

**Quick numbers:**

| Tier | Skills | In registry.json | SkillHub-compatible | Discovered |
|------|--------|-----------------|---------------------|------------|
| Tier 1 — registered top-level | 22 | 22 (100%) | 0 (0%) | 0 |
| Tier 2 — unity-skills sub-modules | 68 | 0 (0%) | 0 (0%) | 2† |
| Tier 3 — unity-dots sub-skills | 96 | 0 (0%) | 0 (0%) | 0 |
| **Total** | **186** | **22** | **0** | **2** |

† These 2 (`unity-scene`, `unity-cleaner`) were likely discovered because SkillHub's upstream index already contained them from the source repo (`github.com/Besty0728/Unity-Skills v1.9.2`). All 68 Tier 2 skills have matching frontmatter names but lack `task-categories`.

---

## Root Cause Analysis

### Primary Cause — `task-categories` field missing from SKILL.md frontmatter

`skills_validator.py` explicitly labels `task-categories` as "Add category tags for SkillHub discovery" and flags its absence as a warning. This field is present in `registry.json` for all 22 registered skills but is **not** in any SKILL.md file's YAML frontmatter. SkillHub scans frontmatter. Registry is internal only.

```
# Evidence: skills_validator.py check_routing_evidence()
"Missing 'task-categories'. Add category tags for SkillHub discovery."
# All 22 registered skills trigger this warning. Tier 2 and 3 are not checked at all.
```

### Secondary Cause — 164 skills not in registry.json

`build_skill_registry.py` only scans direct children of `.claude/skills/`. It never descends into `unity-skills/skills/*/` or `unity-dots/*/`. These 164 skills are invisible to both the `/team` routing system and SkillHub's registry-aware scan path.

### Tertiary Causes — skills fail SkillHub packaging requirements

Even after `task-categories` is added, additional fields must pass validation before SkillHub can index:

| Failure | Scope | Count |
|---------|-------|-------|
| Missing `task-categories` in SKILL.md frontmatter | All tiers | 186 |
| Not in registry.json (`build_skill_registry.py` scan gap) | Tier 2, 3 | 164 |
| Missing YAML frontmatter entirely | Tier 3 | 86 |
| Name-folder mismatch (`name` ≠ parent folder name) | Tier 2 | 68 |
| `user-invocable: false` key (not in `ALLOWED_PROPERTIES`) | Tier 1 | 4 |
| Description >1024 chars | Tier 2 | 4 |
| Missing `use-when`, `do-not-use-when`, `platforms` | Tier 1 partial | 16 |

---

## Validator Coverage Map

Three validators with incompatible scopes and differing requirements:

| Validator | Scope | Required fields | Outcome |
|-----------|-------|-----------------|---------|
| `skill-creator/scripts/quick_validate.py` | All SKILL.md files | `name`, `description` (+ only allows `license`, `allowed-tools`, `metadata`, `compatibility`) | 88 PASS / 99 FAIL |
| `.claude/scripts/validate_skill_pack.py` | All SKILL.md files | `name` must equal parent folder name | 159 issues |
| `.claude/scripts/skills_validator.py` | Only 22 in registry.json | `name`, `description`, `use-when`, `do-not-use-when`, `platforms` + recommended: `task-categories` | FAIL: 2 errors, 66 warnings |

**Key conflict:** `quick_validate.py` forbids `use-when`, `do-not-use-when`, `platforms` (not in ALLOWED_PROPERTIES). `skills_validator.py` requires them. Any skill conforming to one validator fails the other.

---

## Tier 1: Registered Skills (22 total)

All 22 are direct children of `.claude/skills/` and present in `registry.json`.

### Frontmatter state

| Skill | FM keys present | quick_validate | task-categories in FM | SkillHub-ready |
|-------|----------------|---------------|-----------------------|----------------|
| `agentmemory-codebase-recall` | name, description, use-when, do-not-use-when, platforms, **user-invocable** | FAIL (user-invocable unexpected) | NO | NO |
| `architect` | name, description, use-when, do-not-use-when, platforms | FAIL (use-when etc. unexpected) | NO | NO |
| `burst-safety` | name, description, use-when, do-not-use-when, platforms | FAIL (use-when etc. unexpected) | NO | NO |
| `codebase-understanding` | name, description, use-when, do-not-use-when, platforms | FAIL (use-when etc. unexpected) | NO | NO |
| `data-tool` | name, description, use-when, do-not-use-when, platforms | FAIL (use-when etc. unexpected) | NO | NO |
| `ecs-job-patterns` | name, description, use-when, do-not-use-when, platforms | FAIL (use-when etc. unexpected) | NO | NO |
| `editor-data-tools` | name, description, **user-invocable** | FAIL (user-invocable unexpected) | NO | NO |
| `investigation` | name, description | PASS | NO | NO |
| `memory-safety` | name, description | PASS | NO | NO |
| `ownership-partitioning` | name, description | PASS | NO | NO |
| `qa-validation` | name, description, **user-invocable** | FAIL (user-invocable unexpected) | NO | NO |
| `routing` | name, description | PASS | NO | NO |
| `skill-creator` | name, description | PASS | NO | NO |
| `tester` | name, description | PASS | NO | NO |
| `triage` | name, description | PASS | NO | NO |
| `unity-classic` | name, description | PASS | NO | NO |
| `unity-dev` | name, description | PASS | NO | NO |
| `unity-dots` | name, description | PASS | NO | NO |
| `unity-dots-best-practices` | name, description, **user-invocable** | FAIL (user-invocable unexpected) | NO | NO |
| `unity-foundation` | name, description | PASS | NO | NO |
| `unity-skills` | name, description | PASS | NO | NO |
| `verifier` | name, description | PASS | NO | NO |

**Summary:**
- All 22 have `task-categories` in `registry.json` (NOT in frontmatter)
- 6 have extended fields (`use-when`, `do-not-use-when`, `platforms`) in frontmatter
- 4 have invalid `user-invocable` key: `agentmemory-codebase-recall`, `editor-data-tools`, `qa-validation`, `unity-dots-best-practices`
- `skills_validator.py` result: FAIL — 2 ERRORs (false-positive base64 detection in `unity-dots` and `ecs-job-patterns`), 66 WARNINGs

### skills_validator.py false positive ERRORs

`skills_validator.py` uses regex `[A-Za-z0-9+/]{40,}={0,2}` to detect base64 secrets. This incorrectly flags long Unity ECS class names in skill content:
- `unity-dots`: flags `EntityComponentSystemSamples` (40+ alphanum chars)
- `ecs-job-patterns`: flags `BeginSimulationEntityCommandBufferSystem`

These are not secrets. Regex needs whitelist or narrower pattern.

### skills_validator.py trigger collisions (warnings)

| Collision | Skills | Severity |
|-----------|--------|----------|
| codebase-understanding vs architect | both match "architecture investigation" triggers | WARNING |
| architect vs ownership-partitioning | both match "design" triggers | WARNING |
| unity-dots-best-practices vs unity-dots | both match "ECS" triggers | WARNING |
| tester vs qa-validation | both match "test" triggers | WARNING |
| data-tool vs editor-data-tools | both match "editor" triggers | WARNING |

---

## Tier 2: Unity-Skills Sub-Modules (68 total)

Source: `.claude/skills/unity-skills/skills/*/SKILL.md`  
Vendored from: `github.com/Besty0728/Unity-Skills v1.9.2` (commit `80b0c63`, ingested 2026-05-26)

**All 68 are invisible to:**
- `registry.json` (not indexed by `build_skill_registry.py`)
- `/team` skill routing
- `skills_validator.py` (only validates registry entries)

**Uniform frontmatter state:** All 68 have only `name` and `description`. No `task-categories`, `use-when`, `do-not-use-when`, `platforms`.

**Name-folder mismatch:** All 68 fail `validate_skill_pack.py`. Parent folder is short (`scene`, `cleaner`, `animator`…), frontmatter name is `unity-`-prefixed (`unity-scene`, `unity-cleaner`, `unity-animator`…). This is an upstream convention — the upstream package uses the `unity-` prefix in `name` while organizing folders without the prefix.

**quick_validate.py results:** 64 PASS / 4 FAIL (description too long):
- `perception`: 1379 chars
- `shadergraph-design`: 1202 chars
- `test`: 1185 chars
- `validation`: 1092 chars

**Full module list:**

<details>
<summary>All 68 Tier 2 modules (expand)</summary>

| Folder | Frontmatter name | quick_validate | validate_skill_pack |
|--------|-----------------|----------------|---------------------|
| addressables-design | unity-addressables-design | PASS | FAIL (name mismatch) |
| adr | unity-adr | PASS | FAIL |
| animator | unity-animator | PASS | FAIL |
| architecture | unity-architecture | PASS | FAIL |
| asmdef | unity-asmdef | PASS | FAIL |
| async | unity-async | PASS | FAIL |
| audio | unity-audio | PASS | FAIL |
| cinemachine | unity-cinemachine | PASS | FAIL |
| cleaner | unity-cleaner | PASS | FAIL |
| component | unity-component | PASS | FAIL |
| console | unity-console | PASS | FAIL |
| debug | unity-debug | PASS | FAIL |
| dotween-design | unity-dotween-design | PASS | FAIL |
| editor | unity-editor | PASS | FAIL |
| event | unity-event | PASS | FAIL |
| gameobject | unity-gameobject | PASS | FAIL |
| hybrid | unity-hybrid | PASS | FAIL |
| input | unity-input | PASS | FAIL |
| localization | unity-localization | PASS | FAIL |
| math | unity-math | PASS | FAIL |
| movement | unity-movement | PASS | FAIL |
| navmesh | unity-navmesh | PASS | FAIL |
| netcode | unity-netcode | PASS | FAIL |
| netcode-design | unity-netcode-design | PASS | FAIL |
| optimization | unity-optimization | PASS | FAIL |
| patterns | unity-patterns | PASS | FAIL |
| perception | unity-perception | FAIL (desc 1379 chars) | FAIL |
| performance | unity-performance | PASS | FAIL |
| physics | unity-physics | PASS | FAIL |
| platform | unity-platform | PASS | FAIL |
| prefab | unity-prefab | PASS | FAIL |
| profiler | unity-profiler | PASS | FAIL |
| save | unity-save | PASS | FAIL |
| scene | unity-scene | PASS | FAIL |
| scriptableobject | unity-scriptableobject | PASS | FAIL |
| shadergraph | unity-shadergraph | PASS | FAIL |
| shadergraph-design | unity-shadergraph-design | FAIL (desc 1202 chars) | FAIL |
| tags-layers | unity-tags-layers | PASS | FAIL |
| test | unity-test | FAIL (desc 1185 chars) | FAIL |
| testability | unity-testability | PASS | FAIL |
| timeline | unity-timeline | PASS | FAIL |
| ui | unity-ui | PASS | FAIL |
| uitoolkit | unity-uitoolkit | PASS | FAIL |
| unitask-design | unity-unitask-design | PASS | FAIL |
| urp | unity-urp | PASS | FAIL |
| validation | unity-validation | FAIL (desc 1092 chars) | FAIL |
| vfx | unity-vfx | PASS | FAIL |
| yooasset-design | unity-yooasset-design | PASS | FAIL |
| (20 more modules with PASS / FAIL pattern) | … | PASS | FAIL |

</details>

---

## Tier 3: Unity-DOTS Sub-Skills (96 total)

Source: `.claude/skills/unity-dots/*/SKILL.md`

86 of 96 have **no YAML frontmatter** — fail all validators.

10 sub-skills have minimal frontmatter (`name` + `description` only):
- `dots-baking-patterns`
- `dots-ecb-orchestration`
- `dots-enableable-components`
- `dots-entity-lifecycle`
- `dots-spawning-patterns`
- `ecs-fundamentals-isystem-default`
- `ecs-fundamentals-transformusageflags`
- `entity-query-patterns-requireforupdate-gating`
- `entity-query-patterns-systemapi-query`
- `singleton-patterns-config-and-access`

None are in `registry.json`. All fail `validate_skill_pack.py` (86 for no frontmatter, 10 for name-folder mismatch).

---

## Failure Taxonomy

```
CATEGORY A — Discovery blockers (SkillHub cannot index)
  A1: task-categories absent from SKILL.md frontmatter        → 186 skills
  A2: Not in registry / not scannable                          → 164 skills
  A3: No YAML frontmatter                                      → 86 skills

CATEGORY B — Packaging failures (quick_validate.py)
  B1: user-invocable key not in ALLOWED_PROPERTIES             → 4 skills
  B2: Description >1024 chars                                  → 4 skills
  B3: use-when / platforms keys not in ALLOWED_PROPERTIES      → 6 skills

CATEGORY C — Routing failures (validate_skill_pack.py)
  C1: name ≠ parent folder name                                → 68 skills (Tier 2)

CATEGORY D — Completeness failures (skills_validator.py)
  D1: Missing use-when, do-not-use-when, platforms in SKILL.md → 16 skills (Tier 1)
  D2: False-positive ERROR (base64 regex / Unity class names)  → 2 skills
  D3: Trigger collision warnings                               → 10 skills (5 pairs)
```

---

## Remediation Priority

| Priority | Action | Scope | Effort |
|----------|--------|-------|--------|
| P0 | Add `task-categories` to all SKILL.md frontmatter | 22 Tier 1 skills | Low — data already in registry.json |
| P0 | Fix validator schema conflict (quick_validate vs skills_validator) | 2 validators | Medium — see skill-architecture.md |
| P1 | Register Tier 2 sub-modules individually OR expose via parent skill mechanism | 68 skills | High — design decision required |
| P1 | Add frontmatter to 86 Tier 3 sub-skills | 86 skills | High — bulk operation |
| P2 | Truncate 4 descriptions to ≤1024 chars | 4 Tier 2 skills | Low |
| P2 | Remove `user-invocable: false` from 4 skills OR move to metadata sub-key | 4 Tier 1 skills | Low |
| P2 | Fix base64 regex in skills_validator.py | 1 file | Low |
| P3 | Align Tier 2 name-folder convention | 68 skills | Design decision — see skill-architecture.md |
| P3 | Add missing use-when / do-not-use-when to 16 Tier 1 skills | 16 skills | Medium |

---

## Files Referenced

| File | Role |
|------|------|
| `.claude/skills/registry.json` | Internal /team routing registry (22 skills) |
| `.claude/scripts/build_skill_registry.py` | Builds registry — only scans direct children |
| `.claude/scripts/route_skills.py` | /team skill router — reads registry.json |
| `.claude/scripts/skills_validator.py` | Comprehensive validator (registry-bound) |
| `.claude/scripts/validate_skill_pack.py` | Name-folder validator (all SKILL.md) |
| `.claude/skills/skill-creator/scripts/quick_validate.py` | Packaging validator (all SKILL.md) |
| `.claude/skills/unity-skills/` | Vendored Unity-Skills package (v1.9.2) |
| `.claude/skills/unity-dots/` | Unity DOTS sub-skill library |
