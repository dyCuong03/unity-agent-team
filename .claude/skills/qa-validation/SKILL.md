---
name: qa-validation
description: Validation rules for Unity DOTS features. Use when creating tests, stress scenarios, regression coverage, reproduction steps, or release-readiness checks.
user-invocable: false
---

When validating Unity DOTS features:

- Test correctness, edge cases, failure modes, and scale limits.
- Verify baker output, component state transitions, system ordering, and entity lifecycle.
- Add stress scenarios for high entity counts, bursty spawning, despawning, and structural changes.
- Check regression risk after every fix.
- Prefer reproducible setups, measurable evidence, and concise failure reports.

Every validation pass should answer:

1. What behavior was tested?
2. Under what setup?
3. What was expected?
4. What actually happened?
5. Does the feature remain stable under stress?
6. What risks remain open?
