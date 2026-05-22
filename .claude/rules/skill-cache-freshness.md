# Skill Cache Freshness
<!-- Hash-based cache invalidation for workspace/skill-cache/<module>.cache.md -->

## Problem

A cached skill summary (150 tokens) may be stale if the source SKILL.md was updated
(e.g., unity-skills updates a module, or we update a custom skill file).
Stale cache: agent uses wrong skill names, wrong DO NOT list, wrong parameter names.

## Solution

Store the SHA-256 hash of the source SKILL.md in the cache file header.
On every session start (STEP 1.5), compare current hash vs cached hash.
If different: delete the cache entry. Next agent load triggers a cache miss and fresh load.

## Cache Entry Header Format

```markdown
# <module> SKILL Cache
<!-- hash:sha256:<64-char-hex> -->
<!-- source:.claude/skills/unity-skills/skills/<module>/SKILL.md -->
<!-- written:YYYY-MM-DD by <agent> -->
...
```

## Hash Computation

```python
import hashlib, os

def compute_skill_hash(skill_path):
    if not os.path.exists(skill_path):
        return None
    with open(skill_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def is_cache_fresh(cache_path, skill_path):
    if not os.path.exists(cache_path):
        return False  # cache miss
    cached_hash = read_header_hash(cache_path)
    current_hash = compute_skill_hash(skill_path)
    return cached_hash == current_hash

def read_header_hash(cache_path):
    with open(cache_path) as f:
        for line in f:
            if line.startswith("<!-- hash:sha256:"):
                return line.strip()[len("<!-- hash:sha256:"):-4]
    return None
```

## Invalidation Protocol (STEP 1.5)

```sh
# For each cache file in workspace/skill-cache/:
for cache_file in workspace/skill-cache/*.cache.md; do
    module=$(basename "$cache_file" .cache.md)
    skill_path=".claude/skills/unity-skills/skills/$module/SKILL.md"
    if [ -f "$skill_path" ]; then
        current_hash=$(sha256sum "$skill_path" | cut -d' ' -f1)
        cached_hash=$(grep "hash:sha256:" "$cache_file" | sed 's/.*hash:sha256://;s/ -->//')
        if [ "$current_hash" != "$cached_hash" ]; then
            rm "$cache_file"
            echo "Cache invalidated: $module (hash mismatch)"
        fi
    fi
done
```

Add to STEP 1.5 workspace reset block in team.md.

## When Writing a New Cache Entry

After loading and summarizing a full SKILL.md, compute and store the hash:

```python
skill_path = f".claude/skills/unity-skills/skills/{module}/SKILL.md"
hash_value = compute_skill_hash(skill_path)

cache_content = f"""# {module} SKILL Cache
<!-- hash:sha256:{hash_value} -->
<!-- source:{skill_path} -->
<!-- written:{today} by {agent_name} -->

## Callable Skills (top 5)
{top_5_skills}

## Mode
{mode}

## Key Rules
{top_3_rules}

## DO NOT Hallucinate
{top_3_invalid_names}
"""
write(f"workspace/skill-cache/{module}.cache.md", cache_content)
```

## Fallback

If Python or shell hash computation is unavailable:
- Use file modification time as a proxy: if source SKILL.md is newer than cache file → invalidate
- This is less precise but safe (false positives = extra full loads, no false negatives)

```sh
if [ "$skill_path" -nt "$cache_file" ]; then
    rm "$cache_file"
fi
```

## Git Behavior

Cache files are session-scoped — add to `.gitignore`:
```
workspace/skill-cache/
```

Source SKILL.md files are committed — their content changes cause hash invalidation on next run.
