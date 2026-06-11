---
name: unity-script-roles
description: "Script role planner for Unity. Use when users want to decide class responsibilities — which should be MonoBehaviour, ScriptableObject, pure C# service, or installer. Triggers: script roles, class roles, what should be MonoBehaviour, service class, presenter, installer, responsibility, 脚本职责, 类的职责, 用MonoBehaviour还是纯C#, 怎么分类, 职责划分."
platforms: [unity-editor, claude-code]
task-categories: [scripting, architecture, design-advisory]
use-when: |-
  Load when designing or reviewing script role planner for unity. Load for design advisory guidance — does not require Unity Editor running.
do-not-use-when: |-
  Do not load as a runtime editor-automation skill — this module provides design advisory guidance only. Do not use for direct Unity Editor mutations.
metadata:
  source: https://github.com/Besty0728/Unity-Skills
  version: 1.9.2
  tier: 2

---

# Unity Script Roles

Use this skill before creating a batch of gameplay scripts.

## Goal

Turn a rough script list into explicit roles so AI does not generate everything as `MonoBehaviour`.

## Output Format

- Script name
- Recommended role
- Main responsibility
- Main dependencies
- Why this role fits better than the alternatives

## Common Roles

- `MonoBehaviour` bridge
- `ScriptableObject` config/data
- pure C# domain/service
- presenter / controller
- state / state machine node
- installer / bootstrap helper

## Guardrails

> **Mode**: Documentation only — no REST skills to gate; load freely under any operating mode (Approval / Auto / Bypass).

- Do not make every class a `MonoBehaviour`.
- Do not force `ScriptableObject` onto runtime state that should stay in memory-only objects.
