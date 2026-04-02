# Unity Developer Skills

## Skill Tree

### 1. `ISystem`, `IJobEntity`, and `SystemAPI` Mastery

- design lean `ISystem` lifecycles
- use `SystemAPI` for singleton access, queries, lookups, and time data with clear intent
- choose between `IJobEntity`, `IJobChunk`, and direct update logic based on access patterns and control needs
- manage dependencies explicitly when multiple jobs and write domains overlap
- use system state responsibly without turning systems into hidden object containers

### 2. Burst Optimization

- write Burst-friendly math and control flow
- avoid managed references, virtual dispatch, and unsupported constructs in hot paths
- reduce branch noise and unnecessary scalar work
- structure data and jobs so Burst can optimize predictable loops
- isolate unavoidable non-Burst work from hot simulation phases

### 3. NativeContainer Usage

- choose between `NativeArray`, `NativeList`, `NativeHashMap`, `NativeParallelHashMap`, `NativeQueue`, and other containers based on concurrency and access behavior
- manage allocator choice and disposal lifetime correctly
- prevent container aliasing and ownership confusion across jobs
- reduce per-frame allocation churn
- expose intermediate data structures only when they materially improve performance or clarity

### 4. DynamicBuffer Patterns

- design buffers for variable-size entity state
- keep buffer elements compact and purpose-specific
- manage append, clear, and consume patterns without uncontrolled growth
- use buffers as explicit event or command channels when appropriate
- avoid buffer abuse where simple components or blobs would be more stable

### 5. EntityCommandBuffer Usage

- batch structural changes intentionally
- select playback timing that matches ownership and ordering requirements
- use parallel writers safely
- avoid excessive ECB fragmentation and accidental command storms
- distinguish immediate-state toggles from true structural mutation

### 6. Job Scheduling

- schedule jobs according to read/write domains and sync cost
- maximize safe parallel work
- minimize main-thread fences
- use chunk-friendly iteration and data prefetch logic where useful
- track dependency chains so performance problems remain explainable

### 7. Structural Change Optimization

- reduce add/remove churn in hot loops
- prefer enableable components when semantics fit
- batch spawn, despawn, and archetype transitions
- separate mutation phases from heavy compute phases
- design entity lifecycle with stable states rather than chaotic transitions

## Advanced DOTS Knowledge

- aspects and lookup patterns
- baker design and authoring conversion
- blob asset construction and consumption
- chunk iteration cost and query selectivity
- change filtering and incremental update patterns
- fixed-step versus variable-step simulation boundaries
- race-safe parallel write patterns
- memory-local data transformation pipelines

## Collaboration Skills

- implement strictly from the design or escalate
- expose hooks and observability points needed by Data Tool Engineer
- give Tester deterministic repro paths and expected state transitions
- report tradeoffs in terms of frame cost, memory, structural changes, and sync points
