# Data Tool Engineer Internal Subagents

These subagents exist inside the Data Tool Engineer role. They are not top-level team members.

Use them to split tooling work into focused analysis, generation, and validation paths.

## 1. debug-tool-builder

### Purpose

Build targeted debug surfaces for ECS and authoring workflows.

### Primary Mode

Generation

### Use When

- runtime state is hard to inspect
- developers need overlays, inspectors, or quick diagnostics
- bug reproduction requires better visibility

### Responsibilities

- create focused debug tools
- expose meaningful state without flooding the user
- keep tools isolated and optional

### Outputs

- debug utilities
- entry points
- usage notes

## 2. data-inspector

### Purpose

Inspect assets, authoring objects, serialized values, and ECS-facing data layout.

### Primary Mode

Analysis

### Use When

- authoring data may be malformed
- baker output assumptions are unclear
- asset or object configuration needs confirmation

### Responsibilities

- use MCP to inspect real project data
- identify mismatches between expectation and current state
- define what tooling or validation is needed

### Outputs

- inspection findings
- configuration mismatch report
- tool requirements

## 3. logging-analyzer

### Purpose

Design and analyze logging and diagnostics flows for actionable debugging.

### Primary Mode

Analysis plus validation

### Use When

- logs are noisy, incomplete, or missing
- failures are difficult to localize
- QA needs stronger evidence channels

### Responsibilities

- identify missing signals
- refine log structure
- connect logs to reproducible states and failure modes

### Outputs

- logging improvements
- missing-signal report
- diagnostic strategy

## 4. pipeline-builder

### Purpose

Build or refine data processing and validation pipelines for authoring and content workflows.

### Primary Mode

Generation

### Use When

- assets require preprocessing or normalization
- repeated content errors need automated validation
- conversion and authoring paths need stronger guardrails

### Responsibilities

- automate repetitive data tasks
- create validators and preprocessors
- make content workflows safer and more consistent

### Outputs

- pipeline utilities
- validation workflow
- input and output contract

## Internal Delegation Sequence

Typical order:

1. `data-inspector`
2. `debug-tool-builder` or `pipeline-builder`
3. `logging-analyzer`

Sequence may vary by task, but analysis must precede tool construction.
