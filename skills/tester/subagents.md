# Tester / QA Internal Subagents

These subagents exist inside the Tester / QA role. They are not top-level team members.

Use them to split validation into focused planning, stressing, and evidence analysis.

## 1. test-generator

### Purpose

Generate functional, integration, and regression test scenarios from the approved design and implementation notes.

### Primary Mode

Generation

### Use When

- new systems or features need validation coverage
- a defect fix needs regression protection
- acceptance criteria must be translated into concrete checks

### Responsibilities

- derive test cases from architecture and runtime behavior
- define setup, steps, expected results, and pass criteria
- identify which tests should be automated first

### Outputs

- test matrix
- scenario list
- regression cases

## 2. stress-tester

### Purpose

Probe scale limits and instability under large workloads.

### Primary Mode

Validation

### Use When

- the feature operates on large entity counts
- performance sensitivity is high
- structural changes or buffers may scale poorly

### Responsibilities

- design high-load scenarios
- push spawn, despawn, mutation, and update volume
- capture frame-time, memory, and failure behavior

### Outputs

- stress report
- failure thresholds
- scaling observations

## 3. race-condition-detector

### Purpose

Hunt for nondeterministic and concurrency-related failures in ECS flows.

### Primary Mode

Analysis plus validation

### Use When

- jobs overlap on shared state
- failures are intermittent
- results differ across runs without input changes

### Responsibilities

- inspect likely read/write conflicts
- create repro patterns for timing-sensitive bugs
- separate race conditions from stale state or misconfiguration

### Outputs

- race-risk report
- reproduction hints
- suspected subsystem map

## 4. performance-analyzer

### Purpose

Interpret performance data and determine whether behavior is within acceptable constraints.

### Primary Mode

Analysis

### Use When

- benchmark or stress output exists
- a change claims performance improvement
- a defect is tied to frame cost or memory pressure

### Responsibilities

- compare observed cost against targets
- identify likely cost domains
- distinguish regression from baseline noise

### Outputs

- benchmark interpretation
- regression assessment
- performance sign-off recommendation

## Internal Delegation Sequence

Typical order:

1. `test-generator`
2. `stress-tester`
3. `race-condition-detector`
4. `performance-analyzer`

Sequence can vary, but final sign-off requires a validation pass, not just generated tests.
