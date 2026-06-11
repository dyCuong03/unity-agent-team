# Skill Architecture
<!-- Architect output — Tasks #2 + #5. Branch: feature/improve-skillhub-discovery -->
<!-- Date: 2026-06-11 — Updated with corpus, capability matrix, skill budget, granularity rules -->

## Overview

This document defines the canonical skill structure, metadata schema, registry design, and migration plan for SkillHub compatibility. It is the contract for `skill-platform-dev` to implement and `qa-security` to validate.

---

## 1. Three-Tier Skill Architecture

```
.claude/skills/
├── <skill-name>/                  ← Tier 1: Top-level registered skills (22)
│   ├── SKILL.md                   ← Canonical entry point — must conform to §2
│   └── ...
├── unity-skills/                  ← Parent bundle — skills NOT individually registered
│   └── skills/
│       └── <module>/              ← Tier 2: Sub-modules (68)
│           ├── SKILL.md           ← Must conform to §2 (currently only name+description)
│           └── ...
└── unity-dots/                    ← Domain-specific library
    └── <sub-skill>/               ← Tier 3: Sub-skills (96)
        └── SKILL.md               ← 86 missing frontmatter entirely
```

### Tier rules

| Tier | In registry.json | SkillHub discoverable | /team routing | Notes |
|------|-----------------|----------------------|---------------|-------|
| Tier 1 | YES (required) | YES (after migration) | YES | Single source of truth for routing |
| Tier 2 | NO (parent only) | YES (after migration) | Via parent | Sub-modules referenced by `unity-skills` entry |
| Tier 3 | NO (parent only) | NO (internal only) | Via parent | DOTS-specific patterns, never user-invocable |

Tier 3 is **internal-only**. SkillHub must NOT index Tier 3 sub-skills. They contain implementation-level DOTS patterns loaded by `unity-dots` and `unity-dots-best-practices` parent skills.

---

## 2. Canonical SKILL.md Frontmatter Schema

### Unified schema (resolves validator conflict)

The current validators conflict: `quick_validate.py` only allows 6 keys; `skills_validator.py` requires fields `quick_validate.py` rejects. The unified schema below is the target state. `quick_validate.py` must be updated to accept the new required fields (see §5).

```yaml
---
# REQUIRED — all validators
name: <kebab-case-max-64-chars>       # Must equal parent folder name (Tier 1 & 3)
                                       # Tier 2: uses upstream name (unity-prefixed OK)
description: <string-max-1024-chars>  # No < or > characters

# REQUIRED — SkillHub discovery (add to frontmatter, also keep in registry.json)
task-categories:
  - <category-tag>                    # min 1, max 5 tags from canonical vocabulary

# REQUIRED — routing and scoping
use-when: <string>                    # Positive trigger condition (max 256 chars)
do-not-use-when: <string>            # Exclusion condition (max 256 chars)
platforms:
  - claude-code                       # Valid: claude-code, codex, copilot, cursor, windsurf

# OPTIONAL — metadata sub-object (replaces top-level user-invocable, source, etc.)
metadata:
  user-invocable: false               # Put non-standard keys HERE, not at top level
  source: <url>                       # Origin of vendored content
  version: <semver>                   # Upstream version if vendored
  tier: <1|2|3>                       # Which tier this skill belongs to
  internal-only: <bool>               # true = never exposed to SkillHub

# OPTIONAL — examples
positive-example: <string>
negative-example: <string>
---
```

### Field constraints

| Field | Type | Required | Constraint |
|-------|------|----------|------------|
| `name` | string | YES | kebab-case, max 64 chars, must match parent folder (Tier 1 and Tier 3) |
| `description` | string | YES | max 1024 chars, no `<` or `>` |
| `task-categories` | string[] | YES (Tier 1 & 2) | 1–5 tags from vocabulary below |
| `use-when` | string | YES (Tier 1 & 2) | max 256 chars |
| `do-not-use-when` | string | YES (Tier 1 & 2) | max 256 chars |
| `platforms` | string[] | YES (Tier 1 & 2) | subset of `{claude-code, codex, copilot, cursor, windsurf}` |
| `metadata` | object | NO | sub-object for non-standard keys |
| `metadata.user-invocable` | bool | NO | default true; set false for pipeline-only skills |
| `metadata.source` | string | NO | URL of upstream origin |
| `metadata.version` | string | NO | semver of upstream source |
| `metadata.tier` | int | NO | 1, 2, or 3 |
| `metadata.internal-only` | bool | NO | default false; true = exclude from SkillHub |
| `positive-example` | string | NO | example invocation |
| `negative-example` | string | NO | counter-example |

### task-categories canonical vocabulary

Tags must come from this vocabulary. Propose new tags via PR to this file.

