#!/usr/bin/env python3
"""
Cross-platform preflight for the Unity DOTS Agent Team.

Reports on:
  - Agent Team mode enabled in ~/.claude/settings.json
  - tmux availability (optional; degrades gracefully)
  - ai-game-developer MCP server registered
  - agentmemory MCP server registered

Exits 0 always. The /team command interprets the report; it does NOT block on
missing capabilities — agents proceed in fallback mode.

Usage:
    python .claude/scripts/preflight.py            # one-line summary
    python .claude/scripts/preflight.py --verbose  # per-check detail
    python .claude/scripts/preflight.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import roots  # noqa: E402


def _resolved_roots() -> dict | None:
    try:
        return roots.resolve_all()
    except Exception:
        return None


def _home() -> Path:
    return Path(os.path.expanduser("~"))


def check_agent_team_mode() -> tuple[bool, str]:
    """Look for CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 in ~/.claude/settings.json."""
    path = _home() / ".claude" / "settings.json"
    if not path.exists():
        return False, "settings.json missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"settings.json unreadable: {exc}"
    flag = data.get("env", {}).get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS")
    if str(flag) == "1":
        return True, "enabled"
    return False, "flag not set"


def check_tmux() -> tuple[bool, str]:
    if shutil.which("tmux"):
        return True, "available"
    return False, "not installed"


def _list_mcp_servers() -> list[str]:
    """Best-effort enumeration of MCP servers from common config locations."""
    names: set[str] = set()
    candidates = [
        _home() / ".claude" / "settings.json",
        _home() / ".claude" / "mcp.json",
        _home() / ".claude" / "claude_mcp.json",
        _home() / ".config" / "claude" / "settings.json",
    ]
    for p in candidates:
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for key in ("mcpServers", "mcp_servers", "mcp"):
            block = data.get(key)
            if isinstance(block, dict):
                names.update(block.keys())
    return sorted(names)


def check_mcp(server: str) -> tuple[bool, str]:
    servers = _list_mcp_servers()
    if not servers:
        return False, "no mcp config discovered"
    if server in servers:
        return True, "registered"
    return False, f"not registered (saw: {', '.join(servers) or '<none>'})"


def main() -> int:
    parser = argparse.ArgumentParser(description="Unity DOTS Agent Team preflight")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    checks = {
        "agent-team-mode": check_agent_team_mode(),
        "tmux": check_tmux(),
        "mcp:ai-game-developer": check_mcp("ai-game-developer"),
        "mcp:agentmemory": check_mcp("agentmemory"),
    }

    ctx = _resolved_roots()

    if args.json:
        out = {k: {"ok": ok, "detail": detail} for k, (ok, detail) in checks.items()}
        out["roots"] = ctx if ctx else {"error": "unresolved"}
        print(json.dumps(out, indent=2))
        return 0

    if ctx:
        print(
            f"roots: PROJECT_ROOT={ctx['PROJECT_ROOT']} "
            f"UNITY_PROJECT_ROOT={ctx['UNITY_PROJECT_ROOT']} "
            f"type={ctx['projectType']} branch={ctx['defaultBranch']} "
            f"workspace={ctx['workspaceDir']} reports={ctx['reportsDir']}"
        )
    else:
        print("roots: unresolved -- run: python .claude/scripts/setup.py")

    for name, (ok, detail) in checks.items():
        marker = "OK " if ok else "-- "
        if args.verbose or not ok:
            print(f"{marker}{name}: {detail}")
        else:
            print(f"{marker}{name}")

    # Always exit 0 — preflight is informational, not gating.
    return 0


if __name__ == "__main__":
    sys.exit(main())
