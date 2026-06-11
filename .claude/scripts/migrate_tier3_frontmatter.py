#!/usr/bin/env python3
"""Phase 3: Add metadata.internal-only + metadata.tier to all 96 Tier 3 DOTS sub-skills.

Rules (architect Phase 3 authorization):
- Add metadata.internal-only: true and metadata.tier: 3 to all 96
- Do NOT add task-categories or platforms (Tier 3 must NOT be SkillHub-discoverable)
- All files already have name + description — do not touch those
- Idempotent: re-running produces 0 changes if already applied

Usage:
  python3 .claude/scripts/migrate_tier3_frontmatter.py          # dry-run
  python3 .claude/scripts/migrate_tier3_frontmatter.py --apply  # apply
"""

import re
import sys
from pathlib import Path

TIER3_ROOT = Path(".claude/skills/unity-dots")
APPLY = "--apply" in sys.argv

METADATA_BLOCK = """\
metadata:
  internal-only: true
  tier: 3"""

changed = 0
skipped = 0
errors = 0

for skill_dir in sorted(TIER3_ROOT.iterdir()):
    if not skill_dir.is_dir():
        continue
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"  WARN: {skill_dir.name}/SKILL.md missing — skip")
        errors += 1
        continue

    raw = skill_md.read_bytes()
    # Strip BOM if present
    text = raw.decode("utf-8")
    bom = text.startswith("﻿")
    if bom:
        text = text[1:]

    # Find frontmatter end marker
    fm_match = re.match(r"^(---\s*\n)(.*?)(\n---)", text, re.DOTALL)
    if not fm_match:
        print(f"  ERROR: {skill_dir.name} — no frontmatter block found")
        errors += 1
        continue

    fm_open = fm_match.group(1)   # "---\n"
    fm_body = fm_match.group(2)   # content between markers
    fm_close = fm_match.group(3)  # "\n---"
    rest = text[fm_match.end():]  # everything after closing ---

    # Already has metadata?
    if "metadata:" in fm_body:
        # Check if tier and internal-only already present
        if "internal-only: true" in fm_body and "tier: 3" in fm_body:
            skipped += 1
            continue
        # Has metadata but incomplete — shouldn't happen in clean state
        print(f"  WARN: {skill_dir.name} has partial metadata — manual review needed")
        errors += 1
        continue

    # Append metadata block to frontmatter body
    new_fm_body = fm_body.rstrip() + "\n" + METADATA_BLOCK
    new_text = fm_open + new_fm_body + fm_close + rest

    if bom:
        new_text = "﻿" + new_text

    if APPLY:
        skill_md.write_text(new_text, encoding="utf-8")
        print(f"  CHANGED: {skill_dir.name}")
    else:
        print(f"  WOULD CHANGE: {skill_dir.name}")
    changed += 1

print()
print(f"{'Applied' if APPLY else 'Dry-run'}: {changed} changed, {skipped} already-done, {errors} errors")
if not APPLY and changed > 0:
    print("Re-run with --apply to write changes.")
