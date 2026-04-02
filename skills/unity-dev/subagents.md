# Unity Developer Internal Subagents

These subagents exist inside the Unity Developer role. They are not top-level team members.

Use them to split implementation into focused passes for analysis, generation, and validation.

## 1. code-generator

### Purpose

Generate and refine ECS runtime code from the approved architecture.

### Primary Mode

Generation

### Use When

- creating components, systems, jobs, aspects, or bakers
- wiring new ECS flows
- refactoring runtime code into the approved design

### Responsibilities

- translate architecture into concrete ECS code
- preserve system ordering and ownership assumptions
- expose any missing implementation details

### Outputs

- runtime code changes
- implementation notes
- unresolved integration points

## 2. job-optimizer

### Purpose

Review job structure, scheduling, dependencies, and data access for performance and correctness.

### Primary Mode

Analysis plus refinement

### Use When

- jobs touch overlapping data
- the system is performance-sensitive
- sync points or main-thread work are appearing
- parallelization opportunities are unclear

### Responsibilities

- inspect read/write domains
- reduce unnecessary fences
- improve scheduling topology
- identify chunk-iteration and access-pattern issues

### Outputs

- scheduling recommendations
- dependency fixes
- hotspot notes

## 3. burst-validator

### Purpose

Validate Burst compatibility, job-safety assumptions, and hot-path suitability.

### Primary Mode

Validation

### Use When

- adding or changing performance-critical jobs
- mixing managed and unmanaged paths
- introducing math-heavy or iteration-heavy code

### Responsibilities

- flag non-Burst-friendly constructs
- isolate unavoidable managed work
- confirm hot loops remain suitable for Burst execution

### Outputs

- Burst risk report
- required code corrections
- approval or rejection for hot-path use

## 4. memory-checker

### Purpose

Validate memory behavior, NativeContainer lifetime, buffer growth, and structural-change cost.

### Primary Mode

Validation

### Use When

- using NativeContainers
- introducing buffers or temporary work arrays
- implementing spawn, despawn, or state-transition heavy logic
- dealing with large entity counts

### Responsibilities

- check allocation patterns
- check disposal ownership
- check buffer sizing and churn
- identify memory or archetype pressure risks

### Outputs

- memory-risk report
- structural-change notes
- required fixes before handoff

## Internal Delegation Sequence

Default order:

1. `code-generator`
2. `job-optimizer`
3. `burst-validator`
4. `memory-checker`

For small tasks, this sequence may collapse, but validation still occurs before handoff.
