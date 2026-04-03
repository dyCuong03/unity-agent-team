---
description: Boot the Unity DOTS agent team — parallel execution with self-correction. No blocking. All agents spawn immediately.
argument-hint: "<task> [--fast]"
---

# `/team` — Parallel Unity DOTS Agent Team

**Philosophy:** Spawn all agents immediately. Each agent works with initial assumptions and self-corrects when upstream data arrives. No agent waits on another.

**Modes:**
- `fast` (default): Architect + Unity Dev only.
- `full`: All 4 agents — parallel spawn.

---

## STEP 1: Preflight

```sh
if ! grep -q "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS.*1" ~/.claude/settings.json 2>/dev/null; then
  echo "Agent Team mode not enabled. Run:"
  echo 'mkdir -p ~/.claude && cat > ~/.claude/settings.json << '\''EOF'\'''
  echo '{"env":{"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS":"1"},"preferences":{"tmuxSplitPanes":true}}'
  echo "'EOF'"
  echo "Restart Claude Code, then run /team again."
  exit 1
fi
echo "Preflight: Agent Team mode enabled ✓"
```

---

## STEP 2: Create Team

```
TeamCreate:
  team_name:    unity-dots-team
  description:  Unity DOTS — architect, unity-dev, data-tool, tester (parallel)
  agent_type:    orchestrator
```

---

## STEP 3: Spawn All Agents in Parallel (Single Wave)

All agents receive the task simultaneously. Architect publishes design first; others proceed with assumptions and self-correct.

### Architect

```json
{
  "name": "architect",
  "team_name": "unity-dots-team",
  "subagent_type": "architect",
  "mode": "bypassPermissions",
  "prompt": [
    "@SETUP.md",
    "@skills/architect/role.md",
    "@skills/architect/skills.md",
    "@skills/architect/rules.md",
    "@skills/architect/subagents.md",
    "@architecture.md",
    "@mcp-integration.md",
    "@.claude/skills/unity-dots-best-practices/SKILL.md",
    "\nTask: $ARGUMENTS\n\nWORK IMMEDIATELY. Do not wait for other agents.",
    "Analyze the task, use MCP to inspect the Unity project, then design the ECS architecture.",
    "Publish the approved design via SendMessage to ALL teammates (unity-dev, data-tool, tester) as soon as it is ready.",
    "Design must include: scope, ECS data model, system layout, baker/authoring plan, performance constraints, acceptance criteria, open risks.",
    "After publishing, remain active to answer follow-up questions and review any design deviations flagged by other agents."
  ]
}
```

### Unity Dev

```json
{
  "name": "unity-dev",
  "team_name": "unity-dots-team",
  "subagent_type": "unity-dev",
  "mode": "bypassPermissions",
  "prompt": [
    "@SETUP.md",
    "@skills/unity-dev/role.md",
    "@skills/unity-dev/skills.md",
    "@skills/unity-dev/rules.md",
    "@skills/unity-dev/subagents.md",
    "@architecture.md",
    "@mcp-integration.md",
    "@.claude/skills/unity-dots-best-practices/SKILL.md",
    "@.claude/skills/qa-validation/SKILL.md",
    "\nTask: $ARGUMENTS\n\nWORK IMMEDIATELY. Do not wait on Architect.",
    "Start implementation from your best understanding of the task requirements.",
    "As soon as Architect's design arrives via SendMessage, reconcile it with your in-progress work and self-correct.",
    "Delegate complex code to your subagents (code-generator, job-optimizer, burst-validator, memory-checker).",
    "Surface blockers and performance risks immediately via SendMessage to team lead.",
    "On completion, SendMessage to team lead with: implemented systems, known risks, deferred items."
  ]
}
```

### Data Tool (full mode only)

```json
{
  "name": "data-tool",
  "team_name": "unity-dots-team",
  "subagent_type": "data-tool",
  "mode": "bypassPermissions",
  "prompt": [
    "@SETUP.md",
    "@skills/data-tool/role.md",
    "@skills/data-tool/skills.md",
    "@skills/data-tool/rules.md",
    "@skills/data-tool/subagents.md",
    "@architecture.md",
    "@mcp-integration.md",
    "@.claude/skills/editor-data-tools/SKILL.md",
    "@.claude/skills/qa-validation/SKILL.md",
    "\nTask: $ARGUMENTS\n\nWORK IMMEDIATELY. Do not wait on Unity Dev.",
    "Begin planning tooling based on your understanding of what instruments and diagnostics the task needs.",
    "As Unity Dev's implementation or Architect's design arrives via SendMessage, self-correct tooling scope and approach.",
    "Delegate to your subagents (debug-tool-builder, data-inspector, logging-analyzer, pipeline-builder).",
    "Do NOT silently change runtime behavior. Any tooling that touches runtime logic must be reviewed.",
    "On completion, SendMessage to team lead with: tools added, validators, diagnostics, open blind spots."
  ]
}
```

