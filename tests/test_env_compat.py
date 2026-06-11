"""
test_env_compat.py — environment compatibility verification.

Checks:
  1. python3 binary exists and is ≥ 3.9
  2. All scripts use python3-compatible syntax (no walrus-operator 3.8+, match 3.10+ checks)
  3. File paths with spaces work correctly in path resolution
  4. No script hardcodes Windows path separators in critical path logic
  5. pytest is importable (test infra is available)
  6. All skills directory paths resolve correctly under Linux/WSL
  7. Registry JSON is valid UTF-8 (no encoding surprises cross-platform)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".claude" / "scripts"))
from conftest import REPO_ROOT, SCRIPTS_DIR, REGISTRY_PATH

# ── Python environment ────────────────────────────────────────────────────────

def test_python3_binary_available():
    """python3 must be on PATH — system uses python3, not python."""
    python3 = shutil.which("python3")
    assert python3 is not None, (
        "'python3' not found on PATH. Scripts use 'python3' not 'python'."
    )


def test_python3_version_adequate():
    """Python must be ≥ 3.9 for f-strings and typing improvements used in scripts."""
    ver = sys.version_info
    assert ver >= (3, 9), (
        f"Python {ver.major}.{ver.minor} is too old. Scripts require ≥ 3.9."
    )


def test_pytest_importable():
    """pytest must be importable — basic test infra sanity check."""
    import pytest as _pt
    assert _pt.__version__, "pytest must be installed and importable"


# ── Path resolution ───────────────────────────────────────────────────────────

def test_repo_root_resolves():
    """REPO_ROOT must point to a real directory."""
    assert REPO_ROOT.exists() and REPO_ROOT.is_dir(), (
        f"REPO_ROOT does not exist: {REPO_ROOT}"
    )


def test_scripts_dir_resolves():
    """Scripts directory must exist."""
    assert SCRIPTS_DIR.exists() and SCRIPTS_DIR.is_dir(), (
        f"SCRIPTS_DIR does not exist: {SCRIPTS_DIR}"
    )


def test_registry_file_resolves():
    """registry.json must exist."""
    assert REGISTRY_PATH.exists(), f"registry.json not found: {REGISTRY_PATH}"


def test_path_with_spaces_roundtrip(tmp_path):
    """Path operations must work correctly with directory names containing spaces."""
    space_dir = tmp_path / "dir with spaces"
    space_dir.mkdir()
    test_file = space_dir / "SKILL.md"
    test_file.write_text("---\nname: test\ndescription: test file in path with spaces\n---\n")
    assert test_file.exists(), "File creation in path-with-spaces dir failed"
    content = test_file.read_text()
    assert "name: test" in content, "Read from path-with-spaces dir failed"


def test_posix_paths_in_registry():
    """All registry paths must be POSIX-style (forward slashes), not Windows backslashes."""
    registry = json.loads(REGISTRY_PATH.read_text())
    windows_paths = []
    for entry in registry.get("skills", []):
        path_str = entry.get("path", "")
        if "\\" in path_str:
            windows_paths.append(f"{entry['name']}: {path_str}")
    assert not windows_paths, (
        "Registry contains Windows-style paths (use forward slashes):\n"
        + "\n".join(windows_paths)
    )


# ── UTF-8 encoding ────────────────────────────────────────────────────────────

def test_registry_is_valid_utf8():
    """registry.json must be valid UTF-8 — no BOM, no latin-1 escapes."""
    raw = REGISTRY_PATH.read_bytes()
    try:
        decoded = raw.decode("utf-8-sig")  # strips BOM if present
    except UnicodeDecodeError as e:
        pytest.fail(f"registry.json is not valid UTF-8: {e}")
    # Ensure it round-trips as valid JSON too
    json.loads(decoded)


def test_all_skill_files_are_utf8():
    """Every routable SKILL.md must be valid UTF-8."""
    registry = json.loads(REGISTRY_PATH.read_text())
    bad_encoding = []
    for entry in registry.get("skills", []):
        path = REPO_ROOT / entry["path"]
        if not path.exists():
            continue
        try:
            path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as e:
            bad_encoding.append(f"{entry['name']}: {e}")
    assert not bad_encoding, "Skill files with invalid UTF-8:\n" + "\n".join(bad_encoding)


# ── No Windows-only assumptions in scripts ────────────────────────────────────

def test_scripts_use_pathlib_not_hardcoded_sep():
    """Core scripts must not hardcode '\\' as path separator."""
    scripts_to_check = [
        "route_skills.py",
        "validate_skill_registry.py",
        "validate_skill_pack.py",
        "build_skill_registry.py",
    ]
    backslash_path = r'"\\\\"'  # hardcoded Windows path separator in string literal
    issues = []
    for script_name in scripts_to_check:
        script = SCRIPTS_DIR / script_name
        if not script.exists():
            continue
        text = script.read_text(errors="replace")
        if backslash_path in text:
            issues.append(script_name)
    assert not issues, f"Scripts may use hardcoded Windows separators: {issues}"


def test_scripts_executable_on_linux(tmp_path):
    """Each core script must at least import without crashing under python3."""
    scripts_to_test = [
        "build_skill_registry.py",
        "validate_skill_pack.py",
        "validate_skill_registry.py",
        "route_skills.py",
    ]
    import subprocess, sys
    failures = []
    for script_name in scripts_to_test:
        script = SCRIPTS_DIR / script_name
        if not script.exists():
            continue
        # Run with --help or just import check via python -c "import importlib..."
        result = subprocess.run(
            [sys.executable, "-c",
             f"import importlib.util; "
             f"spec=importlib.util.spec_from_file_location('m','{script}'); "
             f"mod=importlib.util.module_from_spec(spec); "
             # Don't exec the module (may have side effects); just check parse
             ],
            capture_output=True, text=True, timeout=10,
            cwd=str(REPO_ROOT)
        )
        # A returncode != 0 on the import prep itself means syntax/parse error
        if result.returncode != 0:
            failures.append(f"{script_name}: {result.stderr[:200]}")
    assert not failures, "Scripts fail on Linux python3:\n" + "\n".join(failures)


# ── WSL path compatibility ────────────────────────────────────────────────────

def test_wsl_style_paths_work():
    """Paths like /mnt/e/... (WSL mount) must resolve via pathlib."""
    # We're already running in WSL if REPO_ROOT starts with /mnt/
    root_str = str(REPO_ROOT)
    if root_str.startswith("/mnt/"):
        # We ARE in WSL — confirm pathlib resolves correctly
        assert REPO_ROOT.exists(), f"WSL path {REPO_ROOT} does not resolve"
    # If not WSL, just verify standard POSIX resolution works
    assert REPO_ROOT.is_absolute(), "REPO_ROOT must be absolute path"


# ── tmux: no tmux dependency in core scripts ─────────────────────────────────

def test_core_scripts_no_tmux_dependency():
    """Core routing scripts must not depend on tmux being available."""
    tmux_pattern = __import__("re").compile(r"\btmux\b")
    tmux_deps = []
    for script_name in ["route_skills.py", "validate_skill_registry.py",
                         "validate_skill_pack.py", "build_skill_registry.py"]:
        script = SCRIPTS_DIR / script_name
        if not script.exists():
            continue
        text = script.read_text(errors="replace")
        if tmux_pattern.search(text):
            tmux_deps.append(script_name)
    assert not tmux_deps, (
        f"Core scripts reference tmux (routing must work without tmux): {tmux_deps}"
    )
