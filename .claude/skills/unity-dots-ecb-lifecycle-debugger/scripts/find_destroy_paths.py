#!/usr/bin/env python3
"""
find_destroy_paths.py — Entity destruction path scanner for Unity DOTS repositories.

Scans .cs files for all paths that destroy or structurally remove entities:
DestroyEntity calls, RemoveComponent calls, cleanup-state transitions,
LinkedEntityGroup destructions, owner-driven cleanup, pooled returns,
and state-machine destruction patterns.

Usage:
    python3 find_destroy_paths.py <repo-root> [--entity <partial-name>] [--verbose]

Output:
    Structured table of destruction sites grouped by destruction kind.

Security: Read-only. No code execution on target repo. No writes. No network.
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Pattern library
# ---------------------------------------------------------------------------

# Direct destruction patterns
DESTROY_PATTERNS = [
    (r"\becb\w*\.DestroyEntity\s*\(", "ecb.DestroyEntity", "HIGH"),
    (r"\bEntityManager\.DestroyEntity\s*\(", "EntityManager.DestroyEntity", "HIGH"),
    (r"\becb\w*\.LinkedEntityGroupDestroyEntity\s*\(", "ecb.LinkedEntityGroupDestroyEntity", "HIGH"),
    (r"\bEntityManager\.DestroyAndResetAllEntities\s*\(", "DestroyAndResetAllEntities", "HIGH"),
]

# Component removal patterns (may destroy required components)
REMOVE_PATTERNS = [
    (r"\becb\w*\.RemoveComponent\s*[<(]",          "ecb.RemoveComponent",          "MED"),
    (r"\bEntityManager\.RemoveComponent\s*[<(]",   "EntityManager.RemoveComponent", "MED"),
    (r"\becb\w*\.RemoveComponentForEntityQuery\b",  "ecb.RemoveComponentForEntityQuery", "MED"),
]

# Cleanup state marker patterns (structural additions that trigger downstream destruction)
CLEANUP_MARKER_PATTERNS = [
    # Any AddComponent that contains "Cleanup", "Pending", "Dead", "Dying", "Destroy", "Kill",
    # "Remove", "Despawn", "Recycle", "Pool" in the type name — generic lifecycle markers
    (
        r"\becb\w*\.AddComponent\s*<\s*\w*(?:Cleanup|Pending|Dead|Dying|Destroy|Kill|Despawn|Recycle|Pool|Retire|Expired|Finished|Complete)\w*",
        "AddComponent<*CleanupMarker>",
        "MED"
    ),
    (
        r"\bEntityManager\.AddComponent\s*<\s*\w*(?:Cleanup|Pending|Dead|Dying|Destroy|Kill|Despawn|Recycle|Pool|Retire|Expired|Finished|Complete)\w*",
        "EntityManager.AddComponent<*CleanupMarker>",
        "MED"
    ),
    # ICleanupComponentData structs (Unity built-in cleanup system)
    (r"\bICleanupComponentData\b", "ICleanupComponentData (struct decl)", "MED"),
    (r"\bICleanupBufferElementData\b", "ICleanupBufferElementData (struct decl)", "MED"),
]

# Owner-driven cascade patterns
CASCADE_PATTERNS = [
    # Destroying root of a LinkedEntityGroup
    (r"\bLinkedEntityGroup\b.*(?:Destroy|destroy)", "LinkedEntityGroup cascade trigger", "HIGH"),
    # Instantiate/prefab destroy (destroying a prefab entity)
    (r"\becb\w*\.DestroyEntity\s*\([^)]*root[^)]*\)", "DestroyEntity (root)", "HIGH"),
]

# State transition patterns (setting a state that leads to destruction)
STATE_TRANSITION_PATTERNS = [
    # SetComponent that writes to a field named "state", "phase", "status" with destruction keywords
    (
        r"\becb\w*\.SetComponent\s*<[^>]*>\s*\([^,]+,\s*new\s+\w+\s*\{[^}]*(?:Dead|Dying|Destroy|Cleanup|Despawn|Kill|Remove|Retire|Expired)[^}]*\}",
        "SetComponent (state=*Destroy*)",
        "MED"
    ),
    # SetComponentEnabled patterns (disable component as soft-destroy)
    (r"\becb\w*\.SetEnabled\s*\([^,]+,\s*false", "SetEnabled(entity, false)", "LOW"),
    (r"\bEntityManager\.SetEnabled\s*\([^,]+,\s*false", "EntityManager.SetEnabled(false)", "LOW"),
]

# Scene / world unload patterns
SCENE_DESTROY_PATTERNS = [
    (r"\bSceneSystem\.UnloadScene\b", "SceneSystem.UnloadScene (bulk destroy)", "MED"),
    (r"\bEntityManager\.DestroyEntity\s*\([^)]*query[^)]*\)", "DestroyEntity(query) bulk", "HIGH"),
    (r"\bEntityManager\.DestroyEntity\s*\([^)]*world[^)]*\)", "DestroyEntity(world) bulk", "HIGH"),
    (r"\.CompleteAllTrackedJobs\s*\(\)\s*;[^\n]*\n[^\n]*DestroyEntity", "CompleteAllTrackedJobs+Destroy", "HIGH"),
]

# System declaration
SYSTEM_DECL_PATTERN = re.compile(
    r"(?:partial\s+)?(?:struct|class)\s+(\w+)\s*[^{]*?(?::\s*[^{]+)?\{",
    re.MULTILINE
)

# Update group attributes
UPDATE_ATTR_PATTERN = re.compile(
    r"\[(?:UpdateInGroup|UpdateBefore|UpdateAfter|CreateBefore|CreateAfter)\s*\([^)]*\)\]"
)

# ECB singleton phase detection
ECB_PHASE_PATTERNS = [
    (r"BeginSimulationEntityCommandBufferSystem", "BeginSim"),
    (r"EndSimulationEntityCommandBufferSystem",   "EndSim"),
    (r"BeginInitializationEntityCommandBufferSystem", "BeginInit"),
    (r"EndInitializationEntityCommandBufferSystem",   "EndInit"),
    (r"BeginPresentationEntityCommandBufferSystem",   "BeginPres"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def iter_cs_files(root: Path):
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


def detect_ecb_phase(content: str) -> str:
    for pattern, phase in ECB_PHASE_PATTERNS:
        if re.search(pattern, content):
            return phase
    return "unknown"


def extract_current_system(lines: list, line_idx: int) -> str:
    for i in range(line_idx, max(0, line_idx - 100), -1):
        m = SYSTEM_DECL_PATTERN.search(lines[i])
        if m:
            return m.group(1)
    return "unknown"


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

ALL_PATTERNS = (
    DESTROY_PATTERNS + REMOVE_PATTERNS + CLEANUP_MARKER_PATTERNS +
    CASCADE_PATTERNS + STATE_TRANSITION_PATTERNS + SCENE_DESTROY_PATTERNS
)


def scan_file(filepath: Path, root: Path, entity_filter: str = None):
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    # Quick pre-filter
    keywords = ["Destroy", "Remove", "Cleanup", "Dead", "Dying", "ICleanup"]
    if not any(kw in content for kw in keywords):
        return []

    findings = []
    lines = content.splitlines()
    ecb_phase = detect_ecb_phase(content)
    update_attrs = UPDATE_ATTR_PATTERN.findall(content)
    update_attrs_str = "; ".join(update_attrs[:3]) if update_attrs else ""

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Optional entity name filter
        if entity_filter and entity_filter.lower() not in stripped.lower():
            continue

        for pattern, label, risk in ALL_PATTERNS:
            if re.search(pattern, stripped, re.IGNORECASE):
                system = extract_current_system(lines, lineno - 1)
                rel = relative(filepath, root)
                findings.append({
                    "system":   system,
                    "file":     rel,
                    "line":     lineno,
                    "kind":     label,
                    "risk":     risk,
                    "phase":    ecb_phase,
                    "attrs":    update_attrs_str,
                    "raw":      stripped[:120],
                })
                break

    return findings


def scan_repo(root: Path, entity_filter: str = None, verbose: bool = False):
    all_findings = []
    total_files = 0
    scanned_files = 0

    for cs_file in iter_cs_files(root):
        total_files += 1
        findings = scan_file(cs_file, root, entity_filter)
        if findings:
            scanned_files += 1
            all_findings.extend(findings)
            if verbose:
                print(f"  [scanned] {relative(cs_file, root)} — {len(findings)} finding(s)")

    return all_findings, total_files, scanned_files


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_findings(findings: list, group_by: str = "kind"):
    if not findings:
        print("  (none found)")
        return

    groups = defaultdict(list)
    for f in findings:
        groups[f[group_by]].append(f)

    # Print HIGH risk first
    def sort_key(k):
        sample = groups[k][0]
        order = {"HIGH": 0, "MED": 1, "LOW": 2}
        return (order.get(sample["risk"], 3), k)

    for kind in sorted(groups.keys(), key=sort_key):
        items = groups[kind]
        risk = items[0]["risk"]
        print(f"\n  [{risk}] {kind}  ({len(items)} site(s))")
        print(f"  {'System':<35} {'File:Line':<55} {'Phase':<12} {'Code'}")
        print(f"  {'-'*35} {'-'*55} {'-'*12} {'-'*50}")
        for item in items:
            floc = f"{item['file']}:{item['line']}"
            print(f"  {item['system']:<35} {floc:<55} {item['phase']:<12} {item['raw'][:50]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scan a Unity DOTS repo for entity destruction paths (read-only)."
    )
    parser.add_argument("repo_root", help="Path to the Unity project root")
    parser.add_argument(
        "--entity",
        help="Filter: only show lines containing this partial entity/variable name",
        default=None,
    )
    parser.add_argument("--verbose", action="store_true", help="Show per-file scan progress")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== Entity Destruction Path Inventory ===")
    print(f"Repo root   : {root}")
    print(f"Entity filter: {args.entity or 'none (all)'}")
    print()

    findings, total_files, scanned_files = scan_repo(root, args.entity, args.verbose)

    print(f"Scanned {total_files} .cs files, {scanned_files} with destruction patterns")
    print(f"Total findings: {len(findings)}")

    # Summary counts
    high_count = sum(1 for f in findings if f["risk"] == "HIGH")
    med_count  = sum(1 for f in findings if f["risk"] == "MED")
    low_count  = sum(1 for f in findings if f["risk"] == "LOW")
    print(f"Risk summary:  HIGH={high_count}  MED={med_count}  LOW={low_count}")

    print("\n--- Destruction Paths (grouped by kind, HIGH risk first) ---")
    print_findings(findings, group_by="kind")

    # Lifecycle conflict hint
    destroy_systems = {f["system"] for f in findings if f["risk"] == "HIGH" and f["system"] != "unknown"}
    if destroy_systems:
        print("\n=== Investigation Hints ===")
        print(f"  Systems with HIGH-risk destruction paths: {', '.join(sorted(destroy_systems))}")
        print("  Cross-reference with find_ecb_producers.py output:")
        print("  → Do any of these systems share an ECB phase with AppendToBuffer/SetComponent producers?")
        print("  → If yes: that system is a candidate destructive producer for the ECB conflict.")
        print("  → Run find_system_ordering.py to determine which executes first.")

    print()


if __name__ == "__main__":
    main()