### Tester (full mode only)

```json
{
  "name": "tester",
  "team_name": "unity-dots-team",
  "subagent_type": "tester",
  "mode": "bypassPermissions",
  "prompt": [
    "@SETUP.md",
    "@skills/tester/role.md",
    "@skills/tester/skills.md",
    "@skills/tester/rules.md",
    "@skills/tester/subagents.md",
    "@architecture.md",
    "@mcp-integration.md",
    "@.claude/skills/qa-validation/SKILL.md",
    "@.claude/skills/editor-data-tools/SKILL.md",
    "\nTask: $ARGUMENTS\n\nWORK IMMEDIATELY. Do not wait on Data Tool or Unity Dev.",
    "Begin outlining the test matrix, stress scenarios, and acceptance criteria based on the task requirements.",
    "As Architect's design, Unity Dev's implementation notes, or Data Tool's tooling arrive via SendMessage, self-correct your test plan.",
    "Run tests as soon as code is available — do not wait for tooling. Use MCP for test execution and evidence capture.",
    "Delegate to your subagents (test-generator, stress-tester, race-condition-detector, performance-analyzer).",
    "Block completion if correctness or stability gates fail. Return issues to the responsible agent.",
    "On sign-off, SendMessage to team lead with: test results, stress outcomes, open defects, sign-off status."
  ]
}
```

---

## STEP 4: Create Tasks

```json
TaskCreate: { "subject": "ECS architecture design",        "status": "in_progress" }
TaskCreate: { "subject": "ECS implementation",             "status": "in_progress" }
TaskCreate: { "subject": "Tooling and diagnostics",        "status": "in_progress" }  // full mode
TaskCreate: { "subject": "Validation and QA",              "status": "in_progress" }  // full mode
TaskUpdate: { "taskId": "1", "owner": "architect" }
TaskUpdate: { "taskId": "2", "owner": "unity-dev" }
TaskUpdate: { "taskId": "3", "owner": "data-tool" }         // full mode
TaskUpdate: { "taskId": "4", "owner": "tester" }            // full mode
```

---

## Agent Self-Correction Protocol

When an agent receives upstream data (design, implementation, tooling), it must:

1. **Compare** incoming data against its current working assumptions.
2. **Identify** conflicts, gaps, or scope changes.
3. **Self-correct** — update its own plan, code, or test matrix.
4. **Log** what changed and why via SendMessage to team lead.
5. **Flag** any unresolved conflicts to the responsible upstream agent.

No agent is blocked waiting. No agent waits for a perfect upstream signal before starting.

---

## MCP Rule

**Always prefer Unity MCP** over guessing project state.
- Available: use for project inspection, ECS authoring checks, logs, and test execution.
- Unavailable: state *"Running without MCP evidence"* and fall back to source code reasoning.

---

## Quality Gates

| Gate | Rule | Enforcer |
|------|------|----------|
| G1 | Implementation matches Architect's published design; deviations escalate | Unity Dev → Architect |
| G2 | Tooling does not silently change runtime behavior | Data Tool |
| G3 | Correctness + stress evidence required for sign-off | Tester |
| G4 | No completion while regressions remain open | Tester |

---

## Completion Output Format

```
[Team: unity-dots-team] — Done

[Architect]
  <design decisions, acceptance criteria>

[Unity Dev]
  <implemented systems, self-corrections made, known risks>

[Data Tool]  ← full mode
  <tools added, validators, diagnostics>

[Tester]     ← full mode
  <test results, stress outcomes, open defects, sign-off>

Self-corrections: <list of updates made when upstream data arrived>
Open risks: <list>
Next steps: <list>
```

---

## Usage

```sh
# Fast mode — Architect + Unity Dev in parallel
/team Add a health system with damage and death states --fast

# Full mode — All 4 agents in parallel
/team Add stamina regeneration with cooldowns
```
