#!/usr/bin/env python3
"""
Quick anti-pattern scan for Unity DOTS C# code.

Flags common DOTS pitfalls so the unity-dev agent can decide whether to fix or
justify them. Not exhaustive — it's a fast first-pass signal, not a linter.

Usage:
    python .claude/scripts/dots_scan.py <path>            # scan a folder or file
    python .claude/scripts/dots_scan.py <path> --json     # machine-readable
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


# (pattern, severity, message)
RULES: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"\bSystemBase\b"),
        "info",
        "SystemBase used — prefer ISystem (Burst-compilable) on hot paths.",
    ),
    (
        re.compile(r"\.WithoutBurst\(\)"),
        "warn",
        "WithoutBurst() — verifies a hot path is intentionally not Burst-compiled.",
    ),
    (
        re.compile(r"Entities\.ForEach"),
        "info",
        "Entities.ForEach — prefer IJobEntity / IJobChunk for explicit job semantics.",
    ),
    (
        re.compile(r"EntityManager\.(Create|Add|Remove|Destroy)Entity\b"),
        "warn",
        "Direct EntityManager structural change — use EntityCommandBuffer to batch.",
    ),
    (
        re.compile(r"EntityManager\.(Add|Remove)Component\b"),
        "warn",
        "Direct EntityManager component change — consider ECB or enableable components.",
    ),
    (
        re.compile(r"\bGetSingleton\b\("),
        "info",
        "GetSingleton — confirm this isn't inside a tight Burst loop without caching.",
    ),
    (
        re.compile(r"new\s+List<"),
        "warn",
        "List<T> allocation — managed alloc; not job-/Burst-safe.",
    ),
    (
        re.compile(r"new\s+Dictionary<"),
        "warn",
        "Dictionary<T> allocation — use NativeHashMap / NativeParallelHashMap for jobs.",
    ),
    (
        re.compile(r"Debug\.Log"),
        "info",
        "Debug.Log — not Burst-friendly; gate with #if UNITY_EDITOR or ENABLE_PROFILER.",
    ),
    (
        re.compile(r"\.CompleteAllTrackedJobs\(\)"),
        "warn",
        "CompleteAllTrackedJobs — forces a sync point; confirm intentional.",
    ),
    (
        re.compile(r"\.Complete\(\)"),
        "info",
        "JobHandle.Complete — sync point; ensure not in a hot loop.",
    ),
    (
        re.compile(r"\bAllocator\.Persistent\b"),
        "info",
        "Allocator.Persistent — confirm matching Dispose in OnDestroy.",
    ),
    (
        re.compile(r"\[BurstCompile"),
        "ok",
        "BurstCompile attribute present.",
    ),
    (
        re.compile(r"using\s+UnityEditor"),
        "info",
        "UnityEditor reference — should be in Editor/ folder or Editor asmdef only.",
    ),
]

SEVERITY_ORDER = {"warn": 0, "info": 1, "ok": 2}


@dataclass
class Finding:
    file: str
    line: int
    severity: str
    rule: str
    text: str


def scan_file(path: Path) -> list[Finding]:
    out: list[Finding] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return out
    for lineno, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("*"):
            continue
        for pattern, severity, message in RULES:
            if pattern.search(stripped):
                out.append(Finding(
                    file=str(path),
                    line=lineno,
                    severity=severity,
                    rule=message,
                    text=stripped[:160],
                ))
    return out


def iter_cs_files(root: Path):
    if root.is_file():
        if root.suffix == ".cs":
            yield root
        return
    for p in root.rglob("*.cs"):
        # skip generated and library folders
        parts = {x.lower() for x in p.parts}
        if "library" in parts or "obj" in parts or "temp" in parts:
            continue
        yield p


def main() -> int:
    parser = argparse.ArgumentParser(description="Unity DOTS anti-pattern scan")
    parser.add_argument("path", help="File or folder to scan")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--severity", choices=("warn", "info", "ok"), default="info",
                        help="Minimum severity to report")
    args = parser.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"path not found: {root}", file=sys.stderr)
        return 2

    min_sev = SEVERITY_ORDER[args.severity]
    all_findings: list[Finding] = []
    for path in iter_cs_files(root):
        for f in scan_file(path):
            if SEVERITY_ORDER[f.severity] <= min_sev:
                all_findings.append(f)

    if args.json:
        print(json.dumps([asdict(f) for f in all_findings], indent=2))
        return 0

    if not all_findings:
        print("no findings")
        return 0

    by_sev = {"warn": [], "info": [], "ok": []}
    for f in all_findings:
        by_sev[f.severity].append(f)

    for sev in ("warn", "info", "ok"):
        rows = by_sev[sev]
        if not rows:
            continue
        print(f"\n[{sev.upper()}] {len(rows)} finding(s)")
        for f in rows:
            print(f"  {f.file}:{f.line}  {f.rule}")
            print(f"      {f.text}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
