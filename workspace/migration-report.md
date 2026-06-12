# Migration Report

> Template: this file is (re)written by `python3 .claude/scripts/migrate.py`
> on every apply run. Sections: Date/Root/Mode header, Findings, setup.py
> output, Revert instructions. The entry below documents the migration of the
> framework repository itself to the portable layout (performed manually as
> part of the portability work, 2026-06-12).

- Date: 2026-06-12
- Project root: framework repository (`unity-agent-team`)
- Mode: apply (manual — framework-repo self-migration)

## Findings

- **docs-hardcoded-paths** — README.md / SETUP.md / CLONE-SETUP.md contained
  project-specific absolute paths and repo names (old Unity-game examples,
  WSL drive mounts) and the legacy `UNITY_TEAM_PROJECT_ROOT`-only guidance.
  - fix: replaced with generic names (`my-unity-game`,
    `my-cloud-code-service`, `my-workspace`) and `AGENT_TEAM_PROJECT_ROOT`
    (legacy alias documented, not removed).
- **missing-migration-tooling** — no script existed to detect/upgrade
  old-style installs.
  - fix: added `.claude/scripts/migrate.py` (`--check` report mode, git-safe
    apply mode that delegates to `setup.py --yes`).

## Files changed (this migration)

| File | Change |
|------|--------|
| `.claude/scripts/migrate.py` | NEW — old-install detector + git-safe migrator (check/apply, `--allow-dirty`, writes this report) |
| `MIGRATION.md` | appended "v2 → portable (2026-06)" section (what changed, migrate.py usage, revert) |
| `README.md` | portable install quickstart (setup.py), 3 installation modes table, roots/setup/migrate script rows, removed trailing artifacts |
| `SETUP.md` | prerequisites; embedded install via setup.py; setup CLI reference; full `project-config.json` field table + team-profile defaults; root-resolution order; agentmemory via `agentMemoryEnabled`; troubleshooting (RootResolutionError, wrong project, non-Unity); add-project-type + project-local agent/skill guides; uninstall/rollback |
| `CLONE-SETUP.md` | rewritten §0 (three modes, resolver order, namespaced worktrees); generic example names; new §1b external/shared and §1c monorepo walkthroughs; env var renamed to `AGENT_TEAM_PROJECT_ROOT` |
| `.gitignore` | ignore session/research debris: `workspace/audit/`, `workspace/dots-program/`, `workspace/full-team/`, `workspace/collision-disambiguation-draft.md`, `reports/` (nothing removed from disk) |
| `workspace/migration-report.md` | NEW — this report |

## Revert

Migration is additive/doc-only. To revert:

```sh
git checkout -- .claude/ README.md SETUP.md CLONE-SETUP.md MIGRATION.md .gitignore
rm -f .claude/scripts/migrate.py workspace/migration-report.md
```