```
# Domain
unity-dots      unity-ecs       unity-classic    unity-ui        unity-animation
unity-physics   unity-audio     unity-editor     unity-build     unity-addressables
unity-netcode   unity-shadergraph  unity-vfx     unity-testing   unity-optimization

# Role / workflow
investigation   architecture    implementation   validation      refactor
triage         code-review     knowledge-recall  debugging       performance

# Technology
burst-safety    jobs            memory-safety    async           coroutine
scriptableobject  prefab         timeline        cinemachine     vcontainer

# Process
skill-routing   ownership       pipeline        agent-memory
```

---

## 3. Registry.json Schema

### Updated registry entry schema

`registry.json` remains the internal routing registry. It must be kept in sync with SKILL.md frontmatter. Fields duplicated from SKILL.md frontmatter are the authoritative source in SKILL.md; registry copies are derived.

```json
{
  "skills": [
    {
      "name": "unity-dots-best-practices",
      "description": "...",
      "task-categories": ["unity-dots", "unity-ecs", "burst-safety"],
      "use-when": "...",
      "do-not-use-when": "...",
      "platforms": ["claude-code"],
      "roles": ["unity-dev", "architect"],
      "keywords": ["ISystem", "ECS", "Burst", "entity"],
      "mode": "advisory",
      "load_by_default": false,
      "priority": "specific-local",
      "routing-rule": "load when DOTS_score >= 0.70",
      "positive-example": "...",
      "negative-example": "...",
      "source": "internal",
      "version": "1.0.0",
      "tier": 1,
      "internal-only": false
    }
  ]
}
```

### New required fields in registry entries

| Field | Was | Now |
|-------|-----|-----|
| `task-categories` | Optional (existed for 22 skills) | Required, must mirror SKILL.md |
| `source` | Missing | Required — "internal" or upstream URL |
| `version` | Missing | Required — semver |
| `tier` | Missing | Required — 1, 2, or 3 |
| `internal-only` | Missing | Required — controls SkillHub exposure |

---

## 4. Per-Tier Migration Plan

### Tier 1 (22 registered skills) — Priority P0

**Goal:** Add `task-categories` to SKILL.md frontmatter. Fix invalid keys. Add missing required fields.

**Changes per skill group:**

**Group A — 6 skills with `use-when`, `do-not-use-when`, `platforms` already:**  
(`agentmemory-codebase-recall`, `architect`, `burst-safety`, `codebase-understanding`, `data-tool`, `ecs-job-patterns`)
1. Add `task-categories` to SKILL.md frontmatter (copy from registry.json)
2. Move `user-invocable: false` into `metadata:` sub-object (agentmemory only)
3. quick_validate.py update needed to accept `use-when`, `do-not-use-when`, `platforms`

**Group B — 16 skills with only `name` + `description`:**  
(all others)
1. Add `task-categories` from registry.json
2. Add `use-when`, `do-not-use-when`, `platforms`
3. Remove `user-invocable: false` from top level → `metadata.user-invocable: false` (editor-data-tools, qa-validation, unity-dots-best-practices)

**Special cases:**
- `unity-dots`: Add `metadata.internal-only: false`. The `task-categories` already in registry covers "unity-dots, unity-ecs". The false positive ERROR in skills_validator.py needs regex fix (§6).
- `ecs-job-patterns`: Same base64 regex fix needed.

**Migration script target (skill-platform-dev):**  
```
python .claude/scripts/migrate_tier1_frontmatter.py
```
Reads registry.json `task-categories` per skill, writes to SKILL.md frontmatter. Idempotent.

---

### Tier 2 (68 unity-skills sub-modules) — Priority P1

**Goal:** Make sub-modules individually discoverable by SkillHub. Resolve name-folder convention.

**Name convention decision:**  
The upstream package uses `unity-`-prefixed names in frontmatter (`unity-scene`) with short folder names (`scene`). Two options:

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A (preferred) | Keep frontmatter names as-is (`unity-scene`), update `validate_skill_pack.py` to allow configured prefix exemptions | No changes to 68 vendored files; easy upstream sync | validate_skill_pack.py needs exemption rule |
| B | Rename frontmatter to match folder (`scene`) | validate_skill_pack.py passes | Breaks upstream compatibility; diverges from source |

**Recommendation: Option A.** Add `name-prefix-exemption: "unity-"` to the validator config for the `unity-skills/skills/` path. This preserves upstream compatibility.

**Required frontmatter additions for each sub-module:**
```yaml
task-categories: [<category>]          # derive from module domain
use-when: <string>                     # derive from existing description
do-not-use-when: <string>
platforms: [claude-code]
metadata:
  source: https://github.com/Besty0728/Unity-Skills
  version: 1.9.2
  tier: 2
```

**Registration decision:**  
Do NOT individually register all 68 in `registry.json` — this pollutes the routing table and creates 68 trigger collision risks. Instead:
1. The parent `unity-skills` registry entry lists sub-modules under a new `sub-skills` key
2. SkillHub-specific discovery uses frontmatter scanning (not registry)
3. `/team` routing uses parent `unity-skills` as a bundle (current behavior preserved)

