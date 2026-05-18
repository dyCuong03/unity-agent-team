# Hybrid Agent Architecture For Unity DOTS

This document defines the system architecture for the Unity DOTS AI Agent Team.

## Architectural Goal

Provide a reusable execution framework for Unity DOTS projects that separates design, implementation, tooling, and validation while staying grounded in real Unity project state through Unity MCP.

## Layer Model

### Layer 1: Agent Team Orchestration

The top layer is one coordinated Agent Team with exactly four roles:

1. Architect
2. Unity Developer
3. Data Tool Engineer
4. Tester / QA

This layer owns sequencing, handoffs, decision authority, and stabilization loops.

### Layer 2: Role Agents

Each role is a high-level agent with a clear boundary:

- Architect owns system design
- Unity Developer owns ECS implementation
- Data Tool Engineer owns tooling and observability
- Tester owns verification and release gating

Roles must not absorb each other's responsibilities.

### Layer 3: Internal Subagents

Each role contains internal subagents for focused execution.

Internal subagents are not extra top-level roles. They are specialized units used by a role to improve rigor and throughput.

Every role must be able to split work internally into:

- analysis
- generation or synthesis
- validation

### Layer 4: Unity MCP Tool Layer

Unity MCP is the operational interface to the live Unity project.

It provides the evidence plane for:

- reading project structure
- inspecting scenes, assets, GameObjects, and components
- checking editor state and logs
- running tests
- capturing runtime-facing observations

### Layer 5: Unity Project

The final target is the Unity project itself:

- source files
- assets
- scenes
- prefabs
- serialized data
- runtime and editor state

## Why This Hybrid Model Exists

Pure team orchestration without internal specialization tends to blur responsibilities.
Pure subagent decomposition without team roles tends to lose ownership.

This architecture keeps both:

- strong ownership at the top
- specialist execution inside each owner

That combination is important for DOTS work because architecture, low-level performance, tooling, and QA each require different judgment.

## Responsibility Matrix

### Architect

Owns:

- domain model
- ECS decomposition
- data flow
- scheduling model
- acceptance criteria
- design risk management

Does not own:

- final runtime implementation
- editor tooling implementation
- sign-off testing

### Unity Developer

Owns:

- ECS code
- systems, jobs, bakers, and data plumbing
- low-level performance tuning inside approved architecture

Does not own:

- architecture changes without approval
- QA sign-off
- tooling strategy outside direct implementation support

### Data Tool Engineer

Owns:

- editor tooling
- pipeline automation
- validators
- diagnostics
- debug visualization

Does not own:

- final gameplay architecture
- silent changes to runtime behavior
- release sign-off

### Tester / QA

Owns:

- correctness validation
- stress testing
- determinism checks
- performance evidence
- regression protection

Does not own:

- architecture design
- runtime implementation decisions
- tooling architecture except for testability requirements

## Internal Subagent Topology

Each role has fixed internal subagents.

### Architect

- `design-analyzer`
- `dependency-mapper`
- `architecture-validator`

### Unity Developer

- `code-generator`
- `job-optimizer`
- `burst-validator`
- `memory-checker`

### Data Tool Engineer

- `debug-tool-builder`
- `data-inspector`
- `logging-analyzer`
- `pipeline-builder`

### Tester / QA

- `test-generator`
- `stress-tester`
- `race-condition-detector`
- `performance-analyzer`

## Standard Execution Cycle

### Phase 1: Discovery

- gather task intent
- inspect current project state with MCP
- read relevant code and assets
- identify constraints and unknowns

### Phase 2: Design

- Architect uses internal subagents to produce a design
- design is reviewed internally before handoff
- acceptance criteria and performance targets are locked

### Phase 3: Implementation

- Unity Developer implements the design
- internal subagents analyze jobs, Burst compatibility, and memory risks
- deviations trigger escalation back to Architect

### Phase 4: Tooling And Observability

- Data Tool Engineer creates the minimal tooling needed to inspect, validate, and iterate safely
- tooling covers data pipelines, runtime state visibility, and diagnostics

### Phase 5: Validation

- Tester generates functional and stress scenarios
- Tester validates determinism, race risk, performance, and regressions
- failures return to the owning role

### Phase 6: Stabilization

- re-run the loop until all gates pass
- preserve evidence for future maintenance

## Artifact Contracts

Each phase must produce an artifact that the next phase can consume.

### Architect Artifact

- problem framing
- ECS data model
- system map
- job dependency notes
- baker and authoring strategy
- performance constraints
- acceptance criteria
- risk list

### Unity Developer Artifact

- implemented systems and data paths
- unresolved technical debt
- profiler-sensitive notes
- required debug surfaces

### Data Tool Artifact

- tooling entry points
- validators
- inspection methods
- logging channels
- known blind spots

### Tester Artifact

- test matrix
- stress results
- determinism observations
- benchmark notes
- defect list
- sign-off status

## MCP-First Decision Model

The system must not guess Unity project state when MCP can provide evidence.

Use MCP first for:

- scene and object structure
- asset and serialized data
- editor and playmode state
- logs and test results
- inspection of objects, components, and runtime-facing state

Use source reading first for:

- control flow
- algorithms
- system internals not exposed in serialized state
- code-level API usage

In practice, production work usually requires both.

## Scalability Principles

This framework is designed for large DOTS projects, not toy examples.

Scalability rules:

- keep top-level team small and stable
- shift specialization downward into subagents
- maintain strict artifact handoffs
- keep validation independent from implementation
- use MCP to reduce wrong assumptions about live project state
- prefer repeatable evidence over conversational confidence

## Failure Handling

When a failure occurs:

1. identify whether it is architectural, implementation, tooling, or validation failure
2. route it to the correct owner
3. re-run only the necessary phases
4. preserve the evidence that triggered the failure

Common routing:

- wrong system boundaries -> Architect
- incorrect job logic -> Unity Developer
- poor observability -> Data Tool Engineer
- unstable behavior under load -> Tester plus owning implementation role

## Production Readiness Criteria

This framework is production-ready only if it preserves:

- role isolation
- predictable workflow
- MCP-backed project awareness
- performance-aware DOTS design
- explicit validation gates
- repeatable stabilization loops

If any of those are missing, the framework collapses into ad-hoc prompting and should be treated as incomplete.
