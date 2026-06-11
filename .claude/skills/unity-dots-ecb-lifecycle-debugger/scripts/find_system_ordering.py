#!/usr/bin/env python3
"""
find_system_ordering.py — System execution-order scanner for Unity DOTS repositories.

Scans .cs files for system ordering attributes (UpdateInGroup, UpdateBefore, UpdateAfter,
CreateBefore, CreateAfter), ECB phase assignments, and detects ordering ambiguities
(systems without explicit ordering in the same group that both write to shared ECB singletons).

Usage:
    python3 find_system_ordering.py <repo-root> [--group <GroupName>] [--verbose]

Output:
    - Per-system ordering table
    - ECB phase assignment table
    - Ordering ambiguity warnings
    - Suggested frame timeline sketch for ECB conflict investigation

Security: Read-only. No code execution on target repo. No writes. No network.
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Ordering attributes — capture the full attribute including argument
ORDERING_ATTR_RE = re.compile(
    r"\[\s*(UpdateInGroup|UpdateBefore|UpdateAfter|CreateBefore|CreateAfter)\s*"
    r"\(\s*typeof\s*\(\s*([\w.]+)\s*\)\s*\)\s*\]"
)

# System declaration (struct or class — opening brace may be on the next line)
SYSTEM_DECL_RE = re.compile(
    r"(?:public\s+)?(?:partial\s+)?(?:struct|class)\s+(\w+)"
    r"(?:\s*:\s*[\w,\s<>.]+)?\s*$",
    re.MULTILINE
)

# ISystem / SystemBase interface
SYSTEM_INTERFACE_RE = re.compile(r"\b(ISystem|SystemBase)\b")

# ECB singleton references
ECB_SINGLETON_RE = re.compile(
    r"\b(BeginInitializationEntityCommandBufferSystem"
    r"|EndInitializationEntityCommandBufferSystem"
    r"|BeginSimulationEntityCommandBufferSystem"
    r"|EndSimulationEntityCommandBufferSystem"
    r"|BeginPresentationEntityCommandBufferSystem"
    r"|BeginFixedStepSimulationEntityCommandBufferSystem"
    r"|EndFixedStepSimulationEntityCommandBufferSystem)\b"
)

# Structural operations in systems (for ambiguity detection)
STRUCTURAL_RE = re.compile(
    r"\becb\w*\.(DestroyEntity|AppendToBuffer|AddBuffer|SetBuffer|AddComponent|SetComponent|RemoveComponent|CreateEntity|Instantiate)\s*[<(]"
)

# Group names for known Unity system groups
KNOWN_GROUPS = {
    "InitializationSystemGroup",
    "SimulationSystemGroup",
    "PresentationSystemGroup",
    "FixedStepSimulationSystemGroup",
    "BeginInitializationEntityCommandBufferSystem",
    "EndInitializationEntityCommandBufferSystem",
    "BeginSimulationEntityCommandBufferSystem",
    "EndSimulationEntityCommandBufferSystem",
    "BeginPresentationEntityCommandBufferSystem",
}

# ECB singleton → phase label
ECB_PHASE_MAP = {
    "BeginInitializationEntityCommandBufferSystem": "BeginInit",
    "EndInitializationEntityCommandBufferSystem":   "EndInit",
    "BeginSimulationEntityCommandBufferSystem":     "BeginSim",
    "EndSimulationEntityCommandBufferSystem":       "EndSim",
    "BeginPresentationEntityCommandBufferSystem":   "BeginPres",
    "BeginFixedStepSimulationEntityCommandBufferSystem": "BeginFixedSim",
    "EndFixedStepSimulationEntityCommandBufferSystem":   "EndFixedSim",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class SystemInfo:
    def __init__(self, name: str, file: str, line: int):
        self.name = name
        self.file = file
        self.line = line
        self.is_system = False          # True if implements ISystem or SystemBase
        self.update_in_group = None     # group name string
        self.update_before = []         # list of type names
        self.update_after = []          # list of type names
        self.create_before = []
        self.create_after = []
        self.ecb_phases = set()         # set of ECB phase labels used
        self.structural_ops = set()     # set of ECB operation names used
        self.raw_attrs = []             # raw attribute strings for display

    def ordering_summary(self) -> str:
        parts = []
        if self.update_in_group:
            parts.append(f"InGroup({self.update_in_group})")
        for b in self.update_before:
            parts.append(f"Before({b})")
        for a in self.update_after:
            parts.append(f"After({a})")
        return "; ".join(parts) if parts else "(no ordering)"

    def ecb_summary(self) -> str:
        return ", ".join(sorted(self.ecb_phases)) if self.ecb_phases else "—"

    def ops_summary(self) -> str:
        return ", ".join(sorted(self.structural_ops)) if self.structural_ops else "—"


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


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_file(filepath: Path, root: Path) -> list:
    """Parse a .cs file and return a list of SystemInfo objects."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    # Pre-filter: skip files with no system-related content
    if not any(kw in content for kw in ["ISystem", "SystemBase", "UpdateInGroup", "UpdateBefore",
                                          "UpdateAfter", "CommandBuffer"]):
        return []

    lines = content.splitlines()
    systems: list = []
    current: SystemInfo = None
    pending_attrs: list = []

    rel = relative(filepath, root)

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Collect ordering attributes (may precede class/struct declaration)
        m = ORDERING_ATTR_RE.search(stripped)
        if m:
            attr_type = m.group(1)
            attr_arg  = m.group(2)
            pending_attrs.append((attr_type, attr_arg, stripped))
            i += 1
            continue

        # System declaration
        dm = SYSTEM_DECL_RE.search(stripped)
        if dm:
            sys_name = dm.group(1)
            # Check if this looks like a system (ISystem/SystemBase in nearby lines or same line)
            context = "\n".join(lines[max(0, i-2):min(len(lines), i+5)])
            is_system = bool(SYSTEM_INTERFACE_RE.search(context))

            info = SystemInfo(sys_name, rel, i + 1)
            info.is_system = is_system

            # Apply pending attrs
            for attr_type, attr_arg, raw in pending_attrs:
                info.raw_attrs.append(raw)
                if attr_type == "UpdateInGroup":
                    info.update_in_group = attr_arg
                elif attr_type == "UpdateBefore":
                    info.update_before.append(attr_arg)
                elif attr_type == "UpdateAfter":
                    info.update_after.append(attr_arg)
                elif attr_type == "CreateBefore":
                    info.create_before.append(attr_arg)
                elif attr_type == "CreateAfter":
                    info.create_after.append(attr_arg)

            pending_attrs = []
            current = info
            systems.append(info)
            i += 1
            continue

        # ECB phase references
        ecb_match = ECB_SINGLETON_RE.search(stripped)
        if ecb_match and current:
            ecb_name = ecb_match.group(1)
            phase = ECB_PHASE_MAP.get(ecb_name, ecb_name)
            current.ecb_phases.add(phase)

        # Structural operations
        op_match = STRUCTURAL_RE.search(stripped)
        if op_match and current:
            current.structural_ops.add(op_match.group(1))

        # Reset pending attrs if we hit a non-attribute, non-decl line
        if stripped and not stripped.startswith("[") and not dm and pending_attrs:
            # Only clear if the line isn't a continuation (blank, comment, attribute)
            if not stripped.startswith("//") and not stripped.startswith("/*"):
                pending_attrs = []

        i += 1

    return systems