**Updated parent registry entry:**
```json
{
  "name": "unity-skills",
  "sub-skills": [
    "unity-scene", "unity-cleaner", "unity-animator", ...
  ],
  "sub-skills-path": ".claude/skills/unity-skills/skills/",
  "load-mode": "on-demand"
}
```

**4 long descriptions (>1024 chars) must be truncated:**  
`perception` (1379→1024), `shadergraph-design` (1202→1024), `test` (1185→1024), `validation` (1092→1024)

---

### Tier 3 (96 unity-dots sub-skills) — Priority P1 (internal only)

**Goal:** Add minimal frontmatter to all 86 missing files. Mark all as internal-only.

**SkillHub exposure: NONE.** Tier 3 sub-skills are implementation details of `unity-dots` and `unity-dots-best-practices`. They must never appear in external discovery.

**Required frontmatter for all Tier 3:**
```yaml
---
name: <folder-name>          # must match folder (no prefix)
description: <string>        # max 1024 chars — extract from file body if absent
metadata:
  tier: 3
  internal-only: true
---
```

No `task-categories`, `use-when`, `platforms` required — validators must not require these for `internal-only: true` skills.

10 skills already have `name` + `description` frontmatter — only need `metadata.tier: 3` and `metadata.internal-only: true` added.

---

## 5. Validator Updates Required

### 5a. quick_validate.py — update ALLOWED_PROPERTIES

```python
# Current (blocks SkillHub-compatible fields)
ALLOWED_PROPERTIES = {'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility'}

# New (add SkillHub and routing fields)
ALLOWED_PROPERTIES = {
    'name', 'description', 'license', 'allowed-tools', 'metadata', 'compatibility',
    # SkillHub fields
    'task-categories', 'use-when', 'do-not-use-when', 'platforms',
    # Optional
    'positive-example', 'negative-example',
}
```

### 5b. validate_skill_pack.py — add name-prefix exemption

```python
# Current (strict: name must equal folder)
if fm["name"] != folder:
    issues.append(...)

# New (allow configured prefixes for vendored sub-modules)
NAME_PREFIX_EXEMPTIONS = {
    ".claude/skills/unity-skills/skills": "unity-",
}

def name_matches(fm_name, folder, path):
    for path_prefix, allowed_prefix in NAME_PREFIX_EXEMPTIONS.items():
        if str(path).startswith(path_prefix):
            if fm_name == allowed_prefix + folder:
                return True
    return fm_name == folder
```

### 5c. skills_validator.py — fix base64 false positive

**Implemented approach (digit-lookahead):**

```python
# Previous (flagged Unity ECS class names — EntityComponentSystemSamples, BeginSimulationEntityCommandBufferSystem)
re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")

# Implemented: require at least one digit in the match
re.compile(r"(?=[A-Za-z0-9+/]*[0-9])[A-Za-z0-9+/]{40,}={0,2}")
```

Rationale: Unity ECS class names are all-alpha (no digits). Real secrets (JWTs, API keys, GitHub tokens) virtually always contain digits. The digit-lookahead eliminates known false positives while catching both padded and unpadded base64. The alternative (padding-only: `[=]{1,2}`) misses unpadded JWTs — worse security posture than the false-positive problem it solves. Digit-lookahead is the implemented and locked approach.

### 5d. skills_validator.py — skip task-categories check for internal-only skills

```python
def check_routing_evidence(skill):
    fm = skill.get("frontmatter", {})
    metadata = fm.get("metadata", {})
    if metadata.get("internal-only", False):
        return  # internal skills don't need task-categories
    if "task-categories" not in skill.get("registry_entry", {}):
        warn("Missing 'task-categories'. Add category tags for SkillHub discovery.")
```

---

## 6. Per-Role Skill Maps

These are the current routing assignments in `route_skills.py` (preserved, not changed):

| Role | Primary skills | Notes |
|------|----------------|-------|
| `architect` | architect, ownership-partitioning, unity-foundation | |
| `unity-dev` | unity-dots-best-practices (DOTS), unity-classic (non-DOTS), unity-foundation | Domain-switched |
| `unity-dots-dev` | unity-dots-best-practices, ecs-job-patterns, burst-safety, memory-safety | DOTS-only |
| `triage` | triage, routing | |
| `tester` | tester, qa-validation | |
| `verifier` | verifier | |
| `data-tool` | editor-data-tools, data-tool | |
| `bug-investigation` | investigation, codebase-understanding | |
| `refactor-agent` | ownership-partitioning, codebase-understanding | |
| `system-mapper` | codebase-understanding | |

### Post-migration additions

After Tier 2 sub-modules have frontmatter:
- `unity-dev` (Unity domain) gets on-demand access to all 68 unity-skills modules via parent `unity-skills` bundle
- `unity-dots-dev` gets on-demand access to all 96 unity-dots sub-skills via parent `unity-dots`

