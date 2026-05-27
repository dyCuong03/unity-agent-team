---
name: structural-change-cost-model
description: Choose between value mutation, enableable component toggle, and structural add/remove based on change frequency, providing the canonical decision model for ECS state transitions.
---

# Structural Change Cost Model

## Intent
Choose between value mutation, enableable component toggle, and structural add/remove based on change frequency, providing the canonical decision model for ECS state transitions.

## Use When
Designing any system that needs to change entity state. This is the architectural decision that most directly affects ECS runtime performance.

## Avoid When
There is no "avoid when" — this model applies to every state change decision in ECS.

## Senior Pattern (Decision Tree)

1. **Value mutation** (field on existing component): zero structural change, O(1) write, cheapest. Use when the state is a continuous quantity (health, position, speed) or a discrete enum field.
2. **Enableable component** (IEnableableComponent toggle): O(1) bit flip per entity, no chunk migration. Use when binary active/inactive state toggles more than once per second per entity.
3. **Structural change** (AddComponent / RemoveComponent): O(entity) chunk migrations. Use when the state change is infrequent (less than once per second per entity) AND semantic clarity from different archetypes is valuable.

## Frequency Rule
- Frequency > 1/sec per entity → value or enableable.
- Frequency 1/sec – 1/minute per entity → enableable preferred, structural acceptable.
- Frequency < 1/minute per entity → structural is fine and semantically clearest.
- When in doubt: measure. The three-mode benchmark below is the definitive reference.

## Code Template
```csharp
// VALUE — continuous state, always cheapest
public struct EnemyState : IComponentData
{
    public float Health;         // mutate directly
    public float Speed;          // mutate directly
    public EnemyBehavior Mode;   // enum field — value mutation
}

// ENABLEABLE — binary toggle, high-frequency
public struct Stunned : IComponentData, IEnableableComponent
{
    public float RemainingDuration;
}
// Toggle: enabledRef.ValueRW = false  (O(1), no chunk move)

// STRUCTURAL — infrequent semantic archetype boundary
public struct Dead : IComponentData { }
// Add: ecb.AddComponent<Dead>(entity)  (once, when entity dies)
// Natural exclusion: all AI/movement queries use .WithNone<Dead>()
```

## Anti-Patterns
- AddComponent<Dead> / RemoveComponent<Dead> every frame for thousands of enemies — massive per-frame archetype churn.
- Using structural changes for continuous numeric state (health, ammo) — these should always be plain fields.
- Using value mutation when different archetypes would allow natural query filtering — sometimes structural change is the right semantic choice; use the frequency rule to decide.

## Runtime Risks
- High-frequency structural changes on large populations: frame spikes, chunk fragmentation, GC pressure from archetype metadata reallocation.
- At 10,000 entities changing state per frame via structural change: ~80ms overhead (CPU-dependent).
- Enableable component equivalent: ~0.01ms for 10,000 entities.

## Performance Notes
- Structural change cost = entity must be copied from old chunk to new chunk + chunk metadata updates on both sides.
- Enableable component cost = 1 bit flip per entity in chunk bitmask.
- Value mutation = single cache-coherent write per entity — fastest possible.

## Architecture Guidance
The archetype boundary created by structural changes is a feature, not just a cost. Dead enemies in a separate archetype are naturally excluded from AI/movement/animation queries with zero query-time overhead. Use structural changes for state that defines "what kind of entity this is," not for state that defines "what value this entity has."

## Related Skills
[[enableable-component]], [[tag-component]], [[icomponentdata-value-component]]