def scan_repo(root: Path, verbose: bool = False):
    all_systems: list = []
    total_files = 0

    for cs_file in iter_cs_files(root):
        total_files += 1
        systems = parse_file(cs_file, root)
        if systems:
            all_systems.extend(systems)
            if verbose:
                found = [s.name for s in systems if s.is_system]
                if found:
                    print(f"  [found] {relative(cs_file, root)} — {', '.join(found)}")

    return all_systems, total_files


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def find_ordering_ambiguities(systems: list) -> list:
    """
    Find systems in the same group that both use structural ECB ops but
    have no explicit ordering relative to each other.
    Returns a list of (sys_a, sys_b, shared_group, shared_ecb_phases) tuples.
    """
    ambiguities = []
    active = [s for s in systems if s.is_system and s.structural_ops]

    # Group by update_in_group
    by_group = defaultdict(list)
    for s in active:
        group = s.update_in_group or "(unspecified)"
        by_group[group].append(s)

    for group, members in by_group.items():
        if len(members) < 2:
            continue

        for i, sys_a in enumerate(members):
            for sys_b in members[i + 1:]:
                # Check if they share an ECB phase
                shared_phases = sys_a.ecb_phases & sys_b.ecb_phases
                if not shared_phases:
                    continue

                # Check if there's explicit ordering between them
                has_explicit_order = (
                    sys_b.name in sys_a.update_before or
                    sys_a.name in sys_b.update_before or
                    sys_b.name in sys_a.update_after or
                    sys_a.name in sys_b.update_after
                )

                if not has_explicit_order:
                    ambiguities.append((sys_a, sys_b, group, shared_phases))

    return ambiguities


