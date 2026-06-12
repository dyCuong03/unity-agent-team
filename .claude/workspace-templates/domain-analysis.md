# Domain Analysis
<!-- SESSION-SCOPED — written by system-mapper / code-tracer / bug-investigation -->
<!-- Owner: investigation agents | Readers: architect, unity-dev, tester, data-tool -->
<!-- See .claude/docs/rules/code-aware-routing-engine.md for the full pipeline -->

## Task
<!-- Paste the /team task description here -->

## Investigation Evidence

### Touched Files (from CRG)
<!-- List files identified by trace_execution_flow / get_impact_radius -->

| File | CRG evidence | Priority |
|------|-------------|---------|
| | | High / Medium / Low |

### API Scan Results

**DOTS APIs found:**
| API | Weight | File |
|-----|--------|------|
| | | |
**DOTS_raw total:** 0.00

**Unity APIs found:**
| API | Weight | File |
|-----|--------|------|
| | | |
**Unity_raw total:** 0.00

**Hybrid APIs found:**
| API | Weight | File |
|-----|--------|------|
| | | |
**Hybrid_raw total:** 0.00

### Architecture Patterns Detected
<!-- From architecture-pattern-detection.md -->
<!-- Format: Pattern (confidence) — files found in -->

---

## Domain Classification

```
DOTS_score:  0.00   (dots_raw / 1.20)
Unity_score: 0.00   (unity_raw / 1.20)
Hybrid_score: 0.00  (hybrid_raw/1.00 + 0.5 × min(DOTS, Unity))

Dominant domain: [DOTS | Unity | Hybrid | Ambiguous]
Classification method: [threshold | leniency | escalated]
Confidence in classification: [high | medium | low]
```

**If Ambiguous:** [ESCALATE_ARCHITECT: domain ambiguous — scores: DOTS:X Unity:Y Hybrid:Z]

---

## Skills Selected

```
[SKILL_ROUTING_v2] domain:[DOTS|Unity|Hybrid] dominant_score:X
  Layer 1: unity-dots-best-practices (always)
  Layer 2: unity-foundation (always)
  Domain: [<module1>, <module2>] (scores: <s1>, <s2>)
  Advisory: [<a1>, <a2>] (scores: <a1>, <a2>)
  Dropped: [<module>(<score>) reason:<why>]
  Cache hits: [<modules>]
```

---

## Reasoning Weight

```
DOTS reasoning:  XX%
Unity reasoning: XX%
(Should sum to 100%. Hybrid: ~50/50 with explicit contract.)
```

---

## MCP Query Plan

```
Phase 1 investigation calls (READ ONLY):
1. unity_diagnose
2. [domain-specific — see domain-aware-mcp.md]
3.
4.
```

---

## Hybrid Contract (if Hybrid domain)

```
Source of truth: [DOTS component / Unity component]
Data flow: [one-way direction]
Presentation owner: [class name]
Update frequency: [every frame / on change / on event]
Write path: [only via X — never directly]
```

---

## Escalation Risk

```
Domain ambiguity: [none | low | medium | HIGH]
Ownership conflict: [none | detected: <description>]
Cross-domain complexity: [low | medium | HIGH]
Recommended escalation: [none | [ESCALATE_ARCHITECT: reason]]
```

---

## Domain Reload (if triggered)

```
## Domain Reload
Triggered by: <agent>
Previous domain: <domain> (scores: DOTS:X Unity:Y)
Revised domain: <domain> (scores: DOTS:X Unity:Y)
Reason: <API evidence that contradicted initial classification>
Skills added: <list>
Skills removed: <list>
```
