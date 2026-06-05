# Skill Index

Human-readable view of `registry.json`. The registry is the machine source of truth;
this file is for humans. Regenerate understanding via
`python .claude/scripts/build_skill_registry.py list`.

`/team` does **not** load all skills for every agent. The skill router
(`scripts/route_skills.py`) selects a curated, role-correct subset:

```
role primary skills + domain extras + intent extras + keyword matches + agentmemory hint
→ capped at max_total_skills = 7 (role/domain/intent priority beats keyword)
```

Required intent skills are **must-keep** (survive the cap): `investigation` on a bug
and `ownership-partitioning` on refactor/parallel, for the roles that need them.

## Routable skills

| Skill (folder) | Domains | Roles | Priority | Notes |
|---|---|---|---|---|
| `agentmemory-codebase-recall` | Any | all code-reading roles | 98 | recall before reading; files win |
| `codebase-understanding` | Any | all code-reading roles | 95 | CRG-first navigation |
| `architect` | Any | architect | 100 | design / ECS boundaries |
| `unity-foundation` | Unity, Any | architect, unity-dev | 85 | asmdef, scene lifecycle |
| `unity-classic` | Unity | unity-dev, bug-investigation | 100 | MonoBehaviour/UI/DOTween/VContainer/Addressables/pooling |
| `unity-dots-best-practices` | DOTS, Hybrid | unity-dots-dev, architect, bug-investigation | 100 | ISystem/ECS/Burst/jobs |
| `unity-dots` | DOTS | unity-dots-dev | 72 | DOTS reference index — keyword-reachable, NOT a forced primary (its SKILL.md says don't load standalone) |
| `ecs-job-patterns` | DOTS, Hybrid | unity-dots-dev, bug-investigation | 92 | IJobEntity/ECB/Dependency |
| `burst-safety` | DOTS | unity-dots-dev | 90 | `[BurstCompile]` safety |
| `memory-safety` | DOTS | unity-dots-dev | 88 | NativeContainer lifetime |
| `investigation` | Any | bug-investigation | 90 | root cause (bug intent) |
| `ownership-partitioning` | Any | architect, unity-dev, unity-dots-dev, refactor-agent, data-tool | 80 | **conditional**: parallel or refactor |
| `tester` | Any | tester, verifier, qa-tester | 95 | sign-off |
| `qa-validation` | Any | tester, verifier, qa-tester | 92 | test matrix / evidence |
| `verifier` | Any | verifier | 90 | verification bundle |
| `data-tool` | Any | data-tool | 90 | editor tooling |
| `editor-data-tools` | Any | data-tool | 85 | authoring / validators |
| `triage` | Any | triage | 100 | classification |
| `unity-dev` | Unity/DOTS/Hybrid | unity-dev | 60 | role brief (auto-loaded by agent def, not routed as extra) |

## Meta-only skills (never routed into task agents)

| Skill (folder) | Reason |
|---|---|
| `routing` | the lazy router skill itself (orchestrator concept) |
| `skill-creator` | skill authoring tool |
| `unity-skills` | Unity Editor REST automation via MCP — triggered by MCP, not routing |

## Notes

- Registry keys on the **folder name**, not the SKILL.md `name:` frontmatter
  (e.g. folder `investigation` has frontmatter `name: unity-investigation`; the
  routing key is `investigation`).
- DOTS extras (`unity-dots-best-practices`, `unity-dots`, `ecs-job-patterns`,
  `burst-safety`, `memory-safety`) attach to **DOTS lanes only**. `tester`,
  `verifier`, and `data-tool` never receive DOTS skills by default.
- Validate: `python .claude/scripts/build_skill_registry.py check`
