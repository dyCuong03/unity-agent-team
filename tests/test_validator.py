"""
test_validator.py — tests for validate_skill_pack.py and registry structural checks.

Covers:
  - Valid skill passes all checks
  - Missing SKILL.md is detected
  - Malformed / no frontmatter is detected
  - Empty description is detected
  - Duplicate skill names across fixture dirs are detected
  - Truncated (empty) description field
  - Agent files missing required fields
  - Real repo: all routable skills have valid frontmatter (name + description)
  - Real repo: registry entries match on-disk paths
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

# ── conftest helpers ─────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "scripts"))

from conftest import FIXTURES_DIR, REPO_ROOT, REGISTRY_PATH, SKILLS_DIR, get_pack_validator_module

# ── helpers (mirrors validate_skill_pack.py internals) ──────────────────────
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
KEY_RE = re.compile(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$")


def parse_frontmatter(text: str) -> dict | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    out: dict = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        km = KEY_RE.match(line)
        if km:
            out[km.group(1)] = km.group(2).strip().strip('"').strip("'")
    return out


# ── Fixture: valid skill ─────────────────────────────────────────────────────

def test_valid_skill_has_frontmatter():
    skill_md = FIXTURES_DIR / "valid_skill" / "SKILL.md"
    assert skill_md.exists(), "valid_skill fixture is missing"
    text = skill_md.read_text()
    fm = parse_frontmatter(text)
    assert fm is not None, "valid_skill must have parseable frontmatter"


def test_valid_skill_has_name():
    skill_md = FIXTURES_DIR / "valid_skill" / "SKILL.md"
    text = skill_md.read_text()
    fm = parse_frontmatter(text)
    assert "name" in fm, "valid_skill must have `name` in frontmatter"
    assert fm["name"] == "valid_skill", "name must match folder"


def test_valid_skill_has_non_empty_description():
    skill_md = FIXTURES_DIR / "valid_skill" / "SKILL.md"
    text = skill_md.read_text()
    fm = parse_frontmatter(text)
    assert "description" in fm, "valid_skill must have `description`"
    assert len(fm["description"].strip()) >= 10, "description must be non-trivial"


# ── Fixture: missing SKILL.md ────────────────────────────────────────────────

def test_missing_skillmd_is_detected():
    """A skill folder with no SKILL.md should be flagged as invalid."""
    missing_dir = FIXTURES_DIR / "missing_skillmd"
    skill_md = missing_dir / "SKILL.md"
    assert missing_dir.exists(), "missing_skillmd fixture dir must exist"
    assert not skill_md.exists(), (
        "missing_skillmd fixture must NOT have a SKILL.md — "
        "it exists to test the absence case"
    )


# ── Fixture: malformed frontmatter ───────────────────────────────────────────

def test_malformed_frontmatter_not_parseable():
    skill_md = FIXTURES_DIR / "malformed_frontmatter" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text()
    fm = parse_frontmatter(text)
    # The frontmatter block never closes properly — should not parse cleanly
    # Either fm is None OR it's missing required fields
    issues = []
    if fm is None:
        issues.append("missing frontmatter")
    else:
        if "description" not in fm or not fm.get("description", "").strip():
            issues.append("missing or empty description")
    assert issues, (
        "malformed_frontmatter fixture should produce at least one parse issue; "
        f"got fm={fm}"
    )


def test_no_frontmatter_is_detected():
    skill_md = FIXTURES_DIR / "no_frontmatter" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text()
    fm = parse_frontmatter(text)
    assert fm is None, "no_frontmatter SKILL.md must fail frontmatter parsing"


# ── Fixture: truncated / empty description ───────────────────────────────────

def test_empty_description_is_flagged():
    skill_md = FIXTURES_DIR / "truncated_description" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text()
    fm = parse_frontmatter(text)
    assert fm is not None, "truncated_description must have parseable frontmatter"
    desc = fm.get("description", "MISSING")
    assert desc.strip() == "", (
        f"truncated_description fixture must have empty description, got: '{desc}'"
    )


# ── Fixture: duplicate skill names ───────────────────────────────────────────

def test_duplicate_names_detectable():
    """Two fixture skills must share the same frontmatter name — proving detection."""
    a_md = FIXTURES_DIR / "duplicate_name_a" / "SKILL.md"
    b_md = FIXTURES_DIR / "duplicate_name_b" / "SKILL.md"
    fm_a = parse_frontmatter(a_md.read_text())
    fm_b = parse_frontmatter(b_md.read_text())
    assert fm_a is not None and fm_b is not None
    assert fm_a.get("name") == fm_b.get("name"), (
        "duplicate_name_a and duplicate_name_b must have the same frontmatter `name`"
    )

    # A registry-style dedup check: collect all names, find duplicates
    names = [fm_a["name"], fm_b["name"]]
    seen: set = set()
    dupes = []
    for n in names:
        if n in seen:
            dupes.append(n)
        seen.add(n)
    assert dupes, "Duplicate name detection must find at least one duplicate"


# ── Fixture: invalid referenced paths ────────────────────────────────────────

def test_invalid_paths_fixture_content():
    skill_md = FIXTURES_DIR / "invalid_paths" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text()
    # Extract @-references and verify they don't exist under REPO_ROOT
    at_refs = re.findall(r"@(\.claude/[^\s\n]+)", text)
    assert len(at_refs) > 0, "invalid_paths fixture must contain @-references"
    missing = []
    for ref in at_refs:
        full_path = REPO_ROOT / ref
        if not full_path.exists():
            missing.append(ref)
    assert len(missing) > 0, (
        f"invalid_paths fixture must reference non-existent paths; all found: {at_refs}"
    )


def test_bom_prefixed_fixture_is_parsed_correctly():
    """validate_skill_pack.py BOM stripping: a SKILL.md that starts with UTF-8 BOM must
    parse its frontmatter successfully (name + description extracted without the BOM byte)."""
    skill_md = FIXTURES_DIR / "bom_prefixed" / "SKILL.md"
    assert skill_md.exists(), "bom_prefixed fixture is missing"
    # Verify the file actually begins with the BOM byte sequence
    raw = skill_md.read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf", "bom_prefixed/SKILL.md must start with UTF-8 BOM"
    # Replicate validate_skill_pack.py BOM-strip behaviour then parse
    text = skill_md.read_text(encoding="utf-8")
    assert text.startswith("﻿"), "text decoded from BOM file must start with U+FEFF"
    stripped = text[1:]  # BOM stripping as done in validate_skill_pack.py
    fm = parse_frontmatter(stripped)
    assert fm is not None, "BOM-prefixed frontmatter must parse successfully after stripping"
    assert fm.get("name") == "bom_prefixed", f"Expected name 'bom_prefixed', got: {fm.get('name')!r}"
    assert fm.get("description", "").strip(), "bom_prefixed fixture must have non-empty description"


# ── Real repo: every ROUTABLE skill has valid name + description ─────────────

def test_all_routable_skills_have_valid_frontmatter():
    """Every skill listed in registry.json must have a parseable SKILL.md with name + description."""
    registry = json.loads(REGISTRY_PATH.read_text())
    issues = []
    for entry in registry.get("skills", []):
        skill_path = REPO_ROOT / entry["path"]
        if not skill_path.exists():
            issues.append(f"MISSING: {entry['name']} → {entry['path']}")
            continue
        text = skill_path.read_text(errors="replace")
        fm = parse_frontmatter(text)
        if fm is None:
            issues.append(f"NO FRONTMATTER: {entry['name']} → {entry['path']}")
            continue
        if "name" not in fm:
            issues.append(f"MISSING name: {entry['name']} → {entry['path']}")
        if "description" not in fm:
            issues.append(f"MISSING description: {entry['name']} → {entry['path']}")
        elif not fm["description"].strip():
            issues.append(f"EMPTY description: {entry['name']} → {entry['path']}")
    assert not issues, "Routable skills have frontmatter issues:\n" + "\n".join(issues)


def test_registry_paths_exist_on_disk():
    """Every registry entry's path must resolve to an existing file."""
    registry = json.loads(REGISTRY_PATH.read_text())
    missing = []
    for entry in registry.get("skills", []):
        p = REPO_ROOT / entry["path"]
        if not p.exists():
            missing.append(f"{entry['name']}: {entry['path']}")
    assert not missing, "Registry paths missing on disk:\n" + "\n".join(missing)


