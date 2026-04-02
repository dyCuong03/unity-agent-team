# Unity Developer Rules

## Constraints

- follow the approved design strictly
- verify Unity-side context with MCP before assuming scene, asset, or serialized state
- keep runtime code data-oriented and explicit
- separate authoring logic from runtime simulation
- optimize with evidence, not intuition alone

## Anti-Patterns

- monolithic systems doing unrelated work
- structural changes inside high-frequency inner loops without justification
- unmanaged NativeContainer lifetime
- dynamic buffers used as uncontrolled garbage bins
- hidden sync points caused by careless scheduling
- runtime logic that depends on editor-only assumptions
- silent architectural drift during implementation

## Performance Rules

- avoid managed allocations in hot paths
- minimize archetype churn
- keep jobs Burst-compatible whenever practical
- minimize main-thread work
- select containers and buffers based on access pattern, not habit
- avoid unnecessary random lookup patterns inside dense loops
- isolate unavoidable slow paths and document them

## MCP Rules

- inspect objects, components, assets, and logs before blaming code blindly
- re-check Unity state after changes when baker output, serialized data, or scene setup matters
- use tests and console output as evidence before declaring a fix complete

## Escalation Rules

- if implementation reveals a design conflict, stop and escalate to Architect
- if profiling exposes major design-level cost, escalate instead of patching around the root problem
- if tooling gaps block inspection, request Data Tool support explicitly
