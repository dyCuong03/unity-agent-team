# Unity DOTS Agent Team

This project packages a reusable Claude Code team for Unity DOTS development.

## Philosophy

**Agents start work the moment they're spawned.** No blocking preflight, no checklist before doing the task. MCP and memory tools are pulled when actually needed, not as ceremony.

## Required MCP Servers

| Server | Purpose |
|---|---|
| `ai-game-developer` | Unity Editor introspection and mutation |
| `agentmemory` | Cross-session memory (recall, save, consolidate, reflect) |

If either is unavailable, agents state the fallback once and keep working. See `@.claude/docs/mcp-integration.md`.

## Agent Teams Mode (Recommended for Full Team UI)

The default `/team` uses the standard `Agent` tool — works everywhere, zero config.

For the full team UI with one tmux pane per agent (visible parallel execution),
add to your **user-level** `~/.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "preferences": {
    "tmuxSplitPanes": true
  }
}
```

**Restart Claude Code after adding this.** Then use `/team <task> --teams` for pane-per-agent view.

Without `--teams`, the system works identically — agents run via the standard `Agent` tool.

> This setting is user-level only. Never commit it to the project repo.
> See SETUP.md Step 6a for the exact install command per platform.

## Team Activation

When this package handles a task:

1. Run `python .claude/scripts/preflight.py` (informational, never blocks).
2. Spawn the 4 fixed roles in parallel — `architect`, `unity-dev`, `data-tool`, `tester` (or just 2 in `--fast` mode).
3. Each agent self-loads its skills via `@`-imports and starts work immediately.

Entrypoints:
- `/team <task>` (default — fast, 2 agents)
- `/team <task> --full` (all 4 agents)

## Skill Files

| Location | Purpose |
|---|---|
| `.claude/skills/<role>/SKILL.md` | Per-role brief (architect, unity-dev, data-tool, tester) |
| `.claude/skills/unity-dots-best-practices/SKILL.md` | Shared DOTS guidance |
| `.claude/skills/editor-data-tools/SKILL.md` | Shared editor tooling guidance |
| `.claude/skills/qa-validation/SKILL.md` | Shared QA guidance |
| `.claude/skills/start-unity-dots-team/SKILL.md` | Reference notes for `/team` |

## Execution Order

1. **Architect** publishes a design. Other agents may have already started in parallel and reconcile when it arrives.
2. **Unity Dev** implements, escalating any design conflict.
3. **Data Tool** adds tooling, validators, diagnostics.
4. **Tester** validates and blocks completion until evidence supports sign-off.
5. Loop on defects.

## Architect Gate

The design must cover:
- Feature scope
- ECS data model
- Entity / component ownership
- System responsibilities and update order
- Baker / authoring conversion plan
- Performance constraints
- Acceptance criteria
- Known risks

Once published, unity-dev / data-tool / tester self-correct against it.

## Codex Review Gate (MANDATORY for every team task)

Every task executed by the team **must pass a `/codex:review` pass after the Architect publishes the design and again before final sign-off.**

1. **Plan review** — As soon as the Architect publishes a design, the orchestrator (or the agent acting as team lead) invokes `/codex:review` with the design plus the relevant recon facts. Architect must address every blocker / high-severity comment before unity-dev starts irreversible work.
2. **Implementation review** — Before Tester sign-off, run `/codex:review` again over the final diff. Any blocker found returns the task to the responsible role and the loop continues.
3. **Evidence** — Capture the `/codex:review` verdict (pass / changes-requested / block) plus a one-line summary in the completion output under a `Codex review:` field. Never declare a task complete without it.
4. **Fallback** — If `/codex:review` is unavailable, state `"Running without codex review"` once, escalate, and require an extra Architect + Tester review pass to compensate.

This rule applies to bug fixes, features, refactors, and tooling work alike. It is non-optional.

## Subagent Rule

Each role delegates non-trivial work to its internal subagents (listed in `.claude/skills/<role>/SKILL.md`). Subagents stay inside the parent agent — no panes, no top-level promotion.

