# Architect Internal Subagents

These subagents exist inside the Architect role. They are not top-level team members.

The Architect must delegate internally when the task is non-trivial, ambiguous, performance-sensitive, or cross-system.

## 1. design-analyzer

### Purpose

Analyze requirements, inspect current project context, and convert vague feature intent into a structured ECS problem statement.

### Primary Mode

Analysis

### Use When

- requirements are underspecified
- the system spans multiple gameplay domains
- the existing Unity project state may constrain design
- the feature mixes authoring, runtime, and data-flow concerns

### Responsibilities

- identify core entities, components, and state transitions
- separate hard requirements from assumptions
- inspect relevant project state through MCP
- define the real design problem before decomposition starts

### Inputs

- user request
- relevant code
- scenes, prefabs, assets, logs, or tests via MCP

### Outputs

- clarified scope
- candidate data domains
- unresolved questions
- design assumptions

## 2. dependency-mapper

### Purpose

Map system relationships, read/write domains, job dependencies, sync points, and data lifetimes.

### Primary Mode

Analysis plus synthesis

### Use When

- multiple systems will touch overlapping data
- jobs need careful scheduling
- command buffers, buffers, or shared state cross subsystem boundaries
- ordering mistakes could cause determinism or performance issues

### Responsibilities

- build the dependency graph
- identify safe parallel regions
- mark forced synchronization edges
- flag race-prone ownership patterns

### Inputs

- clarified feature scope
- candidate component and system layout

### Outputs

- dependency map
- update-order proposal
- job safety notes
- risk hotspots

## 3. architecture-validator

### Purpose

Perform an independent architecture sanity check before handoff to implementation.

### Primary Mode

Validation

### Use When

- the design affects performance-critical paths
- entity counts may become large
- the design introduces structural changes, buffers, or multi-phase simulation
- the task must be production-ready rather than illustrative

### Responsibilities

- test the design against performance and maintainability constraints
- check for anti-patterns
- verify observability and testability are present
- ensure the design is specific enough for the next roles

### Inputs

- draft architecture
- dependency map
- known project constraints

### Outputs

- approved architecture
- requested revisions
- final risk list
- acceptance-criteria confirmation

## Internal Delegation Sequence

Default order:

1. `design-analyzer`
2. `dependency-mapper`
3. `architecture-validator`

If the task is simple, steps may be lighter, but validation is still required before handoff.
