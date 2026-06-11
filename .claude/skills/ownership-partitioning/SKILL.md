---
name: ownership-partitioning
description: Hard write-partitioning rules for parallel agents when pipeline.parallel_allowed=true. Defines glob-based file ownership, conflict detection, and orchestrate.py ownership-check integration. Prevents concurrent agents from writing the same files.
use-when: |
  Load for unity-dev and data-tool agents when pipeline.json.parallel_allowed=true.
  Load whenever the architect has written workspace/ownership.lock.json to partition files.
do-not-use-when: |
  Do not load for sequential pipelines (parallel_allowed=false). Do not load for
  triage, architect, tester, or verifier roles. Unnecessary when only one writer exists.
platforms: [claude-code, codex, copilot, cursor, windsurf]
task-categories: [architecture, parallel, ownership, refactor]
metadata:
  source: internal
  version: 1.0.0
  tier: 1

---

# Ownership Partitioning

This skill is loaded into every writer agent (`unity-dev`, `data-tool`) whenever
`pipeline.json.parallel_allowed == true`. It is enforced at runtime by
`orchestrate.py ownership-check`.

## Source of Truth

`workspace/ownership.lock.json`. Format:

```json
{
  "partitions": {
    "unity-dev": ["Assets/Scripts/Combat/**", "Assets/Scripts/Movement/**"],
    "data-tool": ["Assets/Editor/Combat/**", "Assets/Configs/Combat/**"]
  },
  "shared_read_only": ["ProjectSettings/**", "Packages/**"],
  "forbidden": ["Assets/Plugins/**"],
  "rationale": "Combat refactor — runtime vs tooling are disjoint"
}
```

Globs are repo-root-relative, POSIX-style (use `/`, not `\`). `**` matches any
number of path segments.

## Rules

1. **You may only write to files matching one of YOUR partition globs.**
   Writing to another agent's partition is a hard violation.
2. **`shared_read_only`** files may be read by anyone but NEVER written this
   session. If you genuinely need to change one, escalate.
3. **`forbidden`** files must not be touched at all (typically generated code,
   third-party plugins, lockfiles).
4. **Before signaling the next phase**, run the check explicitly:

   ```sh
   python .claude/scripts/orchestrate.py ownership-check <your-agent-name> \
       Assets/Scripts/Combat/Health.cs Assets/Scripts/Combat/Damage.cs
   ```

   Non-zero exit means you have a violation. Roll back that file and re-run.

## Architect Responsibilities

For `large` / `critical` complexity, the architect writes
`workspace/ownership.lock.json` as part of the `approved_plan.json` phase. The
partition must:

- Have non-overlapping globs across agents
- Cover every file the plan expects to change
- Not include `shared_read_only` paths inside any partition

The orchestrate.py gate refuses to enter the implementation phase if
`ownership.lock.json` is missing for any plan with `parallel_allowed=true`.

## Triage Responsibilities

For `tiny` / `small` / `medium` complexity with a single writer, triage may
either (a) omit `ownership.lock.json` entirely (unrestricted single writer), or
(b) write a single-agent partition to lock the writer to a known glob.

If `data-tool` is in the pipeline at any complexity, triage MUST partition.
Otherwise `data-tool` and `unity-dev` may both edit the same files.

## Failure Mode

If your edits violated the partition and you only discover it post-hoc:

1. Revert the offending edits via git.
2. Write `[ESCALATE: ownership violation in <files>]` to your impl_result.json.
3. Do NOT request a partition expansion mid-implementation. The architect
    re-issues the plan with a wider partition if justified.

## Anti-Patterns

- Editing a file because "it looked related" but it is outside your partition
- Reading `ownership.lock.json` and assuming silence means "I can write here"
- Touching `shared_read_only` files (config, settings, manifests)
- Editing both your partition AND another agent's, then claiming parallel
  execution was fine because there were no merge conflicts in this run