## MCP & Memory Rule

- **Prefer `ai-game-developer` MCP over guessing Unity-side state** — but only when you actually need to verify or mutate Unity state. Don't pull tools as ceremony.
- **Use `agentmemory` when prior work likely exists** — recall and search. Save a lesson at handoff only when it's non-obvious.
- If a tool is unavailable, state "Running without MCP evidence" / "Running without memory recall" once and continue.

## Unity DOTS Rules

- Prefer `IComponentData`, `IBufferElementData`, `BlobAssetReference<T>`, `IAspect`, `ISystem`, jobs, and Burst.
- Optimize for data layout, cache locality, predictable frame cost.
- No managed allocations in hot paths.
- Minimize structural changes in tight loops (ECB or enableable components).
- Keep authoring/editor code separate from runtime (asmdef boundaries).
- Sync points, main-thread work, and archetype churn are explicit costs.

## Role Boundaries

| Role | Owns | Must not |
|---|---|---|
| Architect | Design, ECS boundaries, update flow, acceptance criteria | Code |
| Unity Dev | Runtime implementation | Change architecture without approval |
| Data Tool | Editor tools, validators, diagnostics | Silently change runtime behavior |
| Tester | Test cases, stress, regression, sign-off | Approve without evidence |

## Communication

Every handoff: objective, inputs, outputs, constraints, open risks. Concise and technical. Conflicts escalate; tests-fail returns to the responsible role; loop continues.

## Domain-Aware Precedence Policy

The system uses **three domains** — not a single DOTS-first policy. Domain is determined by code evidence (API fingerprinting), not task keywords. See `.claude/rules/dual-stack-domain-system.md`.

### Domain 1 — Runtime ECS (DOTS leads)

Applies when: `DOTS_score ≥ 0.70` and `DOTS_score > Unity_score + 0.20`

| DOTS wins | Unity default overridden |
|-----------|--------------------------|
| `ISystem.OnUpdate()` | MonoBehaviour `Update()` |
| `IComponentData` + entity | MonoBehaviour state |
| `Jobs` + `Dependency` chains | async/await in hot paths |
| `ECB` structural changes in jobs | Direct `EntityManager` in jobs |
| ECS singleton (`SystemAPI.GetSingleton<T>()`) | ScriptableObject for runtime state |
| Physics for Entities | MonoBehaviour Rigidbody in simulation |

### Domain 2 — Unity View / Authoring (Unity leads)

Applies when: `Unity_score ≥ 0.70` and `Unity_score > DOTS_score + 0.20`

| Unity wins | Notes |
|-----------|-------|
| MonoBehaviour lifecycle | Correct execution model for view code |
| Coroutines / async | Valid in presentation layer |
| ScriptableObject for config | Correct authoring pattern |
| Prefab workflow | Correct view authoring |
| Animator state machine | Correct for character animation |

DOTS patterns are secondary in this domain. Do not force ECS reasoning onto view code.

### Domain 3 — Hybrid Boundary (Both cooperate)

Applies when: `Hybrid_score ≥ 0.60` and `abs(DOTS_score - Unity_score) < 0.30`

Rule: **DOTS owns runtime truth. Unity owns presentation. Bridge is explicit and one-way.**

Every hybrid feature requires a contract in `workspace/design.md`:
```
Hybrid Contract: <name>
Source of truth: DOTS — <component name>
Presentation owner: Unity — <class name>
Data flow: DOTS → read by Unity (never the reverse at runtime)
Write path: Only via <system or ECB> — Unity never writes entity state directly
```

### Exception Approval (Domain 1 only)

Any deviation from DOTS-first policy within Domain 1 requires architect approval:
```
[DOTS_EXCEPTION: <what rule is relaxed>]
Reason: <technical constraint>
Boundary: <where MonoBehaviour/OOP code is isolated>
Risk: <what breaks if this spreads>
```

### Domain Classification

