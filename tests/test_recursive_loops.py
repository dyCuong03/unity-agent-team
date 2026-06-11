"""
test_recursive_loops.py — verify no recursive skill discovery loops exist.

Checks:
  1. CLAUDE.md does not instruct the agent to recursively scan skill directories.
  2. Agent files do not instruct each other in circular load chains.
  3. No skill SKILL.md @-imports itself or creates a cycle through a known chain.
  4. The team.md command does not trigger re-invocation of /team from within /team.
  5. The router does not allow a skill to include itself via keyword matching.
  6. Meta skills (routing, skill-creator) are not loadable by normal task agents,
     preventing any "skill that loads skills" loop.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "scripts"))

from conftest import REPO_ROOT, SKILLS_DIR, REGISTRY_PATH

COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"

# Patterns that indicate recursive scanning of the skill directory
RECURSIVE_SCAN_PATTERNS = [
    re.compile(r"for\s+(?:skill|file|folder)\s+in\s+\.claude/skills", re.I),
    re.compile(r"glob\s*\(\s*['\"]\.claude/skills/\*\*/\*['\"]", re.I),
    re.compile(r"rglob\s*\(\s*['\"]SKILL\.md['\"]", re.I),
    re.compile(r"find\s+\.claude/skills.*-name\s+SKILL\.md.*-exec", re.I),
    re.compile(r"@\.claude/skills/\*", re.I),  # wildcard @-import
]

# Patterns for circular /team re-invocation
TEAM_REINVOKE_PATTERNS = [
    re.compile(r"/team\s+(?:bug|feature|refactor|explore)\b", re.I),
    re.compile(r"run\s+/team\b", re.I),
    re.compile(r"invoke\s+/team\b", re.I),
    re.compile(r"`/team\b", re.I),
]


# ── CLAUDE.md recursive scan check ───────────────────────────────────────────

def test_claude_md_no_recursive_skill_scan():
    """CLAUDE.md must not contain instructions to recursively scan .claude/skills/."""
    claude_md = REPO_ROOT / "CLAUDE.md"
    if not claude_md.exists():
        pytest.skip("CLAUDE.md not found")
    text = claude_md.read_text(errors="replace")
    # Strip code blocks (examples are OK)
    stripped = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    for pat in RECURSIVE_SCAN_PATTERNS:
        m = pat.search(stripped)
        assert not m, (
            f"CLAUDE.md contains recursive skill scan pattern '{pat.pattern}': "
            f"matched '{m.group(0)[:80]}'"
        )


# ── team.md command no recursive self-invocation ─────────────────────────────

def test_team_md_no_self_reinvoke_pattern():
    """team.md must not instruct spawned agents to call /team (would create loop)."""
    team_md = COMMANDS_DIR / "team.md"
    if not team_md.exists():
        pytest.skip("team.md not found")
    text = team_md.read_text(errors="replace")
    # Only look at non-example prose (strip code blocks showing user invocations)
    # We allow "/team" in headings/examples but NOT in agent prompt templates
    # Find prompt: sections and check them
    prompt_sections = re.findall(r"prompt:\s*['\"](.+?)['\"]", text, re.DOTALL)
    for ps in prompt_sections:
        for pat in TEAM_REINVOKE_PATTERNS:
            m = pat.search(ps)
            assert not m, (
                f"team.md agent prompt template contains /team re-invocation: "
                f"'{m.group(0)[:80]}'"
            )


# ── Agent files no circular skill loads ──────────────────────────────────────

def test_agent_files_no_circular_at_imports():
    """Agent files must not @-import each other in a circular chain."""
    if not AGENTS_DIR.exists():
        pytest.skip("No .claude/agents/ directory")

    # Build import map: agent -> list of @-referenced agents
    at_ref_pattern = re.compile(r"@\.claude/agents/([a-z\-]+)\.md", re.I)
    import_map: dict[str, list[str]] = {}
    for agent_md in AGENTS_DIR.glob("*.md"):
        text = agent_md.read_text(errors="replace")
        refs = at_ref_pattern.findall(text)
        import_map[agent_md.stem] = refs

    # DFS cycle detection
    def has_cycle(start: str, visited: set, path: list) -> list | None:
        if start in visited:
            return path + [start]
        if start not in import_map:
            return None
        visited = visited | {start}
        for dep in import_map[start]:
            result = has_cycle(dep, visited, path + [start])
            if result is not None:
                return result
        return None

    cycles = []
    for agent in import_map:
        cycle = has_cycle(agent, set(), [])
        if cycle:
            cycles.append(" → ".join(cycle))

    assert not cycles, f"Circular agent @-import chains detected:\n" + "\n".join(cycles)


# ── No skill self-imports ─────────────────────────────────────────────────────

def test_no_skill_self_imports():
    """No SKILL.md must @-import itself."""
    registry = json.loads(REGISTRY_PATH.read_text())
    issues = []
    for entry in registry.get("skills", []):
        path = REPO_ROOT / entry["path"]
        if not path.exists():
            continue
        text = path.read_text(errors="replace")
        # Self-import: @.claude/skills/<name>/SKILL.md appearing in its own SKILL.md
        self_ref = f"@.claude/skills/{entry['name']}/SKILL.md"
        if self_ref in text:
            issues.append(f"{entry['name']}: self-imports '{self_ref}'")
    assert not issues, "Skills self-importing:\n" + "\n".join(issues)


# ── Meta skills not loadable via routing ─────────────────────────────────────

def test_meta_skills_blocked_from_routing():
    """Routing, skill-creator meta skills must not appear in any route() output."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "route_skills", str(REPO_ROOT / ".claude" / "scripts" / "route_skills.py")
    )
    route_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(route_mod)

    meta_skills = {"routing", "skill-creator"}
    all_roles = [
        "architect", "unity-dots-dev", "unity-dev", "tester", "verifier",
        "qa-tester", "bug-investigation", "data-tool", "refactor-agent", "system-mapper",
    ]
    leaks = []
    for role in all_roles:
        for domain in ("DOTS", "Unity", "Hybrid", "Any"):
            result = route_mod.route(
                agent=role, domain=domain, intent="feature",
                task_text="routing skill creator meta load"
            )
            leaked = meta_skills & set(result)
            if leaked:
                leaks.append(f"{role}/{domain}: {sorted(leaked)}")
    assert not leaks, (
        "Meta skills leaked into routing results (would create skill-loading loops):\n"
        + "\n".join(leaks)
    )


# ── Skill keyword loop: no skill triggers itself via its own keywords ─────────

def test_no_skill_keyword_loop():
    """No skill must have keywords that match its own name (could cause re-load loop)."""
    registry = json.loads(REGISTRY_PATH.read_text())
    issues = []
    for entry in registry.get("skills", []):
        name = entry["name"]
        keywords = [kw.lower() for kw in entry.get("keywords", [])]
        if name.lower() in keywords:
            issues.append(
                f"'{name}' lists its own name as a keyword — "
                "could trigger endless keyword-match reload"
            )
    assert not issues, "Skills with self-referencing keywords:\n" + "\n".join(issues)


# ── Registry max_total_skills prevents unbounded load ────────────────────────

def test_registry_has_sane_max_total_skills():
    """max_total_skills must be set to a bounded value (1-20) to prevent unbounded loading."""
    registry = json.loads(REGISTRY_PATH.read_text())
    cap = registry.get("max_total_skills")
    assert cap is not None, "registry.json must define 'max_total_skills'"
    assert isinstance(cap, int), "max_total_skills must be an integer"
    assert 1 <= cap <= 20, (
        f"max_total_skills={cap} is outside sane range [1, 20]; "
        "too large a cap risks loading every skill on every task"
    )