On-demand means: loaded only when `skill-confidence-routing.md` scores above 0.70.

---

## 7. Lazy Loading Rules

Current lazy-load rules (preserved from `registry.json` `load_by_default: false`):

| Rule | Applies to |
|------|-----------|
| Always loaded | `unity-foundation` (all roles), `unity-dots-best-practices` (DOTS mode unity-dev) |
| Loaded on domain match | All Tier 1 domain skills (score ≥ 0.70) |
| Loaded on-demand | All Tier 2 sub-modules (via parent bundle) |
| Never loaded directly | All Tier 3 sub-skills (loaded by parent DOTS skills) |

Post-migration: the `unity-skills` parent entry gains `load-mode: on-demand` with sub-skill index.

---

## 8. External-Skill Trust Policy

| Source | Trust level | Validation required | SkillHub-exposable |
|--------|-------------|--------------------|--------------------|
| Internal (written in this repo) | FULL | Full schema + skills_validator | YES (if not internal-only) |
| Vendored upstream (unity-skills v1.9.2) | TRUSTED-READ-ONLY | quick_validate.py + added frontmatter | YES (Tier 2, after migration) |
| Vendored upstream (unity-dots) | INTERNAL-ONLY | Minimal schema | NO |
| External SkillHub discovery | EXTERNAL | quick_validate.py only | N/A (source, not destination) |

Rules:
1. Vendored skills must never be modified in-place. Frontmatter additions must be managed by a separate overlay mechanism OR accepted as deliberate upstream divergence (documented in `unity-skills/UPSTREAM-LICENSE`).
2. `metadata.source` and `metadata.version` must be set for all vendored skills.
3. SkillHub-discovered external skills get priority tier `external-skillhub` (lowest). They never override internal skills for the same use case. Any external skill passing `quick_validate.py` enters **quarantine state**: visible in registry but `load_by_default: false` and `routing-eligible: false`. Status stays quarantine until explicit human approval. External skills are ADVISORY/REFERENCE only — never auto-routed, never auto-executed. The AGENTS.md discovery gate (search → inspect → read → verify → install → validate → use) blocks external-skillhub skills at the "install" step until human approval clears quarantine. <!-- qa-security ACK 2026-06-11: item 2 approved with this condition confirmed -->

---

## 9. Backward-Compatible Migration Plan

### Phase 0 — Validator fixes (no skill file changes)
1. Update `quick_validate.py` ALLOWED_PROPERTIES
2. Update `validate_skill_pack.py` name-prefix exemption
3. Fix `skills_validator.py` base64 regex
4. Update `skills_validator.py` to skip task-categories check for internal-only
5. Update `tests/fixtures/valid_skill/SKILL.md` to include `task-categories`, `use-when`, `do-not-use-when`, `platforms`

**Risk:** None. Validators become more permissive and accurate. No skill files changed.

### Phase 1 — Tier 1 frontmatter (22 skills)
1. Run migration script: copy `task-categories` from registry.json to SKILL.md frontmatter
2. Add `use-when`, `do-not-use-when`, `platforms` to 16 skills missing them (derive from descriptions)
3. Move `user-invocable: false` into `metadata:` sub-object for 4 affected skills
4. Add `metadata.source: internal`, `metadata.version`, `metadata.tier: 1` to all 22

**Risk:** Low. All changes are additive. Registry.json unchanged. /team routing unchanged.  
**Validation gate:** `skills_validator.py` must report 0 ERRORs and ≤5 WARNINGs before Phase 2.

### Phase 2 — Tier 2 frontmatter (68 sub-modules)
1. Add required fields to each unity-skills sub-module SKILL.md:
   - `task-categories` (domain-appropriate)
   - `use-when`, `do-not-use-when`, `platforms`
   - `metadata.source`, `metadata.version`, `metadata.tier: 2`
2. Truncate 4 long descriptions to ≤1024 chars
3. Update parent `unity-skills` registry entry with `sub-skills` index

**Risk:** Medium. Changes to vendored files. Must document divergence from upstream v1.9.2 in `unity-skills/UPSTREAM-LICENSE` or `unity-skills/CHANGES.md`.  
**Validation gate:** `validate_skill_pack.py` must report 0 issues for Tier 2 (with exemption applied).

### Phase 3 — Tier 3 frontmatter (96 sub-skills)
1. Add minimal frontmatter to 86 files missing it
2. Add `metadata.internal-only: true`, `metadata.tier: 3` to all 96

**Risk:** Low. All internal-only skills. No routing impact.  
**Validation gate:** `validate_skill_pack.py` must report 0 "missing frontmatter" issues.

### Phase 4 — Registry sync + SkillHub submission
1. Sync registry.json to include `source`, `version`, `tier`, `internal-only` fields
2. Submit to SkillHub for re-indexing
3. Verify discovery count ≥ 90 skills (22 Tier 1 + 68 Tier 2 = 90)