Determined by code evidence — not keywords. Investigation runs first.
See `workspace/domain-analysis.md` for per-session classification evidence.
If domain is ambiguous → `[ESCALATE_ARCHITECT: domain ambiguous]` before implementation starts.

Full rules: `@.claude/rules/dual-stack-domain-system.md`

## Shared Workspace

All agents communicate through files in `workspace/` at the project root, not through prompt embedding.

| File | Owner | Readers | Scope |
|------|-------|---------|-------|
| `workspace/repo-knowledge.md` | `system-mapper` | all | persistent |
| `workspace/ecs-registry.md` | `architect` | all | persistent |
| `workspace/design.md` | `architect` | unity-dev, data-tool, tester | session |
| `workspace/investigation.md` | `bug-investigation` | unity-dev, tester | session |
| `workspace/test-plan.md` | `tester` | unity-dev, architect | session |
| `workspace/migration-plan.md` | `refactor-agent` → `architect` | unity-dev, tester | session |

**Rules:**
- Read your input files before starting work
- Write to workspace files — do not embed full outputs in SendMessage or chat
- Session-scoped files are overwritten at the start of each new run
- Persistent files are appended/updated with datestamp — never deleted

## Authority Model

These signals are hard stops. The orchestrator MUST check for them before spawning the next phase.

| Signal | Who can issue | Meaning | Orchestrator action |
|--------|-------------|---------|---------------------|
| `[BLOCKED: reason]` | tester, architect | Cannot proceed — hard stop | Halt phase → route to responsible agent |
| `[REJECTED: reason]` | architect | Design or plan rejected | Halt → return to previous phase owner |
| `[ESCALATE: reason]` | any agent | Non-blocking flag | Continue + append to open risks |
| `[SCOPE_EXCEEDED]` | unity-dev | --fast-fix exceeded 20 lines | Halt → re-run as --bug |

**Authority by role:**

| Role | Can BLOCK | Can REJECT | Can ESCALATE | Notes |
|------|-----------|-----------|-------------|-------|
| `architect` | yes | yes | yes | Rejects design deviations and bad migration plans |
| `tester` | yes | no | yes | Blocks sign-off; escalates unresolvable failures to architect |
| `unity-dev` | no | no | yes | Escalates ambiguous design; escalates scope exceeded |
| `data-tool` | no | no | yes | Escalates if tooling requires runtime architecture change |
| `bug-investigation` | no | no | yes | Escalates if root cause is inconclusive |
| `system-mapper` | no | no | yes | Escalates if CRG evidence conflicts with repo-knowledge |
| `refactor-agent` | no | no | yes | Escalates if blast radius is too large for safe migration |

## Hardening Rules (Production Policy — All Agents Must Comply)

Five mandatory policy files govern this system. Every agent reads the relevant sections before acting.

| Rule file | Governs | When to read |
|-----------|---------|-------------|
| `@.claude/rules/skill-confidence-routing.md` | Skill module selection with confidence scores | STEP 1.5 — before any agent spawn |
| `@.claude/rules/cross-agent-skill-cache.md` | Skill deduplication across agents in same session | STEP 1.5 — before Phase 3 spawns |
| `@.claude/rules/mcp-phase-gates.md` | Which MCP/REST operations are allowed per phase | Every agent — before any MCP call |
| `@.claude/rules/repo-learning-loop.md` | When and what to save to repo-knowledge.md | Every agent — after phase completion |
| `@.claude/rules/escalation-policy.md` | Mandatory escalation triggers with routing rules | Every agent — throughout execution |

### Quick Reference

**Skill routing:** Score every candidate module 0.0–1.0. Load threshold: ≥ 0.70. Max 2 domain + 2 advisory per agent. See `skill-confidence-routing.md`.

**Skill cache:** First loader writes a 150-token summary to `workspace/skill-cache/<module>.cache.md`. All subsequent agents read the summary. See `cross-agent-skill-cache.md`.