def build_frame_sketch(systems: list) -> list:
    """
    Build a rough frame timeline sketch for ECB conflict investigation.
    Returns a list of (step, system_name, file, ecb_phases, ops, ordering) tuples.
    """
    # Only include systems with ECB ops
    ecb_systems = [s for s in systems if s.is_system and s.ecb_phases]

    # Group by ECB phase (when do their commands execute?)
    by_phase = defaultdict(list)
    for s in ecb_systems:
        for phase in s.ecb_phases:
            by_phase[phase].append(s)

    sketch = []
    step = 1

    # Simulate group execution order (approximate)
    phase_order = ["BeginInit", "EndInit", "BeginFixedSim", "BeginSim", "EndSim", "BeginPres"]

    for phase in phase_order:
        members = by_phase.get(phase, [])
        for s in members:
            sketch.append({
                "step":     step,
                "system":   s.name,
                "file":     s.file,
                "phases":   s.ecb_summary(),
                "ops":      s.ops_summary(),
                "ordering": s.ordering_summary(),
            })
            step += 1

        if members:
            sketch.append({
                "step":     step,
                "system":   f"[{phase}Playback]",
                "file":     "(ECB system)",
                "phases":   phase,
                "ops":      "(plays all recorded commands)",
                "ordering": f"After all systems writing to {phase}",
            })
            step += 1

    return sketch


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_ordering_table(systems: list, group_filter: str = None):
    active = [s for s in systems if s.is_system]
    if group_filter:
        active = [s for s in active if group_filter in (s.update_in_group or "")]

    if not active:
        print("  (no ISystem/SystemBase declarations found)")
        return

    # Group by update_in_group
    by_group = defaultdict(list)
    for s in active:
        by_group[s.update_in_group or "(unspecified)"].append(s)

    for group in sorted(by_group.keys()):
        members = by_group[group]
        print(f"\n  Group: {group}  ({len(members)} system(s))")
        print(f"  {'System':<40} {'File:Line':<50} {'Ordering':<40} {'ECB phases':<20} {'Ops'}")
        print(f"  {'-'*40} {'-'*50} {'-'*40} {'-'*20} {'-'*30}")
        for s in members:
            floc = f"{s.file}:{s.line}"
            print(f"  {s.name:<40} {floc:<50} {s.ordering_summary():<40} {s.ecb_summary():<20} {s.ops_summary()}")


def print_ambiguities(ambiguities: list):
    if not ambiguities:
        print("  (no ordering ambiguities detected among ECB-using systems)")
        return

    print(f"  {len(ambiguities)} potential ordering ambiguity(ies) found:")
    for sys_a, sys_b, group, shared_phases in ambiguities:
        print(f"\n  ⚠ AMBIGUOUS ORDER: {sys_a.name}  vs  {sys_b.name}")
        print(f"    Group:        {group}")
        print(f"    Shared ECB phases: {', '.join(sorted(shared_phases))}")
        print(f"    {sys_a.name} ops: {sys_a.ops_summary()} @ {sys_a.file}:{sys_a.line}")
        print(f"    {sys_b.name} ops: {sys_b.ops_summary()} @ {sys_b.file}:{sys_b.line}")
        print(f"    → If both systems record DestroyEntity/AppendToBuffer to the same ECB phase,")
        print(f"      the execution order is determined by system creation/registration order,")
        print(f"      which may be non-deterministic. Add explicit [UpdateBefore/After] or")
        print(f"      consolidate to a single lifecycle system.")


def print_frame_sketch(sketch: list):
    if not sketch:
        print("  (no ECB-using systems found for timeline)")
        return

    print(f"  {'Step':<6} {'System':<40} {'ECB Phase':<15} {'Operations':<30} {'Ordering'}")
    print(f"  {'-'*6} {'-'*40} {'-'*15} {'-'*30} {'-'*40}")
    for item in sketch:
        print(f"  {item['step']:<6} {item['system']:<40} {item['phases']:<15} {item['ops']:<30} {item['ordering']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scan a Unity DOTS repo for system execution ordering (read-only)."
    )
    parser.add_argument("repo_root", help="Path to the Unity project root")
    parser.add_argument(
        "--group",
        help="Filter output to systems in a specific group (partial match)",
        default=None,
    )
    parser.add_argument("--verbose", action="store_true", help="Show per-file scan progress")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== System Execution Order & ECB Phase Inventory ===")
    print(f"Repo root   : {root}")
    print(f"Group filter: {args.group or 'none (all)'}")
    print()

    all_systems, total_files = scan_repo(root, args.verbose)
    active = [s for s in all_systems if s.is_system]

    print(f"Scanned {total_files} .cs files")
    print(f"Found {len(all_systems)} class/struct declarations, {len(active)} identified as ISystem/SystemBase")

    print("\n--- System Ordering Table (grouped by UpdateInGroup) ---")
    print_ordering_table(all_systems, args.group)

    print("\n--- Ordering Ambiguity Detection (shared ECB phase, no explicit order) ---")
    ambiguities = find_ordering_ambiguities(all_systems)
    print_ambiguities(ambiguities)

    print("\n--- Approximate Frame Timeline Sketch (ECB-using systems only) ---")
    print("NOTE: This is a heuristic sketch based on UpdateInGroup and ECB phase.")
    print("Verify against actual system group nesting in Unity Editor (SystemGroup window).")
    print()
    sketch = build_frame_sketch(all_systems)
    print_frame_sketch(sketch)

    print("\n=== Investigation Guidance ===")
    if ambiguities:
        print(f"  {len(ambiguities)} ambiguous ordering(s) found.")
        print("  For each ambiguity: check if one system records DestroyEntity and another records")
        print("  AppendToBuffer/SetComponent targeting the same entity in the same ECB phase.")
        print("  If yes: this is the root-cause candidate. Reconstruct the exact frame timeline")
        print("  using Template C in SKILL.md and prove which command executes first.")
    else:
        print("  No ordering ambiguities detected. The execution order issue may be cross-ECB:")
        print("  → Two systems register separate CreateCommandBuffer() calls to the same singleton")
        print("  → Registration order (not system execution order) determines CB playback order")
        print("  → Run find_ecb_producers.py --verbose to identify all CB creation sites")

    print()


if __name__ == "__main__":
    main()
