---
name: triage
description: Adaptive pipeline triage. Classify task complexity/blast radius/domain in ≤8 file reads and emit a schema-valid workspace/triage.json that drives every downstream phase.
---

# Triage Skill

The triage agent runs ONCE per `/team` invocation, before any other agent.
It is the only agent that always runs. Everything downstream is derived from
its output.

## Goal

Produce `workspace/triage.json` matching `.claude/schemas/triage.schema.json`
in under 8 file reads.

## Inputs

- `<intent>` from the user (bug | feature | refactor | explore)
- `<depth>` from the user (quick | normal | deep — default normal)
- `<task description>` free text
- CRG MCP (`code-review-graph`) — preferred
- `ai-game-developer` MCP — optional

## Procedure

1. **CRG first.** No file reads until graph evidence exists.
   - `get_architecture_overview` if domain unknown
   - `trace_execution_flow` from task keywords
   - `get_impact_radius` → seed `systems_affected` and `files_touched_estimate`

2. **Fingerprint up to 5 touched files** for API evidence
   (see `.claude/rules/api-fingerprinting-system.md`).
   - Compute DOTS_score / Unity_score / Hybrid_score
     (see `.claude/rules/domain-scoring-engine.md`).
   - Classify domain. If Ambiguous → `confidence_score ≤ 0.5`.

3. **Classify complexity** using the rubric below.

4. **Pick verification strategy:**
   - `bundle`   — tiny: deterministic verification bundle, no agent
   - `verifier` — small/medium: verifier agent runs the bundle
   - `tester`   — large/critical: full tester agent
   - `stepgated` — refactor only

5. **Partition ownership** when the pipeline has more than one writer (data-tool
   plus unity-dev, or stepgated refactor). Use repo-root-relative globs.
   When in doubt: assign only `unity-dev` (no parallelism).

6. **Emit** `workspace/triage.json` via `python .claude/scripts/triage.py`.
   That helper writes a schema-valid file; do not hand-write the JSON.

## Complexity Rubric

| Complexity | Files | Systems | Blast radius | Pipeline (default) |
|------------|-------|---------|--------------|--------------------|
| **tiny** | 1 | 1 | isolated | `[unity-dev]` |
| **small** | 1–3 | 1 | local | `[unity-dev, verifier]` |
| **medium** | 2–5 | 1–3 | local / multi-system | `[architect, unity-dev, verifier]` |
| **large** | 5–15 | 3–6 | multi-system | `[architect, unity-dev, tester]` |
| **critical** | >15 OR save/multiplayer/economy/world-init | any | cross-cutting | `[architect, unity-dev, data-tool, tester]` |

Examples:
- "Rename `EnemyHP` to `EnemyHealth`" → **tiny**
- "Fix off-by-one in damage calc" → **tiny**
- "Health regen not firing after death respawn" → **small** (1 bug, 1 system)
- "Add stamina component + regen system" → **medium**
- "Spawner refactor across zones + dungeons" → **large**
- "Save system migration v3 → v4" → **critical**

## Intent Overrides

- `bug`     → prepend `bug-investigation` regardless of complexity
- `refactor`→ prepend `refactor-agent` + force `architect` + `stepgated` verification
- `explore` → pipeline is empty; triage is the only output
- `feature` → no override

## Depth Modifier

- `quick`  — downgrade complexity by one tier (`small`→`tiny`, `medium`→`small`).
  Refuse if blast_radius ≥ `multi-system`.
- `normal` — use complexity as classified.
- `deep`   — upgrade complexity by one tier (`small`→`medium`, etc.). Tester
  always spawned. Codex review required at design and at completion.

## Confidence Scoring

`confidence_score ∈ [0.0, 1.0]`:

- 1.0 — Domain unambiguous, blast radius proven via CRG, prior session in
  `repo-knowledge.md` covers the same area.
- 0.8 — Domain clear; blast radius best-effort but evidence-backed.
- 0.6 — Domain clear; blast radius partly guessed.
- 0.4 — Domain ambiguous or CRG unavailable.
- ≤0.3 — `recommended_pipeline` should include an investigator (system-mapper
  or bug-investigation) before implementation begins.

**Parallel execution requires confidence ≥ 0.8** AND complexity ≥ medium AND
ownership partition ≥ 2. The orchestrate.py planner enforces this.

## Skill Pack Selection

Add up to 4 skill packs to `skill_packs[]` based on domain:

- DOTS: `ecs-job-patterns`, `burst-safety`, `memory-safety`
- Unity: (none — Unity-domain work uses the Unity layer of unity-dots-best-practices)
- Hybrid: `ecs-job-patterns` + `ownership-partitioning`

`ownership-partitioning` is added whenever `parallel_allowed=true` so downstream
writers respect their assigned globs.

## Helper Command

```sh
python .claude/scripts/triage.py \
  --intent <bug|feature|refactor|explore> \
  --task "<one line task>" \
  --depth <quick|normal|deep> \
  --complexity <tiny|small|medium|large|critical> \
  --blast-radius <isolated|local|multi-system|cross-cutting> \
  --systems <SystemA> <SystemB> \
  --files-est <N> \
  --confidence <0.0-1.0> \
  --domain <DOTS|Unity|Hybrid|Ambiguous> \
  --pipeline <agent1> <agent2> ... \
  --strategy <bundle|verifier|tester|stepgated> \
  --skill-packs <pack1> <pack2> \
  --own "unity-dev=Assets/Scripts/Combat/**" \
  --own "data-tool=Assets/Editor/**" \
  --rationale "<one paragraph justifying complexity, domain, and parallelism>"
```

Validate before exiting:

```sh
python .claude/scripts/orchestrate.py validate workspace/triage.json triage
```

If validation fails, fix the inputs and re-run. Do not hand-edit the JSON.

## Anti-Patterns

- Reading more than 8 files. Triage is a scout, not the investigator.
- Recommending a 4-agent pipeline for a 1-file change.
- Setting `parallel_allowed=true` with confidence < 0.8.
- Emitting `Ambiguous` domain with `confidence_score > 0.6`.
- Skipping CRG and grepping the repo.
- Hand-writing `triage.json` instead of using the helper.