**MCP phases:**
- Phase 1 (investigation): READ ONLY — no writes of any kind
- Phase 2 (implementation): LIMITED WRITE — scripts, scoped prefabs only
- Phase 3 (validation): PLAYMODE + READ — run tests, no code changes
- Phase 4 (refactor): STEP-GATED WRITE — each step needs tester OK before next
See `mcp-phase-gates.md`.

**Learning triggers:** Save to `workspace/repo-knowledge.md` after: bug fix (bug-investigation), architecture approval (architect), tester sign-off (tester), performance regression (data-tool/tester), refactor incident (refactor-agent). Quality gate: must name specific systems, include detection signal, ≤200 tokens. See `repo-learning-loop.md`.

**Escalation:**
- `[AUTO_ESCALATE]` — non-blocking, appends to open risks
- `[BLOCK]` — hard stop, halts phase
- `[ESCALATE_ARCHITECT]` — architect must respond before phase resumes
- `[ESCALATE_HUMAN]` — human engineer required
Mandatory triggers: >3 systems touched, Burst removed, sync point added, >500 LOC, 3+ failed fixes. See `escalation-policy.md`.

## Anti-Patterns — Banned Behaviors

The following behaviors are forbidden for all agents in all modes:

### Investigation
- Reading files without prior CRG query evidence
- Grepping the repository as a first step
- Opening more than 8 files per investigation
- Inferring architecture from filenames
- Calling both `codebase-reader` AND `feature-dev-agent` — use `code-tracer` (one call)
- Calling `architecture-agent` — use `system-mapper` (prevents naming collision with `architect`)

### Implementation
- Writing any code before `system-mapper` has mapped existing systems (in `--feature` mode)
- Starting implementation before root cause is proven (in `--bug` mode)
- Fixing a bug without a failing baseline test first
- Opportunistic refactoring — fixing code beyond the exact root cause
- Signaling tester before verifying compilation is clean
- Moving or renaming a system's update group without architect approval
- Removing `[BurstCompile]` from a hot-path `ISystem`
- Performing structural changes (`AddComponent`/`RemoveComponent`) inside a scheduled job

### Orchestration
- Spawning `architect` in `--feature` Phase 1 — Phase 1 is always `system-mapper`
- Confusing `system-mapper` (reads codebase) with `architect` (designs new systems)
- Leaving a `--refactor` migration half-done — if a step fails, roll back that step immediately
- Allowing unity-dev to wait indefinitely in step-by-step refactor — tester must reply or unblock
- Declaring a bug fixed without both baseline-FAIL and post-fix-PASS evidence
- Using `--fast-fix` for changes touching system execution order, Burst jobs, or structural changes

### ECS-Specific
- Designing components that duplicate existing components without explicit architect approval
- Adding main-thread work to a system that was previously job-scheduled
- Modifying system execution order (`[UpdateBefore/After]`) without a blast-radius analysis
- Using `Time.time`, `Random.Range`, or `DateTime.Now` in any ECS system (breaks determinism)
- Calling `EntityManager` directly on main thread inside a system that also schedules jobs

---

## CRG-First Codebase Understanding

Five specialized agents handle codebase investigation. All query `code-review-graph` MCP before reading any files.

| Agent | Use Case |
|-------|----------|
| `architecture-agent` | System architecture mapping, domain boundaries, execution flow |
| `codebase-reader` | Feature reading, entry point discovery, behavior summary |
| `bug-investigation` | Root cause tracing, write conflict detection, fix validation |
| `refactor-agent` | Blast radius analysis, safe migration planning |
| `feature-dev-agent` | Pattern discovery, extension point identification, consistent implementation |

### CRG Rules (apply to all 5 agents)

- Query `code-review-graph` before opening any file
- Never grep the repository blindly
- Never infer architecture from filenames
- Never open more than 8 files without graph justification
- If CRG is unavailable: state "Running without CRG evidence" once, then use targeted Grep

Full rules: `@.claude/rules/GRAPH_FIRST.md`
