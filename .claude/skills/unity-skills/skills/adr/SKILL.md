---
name: unity-adr
description: "Architecture decision record helper for Unity projects. Use when users compare options, choose between approaches, or need to lock in a design choice. Triggers: ADR, architecture decision, tradeoff, which approach, compare options, choose pattern, pros and cons, 技术选型, 方案对比, 选哪个, 设计决策, 架构决策, 优缺点对比."
platforms: [unity-editor, claude-code]
task-categories: [architecture, decision-record, documentation]
use-when: |-
  Load when designing or reviewing architecture decision record helper for unity projects. Load for design advisory guidance — does not require Unity Editor running.
do-not-use-when: |-
  Do not load as a runtime editor-automation skill — this module provides design advisory guidance only. Do not use for direct Unity Editor mutations.
metadata:
  source: https://github.com/Besty0728/Unity-Skills
  version: 1.9.2
  tier: 2

---

# Unity ADR

Use this when architecture choices may be revisited later or when multiple plausible options exist.

## Output Format

- Decision
- Context
- Options considered
- Chosen option
- Why this option won
- Consequences
- Revisit triggers

## Example Use Cases

- Coroutine vs UniTask
- Direct reference vs event-driven communication
- ScriptableObject config vs in-scene authoring
- One assembly vs multiple `asmdef`
- Runtime logic in `MonoBehaviour` vs pure C# service

## Guardrails

> **Mode**: Documentation only — no REST skills to gate; load freely under any operating mode (Approval / Auto / Bypass).

- Keep ADRs short.
- Record only decisions that materially affect code generation or architecture direction.