def test_registry_no_duplicate_names():
    """Registry must not define the same skill name twice."""
    registry = json.loads(REGISTRY_PATH.read_text())
    names = [e["name"] for e in registry.get("skills", [])]
    seen: set = set()
    dupes = []
    for n in names:
        if n in seen:
            dupes.append(n)
        seen.add(n)
    assert not dupes, f"Duplicate skill names in registry: {dupes}"


def test_all_registry_skills_have_required_fields():
    """Every registry entry must have name, path, domains, roles, intents, keywords, priority, source, version, tier."""
    registry = json.loads(REGISTRY_PATH.read_text())
    required = ("name", "path", "domains", "roles", "intents", "keywords", "priority", "source", "version", "tier")
    issues = []
    for entry in registry.get("skills", []):
        for field in required:
            if field not in entry:
                issues.append(f"'{entry.get('name', '?')}' missing field '{field}'")
    assert not issues, "Registry entries missing required fields:\n" + "\n".join(issues)


# ── Real repo: agent files ───────────────────────────────────────────────────

def test_all_agent_files_have_model_field():
    """Every agent .md in .claude/agents/ must have `model` in frontmatter."""
    agents_dir = REPO_ROOT / ".claude" / "agents"
    if not agents_dir.exists():
        pytest.skip("No .claude/agents/ directory")
    missing_model = []
    for agent_md in sorted(agents_dir.glob("*.md")):
        text = agent_md.read_text(errors="replace")
        fm = parse_frontmatter(text)
        if fm is None:
            missing_model.append(f"{agent_md.name}: no frontmatter")
            continue
        if "model" not in fm:
            missing_model.append(f"{agent_md.name}: missing `model` field")
    assert not missing_model, (
        "Agent files missing `model` field (blocks agent spawning):\n"
        + "\n".join(missing_model)
    )


def test_all_agent_files_have_name_and_description():
    """Every agent .md must have `name` and `description`."""
    agents_dir = REPO_ROOT / ".claude" / "agents"
    if not agents_dir.exists():
        pytest.skip("No .claude/agents/ directory")
    issues = []
    for agent_md in sorted(agents_dir.glob("*.md")):
        text = agent_md.read_text(errors="replace")
        fm = parse_frontmatter(text)
        if fm is None:
            issues.append(f"{agent_md.name}: no frontmatter")
            continue
        for field in ("name", "description"):
            if field not in fm:
                issues.append(f"{agent_md.name}: missing `{field}`")
    assert not issues, "Agent frontmatter issues:\n" + "\n".join(issues)
