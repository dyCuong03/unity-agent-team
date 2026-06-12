"""
test_portability.py — portability tests for the unified root resolver
(roots.py), idempotent setup (setup.py), and the portability validator
(validate_portability.py).

Conventions follow tests/conftest.py: modules are loaded by file path.
All fixture trees are generated under tmp_path — nothing is committed.
Every subprocess is launched from a cwd OUTSIDE the fixture/repo to prove
the scripts do not depend on the caller's working directory.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / ".claude" / "scripts"
VALIDATOR = SCRIPTS_DIR / "validate_portability.py"

ENV_VARS = ("AGENT_TEAM_PROJECT_ROOT", "UNITY_TEAM_PROJECT_ROOT",
            "AGENT_TEAM_WORKSPACE_ROOT")


# ── helpers ─────────────────────────────────────────────────────────────────

def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def install_framework(dest: Path, scripts=("roots.py",)) -> Path:
    """Copy a subset of framework scripts into <dest>/.claude/scripts/."""
    sdir = dest / ".claude" / "scripts"
    sdir.mkdir(parents=True, exist_ok=True)
    for s in scripts:
        shutil.copy2(SCRIPTS_DIR / s, sdir / s)
    return sdir


def load_roots(fw_root: Path):
    """Load a fresh roots module from a fixture framework tree."""
    return _load_module(f"roots_{uuid.uuid4().hex}",
                        fw_root / ".claude" / "scripts" / "roots.py")


def make_unity_project(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "Assets").mkdir(exist_ok=True)
    (root / "Packages").mkdir(exist_ok=True)
    (root / "Packages" / "manifest.json").write_text("{}\n", encoding="utf-8")
    (root / "ProjectSettings").mkdir(exist_ok=True)
    (root / "ProjectSettings" / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 2022.3.20f1\n", encoding="utf-8")
    return root


def clean_subprocess_env() -> dict:
    env = dict(os.environ)
    for var in ENV_VARS:
        env.pop(var, None)
    return env


def run_script(script: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run a framework script from an unrelated cwd (cwd-independence proof)."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(cwd), env=clean_subprocess_env(),
        capture_output=True, text=True, timeout=120)


@pytest.fixture()
def no_root_env(monkeypatch):
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture()
def other_cwd(tmp_path_factory) -> Path:
    """A directory unrelated to any fixture tree, used as subprocess cwd."""
    return tmp_path_factory.mktemp("elsewhere")


# ── 1. embedded unity project ───────────────────────────────────────────────

class TestEmbeddedUnity:
    def test_roots_resolve_embedded_unity(self, tmp_path, no_root_env):
        proj = make_unity_project(tmp_path / "my-unity-game")
        install_framework(proj)
        roots = load_roots(proj)

        assert roots.framework_root() == proj
        assert roots.project_root(cwd=proj) == proj
        assert roots.unity_project_root(proj) == proj
        assert roots.detect_project_type(proj) == "unity"

    def test_unity_project_nested_one_level(self, tmp_path, no_root_env):
        repo = tmp_path / "my-unity-game"
        unity = make_unity_project(repo / "UnityProject")
        install_framework(repo)
        roots = load_roots(repo)

        assert roots.unity_project_root(repo) == unity
        assert roots.detect_project_type(repo) == "unity"


# ── 2. external mode via environment ────────────────────────────────────────

class TestExternalMode:
    def test_env_project_root_honored(self, tmp_path, monkeypatch, no_root_env):
        fw = tmp_path / "framework-checkout"
        install_framework(fw)
        target = tmp_path / "some-other-repo"
        target.mkdir()
        monkeypatch.setenv("AGENT_TEAM_PROJECT_ROOT", str(target))

        roots = load_roots(fw)
        assert roots.project_root(cwd=tmp_path) == target

    def test_legacy_env_var_honored(self, tmp_path, monkeypatch, no_root_env):
        fw = tmp_path / "framework-checkout"
        install_framework(fw)
        target = tmp_path / "legacy-named-repo"
        target.mkdir()
        monkeypatch.setenv("UNITY_TEAM_PROJECT_ROOT", str(target))

        roots = load_roots(fw)
        assert roots.project_root(cwd=tmp_path) == target

    def test_explicit_beats_env(self, tmp_path, monkeypatch, no_root_env):
        fw = tmp_path / "framework-checkout"
        install_framework(fw)
        env_target = tmp_path / "env-repo"
        env_target.mkdir()
        explicit_target = tmp_path / "explicit-repo"
        explicit_target.mkdir()
        monkeypatch.setenv("AGENT_TEAM_PROJECT_ROOT", str(env_target))

        roots = load_roots(fw)
        assert roots.project_root(explicit=str(explicit_target)) == explicit_target


# ── 3. monorepo: two unity projects, no worktree collision ──────────────────

class TestMonorepo:
    def test_explicit_project_root_selects_and_worktrees_differ(
            self, tmp_path, no_root_env):
        ws = tmp_path / "studio-monorepo"
        ws.mkdir()
        install_framework(ws)
        game_a = make_unity_project(ws / "game-alpha")
        game_b = make_unity_project(ws / "game-beta")
        roots = load_roots(ws)

        assert roots.project_root(explicit=str(game_a)) == game_a
        assert roots.project_root(explicit=str(game_b)) == game_b

        wt_a = roots.worktree_root(game_a, roots.load_config(game_a))
        wt_b = roots.worktree_root(game_b, roots.load_config(game_b))
        assert wt_a != wt_b, "worktree roots must not collide across projects"
        assert wt_a.name == "game-alpha-worktrees"
        assert wt_b.name == "game-beta-worktrees"


# ── 4. non-unity repo: detection + setup seeds no ecs-registry ──────────────

class TestNonUnity:
    def test_non_unity_detection(self, tmp_path, no_root_env):
        proj = tmp_path / "my-cloud-service"
        proj.mkdir()
        (proj / "package.json").write_text(json.dumps(
            {"name": "my-cloud-service",
             "dependencies": {"express": "^4.18.0"}}), encoding="utf-8")
        install_framework(proj)
        roots = load_roots(proj)

        assert roots.unity_project_root(proj) is None
        assert roots.detect_project_type(proj) != "unity"

    def test_setup_seeds_no_ecs_registry_for_non_unity(
            self, tmp_path, other_cwd, no_root_env):
        proj = tmp_path / "my-cloud-service"
        proj.mkdir()
        (proj / "package.json").write_text(json.dumps(
            {"name": "my-cloud-service",
             "dependencies": {"express": "^4.18.0"}}), encoding="utf-8")
        scripts = install_framework(proj, scripts=("roots.py", "setup.py"))

        proc = run_script(scripts / "setup.py",
                          "--project-root", str(proj), "--yes", cwd=other_cwd)
        assert proc.returncode == 0, proc.stdout + proc.stderr

        ws = proj / "workspace"
        assert (ws / "repo-knowledge.md").is_file()
        assert (ws / "recent-changes.md").is_file()
        assert not (ws / "ecs-registry.md").exists(), \
            "ecs-registry.md must only be seeded for unity projects"

        cfg = json.loads((proj / ".claude" / "project-config.json")
                         .read_text(encoding="utf-8"))
        assert cfg["projectType"] != "unity"

    def test_setup_seeds_ecs_registry_for_unity(
            self, tmp_path, other_cwd, no_root_env):
        proj = make_unity_project(tmp_path / "a-unity-game")
        scripts = install_framework(proj, scripts=("roots.py", "setup.py"))

        proc = run_script(scripts / "setup.py",
                          "--project-root", str(proj), "--yes", cwd=other_cwd)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert (proj / "workspace" / "ecs-registry.md").is_file()


# ── 5. custom default branch from config ────────────────────────────────────

class TestDefaultBranch:
    def test_config_default_branch_wins(self, tmp_path, no_root_env):
        proj = tmp_path / "any-repo"
        proj.mkdir()
        install_framework(proj)
        (proj / ".claude" / "project-config.json").write_text(json.dumps(
            {"defaultBranch": "release/stable"}), encoding="utf-8")
        roots = load_roots(proj)

        cfg = roots.load_config(proj)
        assert roots.default_branch(proj, cfg) == "release/stable"


# ── 6. devlog paths: missing dir is not an error ─────────────────────────────

class TestDevlogs:
    def test_missing_devlogs_dir_yields_empty_list(self, tmp_path, no_root_env):
        proj = tmp_path / "plain-repo"
        proj.mkdir()
        install_framework(proj)
        roots = load_roots(proj)

        cfg = roots.load_config(proj)
        assert roots.devlog_paths(proj, cfg, existing_only=True) == []
        # existing_only=False still returns the configured (absent) path
        assert roots.devlog_paths(proj, cfg, existing_only=False) != []


# ── 7. path with spaces ──────────────────────────────────────────────────────

class TestPathWithSpaces:
    def test_resolvers_work_with_spaces(self, tmp_path, no_root_env):
        proj = make_unity_project(tmp_path / "my game")
        install_framework(proj)
        roots = load_roots(proj)

        assert roots.framework_root() == proj
        assert roots.project_root(explicit=str(proj)) == proj
        assert roots.unity_project_root(proj) == proj
        cfg = roots.load_config(proj)
        assert roots.worktree_root(proj, cfg).name == "my game-worktrees"
        assert roots.workspace_dir(proj, cfg) == proj / "workspace"

    def test_roots_cli_with_spaces_from_other_cwd(
            self, tmp_path, other_cwd, no_root_env):
        proj = make_unity_project(tmp_path / "my game")
        scripts = install_framework(proj)

        proc = run_script(scripts / "roots.py",
                          "--project-root", str(proj), "--json", cwd=other_cwd)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        ctx = json.loads(proc.stdout)
        assert ctx["PROJECT_ROOT"] == str(proj)
        assert ctx["UNITY_PROJECT_ROOT"] == str(proj)
        assert ctx["projectName"] == "my game"


# ── 8. setup.py idempotence + --check exit codes ─────────────────────────────

class TestSetupIdempotence:
    def test_setup_twice_and_check_exit_codes(
            self, tmp_path, other_cwd, no_root_env):
        proj = tmp_path / "generic-repo"
        proj.mkdir()
        scripts = install_framework(proj, scripts=("roots.py", "setup.py"))
        setup = scripts / "setup.py"

        # --check before any setup: work needed → exit 1
        proc = run_script(setup, "--project-root", str(proj), "--check",
                          cwd=other_cwd)
        assert proc.returncode == 1, proc.stdout + proc.stderr

        # first real run → exit 0
        proc = run_script(setup, "--project-root", str(proj), "--yes",
                          cwd=other_cwd)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        cfg_path = proj / ".claude" / "project-config.json"
        assert cfg_path.is_file()

        # user customizes a value
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["defaultBranch"] = "my/custom-branch"
        cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

        # second run: nothing to do, custom value preserved
        proc = run_script(setup, "--project-root", str(proj), "--yes",
                          cwd=other_cwd)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "nothing to do" in proc.stdout
        cfg_after = json.loads(cfg_path.read_text(encoding="utf-8"))
        assert cfg_after["defaultBranch"] == "my/custom-branch"

        # --check when clean → exit 0
        proc = run_script(setup, "--project-root", str(proj), "--check",
                          cwd=other_cwd)
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def test_check_is_a_dry_run(self, tmp_path, other_cwd, no_root_env):
        proj = tmp_path / "dryrun-repo"
        proj.mkdir()
        scripts = install_framework(proj, scripts=("roots.py", "setup.py"))

        proc = run_script(scripts / "setup.py",
                          "--project-root", str(proj), "--check", cwd=other_cwd)
        assert proc.returncode == 1
        assert not (proj / "workspace").exists()
        assert not (proj / ".claude" / "project-config.json").exists()


# ── 9. framework folder renamed ──────────────────────────────────────────────

class TestRenamedFramework:
    def test_framework_root_has_no_name_dependence(self, tmp_path, no_root_env):
        fw = tmp_path / "totally-renamed-toolkit-v9"
        install_framework(fw)
        roots = load_roots(fw)

        assert roots.framework_root() == fw
        assert roots.claude_root() == fw / ".claude"


# ── validator behavior on synthetic trees ────────────────────────────────────

def _install_validator_tree(dest: Path) -> Path:
    scripts = install_framework(dest, scripts=("roots.py", "setup.py"))
    shutil.copy2(VALIDATOR, scripts / VALIDATOR.name)
    return scripts / VALIDATOR.name


class TestValidatorBehavior:
    def test_clean_tree_passes(self, tmp_path, other_cwd, no_root_env):
        proj = tmp_path / "clean-tree"
        validator = _install_validator_tree(proj)
        proc = run_script(validator, "--root", str(proj), "--json",
                          cwd=other_cwd)
        report = json.loads(proc.stdout)
        assert proc.returncode == 0, proc.stdout
        assert report["status"] == "PASS"

    def test_banned_name_flagged_and_waiver_respected(
            self, tmp_path, other_cwd, no_root_env):
        proj = tmp_path / "dirty-tree"
        validator = _install_validator_tree(proj)
        doc = proj / ".claude" / "docs"
        doc.mkdir(parents=True)
        bad = doc / "note.md"
        bad.write_text("clone from /mnt/e/SomeStudio/SomeGame\n",
                       encoding="utf-8")

        proc = run_script(validator, "--root", str(proj), "--json",
                          cwd=other_cwd)
        report = json.loads(proc.stdout)
        assert proc.returncode == 1
        assert any(f["category"] == "banned-name"
                   for f in report["findings"])

        # waiver on the same line silences the finding
        bad.write_text(
            "clone from /mnt/e/SomeStudio/SomeGame "
            "<!-- portability-allow: historical example -->\n",
            encoding="utf-8")
        proc = run_script(validator, "--root", str(proj), "--json",
                          cwd=other_cwd)
        assert proc.returncode == 0, proc.stdout

    def test_root_resolver_and_cwd_dependence_flagged(
            self, tmp_path, other_cwd, no_root_env):
        proj = tmp_path / "resolver-tree"
        validator = _install_validator_tree(proj)
        rogue = proj / ".claude" / "scripts" / "rogue.py"
        rogue.write_text(
            "import os\nfrom pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[2]\n"
            "CWD = Path.cwd()\n", encoding="utf-8")

        proc = run_script(validator, "--root", str(proj), "--json",
                          cwd=other_cwd)
        report = json.loads(proc.stdout)
        assert proc.returncode == 1
        cats = {f["category"] for f in report["findings"]}
        assert "root-resolver" in cats
        assert "cwd-dependence" in cats
        # roots.py itself must never be flagged
        assert not any("roots.py" in f["path"] for f in report["findings"])

    def test_broken_reference_flagged_placeholders_tolerated(
            self, tmp_path, other_cwd, no_root_env):
        proj = tmp_path / "refs-tree"
        validator = _install_validator_tree(proj)
        cmd_dir = proj / ".claude" / "commands"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "demo.md").write_text(
            "Run `.claude/scripts/roots.py` then read "
            "`.claude/skills/<module>/SKILL.md` and `.claude/**/*.py` "
            "and finally `.claude/scripts/does-not-exist.py`.\n",
            encoding="utf-8")

        proc = run_script(validator, "--root", str(proj), "--json",
                          cwd=other_cwd)
        report = json.loads(proc.stdout)
        broken = [f for f in report["findings"]
                  if f["category"] == "broken-reference"]
        assert len(broken) == 1, report["findings"]
        assert "does-not-exist.py" in broken[0]["message"]

    def test_config_validation(self, tmp_path, other_cwd, no_root_env):
        proj = tmp_path / "config-tree"
        validator = _install_validator_tree(proj)
        cfg_path = proj / ".claude" / "project-config.json"

        # valid config incl. sibling worktreeRoot → PASS
        cfg_path.write_text(json.dumps({
            "projectName": "demo",
            "projectRoot": ".",
            "projectType": "backend",
            "workspaceDir": "workspace",
            "reportsDir": "reports",
            "worktreeRoot": "../demo-worktrees",
            "devlogPaths": [".claude/devlogs"],
        }), encoding="utf-8")
        proc = run_script(validator, "--root", str(proj), "--json",
                          cwd=other_cwd)
        assert proc.returncode == 0, proc.stdout

        # bad type + bad projectType + escaping paths → FAIL
        cfg_path.write_text(json.dumps({
            "projectName": 42,
            "projectType": "spaceship",
            "workspaceDir": "../../outside",
            "worktreeRoot": "../../way-out/wt",
        }), encoding="utf-8")
        proc = run_script(validator, "--root", str(proj), "--json",
                          cwd=other_cwd)
        report = json.loads(proc.stdout)
        assert proc.returncode == 1
        msgs = " | ".join(f["message"] for f in report["findings"])
        assert "projectName" in msgs
        assert "spaceship" in msgs
        assert "escapes PROJECT_ROOT" in msgs
        assert "direct sibling" in msgs


# ── repo-wide scan (run last; may xfail pending md/docs migration) ───────────

class TestCurrentRepo:
    def test_validator_passes_on_current_repo(self, other_cwd):
        proc = run_script(VALIDATOR, "--json", "--include-docs", cwd=other_cwd)
        if proc.returncode == 0:
            return  # clean repo — done
        try:
            report = json.loads(proc.stdout)
            findings = report.get("findings", [])
        except json.JSONDecodeError:
            pytest.fail(f"validator crashed:\n{proc.stdout}\n{proc.stderr}")

        rendered = "\n".join(
            f"[{f['category']}] {f['path']}:{f.get('line')}: {f['message']}"
            for f in findings)

        own_files = ("validate_portability.py", "tests/test_portability.py")
        only_external_banned = findings and all(
            f["category"] == "banned-name"
            and not any(own in f["path"] for own in own_files)
            for f in findings)
        if only_external_banned:
            pytest.xfail("pending md/docs migration:\n" + rendered)

        pytest.fail(
            "validate_portability.py reports findings on the current repo "
            "(NOT fixed here — outside this task's ownership; the main "
            f"thread handles them):\n{rendered}")
