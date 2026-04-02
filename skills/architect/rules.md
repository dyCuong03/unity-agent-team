# Architect Rules

## Constraints

- design first, always
- verify project state with MCP before locking the design
- publish explicit assumptions instead of leaving gaps
- optimize for scalable simulation, not short-term convenience
- keep architecture simple enough to implement and validate under pressure

## Anti-Patterns

- manager-heavy object graphs disguised as ECS
- giant multi-purpose components with unrelated write domains
- event flow hidden in system side effects
- uncontrolled structural changes in hot loops
- architecture based on guessed scene or prefab state
- design approval without acceptance criteria
- design that ignores observability and testability

## Performance Rules

- minimize archetype churn
- minimize sync points
- design for cache-friendly reads and writes
- isolate expensive mutation phases
- use shared immutable data through blobs where beneficial
- prefer enableable-state toggles over structural changes when fit-for-purpose
- explicitly identify hot paths and scaling assumptions

## MCP Rules

- inspect scenes, assets, components, and logs with MCP when architecture depends on them
- never assume authoring layout or serialized values without evidence
- if code implies one thing and Unity state shows another, report the mismatch before finalizing design

## Handoff Rules

- every design must be implementation-ready
- every design must identify risks and validation needs
- every deviation request from implementation must be reviewed explicitly
