#!/usr/bin/env python3
"""
find_ecb_producers.py — ECB producer inventory scanner for Unity DOTS repositories.

Scans .cs files for EntityCommandBuffer producers: ECB singleton references,
CreateCommandBuffer calls, AsParallelWriter calls, structural commands
(DestroyEntity, AppendToBuffer, AddBuffer, SetBuffer, AddComponent, SetComponent,
RemoveComponent, CreateEntity, Instantiate).

Usage:
    python3 find_ecb_producers.py <repo-root> [--phase <ecb-phase>] [--verbose]

Output:
    Structured table of ECB producer sites with file:line evidence.
    Grouped by detected ECB phase (BeginSim, EndSim, BeginInit, EndInit, BeginPres).

Security: Read-only. No code execution on target repo. No writes. No network.
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Pattern library — generic, works on any DOTS repo
# ---------------------------------------------------------------------------

# ECB singleton type names (standard Unity Entities package)
ECB_SINGLETON_PATTERNS = [
    (r"BeginInitializationEntityCommandBufferSystem", "BeginInit"),
    (r"EndInitializationEntityCommandBufferSystem",   "EndInit"),
    (r"BeginSimulationEntityCommandBufferSystem",     "BeginSim"),
    (r"EndSimulationEntityCommandBufferSystem",       "EndSim"),
    (r"BeginPresentationEntityCommandBufferSystem",   "BeginPres"),
    (r"BeginFixedStepSimulationEntityCommandBufferSystem", "BeginFixedSim"),
    (r"EndFixedStepSimulationEntityCommandBufferSystem",   "EndFixedSim"),
]

# ECB creation patterns
ECB_CREATION_PATTERNS = [
    r"\.CreateCommandBuffer\s*\(",
    r"EntityCommandBuffer\s+\w+\s*=",
    r"new\s+EntityCommandBuffer\s*\(",
    r"\.AsParallelWriter\s*\(",
]

# Structural command patterns (ECB method calls)
STRUCTURAL_CMD_PATTERNS = [
    (r"\becb\w*\.DestroyEntity\s*\(",          "DestroyEntity"),
    (r"\becb\w*\.CreateEntity\s*\(",           "CreateEntity"),
    (r"\becb\w*\.Instantiate\s*\(",            "Instantiate"),
    (r"\becb\w*\.AddComponent\s*[<(]",         "AddComponent"),
    (r"\becb\w*\.SetComponent\s*[<(]",         "SetComponent"),
    (r"\becb\w*\.RemoveComponent\s*[<(]",      "RemoveComponent"),
    (r"\becb\w*\.AppendToBuffer\s*[<(]",       "AppendToBuffer"),
    (r"\becb\w*\.AddBuffer\s*[<(]",            "AddBuffer"),
    (r"\becb\w*\.SetBuffer\s*[<(]",            "SetBuffer"),
    (r"\becb\w*\.AddSharedComponent\s*[<(]",   "AddSharedComponent"),
    (r"\becb\w*\.SetSharedComponent\s*[<(]",   "SetSharedComponent"),
    (r"\becb\w*\.RemoveSharedComponent\s*[<(]","RemoveSharedComponent"),
    (r"\becb\w*\.SetEnabled\s*\(",             "SetEnabled"),
    (r"\becb\w*\.LinkedEntityGroupDestroyEntity\s*\(", "LinkedEntityGroupDestroyEntity"),
]

# System declaration patterns
SYSTEM_DECL_PATTERN = re.compile(
    r"(?:partial\s+)?(?:struct|class)\s+(\w+)\s*[^{]*?(?::\s*[^{]+)?\{",
    re.MULTILINE
)

# Update group / ordering attributes
UPDATE_ATTR_PATTERN = re.compile(
    r"\[(?:UpdateInGroup|UpdateBefore|UpdateAfter|CreateBefore|CreateAfter)\s*\([^)]*\)\]"
)

# ISystem / SystemBase declaration
SYSTEM_INTERFACE_PATTERN = re.compile(
    r"\b(ISystem|SystemBase)\b"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def iter_cs_files(root: Path):
    """Recursively yield .cs files, skipping common non-runtime directories."""
    skip_dirs = {"Library", "Temp", "obj", "bin", ".git", "Packages/cache", "node_modules"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            if fname.endswith(".cs"):
                yield Path(dirpath) / fname


def relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def detect_ecb_phase_in_file(content: str) -> str:
    """Return the most specific ECB singleton referenced in this file."""
    for pattern, phase in ECB_SINGLETON_PATTERNS:
        if re.search(pattern, content):
            return phase
    return "unknown"


def extract_current_system(lines: list, line_idx: int) -> str:
    """
    Walk backward from line_idx to find the enclosing class/struct name.
    Returns 'unknown' if not found within 100 lines.
    """
    for i in range(line_idx, max(0, line_idx - 100), -1):
        m = SYSTEM_DECL_PATTERN.search(lines[i])
        if m:
            return m.group(1)
    return "unknown"


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def scan_file(filepath: Path, root: Path, phase_filter: str = None):
    """Scan a single .cs file and return a list of finding dicts."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    findings = []
    lines = content.splitlines()

    # Quick pre-filter: skip files with no ECB-related content
    ecb_keywords = ["CommandBuffer", "ecb", "Ecb", "ECB"]
    if not any(kw in content for kw in ecb_keywords):
        return []

    detected_phase = detect_ecb_phase_in_file(content)

    # Apply phase filter if requested
    if phase_filter and detected_phase != phase_filter:
        return []

    # Collect update attributes for the file (approximate — per-file, not per-class)
    update_attrs = UPDATE_ATTR_PATTERN.findall(content)
    update_attrs_str = "; ".join(update_attrs) if update_attrs else ""

    # Scan line by line for ECB operations
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()

        # ECB singleton reference
        for pattern, phase in ECB_SINGLETON_PATTERNS:
            if re.search(pattern, stripped):
                system = extract_current_system(lines, lineno - 1)
                rel = relative(filepath, root)
                findings.append({
                    "type":      "ecb_singleton",
                    "system":    system,
                    "file":      rel,
                    "line":      lineno,
                    "phase":     phase,
                    "operation": f"GetSingleton<{pattern.split('(')[0].strip()}..>",
                    "raw":       stripped[:120],
                    "attrs":     update_attrs_str,
                })
                break

        # ECB creation
        for cp in ECB_CREATION_PATTERNS:
            if re.search(cp, stripped):
                system = extract_current_system(lines, lineno - 1)
                rel = relative(filepath, root)
                is_parallel = "AsParallelWriter" in stripped
                findings.append({
                    "type":      "ecb_creation",
                    "system":    system,
                    "file":      rel,
                    "line":      lineno,
                    "phase":     detected_phase,
                    "operation": "AsParallelWriter" if is_parallel else "CreateCommandBuffer",
                    "raw":       stripped[:120],
                    "attrs":     update_attrs_str,
                })
                break

        # Structural commands
        for pattern, op_name in STRUCTURAL_CMD_PATTERNS:
            if re.search(pattern, stripped):
                system = extract_current_system(lines, lineno - 1)
                rel = relative(filepath, root)
                findings.append({
                    "type":      "structural_cmd",
                    "system":    system,
                    "file":      rel,
                    "line":      lineno,
                    "phase":     detected_phase,
                    "operation": op_name,
                    "raw":       stripped[:120],
                    "attrs":     update_attrs_str,
                })
                break  # one op per line is enough

    return findings


