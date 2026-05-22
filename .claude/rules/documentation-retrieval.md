# Documentation Retrieval
<!-- Lightweight section-based retrieval from workspace markdown files. No vector DB. -->

## Problem

`repo-knowledge.md` grows over time. Loading the full file is token-expensive.
Agents need only the sections relevant to their current task — not everything.

## Solution

Section tags embedded in headers. Grep for matching tags. Read only matching sections.

## Section Tag Format

Every section header in `repo-knowledge.md` starts with a tag annotation:

```markdown
## [tag:popup,ui,presenter] Popup System Architecture
## [tag:ecs-health,combat] Health Component Ownership
## [tag:routing,hybrid] Domain Routing Threshold History
## [tag:navmesh,movement] NavMesh Bridge Pattern
```

Tags are comma-separated. Tags are lowercase. Tags match keywords from task text and domain.

## Retrieval Algorithm

```python
def retrieve_relevant_sections(file_path, task_text, domain, max_tokens=150):
    sections = parse_sections(file_path)  # split on ## headers
    keywords = extract_keywords(task_text) + [domain]
    scored = []

    for section in sections:
        tags = parse_tags(section.header)  # extract [tag:x,y,z]
        score = sum(1 for kw in keywords if kw.lower() in tags)
        if score > 0:
            scored.append((score, section))

    scored.sort(key=lambda x: -x[0])

    result = []
    total_tokens = 0
    for score, section in scored:
        section_tokens = estimate_tokens(section.content)
        if total_tokens + section_tokens <= max_tokens:
            result.append(section)
            total_tokens += section_tokens
        else:
            break

    return result
```

## Tag Vocabulary

Keep tags consistent. Use these canonical tags:

| Tag | Content type |
|-----|-------------|
| `popup`, `ui`, `canvas`, `presenter` | UI / view architecture |
| `ecs-health`, `ecs-combat`, `ecs-movement` | ECS-specific systems |
| `routing`, `domain`, `hybrid`, `dots`, `unity-view` | Routing and domain rules |
| `navmesh`, `physics`, `animation` | Unity domain specifics |
| `addressables`, `yooasset`, `asset-loading` | Asset management |
| `netcode`, `networking` | Networking architecture |
| `performance`, `profiler`, `burst` | Performance facts |
| `failure-pattern`, `regression` | Bug and regression knowledge |
| `ownership`, `boundary` | Ownership boundaries |
| `refactor-risk` | Refactor hazards |

## Maximum Retrieval Budget

Per agent per task: **150 tokens** from repo-knowledge.md sections.
If no section matches: return empty (do not force-load unrelated sections).

## Fallback (no tags in file)

If repo-knowledge.md does not use section tags (older installs):
- Fall back to reading the last 200 tokens of the file
- Flag: "[NOTICE] repo-knowledge.md lacks section tags — retrieval degraded"
- Architect should add tags during next session in that area

## Section Token Estimation

Rough estimate: 1 token ≈ 4 characters. A 200-character section ≈ 50 tokens.
Sections should be kept to 100–200 characters of content for efficient retrieval.
