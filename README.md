# Unity Agent Team — Adaptive Pipeline (v2)

A Claude Code package that runs an **adaptive Unity DOTS agent pipeline**.
Triage classifies the task, an orchestrator script derives the minimum viable
agent composition, and every phase boundary is a Python gate that exits
non-zero on violation. There is no fixed team and no always-on tester.

```
/team <intent> [depth] <task>

intent ∈ { bug, feature, refactor, explore }
depth  ∈ { quick, normal, deep }   default: normal
```

---

## Why v2 (and what v1 got wrong)

The v1 framework always spawned 4 agents (architect, unity-dev, data-tool,
tester) for every task. Most tasks did not need 4 agents. Most "rules" were
markdown promises ("don't proceed until X") that the orchestrator could
silently ignore. Parallel execution started before the design was certain,
producing conflicting edits. tmux was a hard dependency that leaked into the
architecture.

**v2 fixes those by design, not by docs:**

| v1 problem | v2 design |
|------------|-----------|
| Fixed 4-agent shape | Triage emits a `triage.json`; `orchestrate.py plan` derives 1–4 agents |
| Markdown-only gates | Every phase gate is `orchestrate.py gate <phase-id>` — exit 2 = halt |
| Always-on tester | `verifier` for tiny/small/medium; `tester` only when complexity ≥ large OR confidence < 0.7 |
| Nested subagents (`burst-validator`, `code-generator`, …) | Skill packs loaded as text into the relevant agent |
| Early parallel execution | Parallel allowed only when `confidence ≥ 0.8` AND complexity ≥ medium AND ownership partitioned across ≥ 2 agents |
| tmux as a dependency | tmux is optional UI; orchestration runs identically without it |
| 5+ command flags (`--bug`, `--feature`, `--refactor`, `--fast`, `--full`, `--fast-fix`, `--teams`) | `intent` + `depth` |

---

## Adaptive pipeline at a glance

