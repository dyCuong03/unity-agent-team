# ECS Component & System Registry
<!-- PERSISTENT — do not delete. Architect maintains this. -->
<!-- Owner: architect | Readable by: all agents -->
<!-- Last updated: [DATESTAMP] -->

## Purpose

Single source of truth for ECS ownership. Any agent designing or implementing
must check this registry first to avoid duplicate components, conflicting writers,
and archetype collisions.

---

## Component Registry

| Component | Assembly | Owner System | Writers | Readers | Notes |
|-----------|----------|-------------|---------|---------|-------|
| | | | | | |

---

## System Registry

| System | Group | UpdateAfter | UpdateBefore | Reads | Writes | Burst | Notes |
|--------|-------|-------------|-------------|-------|--------|-------|-------|
| | | | | | | | |

---

## Archetype Hotspots

<!-- Components frequently added/removed in hot loops — flag for ECS safety review -->

| Entity type | Volatile components | System responsible | Risk level |
|------------|--------------------|--------------------|------------|
| | | | |

---

## Ownership Rules

<!-- Explicit rules about what system owns what data -->
<!-- Format: [DATE] Rule: <system> owns <component>. Reason: <why>. -->