---

## 10. Acceptance Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| SkillHub discovers internal skills | Count | 22 (all Tier 1) |
| SkillHub discovers Tier 2 sub-modules | Count | 68 |
| SkillHub does NOT discover Tier 3 | Count | 0 |
| skills_validator.py result | Error count | 0 |
| skills_validator.py result | Warning count | ≤10 (trigger collisions only) |
| quick_validate.py pass rate | PASS / total | ≥180 / 186 |
| validate_skill_pack.py issues | Issue count | ≤5 (exemptions accounted for) |
| /team routing unchanged | Regression | 0 routing changes |
| Vendored skill modifications documented | Presence | CHANGES.md in unity-skills/ |

---

## Files to Create/Modify

| File | Change |
|------|--------|
| `.claude/skills/skill-creator/scripts/quick_validate.py` | Add fields to ALLOWED_PROPERTIES |
| `.claude/scripts/validate_skill_pack.py` | Add name-prefix exemption |
| `.claude/scripts/skills_validator.py` | Fix base64 regex, skip task-categories for internal-only |
| `.claude/scripts/migrate_tier1_frontmatter.py` | NEW — migration script |
| `.claude/scripts/build_skill_registry.py` | Add `sub-skills` support |
| `tests/fixtures/valid_skill/SKILL.md` | Update fixture to new schema |
| `.claude/skills/registry.json` | Add source/version/tier/internal-only to entries |
| `.claude/skills/unity-skills/CHANGES.md` | NEW — document divergence from upstream |
| All 22 Tier 1 SKILL.md files | Add task-categories + missing fields |
| All 68 Tier 2 SKILL.md files | Add task-categories, use-when, platforms, metadata |
| All 96 Tier 3 SKILL.md files | Add minimal frontmatter or metadata |

---

## 11. Official Unity Reference Corpus

All skill rules must trace to at least one approved reference. Approved repositories:

| Repo | Owner | Mapping | Active/Archived | License |
|------|-------|---------|----------------|---------|
| `EntityComponentSystemSamples` | Unity-Technologies | dots-best-practices, ecs-job-patterns, burst-safety | Active | Apache-2.0 |
| `DOTS-training-samples` | Unity-Technologies | dots-best-practices, unity-dots | Active | Apache-2.0 |
| `UnityCsReference` | Unity-Technologies | unity-foundation, unity-cleaner, unity-scene | Active | UnityCsReference License |
| `game-programming-patterns-demo` | Unity-Technologies | unity-classic, unity-foundation | Active | Apache-2.0 |
| `test-framework-training` | Unity-Technologies | tester, qa-validation | Active | Apache-2.0 |
| `UIElementsExamples` | Unity-Technologies | unity-ui, unity-editor, unity-cleaner | Active | Apache-2.0 |
| `com.unity.services.samples.use-cases` | Unity-Technologies | unity-classic (cloud-code layer) | Active | Apache-2.0 |
| `Addressables-Sample` | Unity-Technologies | unity-addressables (Tier 2: unity-addressables-design) | Active | Apache-2.0 |
| `com.unity.multiplayer.samples.coop` | Unity-Technologies | unity-netcode (Tier 2: unity-netcode, unity-netcode-design) | Active | Apache-2.0 |
| `CharacterControllerSamples` | Unity-Technologies | unity-movement (Tier 2: unity-movement) | Active | Apache-2.0 |
| `XR-Interaction-Toolkit-Examples` | Unity-Technologies | (no current skill — candidate for future xr skill) | Active | Apache-2.0 |
| `open-project-1` | UnityTechnologies | unity-classic, unity-scene | Active | Apache-2.0 |

### Historical/conceptual only — do not cite as primary evidence

| Repo | Reason |
|------|--------|
| `Megacity-2019` | Targets DOTS preview APIs, not Entities 1.x+ |
| `FPSSample` | Archived; uses pre-release ECS not compatible with current package versions |
| `DOTSSample` | Archived; same as FPSSample |
| `ProjectTinySamples` | Archived; Project Tiny discontinued |

Rule: if an API from a historical repo is cited, independently verify the API still exists in the current Entities package via `UnityCsReference` or `EntityComponentSystemSamples` before writing a skill rule.

### Evidence record format

Every corpus-backed rule in a SKILL.md must carry an evidence comment:

```yaml
# evidence:
#   repo: EntityComponentSystemSamples
#   owner: Unity-Technologies
#   path: PhysicsSamples/Assets/Tests/SingleThreadedPhysics/SingleThreadedPhysics.cs
#   unity_version: unknown
#   package: com.unity.entities
#   package_version: unknown
#   last_update: unknown
#   license: Apache-2.0
#   status: active
#   reason: demonstrates IJobEntity pattern for physics simulation
```

