# Panel 2 — Reverse Engineer — Wave 1 Assignment

**Wave 1 scope:** HelloCube + Basic ECS Lifecycle.

**Target skills the Architect plans this wave (you produce evidence for each):**
- `ecs-fundamentals` — `IComponentData`, `ISystem` lifecycle (`OnCreate`/`OnUpdate`/`OnDestroy`), `SystemAPI`, basic queries
- `dots-update-groups` — `InitializationSystemGroup` / `SimulationSystemGroup` / `PresentationSystemGroup` / `FixedStepSimulationSystemGroup` / `VariableRateSimulationSystemGroup`; `[UpdateInGroup]` / `[UpdateBefore]` / `[UpdateAfter]` / `OrderFirst` / `OrderLast`; RateManager
- `singleton-patterns` — `RequireForUpdate<T>`, `SystemAPI.GetSingleton<T>` / `GetSingletonRW<T>` / `HasSingleton<T>` / `TryGetSingleton<T>`; bake-time vs runtime-created singletons; single-writer rule
- `entity-query-patterns` — `EntityQuery`, `SystemAPI.QueryBuilder()`, `WithAll` / `WithNone` / `WithAny`, `WithEntityAccess`, cached queries, `RequireForUpdate(query)`

## Required reads (on disk)

Anchor in `E:/BuzzleStudio/BackpackAdventures/EntityComponentSystemSamples/Dots101/Entities101/Assets/HelloCube/`. Suggested order:

1. `1. MainThread/` — baseline ISystem with no jobs
2. `2. IJobEntity/` — same logic in a job
3. `4. IJobChunk/` — chunk iteration
4. `8. CrossQuery/` — multi-query patterns (for entity-query-patterns)
5. `11. FixedTimestep/` — group selection + RateManager (for update-groups)
6. `14. ClosestTarget/` — query results consumed by another system (singleton hand-off)

Budget: 8–20 files; optimize for understanding. You may also cross-reference `EntitiesSamples/Assets/ExampleCode/ComponentsSystems.cs` if it adds production-quality patterns the HelloCube samples omit.

## Existing skills you must be aware of (Wave 1-legacy, already shipped)

These ship under `.claude/skills/unity-dots/` from a prior phase:
- `dots-baking-patterns`, `dots-ecb-orchestration`, `dots-enableable-components`, `dots-entity-lifecycle`, `dots-spawning-patterns`

If a pattern you find overlaps an already-shipped skill, **cite the overlap explicitly** in your evidence (so the Architect can declare the cross-link or split the concept). Do not re-evidence already-covered ground.

## What to write

`workspace/dots-program/outboxes/reverse-engineer/wave-1-evidence.md`. Per target skill:

```markdown
## <skill-name>

### Sources cited
- <relative path>:<line range> — <one line: what the fragment shows>
- (max 5 sources per skill)

### Reusable pattern
<2–4 sentences: production-worthy pattern. Senior-level only. Not a tutorial.>

### Where the sample is a shortcut
<2–3 sentences: where the sample takes a demo convenience that would fail in production. If genuinely production-quality, say so.>

### Failure modes observed or implied
- <symptom> ← <cause>
- (3–5 bullets per skill)

### Overlap with shipped skills
<which shipped skill (if any) this overlaps; how this differs or extends>

### Reusability score (0.0–1.0) + justification

### Open questions for the Architect (≤ 3)
```

## Done condition

1. Write the evidence file above.
2. `touch workspace/dots-program/gates/wave-1-evidence-ready`.
3. Update `workspace/dots-program/status.md` Wave 1 phase to "Reverse Engineer: complete".
4. SendMessage to the **coordinator** (whoever spawned you): one-sentence summary + the evidence file path.

## Hard rules

- Entities 1.x APIs only. Flag any 0.x: `Entities.ForEach`, `SystemBase` outside hybrid, `ISystemStateComponentData`, `Translation`/`Rotation`/`NonUniformScale`, `IConvertGameObjectToEntity`.
- "Challenge the sample" is mandatory.
- Do NOT write SKILL.md. Do NOT write briefs for other panels. Only your own outbox.
- Don't read the deferred `inboxes/wave-2/` — it's old taxonomy.