```
/team <intent> [depth] <task>
       │
       ▼
[Step 0] Bootstrap                  orchestrate.py preflight + reset
       │
       ▼
[Step 1] Triage agent               CRG + fingerprinting → workspace/triage.json
       │
       ▼
[Step 2] Plan                       orchestrate.py plan workspace/triage.json
                                    → workspace/pipeline.json (phases, parallelism, artifacts)
       │
       ▼
[Step 3] Execute phases             For each phase:
                                      orchestrate.py gate <id>      ← exit 2 → halt
                                      spawn agents from phase.agents
                                      each agent writes its artifact and validates
                                    Loop on verifier FAIL (up to 2 retries).
       │
       ▼
[Step 4] Finalize                   orchestrate.py finalize
                                    → completion report or exit 4
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
- `refactor` prepends `refactor-agent`, forces `architect` approval and
  step-gated execution
- `explore` produces an empty pipeline — triage runs alone, updates
  `repo-knowledge.md`, and exits

Depth modifier:

- `quick` downgrades one tier (refused if blast_radius ≥ multi-system)
- `normal` uses triage's classification as-is
- `deep` upgrades one tier, always uses `tester`, requires `/codex:review`

---

## Runtime enforcement

Every artifact has a JSON schema in `.claude/schemas/`. Every phase boundary
calls `.claude/scripts/orchestrate.py`. The exit code is the contract:

| Exit | Meaning |
|------|---------|
| 0 | OK |
| 2 | Gate violation — phase must not proceed |
| 3 | Ownership violation — writer touched a file outside its partition |
| 4 | Verification FAIL — completion blocked |
| 10 | Retry limit hit (3 failed implementation cycles) |

Run the gates yourself any time:

```sh
python .claude/scripts/orchestrate.py validate workspace/triage.json triage
python .claude/scripts/orchestrate.py gate phase-2
python .claude/scripts/orchestrate.py ownership-check unity-dev Assets/Scripts/Combat/Health.cs
python .claude/scripts/orchestrate.py finalize
```

No external dependencies. Stdlib only.

---

## Install

```
1. Copy .claude/ into your Unity project root.
2. (Optional) copy SETUP.md, README.md, CHANGELOG.md, MIGRATION.md, LICENSE.
3. Verify: python3 .claude/scripts/orchestrate.py preflight
```

That is it. Full details in [`SETUP.md`](./SETUP.md).

For cloning into another project + using the real 4-agent **`/team --team`** mode
(Sonnet sessions in tmux + git worktrees), see [`CLONE-SETUP.md`](./CLONE-SETUP.md).

---

## Skill packs (replaces nested subagents)

Loaded into agents as text — never spawned as agents.

| Pack | Loaded into | Replaces v1 subagent |
|------|-------------|---------------------|
| `burst-safety` | unity-dev when domain=DOTS/Hybrid | `burst-validator` |
| `ecs-job-patterns` | unity-dev when domain=DOTS/Hybrid | `job-optimizer` |
| `memory-safety` | unity-dev when domain=DOTS/Hybrid | `memory-checker` |
| `ownership-partitioning` | every writer when parallel_allowed=true | (new) |
| `triage` | triage agent | (new) |
| `verifier` | verifier agent | (new) |

The full Unity DOTS skill (`unity-dots-best-practices/SKILL.md`) is always
loaded into architect and unity-dev. The packs above are the minimum subsets
that replace the v1 subagent fan-out.

---

## Artifacts and schemas

Every artifact is JSON, validated against a schema, and gated by the
orchestrator before the next phase runs.

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
| `root_cause.json` | `bug-investigation` / `refactor-agent` | architect / unity-dev |
| `approved_plan.json` | `architect` (medium+) | unity-dev / data-tool |
| `impl_result.json` | `unity-dev`, `data-tool` | verifier / tester |
| `verification_result.json` | `verifier`, `tester` | `orchestrate.py finalize` |
| `ownership.lock.json` | `architect` (when parallel) / `triage` (when 2 writers) | every writer's `ownership-check` |

---

## Worked examples

### Small bug

```
/team bug "Damage popup shows 0 when hit lands on enemy with shield"
```

- Triage: complexity=`small`, intent=`bug`, domain=`DOTS`, confidence=`0.82`
- Pipeline: `[bug-investigation] → [unity-dev] → [verifier]`
- No architect. No data-tool. Sequential only.
- Artifacts gated: `root_cause.json` → `impl_result.json` → `verification_result.json`

### Medium feature

```
/team feature "Add stamina component with regen and sprint cost"
```

- Triage: complexity=`medium`, domain=`DOTS`, confidence=`0.85`
- Pipeline: `[architect] → [unity-dev] → [verifier]`
- Skill packs: `ecs-job-patterns`, `burst-safety`, `memory-safety`
- No tester unless `depth=deep`.

### Large refactor

```
/team refactor deep "Extract zone spawn logic into shared SpawnerSystem"
```

- Triage: complexity=`large`, intent=`refactor`, domain=`DOTS`
- Pipeline: `[refactor-agent] → [architect] → [unity-dev (step-gated)] → [tester]`
- Architect writes `ownership.lock.json` partitioning runtime files from
  tooling files. unity-dev executes migration step-by-step; tester verifies
  between steps. Codex review pre-impl and pre-completion (because
  `depth=deep`).

### Explore

```
/team explore "How does the dungeon POI spawner interact with EnemyTrackerSystem?"
```

- Triage runs full CRG, writes `triage.json`, appends findings to
  `repo-knowledge.md`, exits.
- Pipeline is empty. `orchestrate.py finalize` reports completion with
  `risk_level=LOW`.

---

## v1 flag mapping (for migration)

| v1 flag | v2 invocation |
|---------|--------------|
| `/team <task>` (default) | `/team feature <task>` (triage picks the rest) |
| `/team <task> --full` | `/team feature deep <task>` |
| `/team <task> --fast` | `/team feature quick <task>` |
| `/team <task> --bug` | `/team bug <task>` |
| `/team <task> --feature` | `/team feature <task>` |
| `/team <task> --refactor` | `/team refactor <task>` |
| `/team <task> --fast-fix` | `/team bug quick <task>` |
| `/team <task> --teams` | enable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` env in `~/.claude/settings.json`; `/team` autodetects |

Full migration guide: [`MIGRATION.md`](./MIGRATION.md).

---

## Layout

```
.claude/
├── CLAUDE.md                       project memory
├── commands/team.md                /team command (adaptive)
├── agents/                         subagent_type definitions
├── skills/                         skill packs (loaded into agents)
├── scripts/orchestrate.py          runtime enforcer (preflight, plan, gate, …)
├── scripts/triage.py               triage helper
├── schemas/*.schema.json           artifact JSON-schemas
├── workspace-templates/            canonical empty artifacts
├── rules/                          operational policy
└── docs/                           architecture + MCP integration deep dives
workspace/                          runtime artifacts (gitignored except persistent ones)
SETUP.md                            install + verify
MIGRATION.md                        v1 → v2 migration
CHANGELOG.md                        version history
```

---

## License

See [`LICENSE`](./LICENSE).
