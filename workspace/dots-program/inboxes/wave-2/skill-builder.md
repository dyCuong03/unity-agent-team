# Panel 4 — DOTS Skill Builder — Wave 2 Assignment

You write the actual `SKILL.md` files. You are the only panel allowed to touch `.claude/skills/unity-dots/<skill-name>/SKILL.md`. You invoke `/skill-creator` — that is mandatory; no manual file authoring.

## Blocking precondition

Wait until `workspace/dots-program/gates/wave-2-qa-approved` exists. If `wave-2-qa-rejected` exists instead, stop and wait — you may not build a rejected spec.

## What to read

1. `outboxes/qa-curator/wave-2-approvals.md` — your authoritative input. Build only specs marked `APPROVED`. Skip `DEFER`/`REJECT_DUPLICATE`.
2. `outboxes/architect/wave-2-specs.md` — the actual spec content. Each section IS the contract for one skill.
3. `outboxes/reverse-engineer/wave-2-evidence.md` — pull example code from the cited sources here. Quote real snippets; don't invent.
4. Format anchors:
   - `.claude/skills/unity-dots/dots-ecb-orchestration/SKILL.md`
   - `.claude/skills/unity-dots/dots-baking-patterns/SKILL.md`
5. `.claude/skills/skill-creator/SKILL.md` — the vendored `/skill-creator` workflow. Follow it.

## `/skill-creator` invocation

In your Claude Code session, the `/skill-creator` skill MUST be loaded (check the available-skills list at session start). If it isn't:
1. Halt.
2. Write `outboxes/skill-builder/wave-2-blocker.md` with: "skill-creator not loaded; cannot proceed per mandatory tooling rule."
3. `touch workspace/dots-program/gates/wave-2-builder-blocked`
4. Coordinator resolves.

When `/skill-creator` IS loaded, invoke it once per approved skill. For each:

```
/skill-creator
```

In the resulting workflow:
- Target path: `.claude/skills/unity-dots/<skill-name>/SKILL.md`
- Source the front-matter `description` from the Architect's "Intent" + "Use when" condensed to one sentence + relevant keywords.
- Body sections (per architect spec): Intent / Use when / Avoid when / Senior pattern / (code example pulled from Reverse Engineer sources, verbatim or with minimal adaptation) / Anti-patterns / Failure modes / Runtime verification / Static verification / Performance notes / Compile safety / Entities version notes / See also.
- The eval/iterate loop in `/skill-creator` may not be runnable without Anthropic API access in your session; if so, document in your build log and ship the description-tuning step as a follow-up.

## What to write (besides the SKILL.md files themselves)

One log: `outboxes/skill-builder/wave-2-build-log.md`. Format:

```markdown
## Build log — Wave 2

### Approved skills built
- <skill-name> — wrote .claude/skills/unity-dots/<skill-name>/SKILL.md (N lines)
  - Front-matter description: <quote>
  - Code example source: <file:lines from evidence package>
  - Eval loop run: yes/no (and why)

### Skipped (per QA decision)
- <skill-name> — DEFER reason: <quote QA>

### Blockers encountered
- <list, or "none">

### Self-review
After writing each SKILL.md, I re-read the Architect's spec and re-verified:
- Every "Use when" / "Avoid when" item appears in the SKILL.md
- Every anti-pattern in the spec appears
- Every failure-mode row in the spec appears
- The static + runtime verification block is present
- No banned APIs from the spec's banned list appear in the example code

Skills where any check failed → re-authored before signing off.
```

## Done condition

1. Each approved skill has a `SKILL.md` at `.claude/skills/unity-dots/<skill-name>/SKILL.md`.
2. `outboxes/skill-builder/wave-2-build-log.md` written.
3. `touch workspace/dots-program/gates/wave-2-skills-shipped`.
4. Update `status.md` Wave 2 phase to "Skill Builder: complete; awaiting coordinator push".

## Hard rules

- You do NOT invent new skills. You build only what QA approved.
- You do NOT modify the Architect's spec mid-build. If you find the spec is wrong, write `[ESCALATE_ARCHITECT]` to your build log and stop on that skill. Coordinator routes back.
- You do NOT touch the existing Wave 1 SKILL.md files.
- You do NOT commit or push. Coordinator does that after all gates flip.
- Code examples in your SKILL.md must trace to a source citation in the evidence package. The Reverse Engineer cited file:line — use those snippets, attributed in a comment.
- Do not adopt the scratch drafts at `workspace/dots-program/scratch/wave-2-orchestrator-drafts/` as your starting point. They were synthesized by the coordinator, which violated the panel rule. Reference for format only; rewrite the content.
