# Changelog

All notable changes to `unity-agent-team` are documented here.

For agent-facing recent changes, see `workspace/recent-changes.md`.

---

## 2026-05-22

### Added
- Multi-layer knowledge system (recent-changes, decay, ownership, token budget, agent policy)
- `workspace/recent-changes.md` — rolling 14-day agent-facing architectural awareness layer
- Knowledge confidence decay (`knowledge-decay-system.md`) — facts decay without revalidation
- Section-tag retrieval for `repo-knowledge.md` — agents read relevant sections only
- Hash-based skill cache freshness (`skill-cache-freshness.md`) — SHA-256 invalidation
- Token budget governance (`knowledge-token-budget.md`) — 800-token hard cap per agent
- Change impact system — risk-category metadata on recent-changes entries
- Per-agent knowledge reading policy (`agent-knowledge-policy.md`)
- Dual-stack domain system — 3 domains (Runtime ECS, Unity View/Authoring, Hybrid Boundary)
- API fingerprinting (50+ DOTS/Unity/Hybrid APIs with confidence weights)
- Domain scoring engine with worked examples
- Dynamic skill reload on domain contradiction
- Domain-aware MCP strategy per domain
- Code-aware routing engine (8-step pipeline replaces keyword routing)
- Architecture pattern detection (9 patterns)

### Changed
- DOTS Conflict Resolution Policy → Domain-Aware Precedence Policy
- `STEP 1.5` now includes hash-based cache invalidation + recent-changes filtering
- `OWNERS.md` — `recent-changes.md` added as persistent team knowledge file
- `CLAUDE.md` — Knowledge System section added above Hardening Rules

### Fixed
- `architecture-agent`, `codebase-reader`, `feature-dev-agent` orphaned agents removed
- `system-mapper` and `code-tracer` cleanly replace deprecated agents

---

## 2026-05-21 (approximate)

### Added
- Full team UI setup (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"`) in SETUP.md Step 6a
- Unity-Skills v1.9.1 integration — layered skill loading (Layer 1–4)
- Skill confidence routing engine with symptom pattern library (8 patterns)
- Cross-agent skill cache (150-token summaries, 42–57% token reduction)
- MCP phase gates (Phase 1–4 permission matrices)
- Repository learning loop (5 triggers, quality gate, retention policy)
- Escalation policy (4 signal types, 4 categories, decision tree)
- Shared workspace (6 structured files replacing prompt embedding)
- Authority model (`[BLOCKED]`, `[REJECTED]`, `[ESCALATE]`, `[SCOPE_EXCEEDED]`)

### Changed
- `team.md` — `--bug`, `--feature`, `--refactor`, `--fast-fix` task mode flags
- Agent prompts — domain-appropriate reasoning injected per phase
- SETUP.md — workspace creation step, unity-skills install guide

### Fixed
- Refactor step-by-step deadlock prevention (BLOCKED signal + orchestrator intervention)
- Compilation gate added to `--bug` flow (verify clean before signaling tester)
- Baseline-FAIL requirement enforced for regression tests

---

## Earlier

See git log for changes prior to 2026-05-21.