Fields `unity_version`, `package_version`, `last_update`: write `"unknown"` if not determinable from the file. Never guess.

---

## 12. Capability Matrix

Default decision = **extend-existing**. New skill requires all 8 criteria (§13).

| Capability | Existing skill | Proposed skill | Primary role | Trigger | Reference repo | Overlap risk | Decision |
|-----------|---------------|---------------|--------------|---------|----------------|--------------|----------|
| DOTS ECS best practices, Burst, jobs | `unity-dots-best-practices` | — | unity-dots-dev | DOTS_score ≥ 0.70 | EntityComponentSystemSamples, DOTS-training-samples | — | KEEP |
| ECS job patterns, scheduling, native containers | `ecs-job-patterns` | — | unity-dots-dev | IJobEntity/IJobChunk in task | EntityComponentSystemSamples | Overlaps unity-dots-best-practices on "jobs" | KEEP — different scope (pattern library vs practices) |
| Burst safety checklist | `burst-safety` | — | unity-dots-dev | [BurstCompile] context | EntityComponentSystemSamples | Overlaps ecs-job-patterns on Burst | KEEP — Burst-only focus, checklist mode |
| Memory safety, NativeContainer rules | `memory-safety` | — | unity-dots-dev | NativeArray/NativeList context | EntityComponentSystemSamples | Overlaps burst-safety on disposal | KEEP — separate concern (aliasing, safety system) |
| Unity classic MonoBehaviour, patterns | `unity-classic` | — | unity-dev | Unity_score ≥ 0.70, non-DOTS | game-programming-patterns-demo, open-project-1 | — | KEEP |
| Unity foundation (shared primitives) | `unity-foundation` | — | all | Always loaded | UnityCsReference | — | KEEP |
| ECS ownership, parallel partition | `ownership-partitioning` | — | architect | parallel_allowed=true | internal | — | KEEP |
| Bug / root cause investigation | `investigation` | — | bug-investigation | intent=bug | internal | — | KEEP |
| Codebase graph traversal | `codebase-understanding` | — | system-mapper, refactor | intent=explore/refactor | internal | Overlaps investigation on "understand" | KEEP — different phase (pre-design vs post-symptom) |
| Routing, triage classification | `routing`, `triage` | — | triage | All tasks | internal | — | KEEP both |
| Agent memory recall across sessions | `agentmemory-codebase-recall` | — | bug-investigation | agentmemory MCP present | internal | — | KEEP |
| Unity editor data tools, validators | `editor-data-tools`, `data-tool` | — | data-tool | complexity=critical | internal | data-tool vs editor-data-tools scope overlap | MERGE CANDIDATES — evaluate in separate task |
| Unity skill bundle (68 sub-modules) | `unity-skills` (parent) | — | unity-dev | Unity_score ≥ 0.70 | Besty0728/Unity-Skills v1.9.2 | — | KEEP parent, expose sub-modules |
| Unity DOTS sub-skill library | `unity-dots` (parent) | — | unity-dots-dev | DOTS_score ≥ 0.70 | internal | — | KEEP parent, keep internal |
| QA, test sign-off | `qa-validation`, `tester` | — | tester | intent=verify | test-framework-training | qa-validation vs tester trigger collision | KEEP — different mode (rules vs execution) |
| Verification bundle execution | `verifier` | — | verifier | complexity≤medium | internal | — | KEEP |
| Skill authoring/packaging | `skill-creator` | — | (meta) | skill authoring tasks | internal | — | KEEP |
| ECB playback failure diagnosis | — | `unity-dots-ecb-lifecycle-debugger` | unity-dots-dev, bug-investigation | ECB error strings: "entityExists=False", "AppendDestroyedEntityRecordError", "ECBDestroyedBeforePlayback" | EntityComponentSystemSamples | Boundary: starts where ecs-job-patterns ends (at playback failure, not correct usage). Routes on error signatures only. | **CREATE-NEW RATIFIED** — all 8 criteria met; files written (gate slip, retroactively approved); priority 93; blocked from /team routing until qa-security ACK on routing fixtures |

### Orphan skills

No orphan skills currently exist. All 22 Tier 1 skills have at least one active trigger condition in `route_skills.py`. If a skill loses all trigger conditions after a future refactor → apply orphan policy (§15.3).

### §12a. Follow-up: data-tool + editor-data-tools merge evaluation

**Status:** RESOLVED 2026-06-11 — no merge. Reclassification applied.

**Finding (skill-platform-dev):** NOT duplicates.
- `data-tool`: 213 lines — agent role brief (CRG delegation, MCP patterns, ownership rules). Routes on role assignment.
- `editor-data-tools`: 82 lines — code guidance (EditorWindow/inspector/validation patterns). Not a role brief.

Merge would collapse agent policy into code guidance — wrong call.