def scan_repo(root: Path, phase_filter: str = None, verbose: bool = False):
    """Scan entire repo and collect all ECB producer findings."""
    all_findings = []
    total_files = 0
    scanned_files = 0

    for cs_file in iter_cs_files(root):
        total_files += 1
        findings = scan_file(cs_file, root, phase_filter)
        if findings:
            scanned_files += 1
            all_findings.extend(findings)
            if verbose:
                print(f"  [scanned] {relative(cs_file, root)} — {len(findings)} finding(s)")

    return all_findings, total_files, scanned_files


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def print_singleton_table(findings: list):
    """Print ECB singleton references grouped by phase."""
    singletons = [f for f in findings if f["type"] == "ecb_singleton"]
    if not singletons:
        print("  (none found)")
        return

    # Group by phase
    by_phase = defaultdict(list)
    for f in singletons:
        by_phase[f["phase"]].append(f)

    for phase, items in sorted(by_phase.items()):
        print(f"\n  Phase: {phase}")
        print(f"  {'System':<35} {'File:Line':<55} {'Context'}")
        print(f"  {'-'*35} {'-'*55} {'-'*40}")
        for item in items:
            floc = f"{item['file']}:{item['line']}"
            print(f"  {item['system']:<35} {floc:<55} {item['raw'][:60]}")


