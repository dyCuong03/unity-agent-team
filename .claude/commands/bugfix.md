---
description: Bug-fix workflow — alias for /team --bug. Use this or /team <task> --bug interchangeably.
argument-hint: "<bug description>"
---

# `/bugfix` — Bug Fix (alias for `/team --bug`)

This command is a named alias. It runs the identical flow as `/team $ARGUMENTS --bug`.

Use whichever form you prefer:
```sh
/bugfix Enemies stop chasing after teleport
# identical to:
/team Enemies stop chasing after teleport --bug
```

**Flow:** See `.claude/commands/team.md` → Mode: `--bug` for the full specification.

**Summary:**
1. `bug-investigation` (sequential, wait) — memory recall → CRG root cause → fix strategy
2. `unity-dev` + `tester` (parallel) — fix with compilation gate / baseline test
3. Tester sign-off (sequential) — fail-before/pass-after evidence required
