# DOTS Skill Program — Panel Coordination Protocol

This directory is the file-based coordination substrate for the 4-panel DOTS skill program. The four panels operate as **independent Claude Code sessions** (run in tmux split panes, one per role). The coordinator role (a fifth session) routes work and verifies gates — it never writes final skills.

## The four panels

| Panel | Role | Owns | Writes to |
|---|---|---|---|
| 1 | **DOTS Architect** | ECS engineering standards, skill specs, anti-pattern catalog | `outboxes/architect/` |
| 2 | **DOTS Reverse Engineer** | Reading `EntityComponentSystemSamples`, evidence packages | `outboxes/reverse-engineer/` |
| 3 | **DOTS QA Curator** | Must-pass checklists, overlap matrices, rejection decisions | `outboxes/qa-curator/` |
| 4 | **DOTS Skill Builder** | Invokes `/skill-creator`, writes `.claude/skills/unity-dots/*/SKILL.md` | `outboxes/skill-builder/` + skill files |

A fifth role (**Coordinator**) sits in another pane (or is the human + this session) — it writes `inboxes/`, monitors `gates/`, and pushes commits. It does NOT write briefs, skills, or evidence.

## Wave lifecycle (per wave N)

```
[Coordinator]    write  inboxes/wave-N/{reverse-engineer,architect,qa-curator,skill-builder}.md
                 touch  gates/wave-N-kickoff

[Panel 2]        read   inboxes/wave-N/reverse-engineer.md
                        + EntityComponentSystemSamples (max 8 files)
                 write  outboxes/reverse-engineer/wave-N-evidence.md
                 touch  gates/wave-N-evidence-ready

[Panel 1]        read   gates/wave-N-evidence-ready  (blocks until present)
                        + outboxes/reverse-engineer/wave-N-evidence.md
                        + inboxes/wave-N/architect.md
                 write  outboxes/architect/wave-N-specs.md
                 touch  gates/wave-N-specs-ready

[Panel 3]        read   gates/wave-N-specs-ready
                        + outboxes/architect/wave-N-specs.md
                        + inboxes/wave-N/qa-curator.md
                 write  outboxes/qa-curator/wave-N-approvals.md
                 touch  gates/wave-N-qa-approved      ← OR
                 touch  gates/wave-N-qa-rejected      → loop to Panel 1

[Panel 4]        read   gates/wave-N-qa-approved
                        + outboxes/qa-curator/wave-N-approvals.md
                        + inboxes/wave-N/skill-builder.md
                 invoke /skill-creator  (mandatory; no manual SKILL.md)
                 write  .claude/skills/unity-dots/<skill>/SKILL.md  (per approved spec)
                 write  outboxes/skill-builder/wave-N-build-log.md
                 touch  gates/wave-N-skills-shipped

[Coordinator]    read   gates/wave-N-skills-shipped
                 commit + push to remote
                 write  inboxes/wave-N+1/* for next wave
```

## Gate files

Gate files are zero-byte markers. A panel checks for the upstream gate file before starting; presence = upstream done = green light.

```
gates/wave-N-kickoff           ← Coordinator → all panels (briefs ready)
gates/wave-N-evidence-ready    ← Panel 2 done
gates/wave-N-specs-ready       ← Panel 1 done
gates/wave-N-qa-approved       ← Panel 3 approved
gates/wave-N-qa-rejected       ← Panel 3 rejected (sends Panel 1 back)
gates/wave-N-skills-shipped    ← Panel 4 done
```

Recommended check command (any shell):
```sh
test -f workspace/dots-program/gates/wave-2-evidence-ready && echo READY || echo BLOCKED
```

## Hard rules (anti-collapse)

1. **No panel reads another panel's inbox.** That's the coordinator's domain.
2. **No panel writes another panel's outbox.** Single-owner per file.
3. **No panel writes SKILL.md files except Panel 4.** The other panels write only briefs/evidence/approvals into their own outbox.
4. **The Coordinator NEVER writes SKILL.md, NEVER writes briefs, NEVER writes evidence.** It writes only `inboxes/wave-N/*.md` and pushes commits.
5. **Disagreements use the rejection gate.** Panel 3 writes `wave-N-qa-rejected` with a precise reason; Panel 1 re-issues specs; the loop continues until `wave-N-qa-approved`.
6. **`/skill-creator` is mandatory in Panel 4.** No bypass. If `/skill-creator` is not loaded in Panel 4's session, Panel 4 halts and writes a blocker to its outbox; Coordinator resolves.

## Starting tmux

```sh
# In the publish package root
tmux new-session -s dots-team -d
tmux split-window -h -t dots-team
tmux split-window -v -t dots-team:0.0
tmux split-window -v -t dots-team:0.1
tmux select-layout -t dots-team tiled

# Attach
tmux attach -t dots-team

# Then in each of the 4 panes, run:
#   claude   (opens a Claude Code session in that pane)
# Each session loads ~/.claude/settings.json with CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1.
# Each pane is independent; they share nothing except the filesystem (this workspace/).
```

In each pane, the first prompt is **the wave's panel brief**: e.g.

```
Read workspace/dots-program/inboxes/wave-2/reverse-engineer.md.
That's your assignment for this session. Follow it exactly. Do not write
anything outside outboxes/reverse-engineer/. When done, touch
workspace/dots-program/gates/wave-2-evidence-ready.
```

## What lives where

```
workspace/dots-program/
├── README.md                       ← THIS FILE
├── status.md                       ← current wave, current phase, blockers
├── inboxes/
│   └── wave-N/
│       ├── reverse-engineer.md
│       ├── architect.md
│       ├── qa-curator.md
│       └── skill-builder.md
├── outboxes/
│   ├── reverse-engineer/
│   │   └── wave-N-evidence.md
│   ├── architect/
│   │   └── wave-N-specs.md
│   ├── qa-curator/
│   │   └── wave-N-approvals.md
│   └── skill-builder/
│       └── wave-N-build-log.md
├── gates/
│   ├── wave-N-kickoff
│   ├── wave-N-evidence-ready
│   ├── wave-N-specs-ready
│   ├── wave-N-qa-approved
│   ├── wave-N-qa-rejected
│   └── wave-N-skills-shipped
└── scratch/                        ← preserved non-canonical material
    └── wave-2-orchestrator-drafts/ ← prior-session synthesis (do NOT ship as-is)
```

## Coordinator status file

`status.md` is the at-a-glance state. The coordinator updates it after each gate flip:

```markdown
# DOTS Program — Status (last updated YYYY-MM-DD HH:MM)

Current wave: 2
Current phase: Reverse Engineer (awaiting evidence)
Blockers: none
Last gate flipped: wave-2-kickoff (coordinator)
Next expected gate: wave-2-evidence-ready (Panel 2)

## Waves
- Wave 1 — SHIPPED (5 skills, pre-panel-protocol)
- Wave 2 — IN FLIGHT (panel-owned redo)
- Wave 3 — BLOCKED on Wave 2
```

## Why this works

The substrate is the filesystem. The panels never talk to each other directly; they leave artifacts and gate files. The coordinator is a thin checker, not a synthesizer. If a panel goes idle, you can pick up its work in a new pane by reading its inbox and outbox. The entire program state is git-trackable.
