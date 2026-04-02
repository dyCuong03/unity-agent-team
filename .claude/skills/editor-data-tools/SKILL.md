---
name: editor-data-tools
description: Guidance for Unity data processing, editor tooling, validators, and DOTS debugging helpers. Use when building authoring workflows, diagnostics, inspectors, or developer utilities.
user-invocable: false
---

When building Unity data tools and diagnostics:

- Keep editor-only code isolated from runtime assemblies.
- Prefer tools that reduce repetitive authoring and validation work.
- Validate input data early with actionable error messages.
- Make baker output and runtime ECS state inspectable.
- Keep diagnostics cheap when disabled and explicit when enabled.
- Avoid leaking debug-only dependencies into shipping runtime code.
- Build reproducible fixtures, debug views, and tracing helpers for investigation.

Every tool should clearly define:

1. Target user
2. Inputs
3. Outputs
4. Validation behavior
5. Performance impact
6. Failure modes
