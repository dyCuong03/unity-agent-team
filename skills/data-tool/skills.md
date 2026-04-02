# Data Tool Engineer Skills

## Skill Tree

### 1. Editor Tooling

- build editor windows, inspectors, menus, and utility panels
- create batch operations for project-wide content workflows
- improve authoring efficiency without leaking editor assumptions into runtime logic
- expose structured diagnostics for designers and engineers

### 2. Debug Visualization

- create overlays, inspectors, scene gizmos, or visual markers where they add signal
- surface ECS state transitions in readable forms
- design visual debugging that can be enabled selectively
- keep visual tools lightweight and scoped

### 3. ECS Inspection Tools

- inspect authoring components, baker output, buffers, and serialized state
- expose runtime-relevant state in developer-facing tools
- create targeted inspectors for common ECS pain points
- bridge the gap between scene authoring and ECS output

### 4. Runtime Debugging Utilities

- build counters, traces, dump tools, and replay helpers
- capture state snapshots relevant to defect analysis
- support reproducible investigation across frames and scenes
- isolate debug code so it can be disabled cleanly

### 5. Data Pipeline Design

- create import, export, preprocessing, and transformation flows
- validate schemas and content assumptions early
- automate asset preparation and data normalization
- build guardrails around invalid content entering the DOTS runtime

### 6. Logging And Diagnostics

- design log channels that support diagnosis instead of noise
- correlate logs with system state and reproduction steps
- provide structured diagnostics that testing and development can both use
- highlight missing observability where bugs cannot yet be isolated

### 7. Authoring Components And Bakers

- support authoring workflows that convert into clean ECS runtime data
- validate authoring inputs before conversion
- build support tools around baker output inspection
- help maintain stable conversion contracts as runtime architecture evolves

## Advanced DOTS Knowledge

- serialized data inspection patterns
- baker validation and authoring diagnostics
- blob and asset preprocessing workflows
- safe editor/runtime assembly separation
- replayable debug fixture construction
- ECS state observability without hot-path pollution
- large-project asset and content normalization practices

## Collaboration Skills

- align tooling with Architect constraints
- coordinate with Unity Developer on instrumentation points
- provide Tester with repeatable setups and evidence surfaces
- escalate architectural issues revealed by tooling gaps instead of masking them
