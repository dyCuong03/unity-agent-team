# Unity Agent Team

A self-contained Claude Code package that runs an **adaptive Unity (DOTS + classic)
agent pipeline**. Triage classifies the task, an orchestrator script derives the
minimum viable agent composition, and every phase boundary is a Python gate that
exits non-zero on violation. No fixed team, no always-on tester, no tmux
dependency. Everything lives in `.claude/` and travels with the folder.

```
/team <intent> [depth] <task>

intent ∈ { bug, feature, refactor, explore }
depth  ∈ { quick, normal, deep }   default: normal
```

Also ships two real multi-session team modes — `/team --team` (Claude Agent
Teams) and `/team --worktrees` (tmux + git worktrees) — see [Modes](#modes).

**Highlights**

- **91 SkillHub-discoverable skills** across 3 tiers, with standardized
  machine-readable frontmatter (`task-categories`, `use-when`,
  `do-not-use-when`, `platforms`, source/version metadata)
- **Deterministic per-role skill routing** — agents load only the skills their
  role needs (cap 7), with priority-resolved trigger-collision handling
- **Skills CLI** — `list` / `validate` / `doctor` / `unused`, enforcing
  zero orphan, zero unreachable, zero duplicate skills
- **494-test suite** — routing corpus, per-skill positive/negative fixtures,
  security checks, malformed-skill fixtures
- **Safe dynamic skill discovery policy** ([`AGENTS.md`](./AGENTS.md)) —
  external skills are reviewed before use, never auto-installed
- **Cross-platform skill metadata** — claude-code, codex, copilot, cursor,
  windsurf

---

## What's in the box

| Component | Count | Where |
|-----------|-------|-------|
| Subagent definitions | 12 | `.claude/agents/` |
| Skill packs (registered) | 23 | `.claude/skills/` + `registry.json` |
| SkillHub-discoverable skills | 91 | Tier 1 (23) + Tier 2 vendor modules (68) |
| Internal sub-skills (Tier 3) | 96 | `.claude/skills/unity-dots/` |
| Python scripts (stdlib only) | 17 | `.claude/scripts/` |
| Tests | 494 | `tests/` |
| Artifact JSON-schemas | 6 | `.claude/schemas/` |
| Operational rule files | 20+ | `.claude/rules/` |
| `/team` command spec | 1 | `.claude/commands/team.md` |
| Discovery policy | 1 | `AGENTS.md` |

---

## Adaptive pipeline at a glance

```
/team <intent> [depth] <task>
       │
       ▼
[Step 0] Bootstrap                  orchestrate.py preflight + reset
       │
       ▼
[Step 1] Triage agent               CRG + API fingerprinting → workspace/triage.json
       │
       ▼
[Step 2] Plan                       orchestrate.py plan workspace/triage.json
                                    → workspace/pipeline.json (phases, parallelism,
                                      skills_by_agent, artifacts)
       │
       ▼
[Step 3] Execute phases             For each phase:
                                      orchestrate.py gate <id>      ← exit 2 → halt
                                      spawn agents from phase.agents
                                      each agent writes + validates its artifact
                                    Loop on verifier FAIL (up to 2 retries).
       │
       ▼
[Step 4] Finalize / commit          orchestrate.py finalize  → completion or exit 4
                                    orchestrate.py commit     → PASS-only, current-branch
```

### Complexity → pipeline

| Complexity | Pipeline | Verification |
|------------|----------|--------------|
| **tiny** | `[unity-dev]` | deterministic bundle (no agent) |
| **small** | `[unity-dev, verifier]` | verifier |
| **medium** | `[architect, unity-dev, verifier]` | verifier |
| **large** | `[architect, unity-dev, tester]` | tester |
| **critical** | `[architect, unity-dev, data-tool, tester]` | tester |

Intent overrides:

- `bug` prepends `bug-investigation`
- `refactor` prepends `refactor-agent`, forces `architect` approval and step-gated execution
- `explore` produces an empty pipeline — triage runs alone, updates `repo-knowledge.md`, exits

Depth modifier:

- `quick` downgrades one tier (refused if blast_radius ≥ multi-system)
- `normal` uses triage's classification as-is
- `deep` upgrades one tier, always uses `tester`, requires `/codex:review`

---

## Agents

12 `subagent_type` definitions in `.claude/agents/`. The orchestrator spawns only
the ones the task needs.

| Agent | Role | Owns | Must not |
|-------|------|------|----------|
| `triage` | classify task (complexity, blast radius, domain, confidence) | `triage.json`, pipeline recommendation | spawn agents, edit files |
| `architect` | ECS/system design, ownership partition, update order | `approved_plan.json`, `ownership.lock.json` | write code |
| `unity-dev` | Unity **classic** impl (MonoBehaviour, UI, gameplay, VContainer, Addressables, pooling, DOTween) | `impl_result.json` | DOTS/ECS files; change arch without plan |
| `unity-dots-dev` | Unity **DOTS** impl (ISystem, Jobs, Burst, ECB, bakers, blobs) | `impl_result.json` | pure UI/Mono files |
| `data-tool` | editor tooling, validators, inspectors, diagnostics | `impl_result.json` (tooling) | silently change runtime behavior |
| `verifier` | run the deterministic verification bundle | `verification_result.json` | design tests, edit code |
| `tester` | test matrix, stress, regression, sign-off | `verification_result.json` | approve without evidence |
| `qa-tester` | `--team` QA lane: review diffs, APPROVE/BLOCK | QA report | edit impl files |
| `bug-investigation` | CRG-first root cause + evidence chain + fix strategy | `root_cause.json` | implement the fix |
| `refactor-agent` | blast radius, migration plan, rollback | `root_cause.json` / migration plan | execute migration |
| `system-mapper` | read existing systems, update `repo-knowledge.md` | domain analysis / system map | design new systems |
| `code-tracer` | trace execution flow + API fingerprinting | `domain-analysis.md` | design |

---

## Skill packs

23 registered packs in `.claude/skills/`, loaded into agents **as text — never
spawned as agents**. A registry + router picks a curated, role-correct subset
per agent (cap `max_total_skills = 7`), so DOTS skills never leak into the
Unity-classic / tester / data-tool lanes.

- **Registry** — `.claude/skills/registry.json` (v2): validated against SKILL.md
  frontmatter (single source of truth). Each entry carries domains / roles /
  intents / keywords / priority / `task-categories` / `routing-rule` /
  positive+negative examples / `routing-eligible` gate / internal-only flags.
- **Router** — `scripts/route_skills.py`: `role primary + domain extra + intent
  extra + keyword + memory hint`, capped and deduped, with per-skill selection
  reasons (`route_with_reasons()`, `--json`). Dry-run any route:
  ```sh
  python3 .claude/scripts/route_skills.py --agent unity-dots-dev --domain DOTS --intent bug --task "ISystem race" --json
  ```
- **Skills CLI** — `scripts/skills.py`:
  ```sh
  python3 .claude/scripts/skills.py list        # all registered skills
  python3 .claude/scripts/skills.py validate    # orphans / unreachable / duplicates report
  python3 .claude/scripts/skills.py doctor      # fix suggestions (no auto-apply)
  python3 .claude/scripts/skills.py unused      # dead-skill check — nonzero exit on orphans
  ```

Notable packs:

| Pack | Loaded into | Purpose |
|------|-------------|---------|
| `triage` | triage | classification protocol, ≤8-file scout budget |
| `unity-dots-best-practices` | architect, unity-dots-dev | core ECS/Jobs/Burst guidance (always on for DOTS) |
| `unity-classic` | unity-dev | MonoBehaviour / UI / gameplay / async (non-DOTS lane) |
| `burst-safety` | unity-dots-dev (DOTS/Hybrid) | Burst-safe rules (replaces v1 `burst-validator`) |
| `ecs-job-patterns` | unity-dots-dev (DOTS/Hybrid) | IJobEntity/IJobChunk, dependency chains, ECB |
| `memory-safety` | unity-dots-dev (DOTS/Hybrid) | native container lifetime, allocators, GC avoidance |
| `ownership-partitioning` | every writer when `parallel_allowed=true` | hard write-partitioning rules |
| `codebase-understanding` / `investigation` | investigators | CRG-first navigation, scene/log/compile reads |
| `routing` | orchestrator | lazy skill-loading router logic |
| `verifier` / `tester` / `qa-validation` | verification lanes | verification bundle, test matrices |
| `editor-data-tools` | data-tool | authoring pipelines, inspectors, diagnostics |
| `agentmemory-codebase-recall` | investigators | recall-layer rules (memory is **not** source of truth) |
| `unity-dots-ecb-lifecycle-debugger` | unity-dots-dev, bug-investigation | ECB playback-failure forensics — routes on error signatures (`entityExists=False`, `AppendDestroyedEntityRecordError`, …) with 3 read-only diagnostic scripts (producer inventory, destroy paths, system ordering) |
| `unity-skills` / `unity-dots` | reference | Unity Editor REST automation; 96-skill DOTS index |
| `skill-creator` | meta | author/measure skills (meta-only) |

---

## Scripts

17 stdlib-only Python scripts in `.claude/scripts/`. No pip, no node.

| Script | What it does |
|--------|--------------|
| `orchestrate.py` | **runtime enforcer.** Subcommands: `preflight`, `reset`, `validate`, `plan`, `gate`, `ownership-check`, `finalize`, `commit`. Non-zero exit blocks the next phase. |
| `triage.py` | packages the triage agent's CRG + fingerprinting decision into a valid `triage.json` (not a classifier itself). |
| `route_skills.py` | the skill router — selects the per-agent skill subset from the registry. |
| `build_skill_registry.py` | load / validate / refresh `registry.json` (`check` subcommand verifies 23/23 intact). |
| `skills.py` | skills CLI — `list` / `validate` / `doctor` / `unused` (dead-skill check fails the build on orphans). |
| `skills_validator.py` | full skill validator: frontmatter parse, unique names, description quality/truncation, referenced files exist, no secrets / personal paths / unsafe instructions, dead-skill + trigger-collision detection. |
| `migrate_tier{1,2,3}_frontmatter.py` | tier-aware SKILL.md frontmatter migration (used for the SkillHub standardization; reusable for future schema changes). |
| `dots_scan.py` | fast anti-pattern scan for DOTS C# (managed alloc in OnUpdate, structural change in job, etc.) — first-pass signal, not a linter. |
| `full_team.py` | real multi-agent orchestrator for `/team --worktrees`. Subcommands: `setup`, `assign`, `prompts`, `status`, `teardown` (+ internal `env_check`). Creates tmux session + 4 windows + one git worktree per role. |
| `unity_skills.py` | Unity Editor REST automation helper (scene/asset/script ops, version routing). |
| `preflight.py` | environment / MCP / tmux sanity (informational, never blocks). |
| `validate_skill_registry.py` | structural + behavioral routing assertions over the registry. |
| `validate_skill_routing.py` | proves lane-correctness for both adaptive (`skills_by_agent`) and `--team` Read-first skill blocks. |
| `validate_skill_pack.py` | validates an individual skill pack's shape. |
| `validate_agentmemory_rule.py` | verifies the "agentmemory = recall layer, not source of truth" rule is stated in SKILL.md + CLAUDE.md + team.md. |

---

## Skill system & SkillHub discoverability

Every public skill carries standardized, machine-readable SKILL.md frontmatter
so external indexers (SkillHub and others) can discover it — and so agents can
route on it deterministically.

**Three tiers:**

| Tier | Count | Discoverable | What |
|------|-------|--------------|------|
| 1 — registered | 23 | yes | role briefs, domain packs, the ECB debugger |
| 2 — vendor modules | 68 | yes | `unity-skills/*` (upstream Besty0728/Unity-Skills v1.9.2, divergences tracked in `CHANGES.md`) |
| 3 — internal sub-skills | 96 | no (`internal-only`) | `unity-dots/*` patterns loaded via the parent index |

**Frontmatter contract** (validated by `skills_validator.py`): unique `name`
matching the directory, non-truncated `description`, `use-when` +
`do-not-use-when`, `task-categories`, `platforms`
(claude-code / codex / copilot / cursor / windsurf),
`metadata.source/version/tier`.

**Quality gates** (all enforced by tests + CLI, all currently zero):

```
orphan skills: 0 · unreachable skills: 0 · unresolved duplicates: 0
```

**Safe external discovery** — [`AGENTS.md`](./AGENTS.md): external skills go
through search → inspect source → read SKILL.md → read scripts → verify
compatibility → install → validate → use. Auto-install is forbidden; external
entries default to `routing-eligible: false` until human approval; local skills
always win trigger collisions.

**Test suite** — `tests/` (494 tests): 12-case usage corpus (DOTS perf, classic
refactor, scene loading, cleanup, editor tooling, Cloud Code, Addressables,
test framework, both Netcodes, generic C#, docs-only), per-skill
positive/negative routing fixtures, 12-point orphan verification, security
checks (secrets, unsafe commands, auto-install prevention, recursive-loop
detection), malformed-skill fixtures (BOM, truncation, duplicates, bad refs).

```sh
python3 -m pytest tests/ -q                      # 494 passed
python3 .claude/scripts/skills.py validate       # PASS — 0 orphans / 0 unreachable / 0 duplicates
```

Deep dives: [`docs/skillhub-audit.md`](./docs/skillhub-audit.md) (why discovery
failed before), [`docs/skill-architecture.md`](./docs/skill-architecture.md)
(schema, capability matrix, trigger priority, reference corpus),
[`docs/skillhub-validation-report.md`](./docs/skillhub-validation-report.md)
(final numbers).

---

## Runtime enforcement

Every artifact has a JSON schema; every phase boundary calls `orchestrate.py`.
The exit code is the contract:

| Exit | Meaning |
|------|---------|
| 0 | OK |
| 2 | Gate violation — phase must not proceed |
| 3 | Ownership violation — writer touched a file outside its partition |
| 4 | Verification FAIL — completion blocked |
| 10 | Retry limit hit (3 failed implementation cycles) |

Run the gates yourself any time:

```sh
python3 .claude/scripts/orchestrate.py validate workspace/triage.json triage
python3 .claude/scripts/orchestrate.py gate phase-2
python3 .claude/scripts/orchestrate.py ownership-check unity-dev Assets/Scripts/Combat/Health.cs
python3 .claude/scripts/orchestrate.py finalize
python3 .claude/scripts/orchestrate.py commit          # PASS-only, current-branch, no force-push
```

---

## Artifacts and schemas

Every artifact is JSON, validated against a schema in `.claude/schemas/`, and
gated by the orchestrator before the next phase runs.

```
.claude/schemas/
├── triage.schema.json
├── root_cause.schema.json
├── approved_plan.schema.json
├── impl_result.schema.json
├── verification_result.schema.json
└── ownership.schema.json
```

| Artifact | Owner | Required by |
|----------|-------|-------------|
| `triage.json` | `triage` (always) | every phase |
| `pipeline.json` | `orchestrate.py plan` | every phase |
| `root_cause.json` | `bug-investigation` / `refactor-agent` | architect / impl |
| `approved_plan.json` | `architect` (medium+) | unity-dev / unity-dots-dev / data-tool |
| `impl_result.json` | impl agents | verifier / tester |
| `verification_result.json` | `verifier`, `tester` | `finalize` / `commit` |
| `ownership.lock.json` | `architect` (parallel) / `triage` (2 writers) | every writer's `ownership-check` |

Persistent knowledge (committed): `workspace/repo-knowledge.md`,
`ecs-registry.md`, `recent-changes.md`. Session artifacts are gitignored.

---

## Modes

| Mode | Invocation | What it is |
|------|------------|-----------|
| **Adaptive** (default) | `/team <intent> [depth] <task>` | single session, triage-derived 1–4 agents, Python-gated, sequential unless certainty ≥ 0.8 |
| **Agent Teams** | `/team --team <task>` | current session = teamlead, spawns 4 Sonnet teammates (`architect`, `unity-dots-dev`, `unity-dev`, `qa-tester`) via `TeamCreate` + shared task list. Fails fast if Agent Teams off. |
| **Worktrees** | `/team --worktrees <task>` | `full_team.py`: 4 real `claude` CLI sessions in tmux, one git worktree/branch each, QA-gated merge |
| **Explore** | `/team explore <question>` | triage-only, no code |

`/team --full` is a deprecated alias of `--team`. Both team modes require
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `~/.claude/settings.json`.

---

## Install

```
1. Copy .claude/ into your Unity project root.
2. (Optional) copy SETUP.md, README.md, CHANGELOG.md, MIGRATION.md, CLONE-SETUP.md, LICENSE.
3. Verify: python3 .claude/scripts/orchestrate.py preflight
4. (Recommended) set up RTK token-optimized commands — CLONE-SETUP.md §2b.
```

Self-contained — drop `.claude/` into any repo's root and `/team` works there
immediately, for Unity classic, Unity DOTS/ECS, and plain C# / non-Unity repos
(irrelevant skills score low and never load). Full details in
[`SETUP.md`](./SETUP.md); cross-project + team modes in
[`CLONE-SETUP.md`](./CLONE-SETUP.md).

```sh
# verify a fresh install
python3 .claude/scripts/orchestrate.py preflight
python3 .claude/scripts/build_skill_registry.py check    # registry intact (23/23)
python3 .claude/scripts/validate_skill_routing.py        # routing lanes correct
python3 .claude/scripts/skills.py validate               # 0 orphans / 0 unreachable / 0 duplicates
```

**Optional MCP servers:** `code-review-graph` (triage + investigators; falls back
to Grep with −0.2 confidence if absent), `ai-game-developer` (Unity Editor
introspection/mutation), `agentmemory` (recall only — live files always win).

---

## Worked examples

### Small bug
```
/team bug "Damage popup shows 0 when hit lands on enemy with shield"
```
Triage `small`/`DOTS`/conf `0.82` → `[bug-investigation] → [unity-dots-dev] → [verifier]`.
No architect, no data-tool, sequential. Gates: `root_cause.json` → `impl_result.json` → `verification_result.json`.

### Medium feature
```
/team feature "Add stamina component with regen and sprint cost"
```
Triage `medium`/`DOTS` → `[architect] → [unity-dots-dev] → [verifier]`.
Skill packs: `ecs-job-patterns`, `burst-safety`, `memory-safety`. No tester unless `depth=deep`.

### Large refactor
```
/team refactor deep "Extract zone spawn logic into shared SpawnerSystem"
```
`[refactor-agent] → [architect] → [unity-dots-dev (step-gated)] → [tester]`.
Architect writes `ownership.lock.json`; impl runs step-by-step, tester verifies between steps;
Codex review pre-impl and pre-completion (`depth=deep`).

### Explore
```
/team explore "How does the dungeon POI spawner interact with EnemyTrackerSystem?"
```
Triage runs full CRG, writes `triage.json`, appends to `repo-knowledge.md`, exits. Empty pipeline.

---

## Background — v1 → v2

v1 always spawned a fixed 4-agent team and relied on markdown "rules" the
orchestrator could ignore. v2 makes the shape adaptive and the gates executable:

| v1 problem | v2 design |
|------------|-----------|
| Fixed 4-agent shape | `triage.json` → `orchestrate.py plan` derives 1–4 agents |
| Markdown-only gates | `orchestrate.py gate <id>` — exit 2 = halt |
| Always-on tester | `verifier` for tiny/small/medium; `tester` only for ≥ large OR confidence < 0.7 |
| Nested subagents | skill packs loaded as text |
| Early parallel execution | parallel only when confidence ≥ 0.8 AND complexity ≥ medium AND ownership partitioned |
| tmux as a dependency | tmux optional |
| 5+ command flags | `intent` + `depth` |

Flag mapping + full migration guide: [`MIGRATION.md`](./MIGRATION.md).

---

## Layout

```
.claude/
├── CLAUDE.md                       project memory + skill discovery policy
├── commands/team.md                /team command spec
├── agents/                         12 subagent definitions
├── skills/                         23 skill packs + registry.json (v2) + INDEX.md
├── scripts/                        17 stdlib scripts (orchestrate, route, skills CLI, validate, …)
├── schemas/                        6 artifact JSON-schemas
├── workspace-templates/            canonical empty artifacts
├── rules/                          operational policy (phase gates, ownership, escalation, …)
└── docs/                           architecture + MCP integration deep dives
AGENTS.md                           safe external-skill discovery policy
docs/                               SkillHub audit · skill architecture · validation report
tests/                              494-test suite (routing, security, fixtures)
workspace/                          runtime artifacts (gitignored except persistent knowledge)
.rtk/filters.toml                   RTK token-optimized command filters
SETUP.md · CLONE-SETUP.md           install + cross-project / team-mode setup
MIGRATION.md · CHANGELOG.md         v1→v2 migration · version history
```

---

## License

See [`LICENSE`](./LICENSE).
</content>
</invoke>
