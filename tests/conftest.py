"""
conftest.py — shared pytest fixtures and helpers for skillhub-discovery tests.

All tests run from the repo root (unity-agent-team/). Fixtures live in
tests/fixtures/ and are intentionally bad in predictable ways.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# ── Repo root (two dirs up from this conftest) ──────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
SCRIPTS_DIR = REPO_ROOT / ".claude" / "scripts"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
REGISTRY_PATH = SKILLS_DIR / "registry.json"


def _load_module(name: str, path: Path):
    """Load a Python module by file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Lazy-loaded module references (loaded once per session by pytest).
_ROUTE_MOD = None
_PACK_MOD = None


def get_route_module():
    global _ROUTE_MOD
    if _ROUTE_MOD is None:
        _ROUTE_MOD = _load_module("route_skills", SCRIPTS_DIR / "route_skills.py")
    return _ROUTE_MOD


def get_pack_validator_module():
    global _PACK_MOD
    if _PACK_MOD is None:
        _PACK_MOD = _load_module("validate_skill_pack", SCRIPTS_DIR / "validate_skill_pack.py")
    return _PACK_MOD
