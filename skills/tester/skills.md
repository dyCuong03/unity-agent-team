# Tester / QA Skills

## Skill Tree

### 1. ECS Testing Strategy

- derive tests from architecture acceptance criteria
- cover system ordering, state transitions, conversion behavior, and data integrity
- build unit, integration, and scenario-level coverage where each adds value
- identify which failures need deterministic fixtures versus stochastic stress runs

### 2. Stress Testing

- design 100k+ entity scenarios when scale is relevant
- test spawn, despawn, buffer growth, and command pressure under load
- detect frame-time collapse and memory instability
- compare expected scaling behavior against actual results

### 3. Determinism Validation

- validate repeatability under fixed inputs and seeds
- inspect cross-frame state progression for nondeterministic drift
- test ordering-sensitive logic and event timing
- identify when floating-point, scheduling, or race conditions break expectations

### 4. Race Condition Detection

- identify overlapping read/write domains
- probe job interactions likely to produce non-repeatable results
- use targeted repro patterns for intermittent failures
- distinguish true race conditions from stale state or setup errors

### 5. Performance Benchmarking

- measure frame cost, memory behavior, and throughput under realistic loads
- build repeatable benchmark scenarios
- separate cold-start noise from steady-state cost
- identify whether the issue is algorithmic, scheduling, memory, or structural

### 6. Regression Testing

- convert defect fixes into repeatable coverage
- preserve failure setups for future validation
- verify tool-assisted and data-assisted workflows remain stable
- ensure fixes do not reopen adjacent defects

## Advanced DOTS Knowledge

- DOTS conversion and baker validation
- entity lifecycle edge cases
- buffer and ECB stress behavior
- job-order and sync-point failure modes
- deterministic test harness design
- performance behavior at large entity counts
- memory and allocation regression indicators

## Collaboration Skills

- derive validation targets from Architect criteria
- request debug surfaces and tooling where observability is insufficient
- use Unity Developer repro notes to isolate failure domains
- escalate untestable or underspecified behavior instead of papering over it