def print_structural_table(findings: list):
    """Print structural ECB commands grouped by operation type."""
    structural = [f for f in findings if f["type"] == "structural_cmd"]
    if not structural:
        print("  (none found)")
        return

    # Group by operation
    by_op = defaultdict(list)
    for f in structural:
        by_op[f["operation"]].append(f)

    # Print high-risk ops first
    priority_ops = ["DestroyEntity", "RemoveComponent", "LinkedEntityGroupDestroyEntity",
                    "AppendToBuffer", "SetComponent", "AddComponent"]
    ordered_ops = [op for op in priority_ops if op in by_op]
    ordered_ops += [op for op in sorted(by_op) if op not in ordered_ops]

    for op in ordered_ops:
        items = by_op[op]
        risk = "HIGH" if op in ("DestroyEntity", "RemoveComponent", "LinkedEntityGroupDestroyEntity") else "MED"
        print(f"\n  Operation: {op}  [risk: {risk}]  ({len(items)} site(s))")
        print(f"  {'System':<35} {'File:Line':<55} {'Phase':<12} {'Code'}")
        print(f"  {'-'*35} {'-'*55} {'-'*12} {'-'*50}")
        for item in items:
            floc = f"{item['file']}:{item['line']}"
            print(f"  {item['system']:<35} {floc:<55} {item['phase']:<12} {item['raw'][:50]}")


def print_creation_table(findings: list):
    """Print ECB creation/ParallelWriter sites."""
    creations = [f for f in findings if f["type"] == "ecb_creation"]
    if not creations:
        print("  (none found)")
        return

    print(f"  {'System':<35} {'File:Line':<55} {'Phase':<12} {'Operation':<20} {'Code'}")
    print(f"  {'-'*35} {'-'*55} {'-'*12} {'-'*20} {'-'*40}")
    for item in creations:
        floc = f"{item['file']}:{item['line']}"
        print(f"  {item['system']:<35} {floc:<55} {item['phase']:<12} {item['operation']:<20} {item['raw'][:40]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scan a Unity DOTS repo for ECB producer sites (read-only)."
    )
    parser.add_argument("repo_root", help="Path to the Unity project root")
    parser.add_argument(
        "--phase",
        choices=["BeginInit", "EndInit", "BeginSim", "EndSim", "BeginPres",
                 "BeginFixedSim", "EndFixedSim"],
        help="Filter output to a specific ECB phase",
    )
    parser.add_argument("--verbose", action="store_true", help="Show per-file scan progress")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== ECB Producer Inventory ===")
    print(f"Repo root : {root}")
    print(f"Phase filter: {args.phase or 'all'}")
    print()

    findings, total_files, scanned_files = scan_repo(root, args.phase, args.verbose)

    print(f"Scanned {total_files} .cs files, {scanned_files} with ECB content")
    print(f"Total findings: {len(findings)}")

    print("\n--- ECB Singleton References (playback phase anchor) ---")
    print_singleton_table(findings)

    print("\n--- ECB Creation / AsParallelWriter Sites ---")
    print_creation_table(findings)

    print("\n--- Structural Commands (HIGH RISK first) ---")
    print_structural_table(findings)

    print("\n=== Investigation Notes ===")
    destroy_count = sum(1 for f in findings if f["operation"] == "DestroyEntity")
    append_count  = sum(1 for f in findings if f["operation"] == "AppendToBuffer")
    if destroy_count > 0 and append_count > 0:
        print(f"  ATTENTION: {destroy_count} DestroyEntity site(s) + {append_count} AppendToBuffer site(s)")
        print("  Cross-reference systems with same ECB phase — possible lifecycle conflict.")

    phases_present = {f["phase"] for f in findings if f["phase"] != "unknown"}
    if len(phases_present) > 1:
        print(f"  Multiple ECB phases in use: {', '.join(sorted(phases_present))}")
        print("  Verify that CleanupSystem and DependentSystem do not share a phase.")

    print()


if __name__ == "__main__":
    main()
