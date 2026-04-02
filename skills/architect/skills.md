# Architect Skills

## Skill Tree

### 1. ECS Architecture Patterns

- choose between component, buffer, aspect, blob asset, singleton, and enableable-component patterns
- design phase-based simulation pipelines
- separate simulation, command intake, state transition, and presentation-adjacent flows
- model event flow using explicit data carriers instead of hidden side effects
- choose stable entity ownership boundaries across gameplay subsystems

### 2. System Decomposition

- decompose features into small systems with explicit read and write domains
- organize systems into groups and update phases
- isolate high-frequency hot loops from low-frequency orchestration
- separate authoring concerns from runtime concerns
- define which systems may create structural changes and where that cost is acceptable

### 3. Data Flow Design

- define data producers, consumers, and lifetime
- design request, command, event, and state channels across frames
- model transient versus persistent state explicitly
- eliminate ambiguous ownership and hidden cross-system coupling
- design failure-resistant handoff points between systems

### 4. Memory Layout Optimization

- pack data by access pattern instead of object identity
- choose compact components and buffers to reduce bandwidth pressure
- decide when to use blobs for shared immutable data
- avoid bloated components with unrelated write frequency
- reduce memory churn caused by transient allocations or frequent archetype changes

### 5. Cache-Friendly Design

- maximize chunk-local iteration
- minimize random access and scatter reads
- reduce write contention across jobs
- align component splitting with read frequency
- design for predictable traversal order and low cache pollution

### 6. Job Dependency Graph Design

- model read/write sets before implementation
- design job ordering to minimize sync points
- identify safe parallel domains and forced main-thread boundaries
- plan ECB playback points intentionally
- define how jobs exchange data without race-prone shortcuts

### 7. Large-Scale System Planning

- design for 100k+ entity scenarios when relevant
- plan streaming, batching, pooling, and spawn/despawn strategy
- account for data import volume and authoring workflow scale
- incorporate observability and testability as part of architecture
- define fallback strategies when performance limits are exceeded

## Advanced DOTS Knowledge

- archetype and chunk behavior
- structural-change cost modeling
- enableable components versus add/remove patterns
- dynamic buffer growth tradeoffs
- blob asset lifecycle and sharing
- baker output boundaries
- system ordering and world initialization constraints
- deterministic simulation design under jobs and parallel scheduling

## Collaboration Skills

- translate design into implementation-ready tasks
- expose observability needs to Data Tool Engineer
- define measurable test targets for Tester
- review implementation deviations and either approve or reject them with reasoning
