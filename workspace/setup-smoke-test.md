# Setup Smoke Test Report

Date: 2026-06-12
Method: real cold-start runs in temporary fixture repositories under /tmp/smoke
(framework copied; nothing mocked). Plus 516-test pytest suite (22 portability tests).

## Fixture 1 — embedded Unity project `my-unity-game`

- Layout: `.claude/` copied into repo root; Unity markers (Assets/, Packages/manifest.json, ProjectSettings/ProjectVersion.txt); branch `develop`.
- `setup.py --yes`: detected `projectType=unity`; created workspace/, reports/, devlogs; wrote project-config.json; seeded repo-knowledge.md, recent-changes.md, **ecs-registry.md**.
- Second run: "nothing to do"; `--check` exit 0. **Idempotent: PASS.**
- `roots.py --json`: UNITY_PROJECT_ROOT=repo root; defaultBranch=`develop` (not hardcoded); worktreeRoot=`/tmp/smoke/my-unity-game-worktrees` (project-namespaced); teamProfiles.full = architect/unity-dots-dev/unity-dev/qa-tester.
- `orchestrate.py preflight` invoked **from /tmp** (different cwd): resolved correct repo_root/workspace. **cwd-independent: PASS.**

## Fixture 2 — non-Unity `my-cloud-code-service`

- package.json with express → detected `projectType=backend`.
- Seeded repo-knowledge.md + recent-changes.md; **NO ecs-registry.md** (Unity-only seed correctly skipped).
- UNITY_PROJECT_ROOT=None; teamProfiles.full = architect/**backend-dev**/qa-tester.
- **Unity-specific behavior disabled for non-Unity: PASS.**

## Fixture 3 — monorepo `my-workspace` + external framework (renamed dir)

- Framework copied as `agent-team-framework-renamed` (different name — no name dependence).
- Two Unity projects `game-a`, `game-b`.
- `setup.py --project-root game-a` from workspace root: correct root + type.
- `AGENT_TEAM_PROJECT_ROOT=game-b roots.py`: PROJECT_ROOT=game-b, worktreeRoot=`game-b-worktrees` (≠ game-a's), FRAMEWORK_ROOT=renamed dir. **Per-project isolation + rename safety: PASS.**

## Additional coverage via pytest (tests/test_portability.py, 22 tests)

- legacy `UNITY_TEAM_PROJECT_ROOT` alias honored
- custom defaultBranch from config returned
- missing devlogs dir → empty list, no exception
- project path containing spaces → all resolvers work
- setup run twice → values preserved; `--check` exit-code contract
- subprocesses launched from unrelated cwd throughout

## Validators

- `validate_portability.py`: **PASS (0 findings)**
- `skills.py validate`: PASS (orphans 0, unreachable 0, unresolved_duplicates 0; 5 documented collision warnings)
- Full suite: **516 passed, 0 failed**

## Verdict: PASS — all acceptance smoke criteria met in 3 differently named fixtures.