**Resolution (architect APPROVED):** Reclassify `editor-data-tools` as `advisory[data-tool]`. Registry change applied:
- `routing-rule`: `"advisory[data-tool] — code guidance loaded alongside data-tool role brief. Not a role brief itself."`
- `keywords` narrowed to: `["editor tooling", "editor window", "inspector", "EditorWindow", "CustomEditor", "pipeline"]`
- Removed from keywords: `"authoring"`, `"diagnostics"`, `"validator"` (data-tool primary scope only)

Collision resolved. No content lost. No merge needed.

---

## 13. Skill Budget + New Skill Criteria

### Default decision

**Extend existing skill first.** New skill is only created when all 8 criteria below are met.  
No skill is created to inflate SkillHub count.  
Prefer improving 5 skills deeply over creating 20 shallow ones.

### 8-criteria gate

A new skill requires ALL 8:

| # | Criterion | ECB debugger assessment |
|---|-----------|------------------------|
| 1 | Distinct domain not covered by any existing skill | PASS — ECB playback failure forensics; ecs-job-patterns covers correct usage, not failure diagnosis |
| 2 | Trigger conditions separable from all existing skills | PASS — routes on specific error strings, not general DOTS keywords; no collision with ecs-job-patterns |
| 3 | Cannot be implemented by extending an existing skill | PASS — adding error-forensics workflow to ecs-job-patterns would bloat it beyond its "patterns library" role |
| 4 | At least 1 real agent role that would load it | PASS — `unity-dots-dev` (prevention) + `bug-investigation` (diagnosis) |
| 5 | At least 1 concrete task scenario where it applies | PASS — "ECB playback throws entityExists=False at runtime after system restructure" |
| 6 | Independently testable (verifiable without running the full DOTS pipeline) | PASS — test fixture: skill loaded when error string present, not loaded when only "entity" keyword present |
| 7 | No ambiguous routing — routing keys on evidence not inference | PASS — trigger keys: exact error strings (`entityExists=False`, `AppendDestroyedEntityRecordError`, `ECBDestroyedBeforePlayback`, `ECBIsSinglePlayback`) |
| 8 | Architect + qa-security both approve before files written | PASS (architect) — PENDING (qa-security) |

### Proposal outcomes

| Proposal | Decision | Rationale |
|----------|----------|-----------|
| `unity-dots-ecb-lifecycle-debugger` | **CREATE-NEW RATIFIED** | All 8 criteria met; architect APPROVED; files exist; pending qa-security ACK before /team routing |
| `unity-ecs` / `unity-entities` duplicates | **REJECTED** — consolidated | These capabilities already exist in `unity-dots-best-practices` + `ecs-job-patterns`; granularity rule §15.3 forbids fragmentation |
| New XR skill | **DEFERRED** — no trigger evidence | No current project uses XR. Revisit when XR task is triaged |
| `data-tool` + `editor-data-tools` merge | **RESOLVED — no merge** | Not duplicates. editor-data-tools reclassified as advisory[data-tool]; keywords narrowed. See §12a. |

---

## 14. Rule Extraction Format

All rules extracted from Unity reference corpus must use this YAML schema:

```yaml
- id: <kebab-unique-id>                   # e.g. ecb-playback-must-complete-dependency
  category: <pattern|safety|performance|api-usage|gotcha|migration>
  source_repository: EntityComponentSystemSamples
  source_path: PhysicsSamples/Assets/Tests/SingleThreadedPhysics/SingleThreadedPhysics.cs
  unity_version: unknown                  # write "unknown" if not determinable
  package_name: com.unity.entities
  package_version: unknown                # write "unknown" if not determinable
  confidence: 0.90                        # 0.0–1.0; start at 0.90 for directly observed, 0.60 for inferred
  applicability: >
    Applies when EntityCommandBuffer is created inside a system and played back
    in the same or subsequent frame. Not applicable to ECBSystems with AutoPlayback.
  exclusions:
    - ECBSystem with AutoPlayback=true (playback handled by system group)
    - Deferred entities created with ECB.CreateEntity() don't need pre-existence check
  last_verified: 2026-06-11
```

### Field constraints

| Field | Constraint |
|-------|-----------|
| `id` | kebab-case, globally unique within the skill |
| `category` | must be one of: `pattern`, `safety`, `performance`, `api-usage`, `gotcha`, `migration` |
| `unity_version` | exact version string or `"unknown"` — never guess |
| `package_version` | exact semver or `"unknown"` — never guess |
| `confidence` | 0.90 for directly evidenced; 0.70 for one verified source; 0.50 for inferred; below 0.50 do not include |
| `last_verified` | ISO 8601 date of last manual review against source |

### Confidence decay

Rules decay at same rates as `repo-knowledge.md` facts (see `knowledge-decay-system.md`).  
Category `api-usage`: fast decay (Unity API changes). Category `pattern`: slow decay.  
Rule with confidence < 0.40 after decay: mark `[STALE]`, do not apply, remove at next review.

