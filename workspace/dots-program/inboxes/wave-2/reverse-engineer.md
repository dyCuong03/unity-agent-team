# Panel 2 — Reverse Engineer — Wave 2 Assignment

You are the only panel allowed to read `EntityComponentSystemSamples`. Your output is an **evidence package** the Architect (Panel 1) consumes. You do not author skills.

## Wave 2 scope

The Architect plans to ship these 5 skills this wave:
- `dots-update-groups`
- `dots-singleton-patterns`
- `dots-transform-patterns`
- `dots-hybrid-bridge`
- `dots-event-driven-ecs`

You must produce evidence for each. **Do not read the whole repo.** Hard cap: 8 files total.

## Required reads (these exist on disk)

Mandatory:
- `E:/BuzzleStudio/BackpackAdventures/EntityComponentSystemSamples/Dots101/Entities101/Assets/HelloCube/11. FixedTimestep/` (system files inside) — for update-groups
- `E:/BuzzleStudio/BackpackAdventures/EntityComponentSystemSamples/Dots101/Entities101/Assets/HelloCube/5. Reparenting/` — for transform-patterns
- `E:/BuzzleStudio/BackpackAdventures/EntityComponentSystemSamples/Dots101/Entities101/Assets/HelloCube/12. CustomTransforms/` — for transform-patterns
- `E:/BuzzleStudio/BackpackAdventures/EntityComponentSystemSamples/Dots101/Entities101/Assets/HelloCube/7. GameObjectSync/` — for hybrid-bridge
- `E:/BuzzleStudio/BackpackAdventures/EntityComponentSystemSamples/Dots101/Entities101/Assets/HelloCube/15. UnityObjectRef/` — for hybrid-bridge

For `dots-singleton-patterns` and `dots-event-driven-ecs`, you may cross-reference Wave 1 reads (HelloCube/3.Prefabs, HelloCube/13.StateChange) without re-reading them — but you must cite which samples back each claim.

## Prior-session reference (do NOT trust verbatim)

`workspace/dots-program/inboxes/wave-2/prior-session-reports/reverse-engineer-report.md` contains a prior subagent's pattern report on the same scope. **Audit it.** For each pattern claim there:
- Mark `[CONFIRMED]` if your read supports it
- Mark `[REVISE]` with the corrected claim if it overstated/understated
- Mark `[REMOVE]` if no source evidence backs it

Do not adopt it wholesale. Your name is on the new evidence file.

## What to write

One file: `outboxes/reverse-engineer/wave-2-evidence.md`.

Format per skill:

```markdown
## <skill-name>

### Sources cited
- <relative path>:<line range> — <one line: what this fragment shows>
- (max 4 sources per skill)

### Reusable pattern
<2–4 sentences: the production-worthy pattern this evidence supports. Senior-level only. Not a tutorial.>

### Where the sample is a shortcut
<2–3 sentences: where the sample chose a demo convenience that would fail in production. Be specific (file:line). If the sample is genuinely production-quality, say "no shortcuts observed" and explain why.>

### Failure modes observed or implied
- <symptom> ← <cause>
- (3–5 bullets per skill)

### Reusability score (0.0–1.0)
<score> — <one-sentence justification>

### Open questions for the Architect
- <max 3 bullets per skill>
```

Five sections, one per target skill. Total length: ≤ 1500 lines, ideally 800–1200.

## Done condition

1. `outboxes/reverse-engineer/wave-2-evidence.md` written and committed (do not push; the coordinator pushes).
2. `touch workspace/dots-program/gates/wave-2-evidence-ready`
3. Update `workspace/dots-program/status.md` Wave 2 phase to "Reverse Engineer: complete".

## Hard rules

- ≤ 8 file reads. The 5 mandatory paths consume 5. You have 3 spares for cross-checks.
- Entities 1.x APIs only. Flag any 0.x APIs you spot (`Entities.ForEach`, `SystemBase` outside hybrid, `ISystemStateComponentData`, `Translation`/`Rotation`/`NonUniformScale`, `IConvertGameObjectToEntity`, `ConvertToEntity`) with explicit "DEPRECATED — do not propagate" notes.
- "Challenge the sample" is mandatory. Samples are learning material, not truth.
- Do NOT write SKILL.md files. Do NOT write briefs for other panels. Do NOT write into `outboxes/` other than your own.
- If you cannot find evidence for one of the 5 target skills, say so explicitly and ship the partial package — the Architect decides whether to defer.

## Communication with other panels

You don't message them directly. The Architect reads your outbox when `wave-2-evidence-ready` is touched. If you discover something that invalidates a different panel's prior assumption, write it under "Open questions for the Architect" — the Architect routes it.
