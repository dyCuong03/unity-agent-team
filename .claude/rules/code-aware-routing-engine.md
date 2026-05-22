# Code-Aware Routing Engine
<!-- Replaces task-keyword → skill routing with code-evidence-driven domain classification. -->

## Pipeline

```
Task received
     │
     ▼ Step 1
CRG Investigation
(system-mapper / code-tracer)
     │
     ▼ Step 2
Code Fingerprinting
(api-fingerprinting-system.md)
     │
     ▼ Step 3
Architecture Pattern Detection
(architecture-pattern-detection.md)
     │
     ▼ Step 4
Domain Scoring
(domain-scoring-engine.md)
     │
     ▼ Step 5
Skill Loading Decision
(routing/SKILL.md + confidence threshold)
     │
     ▼ Step 6
Write workspace/domain-analysis.md
     │
     ▼ Step 7
Spawn agents with domain-appropriate prompts
     │
     ▼ (if investigation contradicts initial domain)
Dynamic Skill Reload
(dynamic-skill-reload.md)
```

---

## Step 1 — CRG Investigation (Mandatory First Step)

**Who:** system-mapper (--feature), code-tracer (--bug), refactor-agent (--refactor)

**What:** Use code-review-graph to find:
- Touched files (trace_execution_flow, get_impact_radius)
- Related symbols (list_related_symbols, trace_callers_callees)
- Dependency chain
- Entry point

**Hard rule:** No assumptions about domain before CRG evidence. Keyword observation
is a hint, not a classification. CRG evidence overrides keyword-based domain guesses.

**Output:** File list with class names, namespaces detected (not yet scored).

---

## Step 2 — Code Fingerprinting

**Who:** code-tracer (reads touched files, extracts API evidence)

**What:** Scan touched files for API fingerprints.
See `api-fingerprinting-system.md` for the complete table.

**Process:**
```python
dots_hits = scan_for_dots_apis(touched_files)       # returns {api: weight}
unity_hits = scan_for_unity_apis(touched_files)     # returns {api: weight}
hybrid_hits = scan_for_hybrid_apis(touched_files)   # returns {api: weight}
```

**Read limit:** Max 8 files (existing CRG budget). Prioritize files in the execution path.

**Output:** Raw API hit lists with confidence weights for domain scoring.

---

## Step 3 — Architecture Pattern Detection

**Who:** code-tracer

**What:** Detect design patterns in touched code.
See `architecture-pattern-detection.md` for detection rules.

**Output:** Detected patterns (Presenter, MVVM, Factory, Pool, StateMachine, DI, etc.)

**Effect on skill loading:**
- Presenter pattern detected → load `ui` skills + async lifecycle advisory
- Object Pool detected → load `optimization` skills (pooling guidance)
- DI/VContainer detected → load `asmdef` advisory (composition root pattern)
- State Machine detected → no domain change, but flag complexity risk

---

## Step 4 — Domain Scoring

**Who:** code-tracer (writes scores to domain-analysis.md)

**What:** Calculate DOTS_score, Unity_score, Hybrid_score.
See `domain-scoring-engine.md` for the full formula.

**Decision thresholds:**
```
DOTS domain:   DOTS_score ≥ 0.70 AND DOTS_score > Unity_score + 0.20
Unity domain:  Unity_score ≥ 0.70 AND Unity_score > DOTS_score + 0.20
Hybrid domain: Hybrid_score ≥ 0.60 AND abs(DOTS_score - Unity_score) < 0.30
Ambiguous:     none of the above → [ESCALATE_ARCHITECT: domain ambiguous]
```

---

## Step 5 — Skill Loading Decision

**Who:** Orchestrator (reads domain-analysis.md)

**What:** Select skills based on dominant domain + scored modules.

```
If DOTS domain:
  Load: Layer 1 (ECS) heavy + Layer 2 (Foundation) light
  Domain skills: from DOTS side (movement, physics, netcode if detected)
  Advisory: performance, asmdef
  Skip: animator, dotween, ui, timeline (unless hybrid APIs detected)

If Unity domain:
  Load: Layer 2 (Unity Foundation) heavy + Layer 1 (ECS) light
  Domain skills: from Unity side (ui, animator, addressables-design, shadergraph, etc.)
  Advisory: architecture, async, testability
  Skip: burst, scheduling, native-containers reasoning (unless DOTS APIs detected)

If Hybrid domain:
  Load: Both Layer 1 and Layer 2 balanced
  Domain skills: from BOTH sides (ui + physics, or addressables + jobs)
  Explicit hybrid contract must be defined in workspace/design.md

If Ambiguous:
  Load: Layer 1 + Layer 2 only
  No domain skills
  Escalate to architect before spawning unity-dev
```

**Budget:** Still max 2 domain + 2 advisory per agent. Confidence threshold still ≥ 0.70.

---

## Step 6 — Write workspace/domain-analysis.md

**Who:** code-tracer / system-mapper (writes); all agents (read before starting work)

**What:** Fill all sections of the domain-analysis.md template.
See `workspace-domain-analysis.md` for format.

**Hard rule:** unity-dev and architect must read domain-analysis.md before starting.
They inherit the domain classification — they do not re-derive it.

---

## Step 7 — Spawn Agents with Domain-Appropriate Prompts

**Who:** Orchestrator

**What:** Add domain-specific reasoning instructions to each agent's prompt.

```
If DOTS domain:
  Add to unity-dev prompt: "Domain: RUNTIME ECS. Apply DOTS-first reasoning.
  ECS APIs take precedence. Avoid MonoBehaviour patterns in hot paths."

If Unity domain:
  Add to unity-dev prompt: "Domain: UNITY VIEW/AUTHORING. Apply Unity-first reasoning.
  MonoBehaviour lifecycle is appropriate. Coroutines, events, and prefab patterns are correct."

If Hybrid domain:
  Add to unity-dev prompt: "Domain: HYBRID BOUNDARY. Apply dual-stack reasoning.
  DOTS owns runtime truth. Unity owns presentation. Define the contract explicitly."
```

---

## Dynamic Reload (Step 8 — Conditional)

If investigation reveals a domain different from the initial classification:
See `dynamic-skill-reload.md`.

Action: Update workspace/domain-analysis.md with revised scores. Orchestrator
re-reads before spawning implementation agents. No re-investigation needed —
just re-scoring from the evidence now in domain-analysis.md.
