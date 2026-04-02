# Unity MCP Integration Guide

This framework is designed to operate with Unity MCP:

https://github.com/IvanMurzak/Unity-MCP

## Core Rule

ALWAYS prefer MCP over guessing project state.

Unity MCP is the primary evidence source for live Unity project context. It should be used whenever a decision depends on actual editor state, assets, scenes, serialized data, logs, tests, or runtime-observable structure.

## What Unity MCP Is Used For

Use Unity MCP for:

- reading project structure
- inspecting scenes and prefabs
- inspecting GameObjects and Components
- inspecting assets and serialized data
- debugging runtime-visible data
- analyzing authoring output and conversion results
- reading logs and editor state
- running tests and collecting results
- capturing screenshots when visual confirmation matters

Use source file reading for code logic and implementation details.
Use MCP for current Unity state and evidence.

## Mandatory Usage Policy

Every role must use Unity MCP at the points below whenever relevant.

### 1. Task Start

Before planning or implementation:

- inspect the active Unity project
- inspect relevant scenes, prefabs, assets, and scripts
- inspect packages or editor state if the task depends on them

### 2. Before Design Freeze

Architect must use MCP to confirm:

- relevant assets or scenes exist
- authoring objects and serialized data align with assumptions
- the project structure matches the design surface

### 3. Before Runtime Changes

Unity Developer must use MCP to inspect:

- the current object and component setup
- relevant assets and scripts
- logs or test failures already present

### 4. Before Tooling Decisions

Data Tool Engineer must use MCP to inspect:

- what state is already observable
- where authoring or serialized data lives
- whether the missing visibility is in assets, scene objects, logs, or test output

### 5. Before Sign-Off

Tester must use MCP to:

- run tests
- inspect logs
- confirm runtime or editor state
- gather benchmark or stress evidence

## Preferred MCP Usage By Problem Type

### Project Structure

Use MCP to discover:

- asset locations
- open scenes
- scene hierarchies
- package dependencies
- selected objects

Typical tool categories:

- asset search and asset data
- scene listing and scene data
- package listing
- editor selection and editor state

### ECS And Runtime Inspection

Use MCP to inspect:

- GameObjects used as authoring roots
- Components attached to authoring or scene objects
- serialized data on assets and objects
- debug or inspector-facing state

Typical tool categories:

- GameObject search
- component get and modify
- object data
- asset data
- reflection lookup for code surfaces when needed

### Debugging And Diagnostics

Use MCP to gather:

- console logs
- editor state
- playmode status
- screenshots
- reflection-based inspection or targeted method calls when appropriate

Typical tool categories:

- console logs
- editor application state
- game view and scene view screenshots
- reflection find and reflection call

### Validation

Use MCP to:

- execute EditMode or PlayMode tests
- clear logs before reproducing issues
- inspect failure artifacts
- confirm fixed behavior after changes

Typical tool categories:

- tests
- console clear
- console logs
- screenshots
- scene state inspection

## Role-Specific MCP Guidance

### Architect

Architect uses MCP to anchor design in real project state.

Use MCP for:

- asset and scene discovery
- existing authoring structure
- serialized configuration data
- current package and tooling availability
- runtime constraints visible from logs or tests

Architect should not invent object layout, content locations, or editor state.

### Unity Developer

Unity Developer uses MCP to verify implementation context and actual Unity-side effects.

Use MCP for:

- inspecting existing authoring objects and components
- checking serialized values after code or baker changes
- reading logs after reproduction
- validating scene or prefab setup before assuming a bug source
- checking playmode state and test output

### Data Tool Engineer

Data Tool Engineer uses MCP more heavily than any other role.

Use MCP for:

- asset and object discovery
- serialized data inspection
- debug output analysis
- editor state checks
- screenshots and reproduction support
- validation of tool impact on actual project state

### Tester / QA

Tester uses MCP to make validation evidence-based.

Use MCP for:

- test execution
- stress run setup
- failure capture
- console and screenshot evidence
- scene and object validation after reproduction

## Read-Only Before Write

Preferred sequence:

1. inspect with MCP
2. inspect source code
3. identify the real change target
4. edit
5. re-check with MCP
6. validate with tests or reproduction

Do not modify the project before understanding current state.

## Recommended MCP Decision Tree

### If the question is "what exists right now?"

Use MCP first.

Examples:

- what scenes are open
- what objects are in the hierarchy
- what serialized values are currently set
- what errors are in the console

### If the question is "how is this implemented?"

Read source first, then verify assumptions with MCP if Unity state matters.

Examples:

- how a system schedules jobs
- how a baker writes components
- how an ECB is used

### If the question is "is this actually working?"

Use MCP plus tests and logs.

Examples:

- is the scene configured correctly
- does the baker output the expected data
- do tests pass
- does playmode reproduce the issue

## Unity MCP Capability Map

Typical high-value capability groups:

- Assets: search, read serialized data, create or modify project assets
- Scenes and Prefabs: inspect hierarchy, open scenes, save scenes, inspect prefab state
- GameObjects and Components: inspect and modify object and component state
- Scripts: read, create, update, delete, execute quick C# experiments
- Console: clear logs and fetch logs
- Editor: inspect playmode, selection, and editor state
- Reflection: discover methods and call targeted utility methods when necessary
- Tests: execute EditMode or PlayMode tests
- Screenshots: capture scene or game view for visual debugging

## Anti-Patterns

Do not:

- assume a scene hierarchy from filenames alone
- assume a component exists because the code references it
- assume a baker output is correct without inspection
- assume logs are clean without reading them
- assume tests passed unless the test runner says they passed
- assume runtime visuals are correct without direct evidence when visuals matter

## Escalation Rule

If MCP evidence conflicts with code assumptions:

1. report the mismatch explicitly
2. identify whether the problem is stale assets, stale build state, wrong scene, wrong assumptions, or incorrect code
3. do not continue on a guessed explanation

## Integration Statement For All Prompts

Include this rule in all role reasoning:

"ALWAYS prefer MCP over guessing project state. Use Unity MCP to inspect the real Unity project before making design, implementation, tooling, or validation decisions."
