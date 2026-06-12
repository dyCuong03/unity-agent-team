# Architecture Pattern Detection
<!-- Detect design patterns in touched code to refine skill loading. -->

## Purpose

Architecture patterns modify which skills are relevant.
A Presenter pattern in Unity code changes skill loading even before domain scoring.
Detection is code-evidence only — not inferred from class names alone.

## Detection Rules

### Presenter Pattern

**Signals:**
- Class name ends in `Presenter`
- Has a field typed as a `View` (interface or concrete)
- Has a method like `Show()`, `Hide()`, `Refresh()`, `UpdateView()`
- Constructor or Inject receives model/data

**Confidence:** 0.85 if 3+ signals; 0.60 if 2 signals.

**Effect on skill loading:**
- Load `ui` (domain) if not already loaded
- Load `async` (advisory) for lifecycle management
- Do NOT load Burst, Jobs, scheduling skills
- Load `testability` advisory (Presenter is naturally testable)

---

### MVVM Pattern

**Signals:**
- Class name ends in `ViewModel`
- Has observable properties (ReactiveProperty, ObservableField, or event-backed fields)
- Has a `Model` dependency
- Uses data binding (VContainer, UniRx, or manual subscribe pattern)

**Confidence:** 0.80 if 3+ signals.

**Effect on skill loading:**
- Load `ui` or `uitoolkit` depending on View type
- Load `async` advisory
- Note: If using VContainer → load `asmdef` advisory (composition root required)

---

### Object Pool Pattern

**Signals:**
- Class name ends in `Pool` or contains `Pool`
- Has `Get()` / `Return()` or `Spawn()` / `Despawn()` methods
- Has a capacity field or max-size limit
- Uses `Queue<T>` or `Stack<T>` or `List<T>` as backing store

**Confidence:** 0.85 if 3+ signals.

**Effect on skill loading:**
- Load `optimization` advisory (pooling is a performance pattern)
- If DOTS domain: note that ECS entities don't need traditional pools (ECB spawn is pooled)
- If Unity domain: load standard pool guidance

---

### Factory Pattern

**Signals:**
- Class name ends in `Factory` or `Builder`
- Has `Create()` or `Build()` method
- Returns a concrete type or interface
- Takes configuration parameters

**Confidence:** 0.75 if 2+ signals.

**Effect on skill loading:**
- Minimal effect on domain
- Flag: factory often indicates complex initialization — check for Baker equivalent in DOTS code

---

### State Machine Pattern

**Signals:**
- Enum with state names (`State`, `Phase`, `Mode` suffix)
- `switch(currentState)` or `TransitionTo()` method
- Current state field + history

**Confidence:** 0.80 if 3+ signals.

**Effect on skill loading:**
- Load `patterns` advisory (state machine guidance)
- If Animator is involved: load `animator` domain skill
- Flag: state machines in DOTS are often better as enabling components — note this

---

### Dependency Injection (VContainer / Zenject)

**Signals:**
- `[Inject]` attribute on constructor or field
- `IObjectResolver` parameter
- `IContainerBuilder` in bootstrap
- `LifetimeScope` class base

**Confidence:** 0.90 if `[Inject]` found.

**Effect on skill loading:**
- Load `asmdef` advisory (DI requires careful assembly design)
- Note composition root pattern in workspace/domain-analysis.md
- DI + DOTS: valid in authoring layer, not in ISystem (ISystem has no constructor injection)

---

### Reactive Bindings (UniRx / R3)

**Signals:**
- `ReactiveProperty<T>` field
- `.Subscribe()` method calls
- `CompositeDisposable` field
- `IObservable<T>` return type

**Confidence:** 0.80 if 2+ signals.

**Effect on skill loading:**
- Load `async` advisory
- Note: Reactive bindings in hot paths cause GC — flag for tester

---

### Service Locator

**Signals:**
- Static `Instance` property (singleton)
- Static `Get<T>()` method
- Static registry dictionary

**Confidence:** 0.70 if 2+ signals.

**Effect on skill loading:**
- Load `patterns` advisory (service locator is a code smell — document alternatives)
- If in DOTS domain: note that SystemAPI.GetSingleton<T>() is the ECS equivalent

---

### Command Pattern

**Signals:**
- Interface `ICommand` with `Execute()` method
- Command queue or history
- Undo/Redo methods

**Confidence:** 0.75 if 2+ signals.

**Effect on skill loading:**
- Minimal domain effect
- In DOTS: ECB is the native command pattern — flag if custom command system found alongside ECB

---

## Pattern Detection Output Format

Example (illustrative class names — not tied to any specific project):

```markdown
## Architecture Patterns Detected
- Presenter (confidence: 0.85) — PopupPresenter.cs, InventoryPresenter.cs
- DI/VContainer (confidence: 0.90) — [Inject] found in UIManager.cs
- Object Pool (confidence: 0.70) — EnemyPool.cs (Get/Return methods)

## Pattern Effect on Skills
- Presenter → +ui, +async advisory
- DI → +asmdef advisory
- Pool → +optimization advisory
```

---

## Fallback

If no pattern is detected: no pattern-based skill adjustment. Domain scores alone drive loading.
Never invent a pattern from class names alone — require code evidence.