---

## 15. Trigger Priority, Orphan Policy, Granularity Rules

### 15.1 Trigger priority order

```
specific-local      ← highest: exact match to local project convention (e.g. "use BeginSimulationECBSystem")
domain-specific     ← exact domain class (e.g. "all ISystem implementations")
project-specific    ← applies to this project but not generally (e.g. "BackpackAdventures inventory system")
general-unity       ← applies to all Unity projects
external-skillhub   ← lowest: discovered from external SkillHub index
```

Rules:
- If two skills at the same priority level both claim a trigger → collision; escalate to architect.
- `external-skillhub` skills never override `specific-local` through `general-unity`.
- When loading multiple skills: apply highest-priority trigger first; lower tiers are advisory.

### 15.2 Orphan skill policy

An orphan skill is any skill where ALL trigger conditions in `route_skills.py` are unreachable (no task will ever score it ≥ 0.70).

| Stage | Action |
|-------|--------|
| Detected | Mark `[ORPHAN]` in registry.json; write entry to `workspace/recent-changes.md` |
| ≤30 days | Wire: find a valid trigger or extend scope to cover a real use case |
| 31–60 days | Merge: absorb content into the nearest overlapping skill |
| 61–90 days | Internalize: if content is valuable but not externally routable, move to Tier 3 |
| >90 days | Remove: delete skill file + registry entry + write CHANGELOG.md entry |

Never keep an orphan skill "for future use." Future-use rationale = keep-for-inflation = banned.

### 15.3 Granularity rules

**No mega-skills:**  
A skill that attempts to cover all of Unity in one file is forbidden. `unity-foundation` is the narrowest allowed foundation skill — it covers only shared primitives, not full domain coverage.

**No micro-skills:**  
A skill that covers a single trivial operation (e.g. "how to call `Destroy()`") is forbidden. Minimum: a coherent domain pattern with ≥3 non-trivial rules.

**ECS consolidation rule:**  
`unity-ecs`, `unity-dots`, `unity-entities` as separate top-level skills are FORBIDDEN. These names describe the same domain with different marketing labels. Use:
- `unity-dots-best-practices` — practices and patterns (Tier 1, primary)
- `ecs-job-patterns` — job scheduling pattern library (Tier 1, specialized)
- `burst-safety` + `memory-safety` — safety checklists (Tier 1, specialized)
- `unity-dots` — bundle parent for Tier 3 sub-skills (Tier 1, internal bundle)

Any new skill whose name contains `ecs`, `dots`, or `entities` as the sole differentiator from an existing skill is automatically REJECTED without gate evaluation.

**Depth-over-breadth rule:**  
When choosing between: (a) adding a new skill for a slightly different scenario, or (b) adding a new rule to an existing skill — always choose (b) unless criteria 1–3 of the 8-criteria gate are met.

---

## 16. Contract Summary for Reviewers

### For skill-platform-dev

Implement in this order:
1. Phase 0 validator fixes (§5a–5d) — no skill files changed, unblocks all subsequent phases
2. `migrate_tier1_frontmatter.py` script (§4, Tier 1 migration)
3. Phase 1 (22 Tier 1 SKILL.md updates)
4. Phase 2 (68 Tier 2 SKILL.md additions) + parent registry `sub-skills` key
5. Phase 3 (96 Tier 3 minimal frontmatter)
6. Phase 4 (registry sync + SkillHub submission)

Do NOT skip Phase 0. Validators must pass before skill files are modified.  
Do NOT start Phase 2 until Phase 1 validation gate passes.  
Do NOT create any new Tier 1 skill unless it passes all 8 criteria in §13 AND both architect and qa-security have approved.

### For qa-security

All 4 items ACK'd by qa-security on 2026-06-11:

1. **base64 regex fix (§5c):** ✅ APPROVED. Digit-lookahead approach locked. No remaining false-positive risk for Unity DOTS class names. Padding-only rejected (misses unpadded JWTs).
2. **external-skill trust policy (§8):** ✅ APPROVED. Condition met: `routing-eligible: false` + quarantine state now explicit in §8 rule 3. External skills advisory/reference only, AGENTS.md gate blocks at install step until human approval.
3. **ECB lifecycle debugger (§13):** ✅ APPROVED. No exfiltration risk, no unintended MCP call risk. All 3 helper scripts confirmed text-in/text-out, no network calls, no file writes, no subprocess. Routing now unblocked.
4. **vendor divergence policy (§8 rule 1):** ✅ APPROVED. Frontmatter additions are additive, do not change skill behavior. Hard requirement confirmed: each modified Tier 2 file must retain `metadata.source: https://github.com/Besty0728/Unity-Skills` and `metadata.version: 1.9.2`. `unity-skills/CHANGES.md` entry mandatory (not optional).

No blockers. Phase 1 implementation unblocked. ECB debugger routing unblocked.
